from __future__ import annotations

from typing import Callable

from bakeoff.players.always_jump import AlwaysJumpPlayer
from bakeoff.players.base import Player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.jev import JevPlayer
from bakeoff.players.jev_composed import JevComposedPlayer
from bakeoff.players.llm import LlmPlayer
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.set_players import SET_PLAYERS
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
    "jev": JevPlayer, "jev_composed": JevComposedPlayer, "llm": LlmPlayer,
    **{player.name: player for player in SET_PLAYERS}}
# these take cache= and budget=; without a budget they can only replay the cache
PAID = ("jev", "jev_composed", "llm", *(player.name for player in SET_PLAYERS))


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
