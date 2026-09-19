"""Seeded track generator with a guaranteed survivable path. Pure: no I/O, no global randomness."""

from __future__ import annotations

import random
from dataclasses import dataclass

LANES = 12
MAX_ROWS = 300
DIFFICULTY_ROWS = 300  # gap density ramps over this many rows whatever max_rows is, so tracks are prefix-stable
LOOKAHEAD = 6
RUNWAY_ROWS = 4  # rows 0..RUNWAY_ROWS are all floor so nobody dies before seeing a gap
START_GAP_RATE = 0.04  # chance that a lane starts a gap run, at row 0
END_GAP_RATE = 0.16  # the same chance at row max_rows
MAX_GAP_WIDTH = 3
_PATH_MOVES = ("stay", "stay", "stay", "stay", "left", "left", "right", "right", "jump")


@dataclass(frozen=True)
class Track:
    seed: int
    lanes: int
    max_rows: int
    gaps: tuple[tuple[int, ...], ...]  # gaps[row] = sorted lanes that are gaps in that row

    def is_gap(self, row: int, lane: int) -> bool:
        return row < len(self.gaps) and (lane % self.lanes) in self.gaps[row]

    def to_json(self) -> dict:
        return {"seed": self.seed, "lanes": self.lanes, "max_rows": self.max_rows,
                "gaps": [list(row) for row in self.gaps]}


def start_lane(lanes: int = LANES) -> int:
    return lanes // 2


def _safe_path(rng: random.Random, lanes: int, length: int) -> set[tuple[int, int]]:
    """Tiles of one legal walk from the start to beyond the last row; these stay floor."""
    row, lane = 0, start_lane(lanes)
    tiles = {(row, lane)}
    while row < length:
        move = rng.choice(_PATH_MOVES)
        if move == "jump":
            row += 2
        else:
            row += 1
            lane = (lane + {"left": -1, "right": 1, "stay": 0}[move]) % lanes
        tiles.add((row, lane))
    return tiles


def generate_track(seed: int, lanes: int = LANES, max_rows: int = MAX_ROWS) -> Track:
    # Two independent streams (string seeds hash the same in every process): a longer track
    # extends the path without shifting the gap scatter, so any max_rows plays a prefix.
    path_rng, gap_rng = random.Random(f"{seed}:path"), random.Random(f"{seed}:gaps")
    length = max_rows + LOOKAHEAD + 2  # so look-ahead and a last jump never leave the track
    protected = _safe_path(path_rng, lanes, length)
    gaps: list[tuple[int, ...]] = []
    for row in range(length):
        row_gaps: set[int] = set()
        if row > RUNWAY_ROWS:
            progress = min(1.0, row / DIFFICULTY_ROWS)
            rate = START_GAP_RATE + (END_GAP_RATE - START_GAP_RATE) * progress
            widest = 1 + min(MAX_GAP_WIDTH - 1, int(progress * MAX_GAP_WIDTH))
            for lane in range(lanes):
                if gap_rng.random() < rate:
                    width = gap_rng.randint(1, widest)
                    row_gaps.update((lane + i) % lanes for i in range(width))
        gaps.append(tuple(sorted(l for l in row_gaps if (row, l) not in protected)))
    return Track(seed=seed, lanes=lanes, max_rows=max_rows, gaps=tuple(gaps))


def survivable(track: Track) -> bool:
    """True if some legal action sequence reaches max_rows. Independent check of the generator."""
    reachable = {0: {start_lane(track.lanes)}}
    for row in range(track.max_rows):
        for lane in reachable.get(row, ()):
            for target_row, target_lane in ((row + 1, lane - 1), (row + 1, lane), (row + 1, lane + 1), (row + 2, lane)):
                if not track.is_gap(target_row, target_lane):
                    reachable.setdefault(target_row, set()).add(target_lane % track.lanes)
    return bool(reachable.get(track.max_rows) or reachable.get(track.max_rows + 1))
