"""Engine state -> JSON senses and -> looming rates. One source of truth, two encodings. Pure."""

from __future__ import annotations

import math

from bakeoff.game.engine import Game

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
# Where each action lands, as (index into `ahead`, lane offset): the rule of the game, written once for
# everything that reads senses (the composed Jev's questions, the report's truth for them).
LANDS = {"left": (0, -1), "stay": (0, 0), "right": (0, 1), "jump": (1, 0)}


def compute_senses(game: Game) -> dict:
    # what the game version shows: `lookahead` rows, `window` lanes either side of the runner
    lookahead, window = game.track.rules.lookahead, game.track.rules.window
    ahead = []
    for distance in range(1, lookahead + 1):
        offsets = [o for o in range(-window, window + 1) if game.track.is_gap(game.row + distance, game.lane + o)]
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


def lands_on_gap(senses: dict, action: str) -> bool:
    """Does `action` land on a tile the senses show as a gap? Read from the senses alone, so it can be
    asked of a logged record. It is the truth of the composed Jev's questions, which ask about the senses;
    the engine differs only past the finish line, where a gap no longer kills."""
    ahead, offset = LANDS[action]
    return offset in senses["ahead"][ahead]["gaps_relative"]
