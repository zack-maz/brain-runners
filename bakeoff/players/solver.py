"""Reference player: scripted search over the visible rows. Not a contestant."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision
from bakeoff.senses import WINDOW

_MOVES = (("stay", 1, 0), ("left", 1, -1), ("right", 1, 1), ("jump", 2, 0))  # tie-break order


def solve(senses: dict) -> str:
    """First action of the longest sequence known to survive. Tiles outside the visible
    window count as gaps, so the solver only trusts what every contestant can see."""
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

    best_action, best_depth = "stay", -1
    for action, advance, shift in _MOVES:
        reached = depth(advance, shift) if safe(advance, shift) else 0
        if reached > best_depth:
            best_action, best_depth = action, reached
    return best_action


class SolverPlayer:
    name = "solver"

    def reset(self, game: Game, seed: int) -> None:
        pass

    def act(self, senses: dict) -> Decision:
        return Decision(solve(senses))

    def observe(self, executed_action: str) -> None:
        pass
