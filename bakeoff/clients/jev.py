"""Thin Jev client: one system_one request per decision, through the shared cache and cap."""

from __future__ import annotations

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import require_key


class JevClient(PaidClient):
    provider = "jev"
    key_name = "TYPESAFE_API_KEY"
    default_model = "jev-latest"

    def _live(self, senses: dict, questions: dict) -> dict:
        # imported here: listing players or replaying from the cache never loads the SDK
        from typesafe_sdk import Choice, Noul, RetryPolicy, TypeSafeClient, TypeSafeError

        if self._sdk is None:
            # no SDK retries: one spent request is one HTTP request, so the cap is exact
            self._sdk = TypeSafeClient(api_key=require_key(self.key_name), retry=RetryPolicy(max_retries=0))
        kinds = {"choice": Choice, "noul": Noul}
        built = {name: kinds[q["type"]](**{k: v for k, v in q.items() if k != "type"}) for name, q in questions.items()}
        try:
            response = self._sdk.system_one(state=senses, questions=built, model=self.model)
        except TypeSafeError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        return response.model_dump()  # {"model", "usage": {input_tokens, output_tokens}, "answers": {...}}
