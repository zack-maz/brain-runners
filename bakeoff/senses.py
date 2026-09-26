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
# everything that reads senses (the step1 set's questions, the report's truth for them).
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
    asked of a logged record. It is the truth of the step1 set's questions, which ask about the senses;
    the engine differs only past the finish line, where a gap no longer kills."""
    ahead, offset = LANDS[action]
    return offset in senses["ahead"][ahead]["gaps_relative"]


def trapped(senses: dict, action: str) -> bool:
    """After `action`, would every next move land on a gap the senses show? (The step2 question sets
    ask this; it needs two more rows in view beyond the landing row.)"""
    ahead, offset = LANDS[action]
    if ahead + 2 >= len(senses["ahead"]):
        raise IndexError(f"the view ends before the move after `{action}`")
    return all(offset + shift in senses["ahead"][ahead + step]["gaps_relative"]
               for step, shift in ((1, -1), (1, 0), (1, 1), (2, 0)))


def tile_id(row: int, offset: int) -> str:
    """The question id of one visible tile: `tile_r2_c` is the runner's lane two rows ahead, `tile_r1_l3`
    three lanes to its left one row ahead, `tile_r4_r1` one lane to its right four rows ahead."""
    side = "c" if offset == 0 else ("l" if offset < 0 else "r") + str(abs(offset))
    return f"tile_r{row}_{side}"


def parse_tile_id(noul_id: str) -> tuple[int, int] | None:
    """(row, offset) of a `tile_id`, or None if `noul_id` is not one."""
    parts = noul_id.split("_")
    if len(parts) != 3 or parts[0] != "tile" or not parts[1].startswith("r") or not parts[1][1:].isdigit():
        return None
    side = parts[2]
    if side == "c":
        return int(parts[1][1:]), 0
    if side[:1] in ("l", "r") and side[1:].isdigit() and side[1:] != "0":
        return int(parts[1][1:]), int(side[1:]) * (-1 if side[0] == "l" else 1)
    return None


def truth_of(senses: dict, noul_id: str) -> bool | None:
    """The truth of a question-set Noul, read from the senses alone (so the report can score any record):
    `gap_<action>`, `trapped_<action>` and `tile_r<row>_<side>`. None for any other id, or for a tile or a
    follow-up the senses do not reach."""
    kind, _, rest = noul_id.partition("_")
    if kind in ("gap", "trapped") and rest in LANDS:
        try:
            return lands_on_gap(senses, rest) if kind == "gap" else trapped(senses, rest)
        except IndexError:
            return None
    tile = parse_tile_id(noul_id)
    if tile is not None and 1 <= tile[0] <= len(senses["ahead"]):
        return tile[1] in senses["ahead"][tile[0] - 1]["gaps_relative"]
    return None
