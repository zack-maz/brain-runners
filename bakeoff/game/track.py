"""Seeded track generator with a guaranteed survivable path. Pure: no I/O, no global randomness."""

from __future__ import annotations

import random
from dataclasses import dataclass

from bakeoff.game.rules import DEFAULT, RULES, Rules, resolve

_PATH_MOVES = ("stay", "stay", "stay", "stay", "left", "left", "right", "right", "jump")


@dataclass(frozen=True)
class Track:
    seed: int
    rules: Rules
    gaps: tuple[tuple[int, ...], ...]  # gaps[row] = sorted lanes that are gaps in that row

    @property
    def lanes(self) -> int:
        return self.rules.lanes

    @property
    def max_rows(self) -> int:
        return self.rules.max_rows

    def is_gap(self, row: int, lane: int) -> bool:
        return row < len(self.gaps) and (lane % self.lanes) in self.gaps[row]

    def to_json(self) -> dict:
        return {"seed": self.seed, "lanes": self.lanes, "max_rows": self.max_rows,
                "gaps": [list(row) for row in self.gaps]}


def start_lane(lanes: int = RULES[DEFAULT].lanes) -> int:
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


def generate_track(seed: int, rules: Rules | None = None, max_rows: int | None = None) -> Track:
    """The track of `seed` in a game version (default: the current one). `max_rows` shortens or
    lengthens it; the rows it shares with the full track are the same."""
    rules = resolve(rules, max_rows)
    # Two independent streams (string seeds hash the same in every process): a longer track
    # extends the path without shifting the gap scatter, so any max_rows plays a prefix.
    path_rng, gap_rng = random.Random(f"{seed}:path"), random.Random(f"{seed}:gaps")
    length = rules.max_rows + rules.lookahead + 2  # so look-ahead and a last jump never leave the track
    protected = _safe_path(path_rng, rules.lanes, length)
    gaps: list[tuple[int, ...]] = []
    for row in range(length):
        row_gaps: set[int] = set()
        if row > rules.runway_rows:
            progress = min(1.0, row / rules.difficulty_rows)
            rate = rules.start_gap_rate + (rules.end_gap_rate - rules.start_gap_rate) * progress
            widest = 1 + min(rules.max_gap_width - 1, int(progress * rules.max_gap_width))
            for lane in range(rules.lanes):
                if gap_rng.random() < rate:
                    width = gap_rng.randint(1, widest)
                    row_gaps.update((lane + i) % rules.lanes for i in range(width))
        gaps.append(tuple(sorted(l for l in row_gaps if (row, l) not in protected)))
    return Track(seed=seed, rules=rules, gaps=tuple(gaps))


def survivable(track: Track) -> bool:
    """True if some legal action sequence reaches max_rows. Independent check of the generator."""
    reachable = {0: {start_lane(track.lanes)}}
    for row in range(track.max_rows):
        for lane in reachable.get(row, ()):
            for target_row, target_lane in ((row + 1, lane - 1), (row + 1, lane), (row + 1, lane + 1), (row + 2, lane)):
                if target_row > track.max_rows or not track.is_gap(target_row, target_lane):
                    reachable.setdefault(target_row, set()).add(target_lane % track.lanes)
    return bool(reachable.get(track.max_rows) or reachable.get(track.max_rows + 1))
