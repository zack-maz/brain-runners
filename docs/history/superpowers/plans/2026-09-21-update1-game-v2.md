# Update 1: Game v2 (named game versions, a shorter track, a faster ramp) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** everything that defines a game moves into one frozen record, `Rules`, with two named versions: `v1` (the game phases 1 to 5 were played on, unchanged tile for tile) and `v2`, the new default (150 rows, full gap density by row 100, the same 6 rows × 3 lanes of vision). Vision becomes a setting (`--lookahead`, `--window`) that renames the game. Runs record their game; a replay never mixes two games.

**Architecture:** `bakeoff/game/rules.py` (new) holds `Rules`, `V1`, `V2`, `RULES`, `DEFAULT`, `rules_for`, `resolve`. A `Track` carries its `Rules`; `generate_track(seed, rules=None, max_rows=None)` reads every number from it; `compute_senses` and `survivable` read vision and length from the track; the solver takes the window as an argument. The runner and `live` take a `Rules` and write `rules.to_json()` into `meta.json`'s `game` block; the CLI chooses the game. `build_replay` compares the recorded games (`Rules.from_json`, `same_game`) and the replay carries a top-level `game` that `Feed` hands to the page, which names the version next to the track.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript with `node --test` (run by `uv run pytest`). No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-21-game-v2-design.md` (binding; amended while prototyping, see its section 1). Background: `docs/UPDATES.md` items 3 and 6, `docs/DECISIONS.md` decision 20.

