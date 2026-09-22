"""Thin GLM client (Zhipu / Z.ai, OpenAI-compatible): one chat completion per decision, through the shared cache
and cap. The standard library makes the request, so there is no SDK retry behind our back and one spent request is
one HTTP request. GLM Flash is a free tier: its price is 0, not unknown (docs/COSTS.md)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from dotenv import dotenv_values

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import ENV_FILE, require_key

TIMEOUT_S = 60.0
# The free tier queues: a share of requests come back "temporarily overloaded" (HTTP 429) or time out. One retry
# after a pause, and the retry spends from the cap like any other request, so the cap is still exactly the number
# of HTTP requests a run may make. Claude Haiku and Jev keep no retries: they are metered, not queued.
RETRIES = 3
RETRY_PAUSES_S = (5.0, 20.0, 60.0)  # the free tier throttles in bursts: back off rather than burn the cap
RETRYABLE = ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "TimeoutError", "URLError")
# the international endpoint; a mainland account reads GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4 from .env
DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"


def base_url() -> str:
    setting = os.environ.get("GLM_BASE_URL") or dotenv_values(ENV_FILE).get("GLM_BASE_URL") or ""
    return setting.strip().rstrip("/") or DEFAULT_BASE_URL


class HttpTransport:
    """One POST per call. Never logs or raises the key: a failure carries the status and the body only."""

    def __init__(self, url: str, api_key: str, timeout_s: float = TIMEOUT_S):
        self._url, self._key, self._timeout_s = url, api_key, timeout_s

    def post(self, body: dict) -> dict:
        request = urllib.request.Request(
            self._url, data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._key}"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}") from e
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e

    def close(self) -> None:
        pass


class GlmClient(PaidClient):
    provider = "glm"
    key_name = "ZHIPU_API_KEY"
    default_model = "glm-4.5-flash"
    # GLM-4.5 thinks by default and its thoughts eat the token budget: the first smoke test came back empty and cut
    # off. Claude Haiku answers these questions without thinking, so neither model thinks. Asked only for "an
    # object", GLM invents a wrapper ({"answer": {...}}), so it gets the same JSON schema Claude Haiku gets. These
    # are part of the cache key, so answers made another way are never replayed; `response_format` names the shape
    # here, and the request below carries the set's own schema.
    request_options = {"temperature": 0, "response_format": "json_schema", "thinking": {"type": "disabled"}}

    def _live(self, senses: dict, questions: dict) -> dict:
        if self._sdk is None:
            self._sdk = HttpTransport(base_url() + "/chat/completions", require_key(self.key_name))
        for attempt in range(RETRIES + 1):
            try:
                return self._once(senses, questions, attempt + 1)
            except ProviderError as e:
                if attempt == RETRIES or not str(e).startswith(RETRYABLE):
                    raise
                self.budget.spend()  # the retry is a request of its own: the cap counts HTTP requests
                time.sleep(RETRY_PAUSES_S[min(attempt, len(RETRY_PAUSES_S) - 1)])
        raise AssertionError("unreachable")

    def _once(self, senses: dict, questions: dict, attempt: int) -> dict:
        data = self._sdk.post({
            "model": self.model,
            "messages": [{"role": "system", "content": questions["system"]},
                         {"role": "user", "content": json.dumps(senses)}],
            "max_tokens": questions["max_tokens"],
            "temperature": self.request_options["temperature"], "thinking": self.request_options["thinking"],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "answers", "strict": True, "schema": questions["schema"]}}})
        try:
            choice = data["choices"][0]
            text, finish = choice["message"]["content"], choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"unreadable reply: {json.dumps(data)[:200]}") from e
        usage = data.get("usage") or {}
        thoughts = (choice["message"].get("reasoning_content") or "") if isinstance(choice.get("message"), dict) else ""
        return {"model": data.get("model") or self.model, "attempts": attempt,
                # nothing should appear here while thinking is off; logged, never parsed, if it does
                **({"reasoning_content": thoughts} if thoughts else {}),
                # the set players read `end_turn` for a complete answer, as Anthropic names it
                "stop_reason": "end_turn" if finish == "stop" else finish,
                "finish_reason": finish, "text": text,
                "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                          "output_tokens": usage.get("completion_tokens", 0)}}
