from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bakeoff.game.engine import Game


@dataclass
class Decision:
    """What a player wants to do. The runner decides what is actually executed."""

    chosen_action: str | None
    gated: bool = False
    invalid: bool = False
    error: str | None = None
    questions: dict | None = None
    answers: dict | None = None
    latency_ms: float | None = None
    usage: dict | None = None
    cache_hit: bool = False
    info: dict | None = None

    @property
    def needs_fallback(self) -> bool:
        return self.gated or self.invalid or self.error is not None or self.chosen_action is None


class Player(Protocol):
    name: str

    def reset(self, game: Game, seed: int) -> None: ...
    def act(self, senses: dict) -> Decision: ...
    def observe(self, executed_action: str) -> None: ...
    # Players may also define close() (release resources) and preflight() (a usage-error check
    # run before the CLI creates the run directory); both optional, checked with getattr.
