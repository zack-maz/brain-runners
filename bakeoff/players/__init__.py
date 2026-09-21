from __future__ import annotations

from typing import Callable

from bakeoff.players.always_jump import AlwaysJumpPlayer
from bakeoff.players.base import Player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.jev import JevPlayer
from bakeoff.players.jev_composed import JevComposedPlayer
from bakeoff.players.llm import LlmPlayer
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
    "jev": JevPlayer, "jev_composed": JevComposedPlayer, "llm": LlmPlayer}
PAID = ("jev", "jev_composed", "llm")  # these take cache= and budget=; without a budget they can only replay the cache


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
