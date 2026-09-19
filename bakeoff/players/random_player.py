from __future__ import annotations

import random

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.players.base import Decision


class RandomPlayer:
    name = "random"

    def __init__(self) -> None:
        self._rng = random.Random("random:0")

    def reset(self, game: Game, seed: int) -> None:
        self._rng = random.Random(f"random:{seed}")  # not the track's integer seed

    def act(self, senses: dict) -> Decision:
        return Decision(self._rng.choice(ACTIONS))

    def observe(self, executed_action: str) -> None:
        pass
