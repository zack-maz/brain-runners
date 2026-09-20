"""What every paid request goes through: the disk cache first, then the hard cap, then the live call."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from bakeoff.clients.keys import require_key
from bakeoff.errors import BudgetExhausted

DEFAULT_CACHE_DIR = Path(".cache") / "responses"  # git-ignored


class ProviderError(Exception):
    """The provider failed (network, HTTP status, unreadable response). The player logs it as the
    step's `error` and the runner executes `stay`. Anything else that goes wrong is our bug and
    is left to end the run."""


def cache_key(provider: str, model: str, senses: dict, questions: dict) -> str:
    """sha256 of provider, model, senses and questions. `questions` is everything else that shapes
    the answer (Jev's questions; the LLM's system prompt and schema), so editing a prompt can never
    be answered from a response to the old one."""
    blob = json.dumps({"provider": provider, "model": model, "senses": senses, "questions": questions},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


class DiskCache:
    """One JSON file per response, <root>/<provider>/<first two hex digits>/<key>.json. The file
    keeps the request next to the response, so a cached answer can be audited by hand."""

    def __init__(self, root: Path | str = DEFAULT_CACHE_DIR):
        self.root = Path(root)

    def _path(self, provider: str, key: str) -> Path:
        return self.root / provider / key[:2] / f"{key}.json"

    def get(self, provider: str, key: str) -> dict | None:
        try:
            return json.loads(self._path(provider, key).read_text())["payload"]
        except (OSError, ValueError, KeyError, TypeError):
            return None  # absent or damaged: ask again

    def put(self, provider: str, key: str, request: dict, payload: dict) -> None:
        path = self._path(provider, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(f".{os.getpid()}.partial")
        partial.write_text(json.dumps({"request": request, "payload": payload}))
        os.replace(partial, path)  # a run killed mid-write never leaves half a response behind


class RequestBudget:
    """The hard cap on live requests. One per paid player per run."""

    def __init__(self, max_requests: int):
        if max_requests < 0:
            raise ValueError(f"max_requests must not be negative: {max_requests}")
        self.max_requests = max_requests
        self.used = 0

    def spend(self) -> None:
        if self.used >= self.max_requests:
            raise BudgetExhausted(f"request cap of {self.max_requests} reached")
        self.used += 1


@dataclass
class Reply:
    payload: dict
    latency_ms: float | None  # None on a cache hit: the report counts a latency as a paid request
    cache_hit: bool


def cached_request(cache: DiskCache, budget: RequestBudget, provider: str, model: str, senses: dict,
                   questions: dict, live: Callable[[], dict]) -> Reply:
    """`live` makes the one real request and returns a JSON-able payload, or raises ProviderError."""
    key = cache_key(provider, model, senses, questions)
    payload = cache.get(provider, key)
    if payload is not None:
        return Reply(payload, latency_ms=None, cache_hit=True)
    budget.spend()  # before the call: a request that fails may still have been billed
    start = time.perf_counter()
    payload = live()
    latency_ms = (time.perf_counter() - start) * 1000.0
    cache.put(provider, key, {"provider": provider, "model": model, "senses": senses, "questions": questions},
              payload)
    return Reply(payload, latency_ms=latency_ms, cache_hit=False)


class PaidClient:
    """Base of the two thin clients. A subclass sets `provider`, `key_name` and `default_model` and
    implements _live(). `sdk` is the provider's SDK client: tests inject a fake, a real one is built
    on the first live request, so a run answered entirely from the cache needs no key."""

    provider: str
    key_name: str
    default_model: str

    def __init__(self, cache: DiskCache, budget: RequestBudget, model: str | None = None, sdk=None):
        self.cache, self.budget, self.model = cache, budget, model or self.default_model
        self._sdk = sdk
        self._owns_sdk = sdk is None

    def preflight(self) -> None:
        if self._owns_sdk and self.budget.max_requests > 0:
            require_key(self.key_name)

    def ask(self, senses: dict, questions: dict) -> Reply:
        return cached_request(self.cache, self.budget, self.provider, self.model, senses, questions,
                              lambda: self._live(senses, questions))

    def _live(self, senses: dict, questions: dict) -> dict:
        raise NotImplementedError

    def close(self) -> None:
        sdk, self._sdk = self._sdk, None
        if sdk is not None and self._owns_sdk:
            sdk.close()
