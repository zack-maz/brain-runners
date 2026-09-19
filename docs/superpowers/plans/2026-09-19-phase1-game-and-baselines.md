# Phase 1: Tunnel Run Game and Baselines — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure, seeded Tunnel Run game with senses, a `random` and a `solver` player, a runner that streams a JSONL step log, a scoreboard report and a CLI. No API keys, no fly.

**Architecture:** Python package `bakeoff/` at the repo root. `game/track.py` and `game/engine.py` are pure; `senses.py` turns engine state into the JSON senses and the two looming rates; players implement one `Player` protocol and return a `Decision`; `runner.py` plays players × seeds, applies the fallback rule and writes one JSONL file per player plus `meta.json`; `report.py` reads those files only. The runner, report, `Decision` and CLI are adapted from the reviewed harness in `../testing/glassbox/` (`zack-maz/jev-testing` PR #1).

**Tech Stack:** Python 3.13, `uv`, `pytest`. No runtime dependencies in this phase.

**Spec:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (binding). Background: `docs/DECISIONS.md`.

**Branch:** `phase1-game-and-baselines` (already created; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv add`, `uv run pytest`, `uv run python -m bakeoff`. Python 3.13. Never call `pip` or bare `python`.
- TDD: write the failing test, watch it fail, then implement. No test touches the network.
- Every shell command that mentions `.env` is blocked by a guard. Nothing in this phase needs keys; do not create, read or mention that file.
- Game constants, verbatim from the spec: **12 lanes** (lane 11 wraps to lane 0), actions `left`, `right`, `jump`, `stay`, look-ahead **6 rows**, `max_rows` default **300**, gaps visible within **±3 lanes**, looming rates **0–250 Hz**.
- The engine and track generator are pure: no I/O, no randomness outside `random.Random(seed)`.
- Fallback rule: when a decision is gated, invalid, errored or missing, the executed action is `stay`, never the solver's move. Every record logs `chosen_action`, `executed_action` and `solver_action` separately.
- Honesty rule: anything that is our mapping rather than fly biology is labelled as such. In this phase that is the looming weighting in `bakeoff/senses.py`; it is provisional and its comment must say so.
- Every code block below was run and passes as written (72 tests). If a test fails, suspect a transcription slip before redesigning. Do not change constants (`START_GAP_RATE`, `END_GAP_RATE`, `_PATH_MOVES`, …): tracks are part of the tournament contract and later tests depend on the exact tracks the seeds produce.
- Commit after every task with the message given. End each commit message with the two attribution lines the session provides.

## Decisions this plan makes beyond the spec

1. **Score.** `rows_survived` is the index of the last row cleared, capped at `max_rows`. A fatal jump still cleared the row it flew over, so it scores one more than a fatal step from the same row.
2. **Three record keys beyond the spec's step record:** `finished` (reached `max_rows` alive), `death_cause` (`ran_into_gap` for `stay`, `jumped_into_gap` for `jump`, `dodged_into_gap` for `left`/`right`, else `null`) and `track` (full track in the first record of each seed, else `null`). The report needs the first two to tell a death from a cut-off run without reading anything but the files.
3. **The solver sees only what contestants see.** Tiles outside the ±3-lane, 6-row window count as gaps. It is a reference under the same partial view, not the optimum: measured on seeds 0–199 it finishes 192 tracks and its worst run is 237 rows (rare late dead ends it cannot see into).
4. **Difficulty numbers** (measured, seeds 0–199): gap fraction about 6 % / 12 % / 24 % in the first / middle / last hundred rows; `random` averages about 29 rows, always-`stay` about 26. A crude reflex stand-in using the provisional looming rates averaged about 99, so there is room between the floor and the reference for the fly to land in.
5. **Provisional looming weighting:** each visible gap `row` rows ahead adds `100 / row` Hz to its eye (both eyes for the runner's own lane), capped at 250 Hz. Phase 2 fixes the final weighting on practice seeds.
6. **`--seed-start`** on the CLI so that phase 2's practice seeds cannot overlap tournament seeds.
7. **Deferred to phase 3, where the data first exists:** Noul calibration (Brier) and cost per run in the report; model ids in `meta.json`. Fly thresholds in `meta.json` arrive in phase 2. `BudgetExhausted` is defined now because the runner's status handling is built and tested here.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml`, `.python-version`, `uv.lock` | Project, pytest config, `slow` and `live` markers | 1 |
| `bakeoff/__init__.py`, `bakeoff/game/__init__.py` | Empty package markers | 1 |
| `bakeoff/game/track.py` | `Track`, `generate_track`, `survivable`, game constants | 1 |
| `tests/conftest.py` | `make_track` fixture for hand-made tracks | 1 |
| `bakeoff/game/engine.py` | `Game`: state, `step(action)`, death, score | 2 |
| `bakeoff/senses.py` | `compute_senses`, `looming_rates`, `ground_truth` | 3 |
| `bakeoff/players/base.py` | `Decision`, `Player` protocol | 4 |
| `bakeoff/players/random_player.py`, `solver.py`, `__init__.py` | Baselines and `make_player` factory | 4 |
| `bakeoff/runner.py` | `Runner`, `RunAborted`, `BudgetExhausted`, step log, `meta.json` | 5 |
| `bakeoff/report.py` | `load_steps`, `summarize`, `format_table` | 6 |
| `bakeoff/__main__.py` | `run` and `report` commands | 7 |
| `README.md`, `CLAUDE.md`, `docs/DECISIONS.md` | Status and how to run | 7 |

---

### Task 1: Project scaffold and track generator

**Files:**
- Create: `pyproject.toml`, `.python-version`, `bakeoff/__init__.py`, `bakeoff/game/__init__.py`, `bakeoff/game/track.py`, `tests/conftest.py`
- Test: `tests/test_track.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Constants `LANES = 12`, `MAX_ROWS = 300`, `LOOKAHEAD = 6`, `RUNWAY_ROWS = 4`.
  - `Track(seed: int, lanes: int, max_rows: int, gaps: tuple[tuple[int, ...], ...])`, frozen dataclass; `gaps[row]` is the sorted tuple of gap lanes in that row; `len(gaps) == max_rows + LOOKAHEAD + 2`.
  - `Track.is_gap(row: int, lane: int) -> bool` (lane wraps modulo `lanes`; rows past the end are floor), `Track.to_json() -> dict`.
  - `start_lane(lanes: int = LANES) -> int` (returns `lanes // 2`, so 6).
  - `generate_track(seed: int, lanes: int = LANES, max_rows: int = MAX_ROWS) -> Track`.
  - `survivable(track: Track) -> bool`.
  - pytest fixture `make_track(gap_rows: dict[int, list[int]], max_rows: int = 10, lanes: int = 12) -> Track`.

- [ ] **Step 1: Create the project**

Write `pyproject.toml`:

```toml
[project]
name = "brain-bakeoff"
version = "0.1.0"
description = "An LLM, Jev and a fruit-fly connectome play the same seeded tunnel runs"
requires-python = ">=3.13"
dependencies = []

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
markers = [
    "slow: needs the fly data in data/ (skipped when absent)",
    "live: makes real API requests (opt-in)",
]
```

Then:

```bash
echo 3.13 > .python-version
mkdir -p bakeoff/game tests
touch bakeoff/__init__.py bakeoff/game/__init__.py
uv add --dev pytest
```

Expected: `uv add` creates `.venv/` and `uv.lock` and appends a `[dependency-groups]` table with `pytest` to `pyproject.toml`. `.venv/` is already git-ignored.

- [ ] **Step 2: Write the fixture and the failing tests**

`tests/conftest.py`:

```python
import pytest

from bakeoff.game.track import LOOKAHEAD, Track


@pytest.fixture
def make_track():
    """Hand-made track: make_track({1: [6], 3: [5, 6, 7]}) puts gaps in those lanes of rows 1 and 3."""

    def _make(gap_rows: dict[int, list[int]], max_rows: int = 10, lanes: int = 12) -> Track:
        length = max_rows + LOOKAHEAD + 2
        gaps = tuple(tuple(sorted(gap_rows.get(row, ()))) for row in range(length))
        return Track(seed=0, lanes=lanes, max_rows=max_rows, gaps=gaps)

    return _make
```

`tests/test_track.py`:

```python
from bakeoff.game.track import (LANES, LOOKAHEAD, MAX_ROWS, RUNWAY_ROWS, generate_track,
                                start_lane, survivable)


def test_same_seed_same_track_and_different_seed_differs():
    assert generate_track(7) == generate_track(7)
    assert generate_track(7).gaps != generate_track(8).gaps


def test_shape_and_defaults():
    track = generate_track(0)
    assert (track.seed, track.lanes, track.max_rows) == (0, LANES, MAX_ROWS) == (0, 12, 300)
    assert len(track.gaps) == MAX_ROWS + LOOKAHEAD + 2
    assert all(0 <= lane < LANES for row in track.gaps for lane in row)
    assert all(list(row) == sorted(set(row)) for row in track.gaps)


def test_runway_is_all_floor_and_start_tile_is_floor():
    for seed in range(20):
        track = generate_track(seed)
        assert all(track.gaps[row] == () for row in range(RUNWAY_ROWS + 1))
        assert not track.is_gap(0, start_lane())


def test_is_gap_wraps_lanes_and_is_false_past_the_end(make_track):
    track = make_track({2: [0, 11]})
    assert track.is_gap(2, 0) and track.is_gap(2, 11)
    assert track.is_gap(2, 12) and track.is_gap(2, -1)  # lane 12 is lane 0, lane -1 is lane 11
    assert not track.is_gap(2, 5)
    assert not track.is_gap(10_000, 0)


def test_every_generated_track_is_survivable():
    assert all(survivable(generate_track(seed)) for seed in range(100))
    assert survivable(generate_track(3, max_rows=40))


def test_survivable_detects_an_impossible_track(make_track):
    wall = list(range(12))
    assert survivable(make_track({5: wall}))  # one full row of gaps can be jumped
    assert not survivable(make_track({5: wall, 6: wall}))  # two in a row cannot


def test_gaps_get_denser_with_distance():
    first = last = 0
    for seed in range(20):
        track = generate_track(seed)
        first += sum(len(track.gaps[row]) for row in range(0, 100))
        last += sum(len(track.gaps[row]) for row in range(200, 300))
    assert last > 2 * first


def test_to_json_round_trips_through_json():
    import json

    track = generate_track(1, max_rows=20)
    data = json.loads(json.dumps(track.to_json()))
    assert data["seed"] == 1 and data["lanes"] == 12 and data["max_rows"] == 20
    assert data["gaps"] == [list(row) for row in track.gaps]
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_track.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.game.track'`.

- [ ] **Step 4: Implement `bakeoff/game/track.py`**

How it guarantees a survivable path: it first takes one legal random walk from the start tile to past the last row and protects every tile the walk lands on, then scatters gap runs and removes any that fall on a protected tile. `survivable` is a separate reachability check so the tests do not trust the generator's own bookkeeping.

```python
"""Seeded track generator with a guaranteed survivable path. Pure: no I/O, no global randomness."""

from __future__ import annotations

import random
from dataclasses import dataclass

LANES = 12
MAX_ROWS = 300
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
    rng = random.Random(seed)
    length = max_rows + LOOKAHEAD + 2  # so look-ahead and a last jump never leave the track
    protected = _safe_path(rng, lanes, length)
    gaps: list[tuple[int, ...]] = []
    for row in range(length):
        row_gaps: set[int] = set()
        if row > RUNWAY_ROWS:
            progress = min(1.0, row / max_rows)
            rate = START_GAP_RATE + (END_GAP_RATE - START_GAP_RATE) * progress
            widest = 1 + min(MAX_GAP_WIDTH - 1, int(progress * MAX_GAP_WIDTH))
            for lane in range(lanes):
                if rng.random() < rate:
                    width = rng.randint(1, widest)
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_track.py -q`
Expected: `8 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .python-version uv.lock bakeoff tests
git commit -m "feat: project scaffold and seeded track generator with a guaranteed path"
```

---

### Task 2: Game engine

**Files:**
- Create: `bakeoff/game/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Track`, `Track.is_gap(row, lane)`, `start_lane(lanes)` from `bakeoff.game.track`; the `make_track` fixture.
- Produces:
  - `ACTIONS = ("left", "right", "jump", "stay")`.
  - `Game(track: Track)` with attributes `track`, `row: int`, `lane: int`, `alive: bool`, `death_cause: str | None`; properties `finished: bool` (alive and `row >= max_rows`), `over: bool` (dead or finished), `rows_survived: int`.
  - `Game.step(action: str) -> None`. Raises `ValueError` for an unknown action and `RuntimeError` when the run is over. On death `row` and `lane` stay on the last safe tile.

- [ ] **Step 1: Write the failing tests**

`tests/test_engine.py`:

```python
import pytest

from bakeoff.game.engine import ACTIONS, Game


def test_actions_and_start_state(make_track):
    game = Game(make_track({}))
    assert ACTIONS == ("left", "right", "jump", "stay")
    assert (game.row, game.lane, game.alive, game.rows_survived) == (0, 6, True, 0)
    assert not game.finished and not game.over and game.death_cause is None


def test_moves(make_track):
    game = Game(make_track({}))
    game.step("stay")
    assert (game.row, game.lane) == (1, 6)
    game.step("left")
    assert (game.row, game.lane) == (2, 5)
    game.step("right")
    assert (game.row, game.lane) == (3, 6)
    game.step("jump")
    assert (game.row, game.lane, game.rows_survived) == (5, 6, 5)


def test_lanes_wrap_around_the_tunnel(make_track):
    game = Game(make_track({}, max_rows=20))
    for _ in range(7):
        game.step("left")
    assert game.lane == 11  # 6 -> 0 -> wraps to 11
    game.step("right")
    assert game.lane == 0


def test_jump_clears_a_gap_in_the_next_row(make_track):
    game = Game(make_track({1: list(range(12))}))
    game.step("jump")
    assert game.alive and game.row == 2


@pytest.mark.parametrize("action, gap, cause, survived", [
    ("stay", (1, 6), "ran_into_gap", 0),
    ("left", (1, 5), "dodged_into_gap", 0),
    ("right", (1, 7), "dodged_into_gap", 0),
    ("jump", (2, 6), "jumped_into_gap", 1),  # a fatal jump still cleared the row it flew over
])
def test_death_causes(make_track, action, gap, cause, survived):
    game = Game(make_track({gap[0]: [gap[1]]}))
    game.step(action)
    assert not game.alive and game.over and not game.finished
    assert game.death_cause == cause and game.rows_survived == survived
    assert (game.row, game.lane) == (0, 6)  # the runner's last safe tile


def test_run_finishes_at_max_rows_and_score_is_capped(make_track):
    game = Game(make_track({}, max_rows=3))
    game.step("stay")
    game.step("stay")
    assert not game.over
    game.step("jump")  # lands on row 4, past max_rows
    assert game.finished and game.over and game.alive
    assert game.rows_survived == 3


def test_step_rejects_unknown_actions_and_finished_runs(make_track):
    game = Game(make_track({1: [6]}))
    with pytest.raises(ValueError, match="unknown action 'fly'"):
        game.step("fly")
    game.step("stay")
    with pytest.raises(RuntimeError, match="over"):
        game.step("stay")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_engine.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.game.engine'`.

- [ ] **Step 3: Implement `bakeoff/game/engine.py`**

```python
"""Game state and rules. Pure: no I/O, no randomness."""

from __future__ import annotations

from bakeoff.game.track import Track, start_lane

ACTIONS = ("left", "right", "jump", "stay")
DEATH_CAUSES = {"stay": "ran_into_gap", "jump": "jumped_into_gap",
                "left": "dodged_into_gap", "right": "dodged_into_gap"}


class Game:
    def __init__(self, track: Track):
        self.track = track
        self.row = 0
        self.lane = start_lane(track.lanes)
        self.alive = True
        self.death_cause: str | None = None
        self._cleared = 0

    @property
    def finished(self) -> bool:
        return self.alive and self.row >= self.track.max_rows

    @property
    def over(self) -> bool:
        return not self.alive or self.finished

    @property
    def rows_survived(self) -> int:
        return min(self._cleared, self.track.max_rows)

    def step(self, action: str) -> None:
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action!r}; choose from {ACTIONS}")
        if self.over:
            raise RuntimeError("the run is over")
        advance = 2 if action == "jump" else 1
        lane = (self.lane + {"left": -1, "right": 1}.get(action, 0)) % self.track.lanes
        row = self.row + advance
        if self.track.is_gap(row, lane):
            self.alive = False
            self.death_cause = DEATH_CAUSES[action]
            self._cleared = row - 1  # a fatal jump still cleared the row it flew over
            return
        self.row, self.lane, self._cleared = row, lane, row
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_engine.py -q`
Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/game/engine.py tests/test_engine.py
git commit -m "feat: game engine with moves, lane wrap, death causes and scoring"
```

---

### Task 3: Senses

**Files:**
- Create: `bakeoff/senses.py`
- Test: `tests/test_senses.py`

**Interfaces:**
- Consumes: `Game` (`row`, `lane`, `rows_survived`, `track`), `Track.is_gap`, `LOOKAHEAD`; the `make_track` fixture.
- Produces:
  - `WINDOW = 3`, `MAX_HZ = 250.0`, `LOOMING_GAIN_HZ = 100.0`, `ACTION_DESCRIPTIONS: dict[str, str]`.
  - `compute_senses(game: Game) -> dict` with keys `lane`, `lanes`, `rows_survived`, `ahead` (six entries `{"row": 1..6, "gaps_relative": [sorted offsets in -3..3]}`), `actions`.
  - `looming_rates(senses: dict) -> tuple[float, float]` as `(left_hz, right_hz)`.
  - `ground_truth(game: Game) -> dict` with keys `gap_ahead`, `left_safe`.

- [ ] **Step 1: Write the failing tests**

`tests/test_senses.py`:

```python
import json

from bakeoff.game.engine import Game
from bakeoff.senses import MAX_HZ, compute_senses, ground_truth, looming_rates


def test_senses_shape_matches_the_spec(make_track):
    game = Game(make_track({1: [5, 6], 3: [8, 9]}))
    senses = compute_senses(game)
    assert senses["lane"] == 6 and senses["lanes"] == 12 and senses["rows_survived"] == 0
    assert senses["ahead"] == [
        {"row": 1, "gaps_relative": [-1, 0]}, {"row": 2, "gaps_relative": []},
        {"row": 3, "gaps_relative": [2, 3]}, {"row": 4, "gaps_relative": []},
        {"row": 5, "gaps_relative": []}, {"row": 6, "gaps_relative": []},
    ]
    assert set(senses["actions"]) == {"left", "right", "jump", "stay"}
    json.dumps(senses)


def test_gaps_beyond_three_lanes_are_not_visible(make_track):
    senses = compute_senses(Game(make_track({1: [2, 3, 9, 10]})))
    assert senses["ahead"][0]["gaps_relative"] == [-3, 3]


def test_offsets_wrap_around_the_tunnel(make_track):
    game = Game(make_track({8: [11, 1]}, max_rows=20))
    for _ in range(6):
        game.step("left")  # now at row 6, lane 0
    assert (game.row, game.lane) == (6, 0)
    assert compute_senses(game)["ahead"][1] == {"row": 2, "gaps_relative": [-1, 1]}


def test_senses_follow_the_runner(make_track):
    game = Game(make_track({3: [6]}))
    game.step("stay")
    senses = compute_senses(game)
    assert senses["rows_survived"] == 1
    assert senses["ahead"][1] == {"row": 2, "gaps_relative": [0]}


def test_no_gaps_means_no_looming(make_track):
    assert looming_rates(compute_senses(Game(make_track({})))) == (0.0, 0.0)


def test_left_gap_drives_left_eye_only_and_right_gap_right_eye_only(make_track):
    left, right = looming_rates(compute_senses(Game(make_track({1: [5]}))))
    assert left > 0 and right == 0
    left, right = looming_rates(compute_senses(Game(make_track({1: [7]}))))
    assert left == 0 and right > 0


def test_gap_in_own_lane_drives_both_eyes_equally(make_track):
    left, right = looming_rates(compute_senses(Game(make_track({1: [6]}))))
    assert left == right > 0


def test_nearer_gaps_loom_larger(make_track):
    near, _ = looming_rates(compute_senses(Game(make_track({1: [5]}))))
    far, _ = looming_rates(compute_senses(Game(make_track({4: [5]}))))
    assert near > far > 0


def test_rates_are_capped_at_250_hz(make_track):
    everything = {row: list(range(12)) for row in range(1, 7)}
    assert looming_rates(compute_senses(Game(make_track(everything)))) == (MAX_HZ, MAX_HZ) == (250.0, 250.0)


def test_ground_truth(make_track):
    assert ground_truth(Game(make_track({1: [6]}))) == {"gap_ahead": True, "left_safe": True}
    assert ground_truth(Game(make_track({1: [5]}))) == {"gap_ahead": False, "left_safe": False}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_senses.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.senses'`.

- [ ] **Step 3: Implement `bakeoff/senses.py`**

`looming_rates` reads the senses dict, not the game, so the fly can never see more than the other contestants. Keep the comment on `LOOMING_GAIN_HZ`: it is the honesty label for a mapping that is ours.

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_senses.py -q`
Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/senses.py tests/test_senses.py
git commit -m "feat: JSON senses, provisional looming rates and ground truth"
```

---

### Task 4: Player interface, random and solver

**Files:**
- Create: `bakeoff/players/__init__.py`, `bakeoff/players/base.py`, `bakeoff/players/random_player.py`, `bakeoff/players/solver.py`
- Test: `tests/test_players.py`

**Interfaces:**
- Consumes: `ACTIONS`, `Game` from `bakeoff.game.engine`; `generate_track` from `bakeoff.game.track`; `compute_senses`, `WINDOW` from `bakeoff.senses`; the `make_track` fixture.
- Produces:
  - `Decision(chosen_action: str | None, gated=False, invalid=False, error: str | None = None, questions: dict | None = None, answers: dict | None = None, latency_ms: float | None = None, usage: dict | None = None, cache_hit=False, info: dict | None = None)` with property `needs_fallback: bool`.
  - `Player` protocol: attribute `name: str`; `reset(game: Game, seed: int) -> None`; `act(senses: dict) -> Decision`; `observe(executed_action: str) -> None`.
  - `solve(senses: dict) -> str` in `bakeoff.players.solver`.
  - `RandomPlayer` (`name = "random"`), `SolverPlayer` (`name = "solver"`).
  - `REGISTRY: dict[str, Callable[..., Player]]` and `make_player(name: str, **options) -> Player` in `bakeoff.players`; unknown names raise `KeyError("unknown player 'x'; choose from [...]")`.

- [ ] **Step 1: Write the failing tests**

`tests/test_players.py`:

```python
import pytest

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players import REGISTRY, make_player
from bakeoff.players.base import Decision
from bakeoff.players.solver import solve
from bakeoff.senses import compute_senses


def play(track, player, seed=0):
    game = Game(track)
    player.reset(game, seed)
    while not game.over:
        decision = player.act(compute_senses(game))
        game.step(decision.chosen_action)
        player.observe(decision.chosen_action)
    return game


def test_decision_defaults_and_fallback_rule():
    decision = Decision("left")
    assert not decision.needs_fallback
    assert (decision.gated, decision.invalid, decision.error, decision.cache_hit) == (False, False, None, False)
    assert Decision("left", gated=True).needs_fallback
    assert Decision("left", invalid=True).needs_fallback
    assert Decision(None, error="boom").needs_fallback
    assert Decision(None).needs_fallback


def test_factory_knows_the_baselines_and_rejects_unknown_names():
    assert set(REGISTRY) == {"random", "solver"}
    assert make_player("random").name == "random" and make_player("solver").name == "solver"
    with pytest.raises(KeyError, match="unknown player 'nope'"):
        make_player("nope")


def test_factory_passes_options_to_the_constructor(monkeypatch):
    class NeedsOptions:
        name = "needs_options"

        def __init__(self, cap):
            self.cap = cap

    monkeypatch.setitem(REGISTRY, "needs_options", NeedsOptions)
    assert make_player("needs_options", cap=3).cap == 3


def test_random_player_is_reproducible_per_seed_and_uses_every_action(make_track):
    def choices(seed):
        player = make_player("random")
        player.reset(Game(make_track({})), seed)
        return [player.act({}).chosen_action for _ in range(200)]

    assert choices(1) == choices(1)
    assert choices(1) != choices(2)
    assert set(choices(1)) == set(ACTIONS)


def test_solver_runs_straight_on_open_floor(make_track):
    assert solve(compute_senses(Game(make_track({})))) == "stay"


def test_solver_dodges_a_gap_ahead(make_track):
    assert solve(compute_senses(Game(make_track({1: [6]})))) == "left"
    assert solve(compute_senses(Game(make_track({1: [5, 6]})))) == "right"


def test_solver_jumps_when_dodging_is_impossible(make_track):
    assert solve(compute_senses(Game(make_track({1: [5, 6, 7]})))) == "jump"


def test_solver_looks_further_than_one_row(make_track):
    # Staying is safe now but runs into a wall of gaps at row 2 whose only hole is two lanes left.
    wall = [lane for lane in range(12) if lane != 4]
    track = make_track({2: wall, 3: wall})
    assert solve(compute_senses(Game(track))) == "left"


def test_solver_does_not_trust_tiles_it_cannot_see(make_track):
    # Left is tried before right, and going left survives rows 1-3, but from there the only way
    # on is a lane 4 to the left, outside the visible window. Unseen tiles count as gaps, so the
    # solver goes right, where it can see floor all the way.
    track = make_track({1: [6], 2: [5, 6], 3: [4, 5, 6], 4: [3, 4, 5, 6], 5: [3, 4, 5, 6]})
    assert solve(compute_senses(Game(track))) == "right"


def test_solver_returns_stay_when_nothing_survives(make_track):
    wall = list(range(12))
    assert solve(compute_senses(Game(make_track({1: wall, 2: wall})))) == "stay"


def test_solver_beats_random_by_a_wide_margin():
    solver_rows = [play(generate_track(seed), make_player("solver"), seed).rows_survived for seed in range(10)]
    random_rows = [play(generate_track(seed), make_player("random"), seed).rows_survived for seed in range(10)]
    assert min(solver_rows) >= 200
    assert sum(random_rows) / 10 < 80
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_players.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.players'`.

- [ ] **Step 3: Implement the interface**

`bakeoff/players/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bakeoff.game.engine import Game


@dataclass
class Decision:
    """What a player wants to do. The runner decides what is actually executed."""

    chosen_action: str | None
    gated: bool = False
    invalid: bool = False
    error: str | None = None
    questions: dict | None = None
    answers: dict | None = None
    latency_ms: float | None = None
    usage: dict | None = None
    cache_hit: bool = False
    info: dict | None = None

    @property
    def needs_fallback(self) -> bool:
        return self.gated or self.invalid or self.error is not None or self.chosen_action is None


class Player(Protocol):
    name: str

    def reset(self, game: Game, seed: int) -> None: ...
    def act(self, senses: dict) -> Decision: ...
    def observe(self, executed_action: str) -> None: ...
```

- [ ] **Step 4: Implement the random player**

`bakeoff/players/random_player.py`:

```python
from __future__ import annotations

import random

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.players.base import Decision


class RandomPlayer:
    name = "random"

    def __init__(self) -> None:
        self._rng = random.Random(0)

    def reset(self, game: Game, seed: int) -> None:
        self._rng = random.Random(seed)

    def act(self, senses: dict) -> Decision:
        return Decision(self._rng.choice(ACTIONS))

    def observe(self, executed_action: str) -> None:
        pass
```

- [ ] **Step 5: Implement the solver**

Depth-first search over the visible window. `depth(row, offset)` is the furthest visible row reachable from a safe tile; the first action (in the order stay, left, right, jump) that reaches the furthest wins. With nothing survivable it returns `stay`.

`bakeoff/players/solver.py`:

```python
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
```

- [ ] **Step 6: Implement the factory**

`bakeoff/players/__init__.py`:

```python
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
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_players.py -q`
Expected: `11 passed`.

- [ ] **Step 8: Commit**

```bash
git add bakeoff/players tests/test_players.py
git commit -m "feat: Decision and Player interface, random and solver baselines, factory"
```

---

### Task 5: Runner and step log

**Files:**
- Create: `bakeoff/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `ACTIONS`, `Game` (`step`, `over`, `alive`, `finished`, `death_cause`, `rows_survived`, `row`, `lane`); `generate_track(seed, max_rows=...)`, `Track.to_json()`, `LANES`, `LOOKAHEAD`, `MAX_ROWS`; `compute_senses`, `looming_rates`, `ground_truth`; `Player`, `Decision.needs_fallback`; `solve`; `make_player`.
- Produces:
  - `RunAborted(Exception)` with class attribute `status = "aborted"`; `BudgetExhausted(RunAborted)` with `status = "budget_exhausted"`.
  - `Runner(out_root: Path | str = "runs", max_consecutive_errors: int = 5)`.
  - `Runner.run_seed(player, seed: int, run_id: str, max_rows: int = MAX_ROWS, sink: Callable[[dict], None] | None = None) -> list[dict]`.
  - `Runner.run(players: list[Player], seeds: Sequence[int], max_rows: int = MAX_ROWS, run_id: str | None = None, args: dict | None = None) -> Path`; writes `<out_root>/<run_id>/<player.name>.jsonl` and `meta.json`; raises `FileExistsError` if the directory exists.
  - Record keys (the contract for report and viewer): `run_id, player, seed, row, lane, senses, looming{left_hz,right_hz}, questions, answers, chosen_action, executed_action, solver_action, gated, invalid, error, ground_truth{gap_ahead,left_safe}, alive, finished, death_cause, rows_survived, latency_ms, usage, cache_hit, info, track`. `row`, `lane`, `senses`, `looming` and `ground_truth` describe the moment of decision; `alive`, `finished`, `death_cause` and `rows_survived` the result of the move.
  - `meta.json` keys: `run_id, schema_version (1), git_sha, status (running → completed | aborted | budget_exhausted | interrupted), players, seeds, game{lanes,max_rows,lookahead}, args, python, versions`.

- [ ] **Step 1: Write the failing tests**

`tests/test_runner.py`:

```python
import json

import pytest

from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.runner import BudgetExhausted, RunAborted, Runner

KEYS = {"run_id", "player", "seed", "row", "lane", "senses", "looming", "questions", "answers",
        "chosen_action", "executed_action", "solver_action", "gated", "invalid", "error",
        "ground_truth", "alive", "finished", "death_cause", "rows_survived", "latency_ms",
        "usage", "cache_hit", "info", "track"}


class Scripted:
    """Returns the same Decision every row."""

    def __init__(self, decision, name="scripted"):
        self.decision, self.name, self.observed = decision, name, []

    def reset(self, game, seed): pass
    def act(self, senses): return self.decision
    def observe(self, executed_action): self.observed.append(executed_action)


def test_solver_run_records(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert all(set(r) == KEYS for r in records)
    assert records[0]["row"] == 0 and records[0]["lane"] == 6
    assert [r["row"] for r in records] == sorted({r["row"] for r in records})
    assert all(r["chosen_action"] == r["executed_action"] == r["solver_action"] for r in records)
    assert all(r["alive"] for r in records)
    assert records[-1]["finished"] and not any(r["finished"] for r in records[:-1])
    assert records[-1]["rows_survived"] == 40
    assert set(records[0]["looming"]) == {"left_hz", "right_hz"}
    assert set(records[0]["ground_truth"]) == {"gap_ahead", "left_safe"}
    json.dumps(records)


def test_track_is_logged_once_per_seed(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert records[0]["track"]["seed"] == 3 and records[0]["track"]["max_rows"] == 40
    assert all(r["track"] is None for r in records[1:])


def test_senses_are_logged_as_seen_before_the_move(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert records[0]["senses"]["rows_survived"] == 0
    assert records[1]["senses"]["lane"] == records[1]["lane"]


def test_sink_is_called_as_each_record_is_produced(tmp_path):
    seen: list[dict] = []
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40, sink=seen.append)
    assert seen == records


@pytest.mark.parametrize("decision", [
    Decision("left", gated=True), Decision("left", invalid=True), Decision(None), Decision("teleport"),
])
def test_fallback_is_stay_never_the_solver(tmp_path, decision):
    player = Scripted(decision)
    records = Runner(tmp_path).run_seed(player, seed=3, run_id="r", max_rows=40)
    assert all(r["executed_action"] == "stay" for r in records)
    assert all(r["chosen_action"] == decision.chosen_action for r in records)
    assert player.observed == ["stay"] * len(records)
    assert not records[-1]["alive"] and records[-1]["death_cause"] == "ran_into_gap"


def test_an_unknown_action_is_recorded_as_invalid(tmp_path):
    records = Runner(tmp_path).run_seed(Scripted(Decision("teleport")), seed=3, run_id="r", max_rows=40)
    assert all(r["invalid"] for r in records)


def test_a_dying_run_ends_with_alive_false_and_a_cause(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("random"), seed=0, run_id="r")
    assert not records[-1]["alive"] and records[-1]["death_cause"] is not None
    assert all(r["alive"] and r["death_cause"] is None for r in records[:-1])


def test_run_writes_one_jsonl_per_player_and_meta(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], range(2), max_rows=40,
                                   run_id="t1", args={"players": "solver,random"})
    assert run_dir == tmp_path / "t1"
    lines = (run_dir / "solver.jsonl").read_text().splitlines()
    assert {json.loads(line)["seed"] for line in lines} == {0, 1}
    assert (run_dir / "random.jsonl").exists()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["players"] == ["solver", "random"] and meta["seeds"] == [0, 1]
    assert meta["game"] == {"lanes": 12, "max_rows": 40, "lookahead": 6}
    assert meta["args"] == {"players": "solver,random"}
    assert meta["status"] == "completed" and meta["schema_version"] == 1
    assert "git_sha" in meta and "anthropic" in meta["versions"]


def test_every_player_gets_the_same_track(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], [5], max_rows=40, run_id="t")
    first = [json.loads((run_dir / f"{name}.jsonl").read_text().splitlines()[0]) for name in ("solver", "random")]
    assert first[0]["track"] == first[1]["track"]


def test_run_aborts_after_too_many_consecutive_errors_and_keeps_the_lines(tmp_path):
    with pytest.raises(RunAborted, match=r"^6 consecutive"):
        Runner(tmp_path).run([Scripted(Decision(None, error="boom"), name="errs")], range(10), run_id="t2")
    lines = [json.loads(line) for line in (tmp_path / "t2" / "errs.jsonl").read_text().splitlines()]
    assert len(lines) == 6 and all(r["executed_action"] == "stay" for r in lines)
    assert json.loads((tmp_path / "t2" / "meta.json").read_text())["status"] == "aborted"


def test_error_streak_resets_after_a_good_step(tmp_path):
    class FlakyThenGood(Scripted):
        calls = 0

        def act(self, senses):
            self.calls += 1
            return Decision("stay") if self.calls % 6 == 0 else Decision(None, error="boom")

    Runner(tmp_path).run([FlakyThenGood(None, name="flaky")], range(3), run_id="t3")  # must not raise


def test_budget_exhausted_is_recorded_in_meta(tmp_path):
    class Broke(Scripted):
        def act(self, senses): raise BudgetExhausted("request cap of 0 reached")

    with pytest.raises(BudgetExhausted):
        Runner(tmp_path).run([Broke(None, name="broke")], range(1), run_id="t4")
    assert json.loads((tmp_path / "t4" / "meta.json").read_text())["status"] == "budget_exhausted"


def test_any_other_exception_marks_the_run_interrupted(tmp_path):
    class Boom(Scripted):
        def reset(self, game, seed): raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        Runner(tmp_path).run([Boom(None, name="boom")], range(1), run_id="t5")
    assert json.loads((tmp_path / "t5" / "meta.json").read_text())["status"] == "interrupted"


def test_close_is_called_and_a_failing_close_does_not_mask_the_real_error(tmp_path):
    class Closing(Scripted):
        closed = False

        def close(self):
            self.closed = True
            raise OSError("close failed")

    ok = Closing(Decision("stay"), name="ok")
    Runner(tmp_path).run([ok], range(1), max_rows=20, run_id="t6")
    assert ok.closed

    class BoomClosing(Closing):
        def reset(self, game, seed): raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        Runner(tmp_path).run([BoomClosing(None, name="boom")], range(1), run_id="t7")


def test_second_run_with_the_same_run_id_raises(tmp_path):
    Runner(tmp_path).run([make_player("solver")], range(1), max_rows=20, run_id="dup")
    with pytest.raises(FileExistsError):
        Runner(tmp_path).run([make_player("solver")], range(1), max_rows=20, run_id="dup")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_runner.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.runner'`.

- [ ] **Step 3: Implement `bakeoff/runner.py`**

Adapted from `../testing/glassbox/runner.py`. Differences that matter: the fallback is `stay`, not the reference player's move; an action outside `ACTIONS` is marked `invalid` by the runner; players with a `close()` are closed in a guard that cannot mask a propagating exception; records are flushed line by line so a killed run keeps everything it produced.

```python
"""Players x seeds, fallback rule, streaming JSONL step log and meta.json run status."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from importlib import metadata
from pathlib import Path
from typing import Callable, Sequence

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import LANES, LOOKAHEAD, MAX_ROWS, generate_track
from bakeoff.players.base import Player
from bakeoff.players.solver import solve
from bakeoff.senses import compute_senses, ground_truth, looming_rates

SCHEMA_VERSION = 1
FALLBACK_ACTION = "stay"  # never the solver's move: a rescue would hide what we want to see


class RunAborted(Exception):
    status = "aborted"  # a subclass may set a more specific status


class BudgetExhausted(RunAborted):
    """Raised by a paid client when the hard request cap is reached (phase 3)."""

    status = "budget_exhausted"


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return None


def _close(player: Player) -> None:
    """Players that hold resources (fly brain, API clients) may define close(). A failing
    close() must not mask an exception that is already propagating."""
    close = getattr(player, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        pass


class Runner:
    def __init__(self, out_root: Path | str = "runs", max_consecutive_errors: int = 5):
        self.out_root = Path(out_root)
        self.max_consecutive_errors = max_consecutive_errors
        # Deliberately counts consecutive errors across seeds and players within one run()
        # call: a whole-run circuit breaker, not a per-seed one.
        self._error_streak = 0

    def run_seed(self, player: Player, seed: int, run_id: str, max_rows: int = MAX_ROWS,
                 sink: Callable[[dict], None] | None = None) -> list[dict]:
        track = generate_track(seed, max_rows=max_rows)
        game = Game(track)
        player.reset(game, seed)
        records: list[dict] = []
        while not game.over:
            senses = compute_senses(game)
            left_hz, right_hz = looming_rates(senses)
            truth = ground_truth(game)
            row, lane = game.row, game.lane
            decision = player.act(senses)
            invalid = decision.invalid or (
                decision.chosen_action is not None and decision.chosen_action not in ACTIONS)
            executed = FALLBACK_ACTION if decision.needs_fallback or invalid else decision.chosen_action
            game.step(executed)
            player.observe(executed)
            record = {
                "run_id": run_id, "player": player.name, "seed": seed, "row": row, "lane": lane,
                "senses": senses, "looming": {"left_hz": left_hz, "right_hz": right_hz},
                "questions": decision.questions, "answers": decision.answers,
                "chosen_action": decision.chosen_action, "executed_action": executed,
                "solver_action": solve(senses), "gated": decision.gated, "invalid": invalid,
                "error": decision.error, "ground_truth": truth, "alive": game.alive,
                "finished": game.finished, "death_cause": game.death_cause,
                "rows_survived": game.rows_survived, "latency_ms": decision.latency_ms,
                "usage": decision.usage, "cache_hit": decision.cache_hit, "info": decision.info,
                "track": track.to_json() if not records else None,
            }
            records.append(record)
            if sink is not None:
                sink(record)
            self._error_streak = self._error_streak + 1 if decision.error is not None else 0
            if self._error_streak > self.max_consecutive_errors:
                raise RunAborted(f"{self._error_streak} consecutive player errors; last: {decision.error}")
        return records

    def run(self, players: list[Player], seeds: Sequence[int], max_rows: int = MAX_ROWS,
            run_id: str | None = None, args: dict | None = None) -> Path:
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        run_dir = self.out_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        meta_path = run_dir / "meta.json"
        meta = {
            "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "status": "running",
            "players": [p.name for p in players], "seeds": list(seeds),
            "game": {"lanes": LANES, "max_rows": max_rows, "lookahead": LOOKAHEAD},
            "args": args or {}, "python": platform.python_version(),
            "versions": {pkg: _version(pkg) for pkg in ("brian2", "typesafe-sdk", "anthropic")},
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        self._error_streak = 0
        try:
            for player in players:
                try:
                    with open(run_dir / f"{player.name}.jsonl", "w") as f:
                        def sink(record: dict, f=f) -> None:
                            f.write(json.dumps(record) + "\n")
                            f.flush()

                        for seed in seeds:
                            self.run_seed(player, seed, run_id, max_rows=max_rows, sink=sink)
                finally:
                    _close(player)
        except RunAborted as abort:
            meta["status"] = abort.status
            raise
        except BaseException:
            meta["status"] = "interrupted"
            raise
        else:
            meta["status"] = "completed"
        finally:
            meta_path.write_text(json.dumps(meta, indent=2))
        return run_dir
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -q`
Expected: `18 passed`.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/runner.py tests/test_runner.py
git commit -m "feat: runner with stay fallback, streaming JSONL step log and run status"
```

---

### Task 6: Report

**Files:**
- Create: `bakeoff/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: only the JSONL files and the record keys listed in Task 5. The tests also use `Runner.run(...)` and `make_player(...)` to produce a real run directory.
- Produces:
  - `COLUMNS = ("player", "runs", "incomplete", "mean_rows", "median_rows", "finished", "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "solver_agreement", "fallback_rate", "invalid_rate", "error_rate", "requests", "mean_latency_ms", "input_tokens", "output_tokens")`.
  - `load_steps(run_dir: Path | str) -> list[dict]`; raises `FileNotFoundError("no such run directory: ...")`; skips a truncated last line, raises `json.JSONDecodeError` for a bad line anywhere else.
  - `summarize(steps: list[dict]) -> list[dict]`, one row per player sorted by name; `format_table(rows: list[dict]) -> str` (Markdown table, `-` for `None`, floats to two places).

Rules: a run is complete when its last record has `finished` true or `alive` false; only complete runs count toward `runs`, the row statistics and the death counts, and the rest are `incomplete`. `solver_agreement` is over steps with a `chosen_action`. `fallback_rate` is the share of steps where executed ≠ chosen. `requests`, latency and tokens count only steps with a `latency_ms` that were not cache hits.

- [ ] **Step 1: Write the failing tests**

`tests/test_report.py`:

```python
import json

import pytest

from bakeoff.players import make_player
from bakeoff.report import COLUMNS, format_table, load_steps, summarize
from bakeoff.runner import Runner


def step(player="p", seed=0, row=0, chosen="stay", executed=None, solver="stay", alive=True,
         finished=False, death_cause=None, rows_survived=0, **extra):
    record = {"player": player, "seed": seed, "row": row, "chosen_action": chosen,
              "executed_action": chosen if executed is None else executed, "solver_action": solver,
              "alive": alive, "finished": finished, "death_cause": death_cause,
              "rows_survived": rows_survived, "gated": False, "invalid": False, "error": None,
              "latency_ms": None, "usage": None, "cache_hit": False}
    record.update(extra)
    return record


def test_rows_deaths_and_finishes():
    steps = [
        step(seed=0, row=0), step(seed=0, row=1, alive=False, death_cause="ran_into_gap", rows_survived=1),
        step(seed=1, row=0), step(seed=1, row=9, alive=False, death_cause="dodged_into_gap", rows_survived=9),
        step(seed=2, row=0), step(seed=2, row=19, finished=True, rows_survived=20),
    ]
    (row,) = summarize(steps)
    assert row["player"] == "p" and row["runs"] == 3 and row["incomplete"] == 0
    assert row["mean_rows"] == 10 and row["median_rows"] == 9 and row["finished"] == 1
    assert (row["ran_into_gap"], row["jumped_into_gap"], row["dodged_into_gap"]) == (1, 0, 1)


def test_a_run_cut_off_midway_is_incomplete_not_a_death():
    steps = [step(seed=0, row=0), step(seed=0, row=1, alive=False, death_cause="ran_into_gap", rows_survived=1),
             step(seed=1, row=0), step(seed=1, row=1, rows_survived=2)]
    (row,) = summarize(steps)
    assert row["runs"] == 1 and row["incomplete"] == 1 and row["mean_rows"] == 1


def test_solver_agreement_ignores_steps_without_a_choice():
    steps = [step(chosen="left", solver="left"), step(row=1, chosen="jump", solver="stay"),
             step(row=2, chosen=None, executed="stay", solver="stay", error="boom", alive=False)]
    (row,) = summarize(steps)
    assert row["solver_agreement"] == 0.5
    assert row["error_rate"] == pytest.approx(1 / 3)
    assert row["fallback_rate"] == pytest.approx(1 / 3)


def test_invalid_rate_and_fallback_rate():
    steps = [step(chosen="teleport", executed="stay", invalid=True), step(row=1, alive=False)]
    (row,) = summarize(steps)
    assert row["invalid_rate"] == 0.5 and row["fallback_rate"] == 0.5


def test_requests_latency_and_tokens_count_only_live_calls():
    steps = [
        step(latency_ms=100.0, usage={"input_tokens": 10, "output_tokens": 2}),
        step(row=1, latency_ms=300.0, usage={"input_tokens": 30, "output_tokens": 4}),
        step(row=2, latency_ms=1.0, usage={"input_tokens": 99, "output_tokens": 99}, cache_hit=True, alive=False),
    ]
    (row,) = summarize(steps)
    assert row["requests"] == 2 and row["mean_latency_ms"] == 200.0
    assert row["input_tokens"] == 40 and row["output_tokens"] == 6


def test_players_are_separate_rows_sorted_by_name():
    rows = summarize([step(player="solver", alive=False), step(player="random", alive=False)])
    assert [r["player"] for r in rows] == ["random", "solver"]


def test_format_table_has_every_column_and_dashes_for_none():
    table = format_table(summarize([step(alive=False, death_cause="ran_into_gap")]))
    header, rule, body = table.splitlines()
    assert header == "| " + " | ".join(COLUMNS) + " |"
    assert " - " in body and "0.00" in body


def test_load_steps_reads_a_real_run(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], range(2), max_rows=30, run_id="t")
    steps = load_steps(run_dir)
    assert {s["player"] for s in steps} == {"solver", "random"}
    rows = {r["player"]: r for r in summarize(steps)}
    assert rows["solver"]["runs"] == 2 and rows["solver"]["solver_agreement"] == 1.0


def test_load_steps_tolerates_a_truncated_last_line_only(tmp_path):
    good = json.dumps(step())
    (tmp_path / "p.jsonl").write_text(good + "\n" + good[:20])
    assert len(load_steps(tmp_path)) == 1
    (tmp_path / "p.jsonl").write_text(good[:20] + "\n" + good + "\n")
    with pytest.raises(json.JSONDecodeError):
        load_steps(tmp_path)


def test_load_steps_rejects_a_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such run directory"):
        load_steps(tmp_path / "nope")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_report.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.report'`.

- [ ] **Step 3: Implement `bakeoff/report.py`**

`report.py` must not import anything else from `bakeoff`: it reads files only, so old runs stay reportable when the game code changes.

```python
"""Step logs -> scoreboard. Reads files only."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

COLUMNS = ("player", "runs", "incomplete", "mean_rows", "median_rows", "finished",
           "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "solver_agreement",
           "fallback_rate", "invalid_rate", "error_rate",
           "requests", "mean_latency_ms", "input_tokens", "output_tokens")


def load_steps(run_dir: Path | str) -> list[dict]:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"no such run directory: {run_dir}")
    steps = []
    for path in sorted(run_dir.glob("*.jsonl")):
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        for number, line in enumerate(lines):
            try:
                steps.append(json.loads(line))
            except json.JSONDecodeError:
                if number != len(lines) - 1:
                    raise
                # a run killed mid-write leaves a truncated last line; the rest is still good
    return steps


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _summarize_player(player: str, steps: list[dict]) -> dict:
    runs = defaultdict(list)
    for s in steps:
        runs[s["seed"]].append(s)
    finals = [max(run, key=lambda s: s["row"]) for run in runs.values()]
    # A run cut off mid-way (abort, budget stop, Ctrl-C) is incomplete, not a death.
    complete = [f for f in finals if f["finished"] or not f["alive"]]
    rows = [f["rows_survived"] for f in complete]

    comparable = [s for s in steps if s["chosen_action"] is not None]
    live = [s for s in steps if s["latency_ms"] is not None and not s["cache_hit"]]
    usage = [s["usage"] or {} for s in live]

    return {
        "player": player, "runs": len(complete), "incomplete": len(finals) - len(complete),
        "mean_rows": _mean(rows), "median_rows": statistics.median(rows) if rows else None,
        "finished": sum(f["finished"] for f in complete),
        **{cause: sum(f["death_cause"] == cause for f in complete)
           for cause in ("ran_into_gap", "jumped_into_gap", "dodged_into_gap")},
        "solver_agreement": _ratio(sum(s["chosen_action"] == s["solver_action"] for s in comparable), len(comparable)),
        "fallback_rate": _ratio(sum(s["executed_action"] != s["chosen_action"] for s in steps), len(steps)),
        "invalid_rate": _ratio(sum(s["invalid"] for s in steps), len(steps)),
        "error_rate": _ratio(sum(s["error"] is not None for s in steps), len(steps)),
        "requests": len(live),
        "mean_latency_ms": _mean([s["latency_ms"] for s in live]),
        "input_tokens": sum(u.get("input_tokens") or 0 for u in usage),
        "output_tokens": sum(u.get("output_tokens") or 0 for u in usage),
    }


def summarize(steps: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for s in steps:
        groups[s["player"]].append(s)
    return [_summarize_player(player, group) for player, group in sorted(groups.items())]


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def format_table(rows: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    lines += ["| " + " | ".join(_fmt(row[c]) for c in COLUMNS) + " |" for row in rows]
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_report.py -q`
Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/report.py tests/test_report.py
git commit -m "feat: scoreboard report over complete runs with death causes and fallback rate"
```

---

### Task 7: CLI, first baseline run and docs

**Files:**
- Create: `bakeoff/__main__.py`
- Modify: `README.md` (the `Status:` line at the end), `CLAUDE.md` (the `## Status` section), `docs/DECISIONS.md` (the `## Next step` section)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `MAX_ROWS`; `REGISTRY`, `make_player(name)`; `Runner(out).run(players, seeds, max_rows=, run_id=, args=)`, `Runner.out_root`, `RunAborted` (with `.status`); `load_steps`, `summarize`, `format_table`.
- Produces: `main(argv: list[str] | None = None) -> int`. Commands: `run --players random,solver --seeds 20 --seed-start 0 --max-rows 300 --out runs` and `report <run_dir>`. Exit codes: 0 success, 1 run aborted (the partial scoreboard is still printed), 2 usage error (unknown player, existing run directory, missing report directory).

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:

```python
import json
import time

from bakeoff.__main__ import main


def test_run_then_report(tmp_path, capsys):
    assert main(["run", "--players", "solver,random", "--seeds", "2", "--max-rows", "30", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "run directory:" in out and "| solver |" in out and "| random |" in out
    (run_dir,) = tmp_path.iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [0, 1]
    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30}

    assert main(["report", str(run_dir)]) == 0
    assert "| solver |" in capsys.readouterr().out


def test_seed_start_offsets_the_seeds(tmp_path):
    assert main(["run", "--players", "solver", "--seeds", "2", "--seed-start", "1000", "--max-rows", "20",
                 "--out", str(tmp_path)]) == 0
    (run_dir,) = tmp_path.iterdir()
    assert json.loads((run_dir / "meta.json").read_text())["seeds"] == [1000, 1001]


def test_unknown_player_is_a_usage_error(tmp_path, capsys):
    assert main(["run", "--players", "nope", "--out", str(tmp_path)]) == 2
    assert "unknown player 'nope'" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_report_on_a_missing_directory_is_a_usage_error(tmp_path, capsys):
    assert main(["report", str(tmp_path / "nope")]) == 2
    assert "no such run directory" in capsys.readouterr().err


def test_run_directory_collision_is_a_usage_error(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(time, "strftime", lambda fmt: "same")
    args = ["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path)]
    assert main(args) == 0
    assert main(args) == 2
    assert "already exists" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -q`
Expected: `ModuleNotFoundError: No module named 'bakeoff.__main__'`.

- [ ] **Step 3: Implement `bakeoff/__main__.py`**

```python
"""uv run python -m bakeoff run|report"""

from __future__ import annotations

import argparse
import sys
import time

from bakeoff.game.track import MAX_ROWS
from bakeoff.players import REGISTRY, make_player
from bakeoff.report import format_table, load_steps, summarize
from bakeoff.runner import RunAborted, Runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakeoff")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run players over seeded tracks")
    run.add_argument("--players", default="random,solver", help=f"comma-separated; available: {sorted(REGISTRY)}")
    run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
    run.add_argument("--seed-start", type=int, default=0,
                     help="first seed; practice seeds must not overlap tournament seeds")
    run.add_argument("--max-rows", type=int, default=MAX_ROWS)
    run.add_argument("--out", default="runs")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "report":
        try:
            print(format_table(summarize(load_steps(args.run_dir))))
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 2
        return 0
    try:
        players = [make_player(name) for name in args.players.split(",")]
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
                "max_rows": args.max_rows}
    status = 0
    try:
        runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
    except FileExistsError:
        print(f"run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    except RunAborted as e:
        print(f"run {e.status}: {e}", file=sys.stderr)
        status = 1
    print(f"run directory: {run_dir}")
    print(format_table(summarize(load_steps(run_dir))))
    return status


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: `72 passed`.

- [ ] **Step 5: First baseline run**

Run: `uv run python -m bakeoff run --seeds 20`
Expected (about a second; `runs/` is git-ignored), these exact numbers because tracks and players are seeded:

```
| player | runs | incomplete | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | solver_agreement | ...
| random | 20 | 0 | 39.15 | 37.00 | 0 | 6 | 6 | 8 | 0.27 | ...
| solver | 20 | 0 | 297.05 | 300.00 | 19 | 1 | 0 | 0 | 1.00 | ...
```

If the numbers differ, a constant or the order of `rng` calls in `track.py` was changed. Fix that rather than the expectation.

- [ ] **Step 6: Update the docs**

In `README.md` replace the last line (the one starting `Status: design in progress.`) with:

```markdown
Status: phase 1 of 5 built (game, senses, `random` and `solver` baselines, runner, report).

    uv run pytest
    uv run python -m bakeoff run --players random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>

See `docs/DECISIONS.md` for what has been decided and what comes next.
```

In `CLAUDE.md` replace the body of `## Status` with:

```markdown
Design approved 2026-09-19. Phase 1 built (plan:
`docs/superpowers/plans/2026-09-19-phase1-game-and-baselines.md`): game, senses, `random` and
`solver`, runner, report, CLI. Baseline on seeds 0–19: random 39 rows, solver 297 (19 of 20
finished). Next: write the phase 2 plan (fly player), then build it. Each phase gets its own plan.
```

In `docs/DECISIONS.md` replace the body of `## Next step` with:

```markdown
Phase 1 is built (game, senses, `random` and `solver`, runner, report, CLI). Write the phase 2
plan (fly player: data fetch, brain wrapper, neuron selection, looming weighting and the two
thresholds fixed on practice seeds via `--seed-start`, first fly-vs-baselines scoreboard).
```

- [ ] **Step 7: Commit**

```bash
git add bakeoff/__main__.py tests/test_cli.py README.md CLAUDE.md docs/DECISIONS.md
git commit -m "feat: bakeoff CLI with run and report; phase 1 status in docs"
```

---

## Notes for the phase 2 plan

- The looming weighting in `bakeoff/senses.py` is provisional. Phase 2 fixes it and the two thresholds on practice seeds (`--seed-start 1000` or similar, never seeds that will be in the tournament), commits them and adds the thresholds to `meta.json`.
- The fly player should define `close()`; the runner already calls it safely. `make_player(name, **options)` already passes constructor options through; the CLI does not yet expose any.
- `Decision.info` reaches the record untouched: put the input rates, read-out rates and spike counts there.
- A 300-row fly run takes about 3.5 minutes; lines are flushed per step, so an interrupted run keeps its rows and is reported as `incomplete`.
- The solver dies on about 4 % of tracks in late dead ends. If that is unwanted for the tournament seeds, pick tournament seeds the solver finishes, and say so in the write-up.
- Phase 3 adds to the report: Noul calibration (Brier) from `answers` against `ground_truth`, and cost per run; and to `meta.json`: model ids and the request cap.
