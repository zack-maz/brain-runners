from __future__ import annotations

from typing import Callable

from bakeoff.clients.core import RequestBudget, UncappedBudget
from bakeoff.players.always_jump import AlwaysJumpPlayer
from bakeoff.players.base import Player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.fly2 import Fly2Player
from bakeoff.players.glm import GlmPlayer
from bakeoff.players.jev import JevPlayer
from bakeoff.players.jev_step1 import JevStep1Player
from bakeoff.players.haiku import HaikuPlayer
from bakeoff.players.names import RENAMED, canonical
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.set_players import SET_PLAYERS
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
    "fly2": Fly2Player,
    "jev_plain": JevPlayer, "jev_step1": JevStep1Player, "haiku_plain": HaikuPlayer, "glm_plain": GlmPlayer,
    **{player.name: player for player in SET_PLAYERS}}
# these take cache= and budget=; without a budget they can only replay the cache
PAID = ("jev_plain", "jev_step1", "haiku_plain", "glm_plain", *(player.name for player in SET_PLAYERS))
# the paid players that play without a cap. None since decision 58: whoever runs it sets every paid player's cap,
# Jev's included, because a stranger's TypeSafe key may be billed (decision 50 had Jev uncapped, when its requests
# cost the one user nothing). The machinery stays, so an uncapped player is one name away.
UNCAPPED: tuple[str, ...] = ()


def budget_of(name: str, max_requests: int) -> RequestBudget:
    """A paid player's budget: the command's cap, or none for a player in UNCAPPED (none since decision 58)."""
    return UncappedBudget() if name in UNCAPPED else RequestBudget(max_requests)


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap).
    An old name (`llm*`, decision 39; `jev`, `jev_composed` and the like, decision 44) still works and makes the
    player it was renamed to."""
    name = canonical(name)
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
