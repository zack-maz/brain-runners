"""Thin Anthropic client: one Messages request per decision, through the shared cache and cap."""

from __future__ import annotations

import json

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import require_key

TIMEOUT_S = 60.0  # the SDK default is 10 minutes; a decision that slow is an error


class LlmClient(PaidClient):
    provider = "llm"
    key_name = "ANTHROPIC_API_KEY"
    default_model = "claude-haiku-4-5-20251001"

    def _live(self, senses: dict, questions: dict) -> dict:
        import anthropic  # imported here: listing players or replaying from the cache never loads the SDK

        if self._sdk is None:
            # no SDK retries: one spent request is one HTTP request, so the cap is exact
            self._sdk = anthropic.Anthropic(api_key=require_key(self.key_name), max_retries=0, timeout=TIMEOUT_S)
        try:
            message = self._sdk.messages.create(
                model=self.model, max_tokens=questions["max_tokens"], system=questions["system"],
                messages=[{"role": "user", "content": json.dumps(senses)}],
                output_config={"format": {"type": "json_schema", "schema": questions["schema"]}})
        except anthropic.APIError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        text = "".join(block.text for block in message.content if block.type == "text")
        return {"model": message.model, "stop_reason": message.stop_reason, "text": text,
                "usage": {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens}}
