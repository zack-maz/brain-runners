from __future__ import annotations

from typing import Callable

from bakeoff.players.base import Player
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {"random": RandomPlayer, "solver": SolverPlayer}


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
