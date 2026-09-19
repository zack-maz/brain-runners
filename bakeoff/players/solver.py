"""Reference player: scripted search over the visible rows. Not a contestant."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision
from bakeoff.senses import WINDOW

_MOVES = (("stay", 1, 0), ("left", 1, -1), ("right", 1, 1), ("jump", 2, 0))  # tie-break order


def solve_depths(senses: dict) -> dict[str, int]:
    """For each action, the furthest visible row its best continuation reaches (0 if the first
    move is not known-safe). Tiles outside the visible window count as gaps, so the solver only
    trusts what every contestant can see."""
    gaps = {(e["row"], o) for e in senses["ahead"] for o in e["gaps_relative"]}
    horizon = len(senses["ahead"])

    def safe(row: int, offset: int) -> bool:
        return row <= horizon and abs(offset) <= WINDOW and (row, offset) not in gaps

    def depth(row: int, offset: int) -> int:
        best = row
        for _, advance, shift in _MOVES:
            if safe(row + advance, offset + shift):
                best = max(best, depth(row + advance, offset + shift))
                if best >= horizon:
                    break
        return best

    return {action: depth(advance, shift) if safe(advance, shift) else 0
            for action, advance, shift in _MOVES}


def solve(senses: dict) -> str:
    """First action (in tie-break order) of the longest sequence known to survive."""
    depths = solve_depths(senses)
    return max(depths, key=depths.get)  # max returns the first maximum


class SolverPlayer:
    name = "solver"

    def reset(self, game: Game, seed: int) -> None:
        pass

    def act(self, senses: dict) -> Decision:
        return Decision(solve(senses))

    def observe(self, executed_action: str) -> None:
        pass
