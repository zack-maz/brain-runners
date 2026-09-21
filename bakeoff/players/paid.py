"""What the two paid players share: one cached, capped request per row; provider errors become a
logged `error` (the runner then executes `stay`); BudgetExhausted is left to end the run."""

from __future__ import annotations

from bakeoff.clients.core import DiskCache, PaidClient, ProviderError, RequestBudget
from bakeoff.game.engine import Game
from bakeoff.players.base import Decision


class PaidPlayer:
    name: str
    client_class: type[PaidClient]
    questions: dict  # plain JSON: logged in every record and part of the cache key

    def __init__(self, cache: DiskCache | None = None, budget: RequestBudget | None = None,
                 model: str | None = None, sdk=None):
        # Without a budget the cap is 0: the player can only replay the cache, never spend.
        self.budget = budget if budget is not None else RequestBudget(0)
        self.client = self.client_class(cache if cache is not None else DiskCache(), self.budget, model, sdk)
        self.model = self.client.model

    def preflight(self) -> None:
        """Called by Runner.run before the run directory exists: a live run without its key is a usage error."""
        self.client.preflight()

    def reset(self, game: Game, seed: int) -> None:
        pass

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        """The provider's payload -> (chosen action, invalid, answers to log)."""
        raise NotImplementedError

    def act(self, senses: dict) -> Decision:
        try:
            reply = self.client.ask(senses, self.questions)
        except ProviderError as e:
            return Decision(None, error=str(e), questions=self.questions)
        action, invalid, answers = self.read(reply.payload)
        return Decision(action, invalid=invalid, questions=self.questions, answers=answers,
                        latency_ms=reply.latency_ms, usage=reply.payload.get("usage"), cache_hit=reply.cache_hit,
                        info={"model": reply.payload.get("model")})

    def observe(self, executed_action: str) -> None:
        pass

    def close(self) -> None:
        self.client.close()
