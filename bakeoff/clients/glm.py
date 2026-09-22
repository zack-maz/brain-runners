"""Thin GLM client (Zhipu / Z.ai, OpenAI-compatible): one chat completion per decision, through the shared cache
and cap. The standard library makes the request, so there is no SDK retry behind our back and one spent request is
one HTTP request. GLM Flash is a free tier: its price is 0, not unknown (docs/COSTS.md)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import dotenv_values

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import ENV_FILE, require_key

TIMEOUT_S = 60.0
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

    def _live(self, senses: dict, questions: dict) -> dict:
        if self._sdk is None:
            self._sdk = HttpTransport(base_url() + "/chat/completions", require_key(self.key_name))
        data = self._sdk.post({
            "model": self.model,
            "messages": [{"role": "system", "content": questions["system"]},
                         {"role": "user", "content": json.dumps(senses)}],
            "max_tokens": questions["max_tokens"], "temperature": 0,
            "response_format": {"type": "json_object"}})
        try:
            choice = data["choices"][0]
            text, finish = choice["message"]["content"], choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"unreadable reply: {json.dumps(data)[:200]}") from e
        usage = data.get("usage") or {}
        return {"model": data.get("model") or self.model,
                # the set players read `end_turn` for a complete answer, as Anthropic names it
                "stop_reason": "end_turn" if finish == "stop" else finish,
                "finish_reason": finish, "text": text,
                "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                          "output_tokens": usage.get("completion_tokens", 0)}}