**Branch:** `phase6-updates` (already created; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network.**
- **Nothing in this plan spends money.** No `--max-requests`, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run` or `bakeoff live` with a paid player (`jev`, `jev_composed`, `llm`) and no fly run (the fly brain needs 1 GB and must never run twice at once).
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command. Nothing here needs it.
- **v1 must stay exactly the game it was.** The v1 fingerprints in `tests/test_track.py` were taken from the generator before this change; if they fail, the generator changed, and that is a bug, never a reason to update the fingerprints.
- **Frozen:** the fly and its constants (`bakeoff/fly/`, except that `calibrate.py` now asks for v1 tracks explicitly), `bakeoff/clients/`, every player other than `solver`, the shape of the senses and of the step record (`schema_version` stays 1), `calibration/`.
- **Viewer rules:** plain JavaScript, no build step, no npm packages; text from a log is always escaped (`Minds.esc`/`esc`); frames reach `app.js` through `Feed` alone.
- Every code block below was run in a prototype and passes as written (final state: 314 fast tests, 9 deselected). If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **A different length keeps the version.** `Rules.variant(max_rows=...)` does not rename the game: the ramp does not depend on `max_rows`, so a shorter run is a prefix of the same tracks. A different vision does rename it (`v2+look3`, `v2+look8+win4`). `--max-rows` stays on the CLI for that reason (the spec is amended accordingly).
2. **`Rules` validates vision:** `lookahead >= 2` (a jump lands two rows on) and `1 <= window <= (lanes - 1) // 2`, so every action's landing tile is always in sight (`senses.lands_on_gap` and the composed Jev rely on it).
3. **The solver takes the window as an argument** (`solve_depths(senses, window)`, `solve(senses, window)`) instead of adding it to the senses: the senses keep their exact shape, so the paid players' cache (keyed on the senses) still replays v1 runs for free.
4. **`make_track` builds v2-based hand-made tracks** and accepts `lookahead`/`window`; tests that depend on v1 numbers (the solver's 200-row floor, the live test where always-stay dies within 40 rows of track 1001, the density test over rows 200–300) name `V1` explicitly.
5. **Replay comparison ignores length only** (`Rules.same_game`), lets a run without `meta.json` through (nothing to compare) and keeps the longest-prefix rule for tracks. The top-level `game` is the first recorded run's rules.
6. **The page states the fly's calibration game:** "practice tracks 1000 to 1199 of game v1", and for any other game "This run is game X; the fly was not retuned for it."

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/game/rules.py` | `Rules`, `V1`, `V2`, `RULES`, `DEFAULT`, `rules_for`, `resolve` | 1, 2 |
| `bakeoff/game/track.py` | `Track(seed, rules, gaps)`, `generate_track(seed, rules, max_rows)` | 1 |
| `bakeoff/senses.py`, `bakeoff/players/solver.py` | vision from the track; the solver's window | 1 |
| `bakeoff/runner.py`, `bakeoff/live.py` | take a `Rules`, record it | 1, 3 |
| `bakeoff/fly/calibrate.py` | pinned to v1 | 1 |
| `bakeoff/__main__.py` | `--game`, `--lookahead`, `--window` | 1, 2 |
| `bakeoff/replay.py` | one game per replay, top-level `game` | 3 |
| `viewer/feed.js`, `viewer/app.js`, `viewer/minds.js` | `game` in `onMeta`, the version by the track, the senses label, the calibration note | 3 |
| `docs/STEP_RECORD.md`, `docs/REPLAY_DATA.md` | the recorded game, the replay's `game` | 3 |
| `tests/…`, `viewer/tests/…` | tests | 1–3 |
| `CLAUDE.md`, `docs/DECISIONS.md`, `docs/UPDATES.md`, `docs/EXPLAINER.html`, `README.md` | status and runbook (controller) | 4 |

---

### Task 1: Named game versions; tracks, senses and the solver read the game's rules

**Files:**
- Modify: `bakeoff/__main__.py`
- Modify: `bakeoff/fly/calibrate.py`
- Create: `bakeoff/game/rules.py`
- Modify: `bakeoff/game/track.py`
- Modify: `bakeoff/live.py`
- Modify: `bakeoff/players/solver.py`
- Modify: `bakeoff/runner.py`
- Modify: `bakeoff/senses.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_live_run.py`
- Test: `tests/test_players.py`
- Test: `tests/test_rules.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_senses.py`
- Test: `tests/test_track.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `bakeoff.game.rules`: `Rules` (frozen dataclass: `version, lanes, max_rows, lookahead, window, runway_rows, start_gap_rate, end_gap_rate, difficulty_rows, max_gap_width`; `variant(max_rows=None, lookahead=None, window=None) -> Rules`, `to_json() -> dict`, `Rules.from_json(block) -> Rules`, `same_game(other) -> bool`), `V1`, `V2`, `RULES`, `DEFAULT = v2`, `rules_for(version) -> Rules`, `resolve(rules=None, max_rows=None) -> Rules`. `Track(seed, rules, gaps)` with properties `lanes`, `max_rows`. `generate_track(seed, rules=None, max_rows=None)`. `solve_depths(senses, window)`, `solve(senses, window)`. `Runner.run_seed(player, seed, run_id, rules=None, max_rows=None, sink=None)`, `Runner.run(players, seeds, rules=None, max_rows=None, run_id=None, args=None)`, `new_meta(run_id, players, seeds, rules, args)`, `LiveRun(players, seed, out_root, rules=None, max_rows=None, run_id=None, args=None, broadcast=None)` with `self.rules`. The module constants `LANES, MAX_ROWS, DIFFICULTY_ROWS, LOOKAHEAD, RUNWAY_ROWS, START_GAP_RATE, END_GAP_RATE, MAX_GAP_WIDTH` (track.py) and `WINDOW` (senses.py) are gone.

The v1 fingerprints in `tests/test_track.py` come from the generator before this change: they must pass unchanged.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_live_run.py`:

```diff
@@ -5,6 +5,7 @@ import json
 import pytest
 
 from bakeoff.errors import BudgetExhausted
+from bakeoff.game.rules import V1
 from bakeoff.live import Broadcast, LiveRun
 from bakeoff.players import make_player
 from bakeoff.players.base import Decision
@@ -38,7 +39,8 @@ def events_of(live):
 
 
 def run_live(tmp_path, players, max_rows=40, seed=1001):
-    live = LiveRun(players, seed, out_root=tmp_path, max_rows=max_rows, run_id="live", args={"port": 0})
+    # v1: always-stay dies on the first 40 rows of this track
+    live = LiveRun(players, seed, out_root=tmp_path, rules=V1, max_rows=max_rows, run_id="live", args={"port": 0})
     live.run()
     return live, events_of(live)
 
```

Replace the whole of `tests/test_players.py` with:

```python
import pytest

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.rules import V1
from bakeoff.game.track import generate_track
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.players.base import Decision
from bakeoff.players.solver import solve, solve_depths
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
    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "jev_composed", "llm"}
    assert set(PAID) == {"jev", "jev_composed", "llm"}
    assert all(make_player(name).name == name for name in REGISTRY)  # a paid player without a budget only replays
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


def test_random_player_stream_is_not_the_tracks_integer_seed(make_track):
    import random

    player = make_player("random")
    player.reset(Game(make_track({})), 5)
    mine = [player.act({}).chosen_action for _ in range(50)]
    track_stream = random.Random(5)
    assert mine != [track_stream.choice(ACTIONS) for _ in range(50)]


def test_always_jump_is_the_floor_for_a_jump_heavy_player():
    # Measured over seeds 0-199: always-jump averages 45.5 rows, random 30.8.
    jump_rows = [play(generate_track(seed), make_player("always_jump"), seed).rows_survived for seed in range(50)]
    random_rows = [play(generate_track(seed), make_player("random"), seed).rows_survived for seed in range(50)]
    assert sum(jump_rows) > sum(random_rows)
    assert max(jump_rows) < 300


def test_solver_runs_straight_on_open_floor(make_track):
    assert solve(compute_senses(Game(make_track({}))), 3) == "stay"


def test_solve_depths_reports_the_furthest_row_each_first_move_reaches(make_track):
    open_floor = solve_depths(compute_senses(Game(make_track({}))), 3)
    assert list(open_floor) == ["stay", "left", "right", "jump"]
    assert set(open_floor.values()) == {6}
    depths = solve_depths(compute_senses(Game(make_track({1: [6]}))), 3)
    assert depths["stay"] == 0  # the first move is not known-safe
    assert depths["left"] == depths["right"] == depths["jump"] == 6


def test_solve_depths_stops_where_the_visible_floor_ends(make_track):
    wall = list(range(12))
    depths = solve_depths(compute_senses(Game(make_track({3: wall, 4: wall}))), 3)
    assert depths == {"stay": 2, "left": 2, "right": 2, "jump": 2}


def test_solve_is_the_first_action_with_the_maximum_depth(make_track):
    senses = compute_senses(Game(make_track({1: [6]})))
    assert solve(senses, 3) == "left"  # left, right and jump tie at 6; left comes first


def test_solver_dodges_a_gap_ahead(make_track):
    assert solve(compute_senses(Game(make_track({1: [6]}))), 3) == "left"
    assert solve(compute_senses(Game(make_track({1: [5, 6]}))), 3) == "right"


def test_solver_jumps_when_dodging_is_impossible(make_track):
    assert solve(compute_senses(Game(make_track({1: [5, 6, 7]}))), 3) == "jump"


def test_solver_looks_further_than_one_row(make_track):
    # Staying is safe now but runs into a wall of gaps at row 2 whose only hole is two lanes left.
    wall = [lane for lane in range(12) if lane != 4]
    track = make_track({2: wall, 3: wall})
    assert solve(compute_senses(Game(track)), 3) == "left"


def test_solver_does_not_trust_tiles_it_cannot_see(make_track):
    # Left is tried before right, and going left survives rows 1-3, but from there the only way
    # on is a lane 4 to the left, outside the visible window. Unseen tiles count as gaps, so the
    # solver goes right, where it can see floor all the way.
    track = make_track({1: [6], 2: [5, 6], 3: [4, 5, 6], 4: [3, 4, 5, 6], 5: [3, 4, 5, 6]})
    assert solve(compute_senses(Game(track)), 3) == "right"


def test_the_solver_sees_the_games_window(make_track):
    # after a step left (lane 5) the only way on is another step left, to lane 4: two lanes from the start,
    # in sight with a window of 3, unseen (so a gap to the solver) with a window of 1
    senses = compute_senses(Game(make_track({1: [6], 2: [5, 6], 3: [5]})))
    assert solve_depths(senses, 1)["left"] == 1 and solve_depths(senses, 3)["left"] == 6
    player = make_player("solver")
    player.reset(Game(make_track({}, window=1)), 0)
    assert player._window == 1


def test_solver_returns_stay_when_nothing_survives(make_track):
    wall = list(range(12))
    assert solve(compute_senses(Game(make_track({1: wall, 2: wall}))), 3) == "stay"


def test_solver_beats_random_by_a_wide_margin():
    solver_rows = [play(generate_track(seed, V1), make_player("solver"), seed).rows_survived for seed in range(10)]
    random_rows = [play(generate_track(seed, V1), make_player("random"), seed).rows_survived for seed in range(10)]
    assert min(solver_rows) >= 200
    assert sum(random_rows) / 10 < 80
```

Create `tests/test_rules.py`:

```python
import json

import pytest

from bakeoff.game.rules import DEFAULT, RULES, V1, V2, Rules, resolve, rules_for


def test_the_two_versions():
    assert DEFAULT == "v2" and RULES == {"v1": V1, "v2": V2}
    assert (V1.max_rows, V1.difficulty_rows, V1.lookahead, V1.window) == (300, 300, 6, 3)
    assert (V2.max_rows, V2.difficulty_rows, V2.lookahead, V2.window) == (150, 100, 6, 3)
    assert (V2.lanes, V2.runway_rows, V2.start_gap_rate, V2.end_gap_rate, V2.max_gap_width) == (12, 4, 0.04, 0.16, 3)


def test_rules_for_names_the_known_versions():
    assert rules_for("v1") is V1
    with pytest.raises(ValueError, match="unknown game version 'v9'; known: v1, v2"):
        rules_for("v9")


def test_a_different_vision_is_named_and_a_different_length_is_not():
    assert V2.variant(lookahead=3).version == "v2+look3"
    assert V2.variant(lookahead=8, window=4).version == "v2+look8+win4"
    assert V2.variant(lookahead=6, window=3) == V2  # unchanged values leave the version alone
    assert V2.variant(max_rows=40) == Rules(**{**V2.to_json(), "max_rows": 40})


def test_resolve_defaults_to_the_current_version():
    assert resolve() == V2 and resolve(V1) == V1
    assert resolve(max_rows=20).max_rows == 20 and resolve(V1, 20).version == "v1"


def test_json_round_trip():
    rules = V2.variant(lookahead=3)
    assert Rules.from_json(json.loads(json.dumps(rules.to_json()))) == rules


def test_a_game_block_from_before_versions_is_v1():
    old = {"lanes": 12, "max_rows": 40, "lookahead": 6, "window": 3, "looming": {"gain_hz": 250.0}}
    assert Rules.from_json(old) == V1.variant(max_rows=40)


def test_a_recorded_block_may_carry_more_than_the_rules():
    assert Rules.from_json({**V2.to_json(), "looming": {"gain_hz": 250.0}}) == V2


def test_same_game_ignores_length_only():
    assert V2.same_game(V2.variant(max_rows=40))
    assert not V2.same_game(V1)
    assert not V2.same_game(V2.variant(lookahead=3))
```

Apply to `tests/test_runner.py`:

```diff
@@ -6,6 +6,7 @@ import pytest
 from bakeoff.players import make_player
 from bakeoff.players.base import Decision
 from bakeoff.errors import PreflightError
+from bakeoff.game.rules import V2
 from bakeoff.runner import BudgetExhausted, RunAborted, Runner
 
 KEYS = {"run_id", "player", "seed", "row", "lane", "senses", "looming", "questions", "answers",
@@ -97,7 +98,7 @@ def test_run_writes_one_jsonl_per_player_and_meta(tmp_path):
     assert (run_dir / "random.jsonl").exists()
     meta = json.loads((run_dir / "meta.json").read_text())
     assert meta["players"] == ["solver", "random"] and meta["seeds"] == [0, 1]
-    assert meta["game"] == {"lanes": 12, "max_rows": 40, "lookahead": 6, "window": 3,
+    assert meta["game"] == {**V2.variant(max_rows=40).to_json(),
                             "looming": {"gain_hz": 250.0, "falloff": 3.0, "step_hz": 25.0, "max_hz": 250.0,
                                         "provisional": False}}
     assert meta["fly"] == {"turn_threshold_hz": 0.0, "jump_threshold_hz": 200.0, "window_ms": 100.0,
@@ -266,7 +267,7 @@ def test_new_meta_is_what_run_writes_first(tmp_path):
     from bakeoff.runner import new_meta
 
     players = [make_player("solver")]
-    meta = new_meta("r", players, [5], 40, {"x": 1})
+    meta = new_meta("r", players, [5], V2.variant(max_rows=40), {"x": 1})
     run_dir = Runner(tmp_path).run(players, [5], max_rows=40, run_id="r", args={"x": 1})
     written = json.loads((run_dir / "meta.json").read_text())
     assert meta["status"] == "running" and meta["finished_at"] is None
```

Apply to `tests/test_senses.py`:

```diff
@@ -112,3 +112,9 @@ def test_lands_on_gap_agrees_with_the_engine_up_to_the_finish_line():
                 checked += 1
             game.step(next(a for a in ("stay", "left", "right", "jump") if not lands_on_gap(senses, a)))
     assert checked > 200
+
+
+def test_the_senses_follow_the_games_vision(make_track):
+    senses = compute_senses(Game(make_track({1: [3, 4], 2: [9]}, lookahead=3, window=2)))
+    assert [e["row"] for e in senses["ahead"]] == [1, 2, 3]
+    assert senses["ahead"][0]["gaps_relative"] == [-2] and senses["ahead"][1]["gaps_relative"] == []
```

Replace the whole of `tests/test_track.py` with:

```python
import hashlib
import json

from bakeoff.game.rules import V1, V2
from bakeoff.game.track import generate_track, start_lane, survivable


def fingerprint(track) -> str:
    return hashlib.sha256(json.dumps(track.to_json()).encode()).hexdigest()[:16]


def test_v1_tracks_are_the_tracks_phases_1_to_5_were_played_on():
    # taken from the generator before game versions existed: old runs must replay tile for tile
    assert {seed: fingerprint(generate_track(seed, V1)) for seed in (0, 7, 1000, 1001)} == {
        0: "06d01a25177a758b", 7: "1ec2d9f9eb2a5592", 1000: "58ce5671352ab3d7", 1001: "d84472fe66921e36"}
    assert fingerprint(generate_track(3, V1, max_rows=40)) == "0d4fd98fd7fc2540"


def test_the_default_game_is_v2():
    track = generate_track(0)
    assert track.rules == V2 and (track.max_rows, track.lanes) == (150, 12)
    assert len(track.gaps) == 150 + 6 + 2


def test_v2_reaches_full_density_by_row_100():
    early = late = 0
    for seed in range(1000, 1020):
        v1, v2 = generate_track(seed, V1), generate_track(seed)
        early += sum(len(v1.gaps[row]) for row in range(90, 110))
        late += sum(len(v2.gaps[row]) for row in range(90, 110))
    assert late > 1.5 * early


def test_a_track_carries_its_vision():
    track = generate_track(5, V2.variant(lookahead=3, window=2))
    assert (track.rules.lookahead, track.rules.window, track.rules.version) == (3, 2, "v2+look3+win2")
    assert len(track.gaps) == 150 + 3 + 2


def test_same_seed_same_track_and_different_seed_differs():
    assert generate_track(7) == generate_track(7)
    assert generate_track(7).gaps != generate_track(8).gaps


def test_a_shorter_track_is_a_prefix_of_the_same_seeds_longer_track():
    for seed in (0, 3, 7, 42):
        short = generate_track(seed, max_rows=50)
        assert short.gaps == generate_track(seed).gaps[:len(short.gaps)]


def test_a_shorter_track_keeps_its_version():
    assert generate_track(3, max_rows=40).rules == V2.variant(max_rows=40)
    assert generate_track(3, max_rows=40).rules.version == "v2"


def test_shape():
    for rules in (V1, V2):
        track = generate_track(0, rules)
        assert (track.seed, track.lanes, track.max_rows) == (0, 12, rules.max_rows)
        assert len(track.gaps) == rules.max_rows + rules.lookahead + 2
        assert all(0 <= lane < 12 for row in track.gaps for lane in row)
    assert all(list(row) == sorted(set(row)) for row in track.gaps)


def test_runway_is_all_floor_and_start_tile_is_floor():
    for seed in range(20):
        track = generate_track(seed)
        assert all(track.gaps[row] == () for row in range(track.rules.runway_rows + 1))
        assert not track.is_gap(0, start_lane())


def test_is_gap_wraps_lanes_and_is_false_past_the_end(make_track):
    track = make_track({2: [0, 11]})
    assert track.is_gap(2, 0) and track.is_gap(2, 11)
    assert track.is_gap(2, 12) and track.is_gap(2, -1)  # lane 12 is lane 0, lane -1 is lane 11
    assert not track.is_gap(2, 5)
    assert not track.is_gap(10_000, 0)


def test_every_generated_track_is_survivable():
    assert all(survivable(generate_track(seed)) for seed in range(100))
    assert all(survivable(generate_track(seed, V1)) for seed in range(30))
    assert survivable(generate_track(3, max_rows=40))


def test_survivable_detects_an_impossible_track(make_track):
    wall = list(range(12))
    assert survivable(make_track({5: wall}))  # one full row of gaps can be jumped
    assert not survivable(make_track({5: wall, 6: wall}))  # two in a row cannot


def test_gaps_get_denser_with_distance():
    first = last = 0
    for seed in range(20):
        track = generate_track(seed, V1)
        first += sum(len(track.gaps[row]) for row in range(0, 100))
        last += sum(len(track.gaps[row]) for row in range(200, 300))
    assert last > 2 * first


def test_to_json_round_trips_through_json():
    import json

    track = generate_track(1, max_rows=20)
    data = json.loads(json.dumps(track.to_json()))
    assert data["seed"] == 1 and data["lanes"] == 12 and data["max_rows"] == 20
    assert data["gaps"] == [list(row) for row in track.gaps]


def test_survivable_agrees_that_a_jump_past_the_finish_line_is_safe(make_track):
    wall = list(range(12))
    assert survivable(make_track({3: wall, 4: wall}, max_rows=3))  # jump from row 2 over the wall to row 4
    assert not survivable(make_track({2: wall, 3: wall, 4: wall}, max_rows=3))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_rules.py tests/test_track.py tests/test_senses.py tests/test_players.py tests/test_runner.py tests/test_live_run.py`
Expected:

```text
ERROR tests/test_rules.py
ERROR tests/test_track.py
ERROR tests/test_players.py
ERROR tests/test_runner.py
ERROR tests/test_live_run.py
5 errors in 0.16s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/__main__.py`:

```diff
@@ -9,7 +9,6 @@ import time
 from pathlib import Path
 
 from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
-from bakeoff.game.track import MAX_ROWS
 from bakeoff.live import LiveRun
 from bakeoff.live_server import EVENTS_PATH, HOST, serve
 from bakeoff.players import PAID, REGISTRY, make_player
@@ -30,7 +29,7 @@ def _parser() -> argparse.ArgumentParser:
     run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
     run.add_argument("--seed-start", type=int, default=0,
                      help="first seed; practice seeds must not overlap tournament seeds")
-    run.add_argument("--max-rows", type=int, default=MAX_ROWS)
+    run.add_argument("--max-rows", type=int, help="play a prefix of each track (default: the whole track)")
     run.add_argument("--out", default="runs")
     run.add_argument("--max-requests", type=int, default=0,
                      help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only replays "
@@ -47,7 +46,7 @@ def _parser() -> argparse.ArgumentParser:
                                        "the run is recorded like any other")
     live.add_argument("--players", default="fly,jev_composed,llm", help=f"comma-separated; available: {sorted(REGISTRY)}")
     live.add_argument("--seed", type=int, default=1001, help="the track; practice seeds are 1000 and up")
-    live.add_argument("--max-rows", type=int, default=MAX_ROWS)
+    live.add_argument("--max-rows", type=int, help="play a prefix of the track (default: the whole track)")
     live.add_argument("--out", default="runs")
     live.add_argument("--max-requests", type=int, default=0,
                       help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only "
```

Apply to `bakeoff/fly/calibrate.py`:

```diff
@@ -19,6 +19,7 @@ from pathlib import Path
 
 from bakeoff.fly.surface import SurrogateBrain, load_surface
 from bakeoff.game.engine import Game
+from bakeoff.game.rules import V1
 from bakeoff.game.track import Track, generate_track
 from bakeoff.players import make_player
 from bakeoff.players.fly import FlyPlayer
@@ -109,13 +110,14 @@ def main(argv: list[str] | None = None) -> int:
         print("usage: python -m bakeoff.fly.calibrate <response_surface.json> <REPORT.md>", file=sys.stderr)
         return 2
     surface = load_surface(argv[0])
-    practice = [generate_track(seed) for seed in PRACTICE_SEEDS]
+    # v1: the frozen numbers were fixed on v1 tracks and must stay reproducible as they were
+    practice = [generate_track(seed, V1) for seed in PRACTICE_SEEDS]
     results = search(surface, practice)
     winner = {k: results[0][k] for k in CONFIG_COLUMNS}
     brain = SurrogateBrain(surface)
 
     def winner_on(seeds: range) -> dict:
-        return score(FlyPlayer(brain_factory=lambda: brain, **winner), [generate_track(seed) for seed in seeds])
+        return score(FlyPlayer(brain_factory=lambda: brain, **winner), [generate_track(seed, V1) for seed in seeds])
 
     floors = [{"player": name, **score(make_player(name), practice)} for name in FLOORS]
     text = report(surface, results, winner_on(HELD_OUT_SEEDS), winner_on(CHECK_SEEDS), floors)
```

Create `bakeoff/game/rules.py`:

```python
"""Named game versions: everything that defines a game, in one frozen record. Pure.

A run records its rules in meta.json; runs of different games never share a scoreboard. v1 is the game
phases 1 to 5 were played on; v2 is shorter and gets hard sooner, so the players separate earlier
(docs/superpowers/specs/2026-09-21-game-v2-design.md)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Rules:
    version: str
    lanes: int
    max_rows: int
    lookahead: int  # rows a player is shown
    window: int  # lanes a player is shown either side of its own
    runway_rows: int  # rows 0..runway_rows are all floor so nobody dies before seeing a gap
    start_gap_rate: float  # chance that a lane starts a gap run, at row 0
    end_gap_rate: float  # the same chance from row difficulty_rows on
    difficulty_rows: int  # gap density ramps over this many rows whatever max_rows is, so tracks are prefix-stable
    max_gap_width: int

    def variant(self, max_rows: int | None = None, lookahead: int | None = None, window: int | None = None) -> Rules:
        """A copy for tests and experiments. A different vision is a different game and says so in its
        version (`v2+look3`, `v2+look8+win4`); a different length plays a prefix of the same tracks, so
        it keeps the version and is recorded in `max_rows`."""
        version = self.version
        if lookahead is not None and lookahead != self.lookahead:
            version += f"+look{lookahead}"
        if window is not None and window != self.window:
            version += f"+win{window}"
        return replace(self, version=version, max_rows=self.max_rows if max_rows is None else max_rows,
                       lookahead=self.lookahead if lookahead is None else lookahead,
                       window=self.window if window is None else window)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, block: dict) -> Rules:
        """The rules of a recorded run. A `game` block without `version` was written before versions
        existed, on v1."""
        if "version" not in block:
            return V1.variant(max_rows=block.get("max_rows"), lookahead=block.get("lookahead"),
                              window=block.get("window"))
        return cls(**{k: block[k] for k in cls.__dataclass_fields__})

    def same_game(self, other: Rules) -> bool:
        """Equal in everything but length: a shorter run plays a prefix of the same tracks."""
        return replace(self, max_rows=0) == replace(other, max_rows=0)


V1 = Rules(version="v1", lanes=12, max_rows=300, lookahead=6, window=3, runway_rows=4, start_gap_rate=0.04,
           end_gap_rate=0.16, difficulty_rows=300, max_gap_width=3)
V2 = replace(V1, version="v2", max_rows=150, difficulty_rows=100)
RULES = {"v1": V1, "v2": V2}
DEFAULT = "v2"


def rules_for(version: str) -> Rules:
    if version not in RULES:
        raise ValueError(f"unknown game version {version!r}; known: {', '.join(RULES)}")
    return RULES[version]


def resolve(rules: Rules | None = None, max_rows: int | None = None) -> Rules:
    """`rules` (default: the current version), `max_rows` rows long if given."""
    return (rules or RULES[DEFAULT]).variant(max_rows=max_rows)
```

Replace the whole of `bakeoff/game/track.py` with:

```python
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
```

Apply to `bakeoff/live.py`:

```diff
@@ -13,7 +13,8 @@ from typing import Iterator
 
 from bakeoff.errors import RunAborted
 from bakeoff.game.engine import Game
-from bakeoff.game.track import MAX_ROWS, generate_track
+from bakeoff.game.rules import Rules, resolve
+from bakeoff.game.track import generate_track
 from bakeoff.players.base import Player
 from bakeoff.replay import META_KEYS, REPLAY_VERSION, build_replay, frame_of, summary_of
 from bakeoff.report import COLUMNS
@@ -79,13 +80,14 @@ class LiveRun:
     a jumper stands two rows on and skips the next tick; the slowest mind sets the pace. Records are
     the runner's own (`play_row`), so the directory is a normal run and `bakeoff view` plays it."""
 
-    def __init__(self, players: list[Player], seed: int, out_root: Path | str = "runs", max_rows: int = MAX_ROWS,
-                 run_id: str | None = None, args: dict | None = None, broadcast: Broadcast | None = None):
+    def __init__(self, players: list[Player], seed: int, out_root: Path | str = "runs", rules: Rules | None = None,
+                 max_rows: int | None = None, run_id: str | None = None, args: dict | None = None,
+                 broadcast: Broadcast | None = None):
         names = [p.name for p in players]
         duplicates = sorted({n for n in names if names.count(n) > 1})
         if duplicates:
             raise ValueError(f"duplicate player names: {duplicates}")
-        self.players, self.seed, self.max_rows = players, seed, max_rows
+        self.players, self.seed, self.rules = players, seed, resolve(rules, max_rows)
         self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
         self.run_dir = Path(out_root) / self.run_id
         self.args = args or {}
@@ -98,7 +100,7 @@ class LiveRun:
         """Preflight, the run directory and meta.json. Returns the empty replay the page starts from."""
         _preflight(self.players)
         self.run_dir.mkdir(parents=True, exist_ok=False)
-        self.meta = new_meta(self.run_id, self.players, [self.seed], self.max_rows, self.args)
+        self.meta = new_meta(self.run_id, self.players, [self.seed], self.rules, self.args)
         self._write_meta()
         return {"replay_version": REPLAY_VERSION,
                 "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}],
@@ -118,7 +120,7 @@ class LiveRun:
     def run(self) -> Path:
         if self.meta is None:
             self.prepare()
-        track = generate_track(self.seed, max_rows=self.max_rows)
+        track = generate_track(self.seed, self.rules)
         games = {p.name: Game(track) for p in self.players}
         questions: dict[str, list[dict]] = {p.name: [] for p in self.players}
         started: set[str] = set()
@@ -142,7 +144,7 @@ class LiveRun:
                         self.broadcast.emit("episode", {
                             "episode": {"player": player.name, "seed": self.seed, "run_id": self.run_id,
                                         "complete": False, "finished": False, "death_cause": None, "rows_survived": 0,
-                                        "max_rows": self.max_rows, "questions": questions[player.name]},
+                                        "max_rows": track.max_rows, "questions": questions[player.name]},
                             "track": track.to_json()})
                     self.broadcast.emit("frame", {"player": player.name, "seed": self.seed, "frame": frame,
                                                   "summary": summary_of(record)})
```

Replace the whole of `bakeoff/players/solver.py` with:

```python
"""Reference player: scripted search over the visible rows. Not a contestant."""

from __future__ import annotations

from bakeoff.game.engine import Game
from bakeoff.players.base import Decision

_MOVES = (("stay", 1, 0), ("left", 1, -1), ("right", 1, 1), ("jump", 2, 0))  # tie-break order


def solve_depths(senses: dict, window: int) -> dict[str, int]:
    """For each action, the furthest visible row its best continuation reaches (0 if the first
    move is not known-safe). Tiles outside the visible window (`window` lanes either side, the
    game's) count as gaps, so the solver only trusts what every contestant can see."""
    gaps = {(e["row"], o) for e in senses["ahead"] for o in e["gaps_relative"]}
    horizon = len(senses["ahead"])

    def safe(row: int, offset: int) -> bool:
        return row <= horizon and abs(offset) <= window and (row, offset) not in gaps

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


def solve(senses: dict, window: int) -> str:
    """First action (in tie-break order) of the longest sequence known to survive."""
    depths = solve_depths(senses, window)
    return max(depths, key=depths.get)  # max returns the first maximum


class SolverPlayer:
    name = "solver"

    def __init__(self):
        self._window = 0

    def reset(self, game: Game, seed: int) -> None:
        self._window = game.track.rules.window

    def act(self, senses: dict) -> Decision:
        return Decision(solve(senses, self._window))

    def observe(self, executed_action: str) -> None:
        pass
```

Apply to `bakeoff/runner.py`:

```diff
@@ -15,11 +15,12 @@ from bakeoff.errors import BudgetExhausted, PreflightError, RunAborted  # noqa:
 from bakeoff.fly import data as fly_data
 from bakeoff.fly.reading import WINDOW_MS
 from bakeoff.game.engine import ACTIONS, Game
-from bakeoff.game.track import LANES, LOOKAHEAD, MAX_ROWS, generate_track
+from bakeoff.game.rules import Rules, resolve
+from bakeoff.game.track import generate_track
 from bakeoff.players import fly
 from bakeoff.players.base import Player
 from bakeoff.players.solver import solve_depths
-from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, WINDOW, compute_senses,
+from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, compute_senses,
                             ground_truth, looming_rates)
 
 SCHEMA_VERSION = 1
@@ -93,7 +94,7 @@ def play_row(player: Player, game: Game, seed: int, run_id: str, first: bool) ->
     senses = compute_senses(game)
     left_hz, right_hz = looming_rates(senses)
     truth = ground_truth(game)
-    depths = solve_depths(senses)
+    depths = solve_depths(senses, game.track.rules.window)
     row, lane = game.row, game.lane
     decision = player.act(senses)
     invalid = decision.invalid or (
@@ -115,13 +116,13 @@ def play_row(player: Player, game: Game, seed: int, run_id: str, first: bool) ->
     }
 
 
-def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], max_rows: int, args: dict | None) -> dict:
+def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], rules: Rules, args: dict | None) -> dict:
     """meta.json as a run starts: status `running`, no finish time yet."""
     return {
         "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
         "started_at": _now(), "finished_at": None, "status": "running",
         "players": [p.name for p in players], "seeds": list(seeds),
-        "game": {"lanes": LANES, "max_rows": max_rows, "lookahead": LOOKAHEAD, "window": WINDOW,
+        "game": {**rules.to_json(),
                  "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                              "max_hz": MAX_HZ, "provisional": not fly.CALIBRATED}},
         "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
@@ -143,9 +144,9 @@ class Runner:
         # call: a whole-run circuit breaker, not a per-seed one.
         self._error_streak = 0
 
-    def run_seed(self, player: Player, seed: int, run_id: str, max_rows: int = MAX_ROWS,
+    def run_seed(self, player: Player, seed: int, run_id: str, rules: Rules | None = None, max_rows: int | None = None,
                  sink: Callable[[dict], None] | None = None) -> list[dict]:
-        track = generate_track(seed, max_rows=max_rows)
+        track = generate_track(seed, rules, max_rows)
         game = Game(track)
         player.reset(game, seed)
         records: list[dict] = []
@@ -159,8 +160,9 @@ class Runner:
                 raise RunAborted(f"{self._error_streak} consecutive player errors; last: {record['error']}")
         return records
 
-    def run(self, players: list[Player], seeds: Sequence[int], max_rows: int = MAX_ROWS,
+    def run(self, players: list[Player], seeds: Sequence[int], rules: Rules | None = None, max_rows: int | None = None,
             run_id: str | None = None, args: dict | None = None) -> Path:
+        rules = resolve(rules, max_rows)
         names = [p.name for p in players]
         duplicates = sorted({n for n in names if names.count(n) > 1})
         if duplicates:  # two players would write the same <name>.jsonl
@@ -170,7 +172,7 @@ class Runner:
         run_dir = self.out_root / run_id
         run_dir.mkdir(parents=True, exist_ok=False)
         meta_path = run_dir / "meta.json"
-        meta = new_meta(run_id, players, seeds, max_rows, args)
+        meta = new_meta(run_id, players, seeds, rules, args)
         meta_path.write_text(json.dumps(meta, indent=2))
         self._error_streak = 0
         try:
@@ -182,7 +184,7 @@ class Runner:
                             f.flush()
 
                         for seed in seeds:
-                            self.run_seed(player, seed, run_id, max_rows=max_rows, sink=sink)
+                            self.run_seed(player, seed, run_id, rules, sink=sink)
                 finally:
                     _close(player)
         except RunAborted as abort:
```

Apply to `bakeoff/senses.py`:

```diff
@@ -5,9 +5,6 @@ from __future__ import annotations
 import math
 
 from bakeoff.game.engine import Game
-from bakeoff.game.track import LOOKAHEAD
-
-WINDOW = 3  # gaps are visible up to this many lanes either side of the runner
 MAX_HZ = 250.0
 # OURS, not the fly's biology: a gap `row` rows ahead adds LOOMING_GAIN_HZ / row ** LOOMING_FALLOFF
 # to its eye; each eye's sum is capped at MAX_HZ and rounded to the nearest LOOMING_STEP_HZ, so
@@ -26,9 +23,11 @@ LANDS = {"left": (0, -1), "stay": (0, 0), "right": (0, 1), "jump": (1, 0)}
 
 
 def compute_senses(game: Game) -> dict:
+    # what the game version shows: `lookahead` rows, `window` lanes either side of the runner
+    lookahead, window = game.track.rules.lookahead, game.track.rules.window
     ahead = []
-    for distance in range(1, LOOKAHEAD + 1):
-        offsets = [o for o in range(-WINDOW, WINDOW + 1) if game.track.is_gap(game.row + distance, game.lane + o)]
+    for distance in range(1, lookahead + 1):
+        offsets = [o for o in range(-window, window + 1) if game.track.is_gap(game.row + distance, game.lane + o)]
         ahead.append({"row": distance, "gaps_relative": offsets})
     return {"lane": game.lane, "lanes": game.track.lanes, "rows_survived": game.rows_survived,
             "ahead": ahead, "actions": dict(ACTION_DESCRIPTIONS)}
```

Replace the whole of `tests/conftest.py` with:

```python
import pytest

from bakeoff.game.rules import V2
from bakeoff.game.track import Track


@pytest.fixture
def make_track():
    """Hand-made track: make_track({1: [6], 3: [5, 6, 7]}) puts gaps in those lanes of rows 1 and 3."""

    def _make(gap_rows: dict[int, list[int]], max_rows: int = 10, lookahead: int | None = None,
              window: int | None = None) -> Track:
        rules = V2.variant(max_rows=max_rows, lookahead=lookahead, window=window)
        length = max_rows + rules.lookahead + 2
        gaps = tuple(tuple(sorted(gap_rows.get(row, ()))) for row in range(length))
        return Track(seed=0, rules=rules, gaps=gaps)

    return _make


def pytest_collection_modifyitems(config, items):
    """`slow` tests run the real fly brain; they are skipped when its data has not been fetched."""
    from bakeoff.fly.data import data_available

    if data_available():
        return
    skip = pytest.mark.skip(reason="fly data absent: uv run python -m scripts.fetch_fly_data")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def brain():
    """The real fly brain, built once per test session (about 1 GB, half a minute). Slow tests only."""
    from bakeoff.fly.brain import Brain

    brain = Brain()
    yield brain
    brain.close()
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_rules.py tests/test_track.py tests/test_senses.py tests/test_players.py tests/test_runner.py tests/test_live_run.py`
Expected: `100 passed in 1.08s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `308 passed, 9 deselected in 27.16s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/__main__.py bakeoff/fly/calibrate.py bakeoff/game/rules.py bakeoff/game/track.py bakeoff/live.py bakeoff/players/solver.py bakeoff/runner.py bakeoff/senses.py tests/conftest.py tests/test_live_run.py tests/test_players.py tests/test_rules.py tests/test_runner.py tests/test_senses.py tests/test_track.py
git commit -F <message file>   # feat: named game versions; tracks, senses and the solver read the game's rules
```

---

### Task 2: run and live choose the game version and the vision

**Files:**
- Modify: `bakeoff/__main__.py`
- Modify: `bakeoff/game/rules.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_live.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: `rules_for`, `RULES`, `DEFAULT`, `Rules.variant` (task 1); `Runner.run(players, seeds, rules, ...)`, `LiveRun(..., rules=...)` (task 1).
- Produces: `Rules.__post_init__` validation (`lookahead must be at least 2 ...`, `window must be 1 to 5 lanes, not N`); CLI flags `--game`, `--lookahead`, `--window` on `run` and `live`, recorded in `meta.json` `args` as `game`, `lookahead`, `window`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_cli.py`:

```diff
@@ -15,7 +15,8 @@ def test_run_then_report(tmp_path, capsys):
     (run_dir,) = tmp_path.iterdir()
     meta = json.loads((run_dir / "meta.json").read_text())
     assert meta["status"] == "completed" and meta["seeds"] == [0, 1]
-    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30,
+    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "game": "v2",
+                            "lookahead": None, "window": None, "max_rows": 30,
                             "max_requests": 0, "cache": ".cache/responses", "tournament": False}
     assert meta["models"] == {} and meta["requests"] == {}
 
@@ -23,6 +24,24 @@ def test_run_then_report(tmp_path, capsys):
     assert "| solver |" in capsys.readouterr().out
 
 
+def test_the_game_version_and_vision_are_chosen_and_recorded(tmp_path):
+    assert main(["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path / "a")]) == 0
+    assert main(["run", "--players", "solver", "--seeds", "1", "--game", "v1", "--lookahead", "3",
+                 "--out", str(tmp_path / "b")]) == 0
+    (a,), (b,) = (tmp_path / "a").iterdir(), (tmp_path / "b").iterdir()
+    game_a, game_b = (json.loads((d / "meta.json").read_text())["game"] for d in (a, b))
+    assert (game_a["version"], game_a["max_rows"]) == ("v2", 20)
+    assert (game_b["version"], game_b["max_rows"], game_b["lookahead"]) == ("v1+look3", 300, 3)
+    first = json.loads((b / "solver.jsonl").read_text().splitlines()[0])
+    assert len(first["senses"]["ahead"]) == 3
+
+
+def test_an_impossible_vision_is_a_usage_error(tmp_path, capsys):
+    assert main(["run", "--players", "solver", "--lookahead", "1", "--out", str(tmp_path)]) == 2
+    assert "lookahead must be at least 2" in capsys.readouterr().err
+    assert list(tmp_path.iterdir()) == []
+
+
 def test_seed_start_offsets_the_seeds(tmp_path):
     assert main(["run", "--players", "solver", "--seeds", "2", "--seed-start", "1000", "--max-rows", "20",
                  "--out", str(tmp_path)]) == 0
```

Apply to `tests/test_cli_live.py`:

```diff
@@ -42,11 +42,20 @@ def test_without_a_cap_a_paid_player_can_only_replay_the_cache(tmp_path, capsys)
     assert json.loads((run_dir / "meta.json").read_text())["requests"] == {"jev_composed": {"max": 0, "used": 0}}
 
 
+def test_a_live_run_plays_the_chosen_game(tmp_path):
+    assert main(live_args(tmp_path, "--game", "v1", "--window", "2")) == 0
+    (run_dir,) = (tmp_path / "runs").iterdir()
+    meta = json.loads((run_dir / "meta.json").read_text())
+    assert meta["game"]["version"] == "v1+win2" and meta["args"]["game"] == "v1" and meta["args"]["window"] == 2
+
+
 def test_usage_errors(tmp_path, capsys):
     assert main(live_args(tmp_path, players="solver,nobody")) == 2
     assert "unknown player 'nobody'" in capsys.readouterr().err
     assert main(live_args(tmp_path, players="solver,solver")) == 2
     assert "duplicate player names" in capsys.readouterr().err
+    assert main(live_args(tmp_path, "--window", "9")) == 2
+    assert "window must be 1 to 5 lanes" in capsys.readouterr().err
     with socket.socket() as taken:
         taken.bind(("127.0.0.1", 0))
         taken.listen()
```

Apply to `tests/test_rules.py`:

```diff
@@ -48,3 +48,12 @@ def test_same_game_ignores_length_only():
     assert V2.same_game(V2.variant(max_rows=40))
     assert not V2.same_game(V1)
     assert not V2.same_game(V2.variant(lookahead=3))
+
+
+def test_every_landing_tile_must_be_in_sight():
+    with pytest.raises(ValueError, match="lookahead must be at least 2"):
+        V2.variant(lookahead=1)
+    with pytest.raises(ValueError, match="window must be 1 to 5 lanes, not 0"):
+        V2.variant(window=0)
+    with pytest.raises(ValueError, match="window must be 1 to 5 lanes, not 6"):
+        V2.variant(window=6)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_cli.py tests/test_cli_live.py tests/test_rules.py`
Expected:

```text
FAILED tests/test_cli.py::test_run_then_report - AssertionError: assert {'pla...
FAILED tests/test_cli.py::test_the_game_version_and_vision_are_chosen_and_recorded
FAILED tests/test_cli.py::test_an_impossible_vision_is_a_usage_error - System...
FAILED tests/test_cli_live.py::test_a_live_run_plays_the_chosen_game - System...
FAILED tests/test_cli_live.py::test_usage_errors - SystemExit: 2
FAILED tests/test_rules.py::test_every_landing_tile_must_be_in_sight - Failed...
6 failed, 30 passed in 4.50s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/__main__.py`:

```diff
@@ -9,6 +9,7 @@ import time
 from pathlib import Path
 
 from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
+from bakeoff.game.rules import DEFAULT, RULES, Rules, rules_for
 from bakeoff.live import LiveRun
 from bakeoff.live_server import EVENTS_PATH, HOST, serve
 from bakeoff.players import PAID, REGISTRY, make_player
@@ -21,6 +22,19 @@ from bakeoff.view import render_html
 FIRST_PRACTICE_SEED = 1000
 
 
+def _add_game_arguments(parser: argparse.ArgumentParser) -> None:
+    parser.add_argument("--game", choices=sorted(RULES), default=DEFAULT,
+                        help=f"the game version (default {DEFAULT}); different versions never share a scoreboard")
+    parser.add_argument("--lookahead", type=int,
+                        help="rows a player is shown (default: the version's); renames the game")
+    parser.add_argument("--window", type=int,
+                        help="lanes a player is shown either side (default: the version's); renames the game")
+
+
+def _rules(args) -> Rules:
+    return rules_for(args.game).variant(lookahead=args.lookahead, window=args.window)
+
+
 def _parser() -> argparse.ArgumentParser:
     parser = argparse.ArgumentParser(prog="bakeoff")
     sub = parser.add_subparsers(dest="command", required=True)
@@ -29,6 +43,7 @@ def _parser() -> argparse.ArgumentParser:
     run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
     run.add_argument("--seed-start", type=int, default=0,
                      help="first seed; practice seeds must not overlap tournament seeds")
+    _add_game_arguments(run)
     run.add_argument("--max-rows", type=int, help="play a prefix of each track (default: the whole track)")
     run.add_argument("--out", default="runs")
     run.add_argument("--max-requests", type=int, default=0,
@@ -46,6 +61,7 @@ def _parser() -> argparse.ArgumentParser:
                                        "the run is recorded like any other")
     live.add_argument("--players", default="fly,jev_composed,llm", help=f"comma-separated; available: {sorted(REGISTRY)}")
     live.add_argument("--seed", type=int, default=1001, help="the track; practice seeds are 1000 and up")
+    _add_game_arguments(live)
     live.add_argument("--max-rows", type=int, help="play a prefix of the track (default: the whole track)")
     live.add_argument("--out", default="runs")
     live.add_argument("--max-requests", type=int, default=0,
@@ -76,6 +92,7 @@ SEED_RULE = ("paid players may not spend requests on seeds below 1000 (tournamen
 
 def _live(args) -> int:
     try:
+        rules = _rules(args)
         players = _players(args.players, DiskCache(args.cache), args.max_requests)
     except KeyError as e:
         print(e.args[0], file=sys.stderr)
@@ -86,10 +103,11 @@ def _live(args) -> int:
     if _spends_on_tournament_seeds(players, args.max_requests, args.seed, args.tournament):
         print(SEED_RULE.format(flag="--seed"), file=sys.stderr)
         return 2
-    run_args = {"command": "live", "players": args.players, "seed": args.seed, "max_rows": args.max_rows,
+    run_args = {"command": "live", "players": args.players, "seed": args.seed, "game": args.game,
+                "lookahead": args.lookahead, "window": args.window, "max_rows": args.max_rows,
                 "max_requests": args.max_requests, "cache": args.cache, "tournament": args.tournament, "port": args.port}
     try:
-        live = LiveRun(players, args.seed, out_root=args.out, max_rows=args.max_rows, args=run_args)
+        live = LiveRun(players, args.seed, out_root=args.out, rules=rules, max_rows=args.max_rows, args=run_args)
         server = serve(None, live.broadcast, args.port)  # before anything is on disk: a busy port leaves nothing behind
     except ValueError as e:
         print(e, file=sys.stderr)
@@ -167,6 +185,7 @@ def main(argv: list[str] | None = None) -> int:
     if args.command == "live":
         return _live(args)
     try:
+        rules = _rules(args)
         players = _players(args.players, DiskCache(args.cache), args.max_requests)
     except KeyError as e:
         print(e.args[0], file=sys.stderr)
@@ -181,12 +200,12 @@ def main(argv: list[str] | None = None) -> int:
     run_id = time.strftime("%Y%m%d-%H%M%S")
     run_dir = runner.out_root / run_id
     seeds = range(args.seed_start, args.seed_start + args.seeds)
-    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
-                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
+    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start, "game": args.game,
+                "lookahead": args.lookahead, "window": args.window, "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
                 "tournament": args.tournament}
     status = 0
     try:
-        runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
+        runner.run(players, seeds, rules, max_rows=args.max_rows, run_id=run_id, args=run_args)
     except FileExistsError:
         print(f"run directory already exists: {run_dir}", file=sys.stderr)
         return 2
```

Apply to `bakeoff/game/rules.py`:

```diff
@@ -22,6 +22,13 @@ class Rules:
     difficulty_rows: int  # gap density ramps over this many rows whatever max_rows is, so tracks are prefix-stable
     max_gap_width: int
 
+    def __post_init__(self):
+        # every action's landing tile must be in sight: a jump lands two rows on, a dodge one lane over
+        if self.lookahead < 2:
+            raise ValueError(f"lookahead must be at least 2 (a jump lands two rows on), not {self.lookahead}")
+        if not 1 <= self.window <= (self.lanes - 1) // 2:
+            raise ValueError(f"window must be 1 to {(self.lanes - 1) // 2} lanes, not {self.window}")
+
     def variant(self, max_rows: int | None = None, lookahead: int | None = None, window: int | None = None) -> Rules:
         """A copy for tests and experiments. A different vision is a different game and says so in its
         version (`v2+look3`, `v2+look8+win4`); a different length plays a prefix of the same tracks, so
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_cli.py tests/test_cli_live.py tests/test_rules.py`
Expected: `36 passed in 4.29s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `312 passed, 9 deselected in 27.25s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/__main__.py bakeoff/game/rules.py tests/test_cli.py tests/test_cli_live.py tests/test_rules.py
git commit -F <message file>   # feat: run and live choose the game version and the vision
```

---

### Task 3: A replay shows one game version, and the page names it

**Files:**
- Modify: `bakeoff/live.py`
- Modify: `bakeoff/replay.py`
- Modify: `docs/REPLAY_DATA.md`
- Modify: `docs/STEP_RECORD.md`
- Modify: `viewer/app.js`
- Modify: `viewer/feed.js`
- Modify: `viewer/minds.js`
- Test: `tests/test_live_run.py`
- Test: `tests/test_replay.py`
- Test: `viewer/tests/feed.test.js`
- Test: `viewer/tests/minds.test.js`

**Interfaces:**
- Consumes: `Rules.from_json`, `Rules.same_game`, `Rules.to_json` (task 1); `LiveRun.rules` (task 1).
- Produces: the replay's top-level `game` (a `Rules.to_json()` dict or null); `Feed`'s `onMeta` gets `{game, runs, players, seeds, scoreboard}`; `store.game` in `app.js`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_live_run.py`:

```diff
@@ -5,7 +5,7 @@ import json
 import pytest
 
 from bakeoff.errors import BudgetExhausted
-from bakeoff.game.rules import V1
+from bakeoff.game.rules import V1, V2
 from bakeoff.live import Broadcast, LiveRun
 from bakeoff.players import make_player
 from bakeoff.players.base import Decision
@@ -130,6 +130,7 @@ def test_prepare_gives_the_page_an_empty_replay_that_names_the_run(tmp_path):
     assert replay["episodes"] == [] and replay["seeds"] == [1001] and replay["scoreboard"]["rows"] == []
     (run,) = replay["runs"]
     assert run["run_id"] == "live" and run["status"] == "running" and run["game"]["lookahead"] == 6
+    assert replay["game"] == V2.variant(max_rows=20).to_json()  # what the page shows next to the track
     assert (live.run_dir / "meta.json").is_file()
 
 
```

Apply to `tests/test_replay.py`:

```diff
@@ -196,6 +196,28 @@ def test_the_longest_track_of_a_seed_is_kept(tmp_path):
     assert [e["max_rows"] for e in replay["episodes"]] == [4, 10]
 
 
+def test_a_replay_shows_one_game(tmp_path):
+    from bakeoff.game.rules import V1, V2
+
+    a = write_run(tmp_path, "a", [record("fly", track=TRACK)], meta={"game": V2.to_json()})
+    b = write_run(tmp_path, "b", [record("llm", track=TRACK)], meta={"game": {**V2.to_json(), "max_rows": 40}})
+    c = write_run(tmp_path, "c", [record("jev", track=TRACK)], meta={"game": V1.to_json()})
+    d = write_run(tmp_path, "d", [record("solver", track=TRACK)])  # no meta: nothing to compare
+    assert build_replay([a, b, d])["game"] == V2.to_json()  # a shorter run of the same game is a prefix
+    with pytest.raises(ValueError, match="a is game v2 but c is game v1; a replay shows one game"):
+        build_replay([a, c])
+
+
+def test_a_run_from_before_game_versions_is_v1(tmp_path):
+    from bakeoff.game.rules import V1
+
+    old = {"lanes": 12, "max_rows": 300, "lookahead": 6, "window": 3, "looming": {"gain_hz": 250.0}}
+    a = write_run(tmp_path, "a", [record("fly", track=TRACK)], meta={"game": old})
+    b = write_run(tmp_path, "b", [record("llm", track=TRACK)], meta={"game": V1.to_json()})
+    assert build_replay([a, b])["game"] == V1.to_json()
+    assert build_replay([write_run(tmp_path, "c", [record(track=TRACK)])])["game"] is None
+
+
 def test_a_run_without_meta_is_named_after_its_directory(tmp_path):
     run_dir = write_run(tmp_path, "nometa", [record(track=TRACK)])
     (run,) = build_replay([run_dir])["runs"]
```

Apply to `viewer/tests/feed.test.js`:

```diff
@@ -23,12 +23,12 @@ const episode = (player, frames) => ({ player, seed: 1000, run_id: "r", complete
 
 test("an embedded replay arrives as meta, then each episode and its frames in order", () => {
   const { calls, handlers } = recorder();
-  const replay = { runs: [{ run_id: "r" }], players: ["fly", "llm"], seeds: [1000], tracks: { 1000: TRACK },
+  const replay = { game: { version: "v2" }, runs: [{ run_id: "r" }], players: ["fly", "llm"], seeds: [1000], tracks: { 1000: TRACK },
                    scoreboard: { columns: ["player"], rows: [], same_seeds: true },
                    episodes: [episode("fly", [frame(0), frame(1)]), episode("llm", [frame(0)])] };
   fromEmbedded(replay, handlers);
   assert.deepEqual(calls.map((c) => c[0]), ["meta", "episode", "frame", "frame", "episode", "frame"]);
-  assert.deepEqual(calls[0][1], { runs: replay.runs, players: replay.players, seeds: [1000], scoreboard: replay.scoreboard });
+  assert.deepEqual(calls[0][1], { game: { version: "v2" }, runs: replay.runs, players: replay.players, seeds: [1000], scoreboard: replay.scoreboard });
   const [, header, track] = calls[1];
   assert.equal(header.player, "fly");
   assert.equal(header.death_cause, "ran_into_gap");
@@ -41,7 +41,7 @@ test("an embedded replay arrives as meta, then each episode and its frames in or
 test("an empty replay, as the live page embeds it, is only meta", () => {
   const { calls, handlers } = recorder();
   fromEmbedded({ runs: [], players: [], seeds: [], tracks: {}, episodes: [] }, handlers);
-  assert.deepEqual(calls, [["meta", { runs: [], players: [], seeds: [], scoreboard: { columns: [], rows: [], same_seeds: true } }]]);
+  assert.deepEqual(calls, [["meta", { game: null, runs: [], players: [], seeds: [], scoreboard: { columns: [], rows: [], same_seeds: true } }]]);
 });
 
 test("a live stream delivers the same calls in the replay's own shapes", () => {
```

Apply to `viewer/tests/minds.test.js`:

```diff
@@ -31,6 +31,12 @@ test("the senses grid's column count follows the window it is given", () => {
   assert.equal(count(html, "<rect"), 5 * 6);
 });
 
+test("the senses grid has as many rows as the player was shown, and says so", () => {
+  const html = Minds.sensesGrid({ ...frame(), ahead: [[0], [], []] }, 3);
+  assert.equal(count(html, "<rect"), 3 * 7);
+  assert.match(html, /aria-label="the 3 rows it was shown"/);
+});
+
 test("the verdict rates the choice against the solver's depths", () => {
   assert.match(Minds.verdict(frame()), /as good as any move \(6 rows seen safe\)/);
   assert.match(Minds.verdict(frame({ chosen_action: "jump", executed_action: "jump" })),
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_replay.py tests/test_live_run.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_replay.py::test_a_replay_shows_one_game - KeyError: 'game'
FAILED tests/test_replay.py::test_a_run_from_before_game_versions_is_v1 - Key...
FAILED tests/test_live_run.py::test_prepare_gives_the_page_an_empty_replay_that_names_the_run
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✖ an...
4 failed, 32 passed in 0.65s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/live.py`:

```diff
@@ -102,7 +102,7 @@ class LiveRun:
         self.run_dir.mkdir(parents=True, exist_ok=False)
         self.meta = new_meta(self.run_id, self.players, [self.seed], self.rules, self.args)
         self._write_meta()
-        return {"replay_version": REPLAY_VERSION,
+        return {"replay_version": REPLAY_VERSION, "game": self.rules.to_json(),
                 "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}],
                 "players": [], "seeds": [self.seed], "tracks": {}, "episodes": [],
                 "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": [], "same_seeds": True}}
```

Apply to `bakeoff/replay.py`:

```diff
@@ -8,6 +8,7 @@ from __future__ import annotations
 
 from pathlib import Path
 
+from bakeoff.game.rules import Rules
 from bakeoff.report import COLUMNS, load_meta, load_steps, summarize
 
 REPLAY_VERSION = 1
@@ -71,6 +72,7 @@ def build_replay(run_dirs: list[Path | str]) -> dict:
     same episode would let the viewer show either, so that is an error, not a silent pick."""
     runs, episodes, tracks, scoreboard = [], [], {}, []
     owner: dict[tuple[str, int], str] = {}
+    game: tuple[str, Rules] | None = None  # the first run that recorded its game, and that game
     for run_dir in map(Path, run_dirs):
         steps = load_steps(run_dir)
         meta = load_meta(run_dir)
@@ -78,6 +80,13 @@ def build_replay(run_dirs: list[Path | str]) -> dict:
         if (meta or {}).get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
             raise ValueError(f"{run_id} has schema_version {meta['schema_version']}; "
                              f"this viewer reads {SCHEMA_VERSION}")
+        if (meta or {}).get("game"):
+            rules = Rules.from_json(meta["game"])
+            if game is None:
+                game = (run_id, rules)
+            elif not game[1].same_game(rules):  # one seed is a different track in another game
+                raise ValueError(f"{game[0]} is game {game[1].version} but {run_id} is game {rules.version}; "
+                                 "a replay shows one game")
         runs.append({"run_id": run_id, **{k: (meta or {}).get(k) for k in META_KEYS}})
         grouped: dict[tuple[str, int], list[dict]] = {}
         for s in steps:
@@ -107,7 +116,7 @@ def build_replay(run_dirs: list[Path | str]) -> dict:
         if e["complete"]:
             seeds_of[(e["run_id"], e["player"])].add(e["seed"])
     return {
-        "replay_version": REPLAY_VERSION, "runs": runs, "players": players,
+        "replay_version": REPLAY_VERSION, "game": game[1].to_json() if game else None, "runs": runs, "players": players,
         "seeds": sorted({e["seed"] for e in episodes}), "tracks": tracks, "episodes": episodes,
         "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": scoreboard,
                        # true only when every scoreboard row (one per run, player) averages the same seeds;
```

Apply to `docs/REPLAY_DATA.md`:

```diff
@@ -10,6 +10,7 @@ records it is built from are described in `docs/STEP_RECORD.md`.
 | key | type | meaning |
 | --- | --- | --- |
 | `replay_version` | int | 1. Bumped on any breaking change to this object |
+| `game` | object or null | the game every run in the replay played (`Rules.to_json()`: `version`, `lanes`, `max_rows`, `lookahead`, `window`, the ramp), null when no run has a `meta.json`. Runs of different games are an error (`ValueError`, exit 2): a seed is a different track in another game. Runs that differ only in `max_rows` are the same game. A `game` block without `version` is v1 |
 | `runs` | object[] | one per run directory, in the order given: `run_id` plus these keys of its `meta.json`, null when absent: `status`, `git_sha`, `git_dirty`, `started_at`, `finished_at`, `players`, `seeds`, `game`, `fly`, `models`, `requests`. A directory without `meta.json` is named after the directory |
 | `players` | string[] | players with at least one episode: `fly`, `jev_composed`, `llm` (the demo's three), then `jev`, then the others in the order the runs planned them |
 | `seeds` | int[] | every seed with at least one episode, ascending |
@@ -45,7 +46,7 @@ Frames are sorted by `row`. A jump advances two rows, so rows are not consecutiv
 
 ## How the viewer uses it
 
-The page never reads this object directly: `viewer/feed.js` hands it over as calls (`onMeta`, then
+The page never reads this object directly: `viewer/feed.js` hands it over as calls (`onMeta` with `game`, then
 `onEpisode` and `onFrame` per episode), the same calls a live run makes, so the two cannot drift apart.
 
 ## The live stream
```

Apply to `docs/STEP_RECORD.md`:

```diff
@@ -122,13 +122,15 @@ line and cannot kill. `finished` is true when the runner's row after the move is
 
 Present only in the first record of each seed (null elsewhere): `{seed, lanes, max_rows, gaps}`.
 `gaps[r]` is the sorted list of lane indices that are gaps in row `r`; the list has
-`max_rows + 8` entries (rows `0 .. max_rows + 7`); rows 0 to 4 are always empty; a row beyond
+`max_rows + lookahead + 2` entries (rows `0 .. max_rows + lookahead + 1`); rows 0 to `runway_rows` are always
+empty; a row beyond
 the list is floor. Lanes wrap. Lookups: gap at (`r`, `l`) iff `r < gaps.length` and
 `gaps[r]` contains `((l % lanes) + lanes) % lanes`.
 
-A track's identity is its seed: the difficulty ramp is fixed at 300 rows, so a run with a smaller
-`max_rows` plays the first rows of the same track (its `gaps` is a prefix of the 300-row
-`gaps`). All players on a seed see the same track.
+A track's identity is its seed and its game version (`meta.json` `game`): the same seed is a different track
+in another version. Within a version the difficulty ramp is fixed (`difficulty_rows`), so a run with a
+smaller `max_rows` plays the first rows of the same track (its `gaps` is a prefix of the full track's).
+All players on a seed see the same track.
 
 ## `meta.json`
 
@@ -142,7 +144,7 @@ A track's identity is its seed: the difficulty ramp is fixed at 300 rows, so a r
 | `status` | string | `running`, then `completed`, `aborted`, `budget_exhausted` or `interrupted` |
 | `players` | string[] | the players planned for this run, in order |
 | `seeds` | int[] | the seeds planned for this run |
-| `game` | object | `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `looming: {gain_hz, falloff, step_hz, max_hz, provisional}` |
+| `game` | object | the game's rules (`bakeoff/game/rules.py`): `version` (`v1`, `v2`, or a vision variant such as `v2+look3`), `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `runway_rows`, `start_gap_rate`, `end_gap_rate`, `difficulty_rows`, `max_gap_width`; and `looming: {gain_hz, falloff, step_hz, max_hz, provisional}`. Runs from before game versions have only `lanes`, `max_rows`, `lookahead`, `window` and `looming`, and were played on v1 |
 | `fly` | object | `turn_threshold_hz`, `jump_threshold_hz`, `window_ms`, `provisional` (true until calibrated), `model_commit`, `annotations_commit` |
 | `models` | object | `{player: model id}` for paid players in the run, e.g. `{"jev": "jev-latest", "llm": "claude-haiku-4-5-20251001"}` |
 | `requests` | object | `{player: {max, used}}` for paid players: the `--max-requests` cap and the live requests spent against it, failed ones included. Written at the start with `used: 0` and rewritten when the run ends, so a crashed run may show a stale count |
```

Apply to `viewer/app.js`:

```diff
@@ -28,7 +28,7 @@
   const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
 
   // ---- the store: everything the feed has delivered -------------------------------------------
-  const store = { runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
+  const store = { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [], scoreboard: null, ended: !liveUrl, error: null };
   const view = {
     seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0,
     t: 0, playing: false, speed: 3, following: !!liveUrl, size: 0, runners: [], panels: {},
@@ -47,7 +47,7 @@
 
   const handlers = {
     onMeta(meta) {
-      Object.assign(store, { runs: meta.runs, players: meta.players.slice(), seeds: meta.seeds.slice(), scoreboard: meta.scoreboard });
+      Object.assign(store, { game: meta.game, runs: meta.runs, players: meta.players.slice(), seeds: meta.seeds.slice(), scoreboard: meta.scoreboard });
     },
     onEpisode(episode, track) {
       store.episodes.push({ ...episode, frames: [] });
@@ -238,7 +238,7 @@
       Tunnel.draw(ctx, size, track, t, maxRows, outline);
       drawRunners(all, track, t, size);
       $("row-label").textContent = "Row " + String(Math.min(Math.floor(t), maxRows)).padStart(4, "0") + " / " + String(maxRows).padStart(4, "0");
-      $("track-label").textContent = "Track " + view.seed;
+      $("track-label").textContent = "Track " + view.seed + (store.game ? " · " + store.game.version : "");
     }
 
     for (const s of all) {
```

Apply to `viewer/feed.js`:

```diff
@@ -1,6 +1,6 @@
 // The one way frames reach the page. A replay file and a live run look the same to it:
 //
-//   handlers.onMeta({runs, players, seeds, scoreboard})   once, from the embedded replay
+//   handlers.onMeta({game, runs, players, seeds, scoreboard})  once, from the embedded replay
 //   handlers.onEpisode(episode, track)                    an episode begins; `episode` has no frames yet
 //   handlers.onFrame(player, seed, frame, summary)        one decision; `summary` is the episode's
 //                                                         {complete, finished, death_cause, rows_survived}
@@ -21,7 +21,7 @@
   };
 
   function fromEmbedded(replay, handlers) {
-    handlers.onMeta({ runs: replay.runs || [], players: replay.players || [], seeds: replay.seeds || [],
+    handlers.onMeta({ game: replay.game || null, runs: replay.runs || [], players: replay.players || [], seeds: replay.seeds || [],
                       scoreboard: replay.scoreboard || { columns: [], rows: [], same_seeds: true } });
     for (const episode of replay.episodes || []) {
       handlers.onEpisode(header(episode), (replay.tracks || {})[String(episode.seed)]);
```

Apply to `viewer/minds.js`:

```diff
@@ -35,7 +35,7 @@
     return '<span class="bar"><i class="fill" style="width:' + width.toFixed(1) + '%"></i>' + tick + "</span>";
   }
 
-  // The senses as the player got them: 6 rows ahead (far at the top), `window` lanes either side, gaps dark.
+  // The senses as the player got them: the game's rows ahead (far at the top), `window` lanes either side, gaps dark.
   function sensesGrid(frame, window) {
     let cells = "";
     for (let r = frame.ahead.length - 1; r >= 0; r--) {
@@ -46,7 +46,8 @@
       }
     }
     const height = frame.ahead.length * 8, width = (2 * window + 1) * 12;
-    return '<svg class="senses" viewBox="0 0 ' + width + " " + (height + 8) + '" role="img" aria-label="the six rows it was shown">' +
+    return '<svg class="senses" viewBox="0 0 ' + width + " " + (height + 8) + '" role="img" aria-label="the ' + frame.ahead.length +
+      ' rows it was shown">' +
       cells + '<circle cx="' + (width / 2 - 0.5) + '" cy="' + (height + 4) + '" r="3" class="me"/></svg>';
   }
 
@@ -202,8 +203,11 @@
       (run.fly.provisional
         ? '<li class="warn">These values were provisional when this run was made: not yet calibrated.</li>'
         : "<li>The gain, the falloff and the two thresholds were chosen once, by a rule fixed beforehand, on practice tracks " +
-          "1000 to 1199 that are not in the tournament, then frozen (calibration/REPORT.md). The cap, the step and the window " +
-          "length are fixed design choices of ours and were not tuned.</li>");
+          "1000 to 1199 of game v1 that are not in the tournament, then frozen (calibration/REPORT.md)." +
+          // a run from before game versions has no version and was v1
+          (run.game.version && !run.game.version.startsWith("v1")
+            ? " This run is game " + esc(run.game.version) + "; the fly was not retuned for it." : "") +
+          " The cap, the step and the window length are fixed design choices of ours and were not tuned.</li>");
   }
 
   // the whole panel for one decision; context = {windowMs, maxHz, window}, from the run's meta
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_replay.py tests/test_live_run.py tests/test_viewer_js.py`
Expected: `36 passed in 0.54s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `314 passed, 9 deselected in 28.28s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live.py bakeoff/replay.py docs/REPLAY_DATA.md docs/STEP_RECORD.md tests/test_live_run.py tests/test_replay.py viewer/app.js viewer/feed.js viewer/minds.js viewer/tests/feed.test.js viewer/tests/minds.test.js
git commit -F <message file>   # feat: a replay shows one game version, and the page names it
```

---

### Task 4: Docs and the first free v2 run (controller)

Done by the controller, not an implementer; nothing here spends money.

- [ ] `uv run python -m bakeoff run --players solver,random,always_jump --seeds 20 --seed-start 1000` (v2 by default) and `uv run python -m bakeoff view <that run> --output <scratchpad>/v2.html`; check the page names "v2" by the track and the tunnel ends at row 150.
- [ ] Check that `uv run python -m bakeoff view runs/20260919-151934 runs/20260920-102919 runs/20260921-120903` still builds (v1 runs from before versions) and that mixing a v1 and a v2 run exits 2 with "a replay shows one game".
- [ ] `docs/DECISIONS.md`: decisions from the spec (the ramp's goal, vision as a setting, 150 rows, approach A and the v2 numbers), the runbook's commands with `--game`, the next step (the players: items 1 and 2 of `docs/UPDATES.md`).
- [ ] `docs/UPDATES.md`: items 3 and 6 built. `CLAUDE.md` status. `README.md` and `docs/EXPLAINER.html`: 150 rows, the ramp, game versions, the fly calibrated on v1.
- [ ] Final whole-branch review aimed at the design: v1 unchanged, no silent mixing of games, the honesty surface (what the page and docs claim about vision and the fly's calibration).
