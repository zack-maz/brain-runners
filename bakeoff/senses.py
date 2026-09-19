"""Engine state -> JSON senses and -> looming rates. One source of truth, two encodings. Pure."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.game.track import LOOKAHEAD

WINDOW = 3  # gaps are visible up to this many lanes either side of the runner
MAX_HZ = 250.0
# PROVISIONAL and OURS, not the fly's biology: a gap `row` rows ahead adds LOOMING_GAIN_HZ / row.
# Phase 2 fixes the final weighting on practice seeds.
LOOMING_GAIN_HZ = 100.0
ACTION_DESCRIPTIONS = {
    "left": "move one lane left", "right": "move one lane right",
    "jump": "clear the next row, land on the one after", "stay": "run straight",
}


def compute_senses(game: Game) -> dict:
    ahead = []
    for distance in range(1, LOOKAHEAD + 1):
        offsets = [o for o in range(-WINDOW, WINDOW + 1) if game.track.is_gap(game.row + distance, game.lane + o)]
        ahead.append({"row": distance, "gaps_relative": offsets})
    return {"lane": game.lane, "lanes": game.track.lanes, "rows_survived": game.rows_survived,
            "ahead": ahead, "actions": dict(ACTION_DESCRIPTIONS)}


def looming_rates(senses: dict) -> tuple[float, float]:
    left = right = 0.0
    for entry in senses["ahead"]:
        intensity = LOOMING_GAIN_HZ / entry["row"]
        for offset in entry["gaps_relative"]:
            if offset <= 0:
                left += intensity
            if offset >= 0:
                right += intensity
    return min(left, MAX_HZ), min(right, MAX_HZ)


def ground_truth(game: Game) -> dict:
    return {"gap_ahead": game.track.is_gap(game.row + 1, game.lane),
            "left_safe": not game.track.is_gap(game.row + 1, game.lane - 1)}
