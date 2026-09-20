"""Engine state -> JSON senses and -> looming rates. One source of truth, two encodings. Pure."""

from __future__ import annotations

import math

from bakeoff.game.engine import Game
from bakeoff.game.track import LOOKAHEAD

WINDOW = 3  # gaps are visible up to this many lanes either side of the runner
MAX_HZ = 250.0
# OURS, not the fly's biology: a gap `row` rows ahead adds LOOMING_GAIN_HZ / row ** LOOMING_FALLOFF
# to its eye; each eye's sum is capped at MAX_HZ and rounded to the nearest LOOMING_STEP_HZ, so
# an eye has 11 input levels and the measured response surface covers every input the fly can get.
# Gain and falloff were fixed on practice seeds 1000-1199 (calibration/REPORT.md); do not retune.
LOOMING_GAIN_HZ = 250.0
LOOMING_FALLOFF = 3.0
LOOMING_STEP_HZ = 25.0
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


def _to_level(hz: float) -> float:
    return math.floor(min(hz, MAX_HZ) / LOOMING_STEP_HZ + 0.5) * LOOMING_STEP_HZ


def looming_rates(senses: dict, gain_hz: float = LOOMING_GAIN_HZ,
                  falloff: float = LOOMING_FALLOFF) -> tuple[float, float]:
    left = right = 0.0
    for entry in senses["ahead"]:
        intensity = gain_hz / entry["row"] ** falloff
        for offset in entry["gaps_relative"]:
            if offset <= 0:
                left += intensity
            if offset >= 0:
                right += intensity
    return _to_level(left), _to_level(right)


def ground_truth(game: Game) -> dict:
    return {"gap_ahead": game.track.is_gap(game.row + 1, game.lane),
            "left_safe": not game.track.is_gap(game.row + 1, game.lane - 1)}
