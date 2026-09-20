"""Second floor: a jump lands on only every other row, so always jumping outlives `random`.
A jump-heavy fly has to beat this, not just `random`."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision


class AlwaysJumpPlayer:
    name = "always_jump"

    def reset(self, game: Game, seed: int) -> None:
        pass

    def act(self, senses: dict) -> Decision:
        return Decision("jump")

    def observe(self, executed_action: str) -> None:
        pass
