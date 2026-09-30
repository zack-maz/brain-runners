# Phase 5c: Go Live — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `uv run python -m bakeoff live` runs the minds on one track in real time, in lockstep by row, records a normal run directory and streams every decision into the demo player over a loopback server.

**Architecture:** the live loop writes the runner's own records and sends the replay's own frames, because both builders are extracted first (`runner.play_row`, `runner.new_meta`, `replay.frame_of`, `replay.summary_of`) and the batch paths keep using them. `bakeoff/live.py` holds `Broadcast` (the run's events, replayed to any listener from the start) and `LiveRun` (the lockstep loop). `bakeoff/live_server.py` is a standard-library HTTP server bound to `127.0.0.1` that serves the page and the event stream and nothing else. `bakeoff/view.py` can mark the page as live (`<body data-live="/events">`); `viewer/feed.js` already speaks the stream (phase 5b). The CLI's `live` command shares the player building and the seed rule with `run`.

**Tech Stack:** Python 3.13 standard library (`http.server`, `threading`), `uv`, `pytest`. No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-20-demo-player-design.md`, section "Phase 5c" (binding).

**Branch:** `phase5-demo-player` (phases 5a and 5b are on it; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Never `pip` or bare `python`. No `uv add`, no `npm`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network;** the server's tests connect to `127.0.0.1` only, to the server under test, on an ephemeral port.
- **Tasks 1 to 5 spend no money** and build no fly brain: no `--max-requests`, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run` or `bakeoff live` with `fly`, `jev`, `jev_composed` or `llm`. The real go-live run is Task 6, the controller's alone, inside decision 19's ceilings.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Frozen:** `bakeoff/game/`, `bakeoff/fly/`, `bakeoff/players/`, `bakeoff/clients/`, `bakeoff/senses.py`, `bakeoff/report.py`, `calibration/`, every file in `viewer/` except the one line of `viewer/app.js` in Task 5. The step record and the replay format do not change. **The runner's behaviour and its existing tests do not change** (Task 1 only moves code).
- **Money and safety rules of `run` hold for `live`:** the cap is per paid player and defaults to 0; a live paid run on a seed below 1000 is refused without `--tournament`; keys are never printed; the server binds to loopback, answers only its own host names, and serves no file.
- Every code block below was run in a prototype and passes as written (final state: 291 fast tests, 9 deselected). A free live run (`solver,random,always_jump`) was watched in a browser: the page streams, plays, shows the final scoreboard, and the directory replays with `bakeoff view`. If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **The run waits for a browser.** `live` prints the address and starts when the first listener connects to the stream, so nothing paid happens unwatched; afterwards it keeps serving until Ctrl-C, so the page can be reloaded. `--no-wait` does neither (tests, scripts).
2. **History is replayed to every listener** (`Broadcast`): a page that connects late or reconnects gets every event again and `feed.js` drops what it has. No event ids, no resume protocol.
3. **The port is bound before anything is written** (`serve(None, ...)`, then `server.page = ...`; `/` answers 503 in between), so a busy port leaves no run directory behind.
4. **The `episode` event is sent just before the player's first frame,** not at the start: only then are its `questions` known, and a runner without a frame cannot be placed anyway.
5. **The stream is checked against the replay, not against a description of it:** a test asserts that the frames sent equal the frames `build_replay` reads from the directory afterwards.
6. **Ending:** `completed`; `budget_exhausted` or `aborted` (more than 5 consecutive provider errors, as the runner) with an `error` event before `end`; Ctrl-C is `interrupted` and exits 1 without a traceback; any other exception is our bug: the directory is closed as `interrupted` and the exception is raised.
7. **The server answers only `Host: 127.0.0.1:<port>` or `localhost:<port>`** (a DNS name rebound to loopback gets 403), sends no CORS header (another origin cannot read the stream), and implements GET only.
8. **`meta.json` of a live run** is the runner's (`new_meta`) with `seeds: [seed]` and `args.command: "live"`.
9. **In a live run every runner that arrives is shown** (the operator chose who plays); the default-three filter applies to replay files only. One line of `viewer/app.js`.
10. **One fly brain:** `LiveRun` calls each player's `reset` once and `close` once; that no second fly process runs next to it stays the operator's rule, and the CLI help and README say so.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/runner.py`, `bakeoff/replay.py`, their tests | `play_row`, `new_meta`, `frame_of`, `summary_of` extracted; behaviour unchanged | 1 |
| `bakeoff/live.py`, `tests/test_live_run.py` | `Broadcast`, `LiveRun` | 2 |
| `bakeoff/live_server.py`, `bakeoff/view.py`, `tests/test_live_server.py` | the loopback server; `render_html(..., live=)` | 3 |
| `bakeoff/__main__.py`, `tests/test_cli_live.py` | the `live` command | 4 |
| `viewer/app.js`, `README.md`, `CLAUDE.md`, `docs/REPLAY_DATA.md` | every live runner is shown; documents | 5 |
| `docs/COSTS.md`, `docs/DECISIONS.md`, `CLAUDE.md` | the real go-live run (controller) | 6 |

(`tests/test_live.py` already exists and holds the opt-in provider tests of phase 3; the new test files are named after what they test.)

---

### Task 1: One builder for records, one for frames

**Files:**
- Modify: `bakeoff/replay.py`
- Modify: `bakeoff/runner.py`
- Test: `tests/test_replay.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Produces: `bakeoff.runner.play_row(player, game, seed, run_id, first) -> dict` (asks, applies the fallback rule, steps the game, returns the step record), `bakeoff.runner.new_meta(run_id, players, seeds, max_rows, args) -> dict`, `bakeoff.replay.frame_of(step, lanes, questions) -> dict` (appends a new question set to `questions`), `bakeoff.replay.summary_of(last_step) -> {complete, finished, death_cause, rows_survived}`. `Runner` and `build_replay` use them; nothing they return changes.

No existing test is edited: that is how this task shows that the runner's behaviour did not change.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_replay.py`:

```diff
@@ -205,3 +205,17 @@ def test_a_run_without_meta_is_named_after_its_directory(tmp_path):
 def test_a_missing_run_directory_raises(tmp_path):
     with pytest.raises(FileNotFoundError, match="no such run directory"):
         build_replay([tmp_path / "nope"])
+
+
+def test_frame_of_and_summary_of_are_the_pieces_the_replay_is_built_from(tmp_path):
+    from bakeoff.replay import frame_of, summary_of
+
+    questions_a = {"action": {"type": "choice"}}
+    steps = [record(row=0, track=TRACK, questions=questions_a), record(row=1, questions=questions_a, **DIED)]
+    run_dir = write_run(tmp_path, "a", steps)
+    (episode,) = build_replay([run_dir])["episodes"]
+    questions: list[dict] = []
+    assert [frame_of(s, 12, questions) for s in steps] == episode["frames"]
+    assert questions == episode["questions"] == [questions_a]
+    assert summary_of(steps[-1]) == {k: episode[k] for k in ("complete", "finished", "death_cause", "rows_survived")}
+    assert summary_of(steps[0])["complete"] is False
```

Apply to `tests/test_runner.py`:

```diff
@@ -242,3 +242,33 @@ def test_run_ending_exceptions_live_in_errors_and_are_re_exported_by_the_runner(
 
     assert runner.RunAborted is errors.RunAborted and runner.BudgetExhausted is errors.BudgetExhausted
     assert errors.BudgetExhausted.status == "budget_exhausted" and errors.RunAborted.status == "aborted"
+
+
+def test_play_row_is_one_decision_one_move_and_the_record_the_runner_writes(tmp_path):
+    from bakeoff.game.engine import Game
+    from bakeoff.game.track import generate_track
+    from bakeoff.runner import play_row
+
+    solver = make_player("solver")
+    game = Game(generate_track(3, max_rows=30))
+    solver.reset(game, 3)
+    first = play_row(solver, game, 3, "r", first=True)
+    second = play_row(solver, game, 3, "r", first=False)
+    assert first["row"] == 0 and first["track"] == game.track.to_json() and second["track"] is None
+    assert second["row"] == first["row"] + (2 if first["executed_action"] == "jump" else 1) == game.row - (
+        2 if second["executed_action"] == "jump" else 1)
+    fresh = make_player("solver")
+    records = Runner(tmp_path).run_seed(fresh, 3, "r", max_rows=30)
+    assert records[:2] == [first, second]  # the runner's records are play_row's, key for key
+
+
+def test_new_meta_is_what_run_writes_first(tmp_path):
+    from bakeoff.runner import new_meta
+
+    players = [make_player("solver")]
+    meta = new_meta("r", players, [5], 40, {"x": 1})
+    run_dir = Runner(tmp_path).run(players, [5], max_rows=40, run_id="r", args={"x": 1})
+    written = json.loads((run_dir / "meta.json").read_text())
+    assert meta["status"] == "running" and meta["finished_at"] is None
+    for key in ("run_id", "schema_version", "players", "seeds", "game", "fly", "models", "args", "versions"):
+        assert written[key] == meta[key]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_runner.py tests/test_replay.py`
Expected:

```text
FAILED tests/test_runner.py::test_play_row_is_one_decision_one_move_and_the_record_the_runner_writes
FAILED tests/test_runner.py::test_new_meta_is_what_run_writes_first - ImportE...
FAILED tests/test_replay.py::test_frame_of_and_summary_of_are_the_pieces_the_replay_is_built_from
3 failed, 48 passed
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/replay.py`:

```diff
@@ -30,6 +30,27 @@ def landing(row: int, lane: int, executed_action: str, lanes: int) -> list[int]:
     return [row + advance, (lane + shift) % lanes]
 
 
+def frame_of(step: dict, lanes: int, questions: list[dict]) -> dict:
+    """A step record as a frame (docs/REPLAY_DATA.md). `questions` is the episode's list of distinct
+    question sets; a set not seen before is appended to it and the frame points at it with `q`."""
+    frame = {k: v for k, v in step.items() if k not in DROPPED}
+    frame["ahead"] = [entry["gaps_relative"] for entry in step["senses"]["ahead"]]
+    frame["landing"] = landing(step["row"], step["lane"], step["executed_action"], lanes)
+    frame["q"] = None
+    if step.get("questions") is not None:
+        if step["questions"] not in questions:
+            questions.append(step["questions"])
+        frame["q"] = questions.index(step["questions"])
+    return frame
+
+
+def summary_of(last: dict) -> dict:
+    """How an episode stands after its latest record. A run cut off mid-way (abort, budget stop,
+    Ctrl-C) is incomplete, not a death; so is a live run that is still going."""
+    return {"complete": bool(last["finished"] or not last["alive"]), "finished": last["finished"],
+            "death_cause": last["death_cause"], "rows_survived": last["rows_survived"]}
+
+
 def _episode(player: str, seed: int, run_id: str, steps: list[dict]) -> tuple[dict, dict | None]:
     steps = sorted(steps, key=lambda s: s["row"])
     for prev, cur in zip(steps, steps[1:]):
@@ -38,24 +59,9 @@ def _episode(player: str, seed: int, run_id: str, steps: list[dict]) -> tuple[di
     track = next((s["track"] for s in steps if s.get("track")), None)
     lanes = track["lanes"] if track else steps[0]["senses"]["lanes"]
     questions: list[dict] = []
-    frames = []
-    for s in steps:
-        frame = {k: v for k, v in s.items() if k not in DROPPED}
-        frame["ahead"] = [entry["gaps_relative"] for entry in s["senses"]["ahead"]]
-        frame["landing"] = landing(s["row"], s["lane"], s["executed_action"], lanes)
-        frame["q"] = None
-        if s.get("questions") is not None:
-            if s["questions"] not in questions:
-                questions.append(s["questions"])
-            frame["q"] = questions.index(s["questions"])
-        frames.append(frame)
-    last = steps[-1]
-    episode = {"player": player, "seed": seed, "run_id": run_id,
-               # a run cut off mid-way (abort, budget stop, Ctrl-C) is incomplete, not a death
-               "complete": bool(last["finished"] or not last["alive"]),
-               "finished": last["finished"], "death_cause": last["death_cause"],
-               "rows_survived": last["rows_survived"], "max_rows": track["max_rows"] if track else None,
-               "questions": questions, "frames": frames}
+    frames = [frame_of(s, lanes, questions) for s in steps]
+    episode = {"player": player, "seed": seed, "run_id": run_id, **summary_of(steps[-1]),
+               "max_rows": track["max_rows"] if track else None, "questions": questions, "frames": frames}
     return episode, track
 
 
```

Replace the whole of `bakeoff/runner.py` with:

```python
"""Players x seeds, fallback rule, streaming JSONL step log and meta.json run status."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Callable, Sequence

from bakeoff.errors import BudgetExhausted, PreflightError, RunAborted  # noqa: F401  (re-exported)
from bakeoff.fly import data as fly_data
from bakeoff.fly.reading import WINDOW_MS
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import LANES, LOOKAHEAD, MAX_ROWS, generate_track
from bakeoff.players import fly
from bakeoff.players.base import Player
from bakeoff.players.solver import solve_depths
from bakeoff.senses import (LOOMING_FALLOFF, LOOMING_GAIN_HZ, LOOMING_STEP_HZ, MAX_HZ, WINDOW, compute_senses,
                            ground_truth, looming_rates)

SCHEMA_VERSION = 1
FALLBACK_ACTION = "stay"  # never the solver's move: a rescue would hide what we want to see


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _git(*args: str) -> str | None:
    """Run git in the package's directory, so the answer does not depend on where the CLI started."""
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except Exception:
        return None


def _git_sha() -> str | None:
    return _git("rev-parse", "HEAD")


def _git_dirty() -> bool | None:
    status = _git("status", "--porcelain")
    return None if status is None else bool(status)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _preflight(players: list[Player]) -> None:
    """Players may define preflight(): a check that they can start at all. It runs before the run
    directory exists, so a usage error (no fly data, no key) leaves nothing behind."""
    for player in players:
        check = getattr(player, "preflight", None)
        if check is None:
            continue
        try:
            check()
        except (OSError, ValueError) as e:
            raise PreflightError(f"{player.name}: {e}") from e


def _requests(players: list[Player]) -> dict:
    """Live requests spent against each paid player's cap (failed requests included)."""
    return {p.name: {"max": p.budget.max_requests, "used": p.budget.used}
            for p in players if getattr(p, "budget", None) is not None}


def play_row(player: Player, game: Game, seed: int, run_id: str, first: bool) -> dict:
    """One decision and one move: asks the player, applies the fallback rule, steps the game and
    returns the step record. The runner and the live loop both build their records here, so a
    live run's log is a normal log. `first`: the episode's first record carries the track."""
    senses = compute_senses(game)
    left_hz, right_hz = looming_rates(senses)
    truth = ground_truth(game)
    depths = solve_depths(senses)
    row, lane = game.row, game.lane
    decision = player.act(senses)
    invalid = decision.invalid or (
        decision.chosen_action is not None and decision.chosen_action not in ACTIONS)
    executed = FALLBACK_ACTION if decision.needs_fallback or invalid else decision.chosen_action
    game.step(executed)
    player.observe(executed)
    return {
        "run_id": run_id, "player": player.name, "seed": seed, "row": row, "lane": lane,
        "senses": senses, "looming": {"left_hz": left_hz, "right_hz": right_hz},
        "questions": decision.questions, "answers": decision.answers,
        "chosen_action": decision.chosen_action, "executed_action": executed,
        "solver_action": max(depths, key=depths.get), "solver_depths": depths,
        "gated": decision.gated, "invalid": invalid, "error": decision.error,
        "ground_truth": truth, "alive": game.alive, "finished": game.finished, "death_cause": game.death_cause,
        "rows_survived": game.rows_survived, "latency_ms": decision.latency_ms,
        "usage": decision.usage, "cache_hit": decision.cache_hit, "info": decision.info,
        "track": game.track.to_json() if first else None,
    }


def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], max_rows: int, args: dict | None) -> dict:
    """meta.json as a run starts: status `running`, no finish time yet."""
    return {
        "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
        "started_at": _now(), "finished_at": None, "status": "running",
        "players": [p.name for p in players], "seeds": list(seeds),
        "game": {"lanes": LANES, "max_rows": max_rows, "lookahead": LOOKAHEAD, "window": WINDOW,
                 "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                             "max_hz": MAX_HZ, "provisional": not fly.CALIBRATED}},
        "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
                "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
        "models": {p.name: p.model for p in players if getattr(p, "model", None)},
        "requests": _requests(players),
        "args": args or {}, "python": platform.python_version(),
        "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic",
                                                     "python-dotenv")},
    }


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
            record = play_row(player, game, seed, run_id, first=not records)
            records.append(record)
            if sink is not None:
                sink(record)
            self._error_streak = self._error_streak + 1 if record["error"] is not None else 0
            if self._error_streak > self.max_consecutive_errors:
                raise RunAborted(f"{self._error_streak} consecutive player errors; last: {record['error']}")
        return records

    def run(self, players: list[Player], seeds: Sequence[int], max_rows: int = MAX_ROWS,
            run_id: str | None = None, args: dict | None = None) -> Path:
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:  # two players would write the same <name>.jsonl
            raise ValueError(f"duplicate player names: {duplicates}")
        _preflight(players)
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        run_dir = self.out_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        meta_path = run_dir / "meta.json"
        meta = new_meta(run_id, players, seeds, max_rows, args)
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
            meta["finished_at"] = _now()
            meta["requests"] = _requests(players)
            meta_path.write_text(json.dumps(meta, indent=2))
        return run_dir
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_runner.py tests/test_replay.py`
Expected: `51 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `270 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/replay.py bakeoff/runner.py tests/test_replay.py tests/test_runner.py
git commit -F <message file>   # refactor: the runner's record and meta builders and the replay's frame builder are functions of their own
```

---

### Task 2: The lockstep loop

**Files:**
- Create: `bakeoff/live.py`
- Test: `tests/test_live_run.py`

**Interfaces:**
- Consumes: Task 1's four functions; `runner._preflight`, `_close`, `_requests`, `_now`.
- Produces: `bakeoff.live.Broadcast` (`emit`, `close`, `listen(poll_seconds) -> iterator of (name, data) or None`, `wait_for_listener`, `closed`, `listeners`), `bakeoff.live.LiveRun(players, seed, out_root, max_rows, run_id, args, broadcast)` with `prepare() -> empty replay`, `run() -> run_dir`, `cancel()`, `status`, `error`, `run_dir`, `broadcast`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_live_run.py`:

```python
"""The lockstep loop of `bakeoff live`, with scripted players. No network, no fly brain."""

import json

import pytest

from bakeoff.errors import BudgetExhausted
from bakeoff.live import Broadcast, LiveRun
from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.replay import build_replay
from bakeoff.report import load_steps


class Scripted:
    """Always the same move; optionally stops like a paid player whose cap is reached."""

    def __init__(self, name, action, cap=None, error=None):
        self.name, self.action, self.cap, self.error, self.asked, self.closed = name, action, cap, error, 0, False

    def reset(self, game, seed): pass

    def act(self, senses):
        if self.cap is not None and self.asked >= self.cap:
            raise BudgetExhausted(f"request cap of {self.cap} reached")
        self.asked += 1
        if self.error:
            return Decision(None, error=self.error, questions={"q": 1})
        return Decision(self.action, questions={"q": 1})

    def observe(self, executed_action): pass

    def close(self): self.closed = True


def events_of(live):
    return list(e for e in live.broadcast.listen(poll_seconds=0.01) if e is not None)


def run_live(tmp_path, players, max_rows=40, seed=1001):
    live = LiveRun(players, seed, out_root=tmp_path, max_rows=max_rows, run_id="live", args={"port": 0})
    live.run()
    return live, events_of(live)


def test_everyone_plays_the_same_track_in_lockstep_and_a_jumper_skips_a_row(tmp_path):
    live, events = run_live(tmp_path, [make_player("solver"), Scripted("jumper", "jump"), Scripted("stayer", "stay")])
    frames = [(data["frame"]["row"], data["player"]) for name, data in events if name == "frame"]
    assert [row for row, _ in frames] == sorted(row for row, _ in frames)  # nobody decides row 5 before everybody decided row 4
    assert [row for row, player in frames if player == "jumper"][:4] == [0, 2, 4, 6]  # in the air over the odd rows
    assert [player for row, player in frames if row == 0] == ["solver", "jumper", "stayer"]  # the order given
    tracks = [data["track"] for name, data in events if name == "episode"]
    assert len(tracks) == 3 and tracks[0] == tracks[1] == tracks[2] and tracks[0]["seed"] == 1001


def test_the_stream_is_the_replay_in_the_replays_own_shapes(tmp_path):
    live, events = run_live(tmp_path, [make_player("solver"), Scripted("stayer", "stay")])
    replay = build_replay([live.run_dir])  # what `bakeoff view` would show afterwards
    for episode in replay["episodes"]:
        name = episode["player"]
        (header,) = [d for n, d in events if n == "episode" and d["episode"]["player"] == name]
        sent = [d for n, d in events if n == "frame" and d["player"] == name]
        assert [d["frame"] for d in sent] == episode["frames"]
        assert sent[-1]["summary"] == {k: episode[k] for k in ("complete", "finished", "death_cause", "rows_survived")}
        assert header["episode"]["questions"] == episode["questions"] and header["episode"]["max_rows"] == 40
        assert header["track"] == replay["tracks"]["1001"]
        assert set(header["episode"]) == set(episode) - {"frames"}
    assert events[0][0] == "episode" and events[1][0] == "frame"  # a runner is announced, then it moves
    name, end = events[-1]
    assert name == "end" and end == {"status": "completed", "runs": replay["runs"], "scoreboard": replay["scoreboard"]}
    json.dumps(events)


def test_the_directory_is_a_normal_completed_run(tmp_path):
    live, _ = run_live(tmp_path, [make_player("solver"), Scripted("stayer", "stay")])
    meta = json.loads((live.run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["finished_at"] and meta["players"] == ["solver", "stayer"]
    assert meta["seeds"] == [1001] and meta["args"] == {"port": 0} and meta["game"]["max_rows"] == 40
    steps = load_steps(live.run_dir)
    finals = {p: [s for s in steps if s["player"] == p][-1] for p in ("solver", "stayer")}
    assert finals["solver"]["finished"] and finals["solver"]["rows_survived"] == 40
    assert not finals["stayer"]["alive"] and finals["stayer"]["death_cause"] == "ran_into_gap"
    assert all(p.closed for p in live.players if hasattr(p, "closed"))


def test_a_cap_stops_everyone_and_leaves_a_valid_incomplete_run(tmp_path):
    capped = Scripted("paid", "stay", cap=3)
    live, events = run_live(tmp_path, [make_player("solver"), capped])
    assert live.status == "budget_exhausted" and live.error == "request cap of 3 reached"
    assert [name for name, _ in events[-2:]] == ["error", "end"]
    assert events[-2][1] == {"message": "request cap of 3 reached"} and events[-1][1]["status"] == "budget_exhausted"
    assert json.loads((live.run_dir / "meta.json").read_text())["status"] == "budget_exhausted"
    replay = build_replay([live.run_dir])
    assert [(e["player"], e["complete"], len(e["frames"])) for e in replay["episodes"]] == [("solver", False, 4), ("paid", False, 3)]
    assert capped.closed


def test_a_provider_that_keeps_failing_aborts_the_run(tmp_path):
    live, events = run_live(tmp_path, [Scripted("paid", "stay", error="HTTPError: 503")])
    assert live.status == "aborted" and "6 consecutive player errors" in events[-2][1]["message"]


def test_ctrl_c_is_an_interrupted_run_not_a_crash(tmp_path):
    class Interrupting(Scripted):
        def act(self, senses):
            if self.asked == 2:
                raise KeyboardInterrupt
            return super().act(senses)

    live, events = run_live(tmp_path, [Interrupting("fly", "stay")])
    assert live.status == "interrupted" and events[-1][0] == "end" and events[-1][1]["status"] == "interrupted"
    assert len(load_steps(live.run_dir)) == 2


def test_our_own_bug_still_closes_the_run_and_is_raised(tmp_path):
    class Buggy(Scripted):
        def act(self, senses): raise RuntimeError("our bug")

    live = LiveRun([Buggy("b", "stay")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    with pytest.raises(RuntimeError, match="our bug"):
        live.run()
    assert json.loads((live.run_dir / "meta.json").read_text())["status"] == "interrupted" and live.broadcast.closed


def test_prepare_gives_the_page_an_empty_replay_that_names_the_run(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    replay = live.prepare()
    assert replay["episodes"] == [] and replay["seeds"] == [1001] and replay["scoreboard"]["rows"] == []
    (run,) = replay["runs"]
    assert run["run_id"] == "live" and run["status"] == "running" and run["game"]["lookahead"] == 6
    assert (live.run_dir / "meta.json").is_file()


def test_usage_errors_leave_no_directory(tmp_path):
    with pytest.raises(ValueError, match="duplicate player names"):
        LiveRun([make_player("solver"), make_player("solver")], 1001, out_root=tmp_path)

    class Unready(Scripted):
        def preflight(self): raise ValueError("TYPESAFE_API_KEY is not set")

    live = LiveRun([Unready("paid", "stay")], 1001, out_root=tmp_path, run_id="live")
    with pytest.raises(ValueError, match="paid: TYPESAFE_API_KEY is not set"):
        live.prepare()
    assert not (tmp_path / "live").exists()


def test_a_late_listener_gets_the_whole_history_and_a_quiet_one_gets_keep_alives():
    broadcast = Broadcast()
    broadcast.emit("frame", {"n": 1})
    listener = broadcast.listen(poll_seconds=0.01)
    assert next(listener) == ("frame", {"n": 1})
    assert next(listener) is None  # nothing new: time for a keep-alive
    broadcast.emit("end", {"status": "completed"})
    broadcast.close()
    assert list(listener) == [("end", {"status": "completed"})]
    assert list(broadcast.listen()) == [("frame", {"n": 1}), ("end", {"status": "completed"})]


def test_cancelling_before_the_run_began_leaves_an_interrupted_run_with_no_logs(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    live.prepare()
    live.cancel()
    meta = json.loads((live.run_dir / "meta.json").read_text())
    assert meta["status"] == "interrupted" and meta["finished_at"] and live.broadcast.closed
    assert list(live.run_dir.glob("*.jsonl")) == []
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_live_run.py`
Expected:

```text
ERROR tests/test_live_run.py
1 error
```

- [ ] **Step 3: Write the implementation**

Create `bakeoff/live.py`:

```python
"""`bakeoff live`: the minds play one track in real time, in lockstep by row, and every decision is
written to a normal run directory and sent to the page as it happens.

`Broadcast` holds the events so far, for any number of listeners; `LiveRun` is the lockstep loop."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Iterator

from bakeoff.errors import RunAborted
from bakeoff.game.engine import Game
from bakeoff.game.track import MAX_ROWS, generate_track
from bakeoff.players.base import Player
from bakeoff.replay import META_KEYS, REPLAY_VERSION, build_replay, frame_of, summary_of
from bakeoff.report import COLUMNS
from bakeoff.runner import _close, _now, _preflight, _requests, new_meta, play_row

MAX_CONSECUTIVE_ERRORS = 5  # as the runner: a provider that keeps failing ends the run


class Broadcast:
    """Every event of the run, in order. A listener gets the history first and then waits for more,
    so a page that connects late, or reconnects, misses nothing. Thread-safe."""

    def __init__(self):
        self._events: list[tuple[str, dict]] = []
        self._changed = threading.Condition()
        self.closed = False
        self.listeners = 0

    def emit(self, name: str, data: dict) -> None:
        with self._changed:
            self._events.append((name, data))
            self._changed.notify_all()

    def close(self) -> None:
        with self._changed:
            self.closed = True
            self._changed.notify_all()

    def wait_for_listener(self, timeout: float | None = None) -> bool:
        with self._changed:
            return self._changed.wait_for(lambda: self.listeners > 0 or self.closed, timeout)

    def listen(self, poll_seconds: float = 15.0) -> Iterator[tuple[str, dict] | None]:
        """Yields (name, data); None when nothing happened for `poll_seconds` (time for a keep-alive).
        Ends after the last event once the broadcast is closed."""
        sent = 0
        with self._changed:
            self.listeners += 1
            self._changed.notify_all()
        while True:
            with self._changed:
                if sent >= len(self._events) and not self.closed:
                    self._changed.wait(poll_seconds)
                batch, done = self._events[sent:], self.closed
            if not batch and done:
                return
            if not batch:
                yield None
            for event in batch:
                yield event
            sent += len(batch)


class LiveRun:
    """One track, every player on it at once. Each tick every player that stands on this row decides;
    a jumper stands two rows on and skips the next tick; the slowest mind sets the pace. Records are
    the runner's own (`play_row`), so the directory is a normal run and `bakeoff view` plays it."""

    def __init__(self, players: list[Player], seed: int, out_root: Path | str = "runs", max_rows: int = MAX_ROWS,
                 run_id: str | None = None, args: dict | None = None, broadcast: Broadcast | None = None):
        names = [p.name for p in players]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate player names: {duplicates}")
        self.players, self.seed, self.max_rows = players, seed, max_rows
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(out_root) / self.run_id
        self.args = args or {}
        self.broadcast = broadcast if broadcast is not None else Broadcast()
        self.status = "running"
        self.error: str | None = None  # why the run stopped early, when a cap or a failing provider stopped it
        self.meta: dict | None = None

    def prepare(self) -> dict:
        """Preflight, the run directory and meta.json. Returns the empty replay the page starts from."""
        _preflight(self.players)
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.meta = new_meta(self.run_id, self.players, [self.seed], self.max_rows, self.args)
        self._write_meta()
        return {"replay_version": REPLAY_VERSION,
                "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}],
                "players": [], "seeds": [self.seed], "tracks": {}, "episodes": [],
                "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": [], "same_seeds": True}}

    def cancel(self) -> None:
        """The operator gave up before the run began (Ctrl-C while waiting for a browser)."""
        self.status = "interrupted"
        self.meta.update(status=self.status, finished_at=_now())
        self._write_meta()
        self.broadcast.close()

    def _write_meta(self) -> None:
        (self.run_dir / "meta.json").write_text(json.dumps(self.meta, indent=2))

    def run(self) -> Path:
        if self.meta is None:
            self.prepare()
        track = generate_track(self.seed, max_rows=self.max_rows)
        games = {p.name: Game(track) for p in self.players}
        questions: dict[str, list[dict]] = {p.name: [] for p in self.players}
        started: set[str] = set()
        logs = {p.name: open(self.run_dir / f"{p.name}.jsonl", "w") for p in self.players}
        streak = 0
        try:
            for player in self.players:
                player.reset(games[player.name], self.seed)
            row = 0
            while not all(game.over for game in games.values()):
                for player in self.players:
                    game = games[player.name]
                    if game.over or game.row != row:
                        continue  # fallen, finished, or in the air over this row
                    record = play_row(player, game, self.seed, self.run_id, first=player.name not in started)
                    logs[player.name].write(json.dumps(record) + "\n")
                    logs[player.name].flush()
                    frame = frame_of(record, track.lanes, questions[player.name])
                    if player.name not in started:
                        started.add(player.name)
                        self.broadcast.emit("episode", {
                            "episode": {"player": player.name, "seed": self.seed, "run_id": self.run_id,
                                        "complete": False, "finished": False, "death_cause": None, "rows_survived": 0,
                                        "max_rows": self.max_rows, "questions": questions[player.name]},
                            "track": track.to_json()})
                    self.broadcast.emit("frame", {"player": player.name, "seed": self.seed, "frame": frame,
                                                  "summary": summary_of(record)})
                    streak = streak + 1 if record["error"] is not None else 0
                    if streak > MAX_CONSECUTIVE_ERRORS:
                        raise RunAborted(f"{streak} consecutive player errors; last: {record['error']}")
                row += 1
            self.status = "completed"
        except RunAborted as abort:  # a cap was reached (budget_exhausted) or a provider kept failing
            self.status, self.error = abort.status, str(abort)
            self.broadcast.emit("error", {"message": self.error})
        except BaseException as e:  # Ctrl-C, or our bug: the directory is still a valid, incomplete run
            self.status = "interrupted"
            if not isinstance(e, KeyboardInterrupt):
                raise
        finally:
            for log in logs.values():
                log.close()
            for player in self.players:
                _close(player)
            self.meta.update(status=self.status, finished_at=_now(), requests=_requests(self.players))
            self._write_meta()
            replay = build_replay([self.run_dir])
            self.broadcast.emit("end", {"status": self.status, "runs": replay["runs"], "scoreboard": replay["scoreboard"]})
            self.broadcast.close()
        return self.run_dir
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_live_run.py`
Expected: `11 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `281 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live.py tests/test_live_run.py
git commit -F <message file>   # feat: LiveRun: every mind decides the same row before anyone moves on, recorded and broadcast as it happens
```

---

### Task 3: The loopback server and the live page

**Files:**
- Create: `bakeoff/live_server.py`
- Modify: `bakeoff/view.py`
- Test: `tests/test_live_server.py`

**Interfaces:**
- Consumes: `Broadcast.listen`.
- Produces: `bakeoff.live_server.serve(page, broadcast, port) -> ThreadingHTTPServer` (daemon thread; `server.page` may be set later), `EVENTS_PATH` (`/events`), `HOST` (`127.0.0.1`); `bakeoff.view.render_html(replay, viewer_dir, live=None)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_live_server.py`:

```python
"""The loopback server of `bakeoff live`, on an ephemeral port with a broadcast filled by hand.
The only connections are to 127.0.0.1, to the server under test."""

import http.client
import json
import re

import pytest

from bakeoff.live import Broadcast
from bakeoff.live_server import EVENTS_PATH, serve
from bakeoff.view import render_html

REPLAY = {"replay_version": 1, "runs": [{"run_id": "live"}], "players": [], "seeds": [1001], "tracks": {}, "episodes": []}


@pytest.fixture
def server():
    broadcast = Broadcast()
    httpd = serve(render_html(REPLAY, live=EVENTS_PATH), broadcast, port=0)
    yield httpd, broadcast
    broadcast.close()
    httpd.shutdown()
    httpd.server_close()


def get(httpd, path, host=None):
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("GET", path, headers={"Host": host} if host else {})
    response = connection.getresponse()
    body = response.read().decode()
    connection.close()
    return response, body


def test_the_live_page_is_the_player_with_an_empty_replay_and_the_stream_address():
    page = render_html(REPLAY, live=EVENTS_PATH)
    assert '<body data-live="/events">' in page
    assert "data-live" not in render_html(REPLAY)  # a replay file never looks for a server
    (data,) = re.findall(r'<script type="application/json" id="replay-data">(.*?)</script>', page, re.S)
    assert json.loads(data) == REPLAY
    with pytest.raises(ValueError, match="live must be a path"):
        render_html(REPLAY, live='"><script>')


def test_it_binds_to_loopback_only_and_serves_the_page(server):
    httpd, _ = server
    assert httpd.server_address[0] == "127.0.0.1"
    response, body = get(httpd, "/")
    assert response.status == 200 and response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert '<body data-live="/events">' in body and response.getheader("Cache-Control") == "no-store"


def test_the_stream_sends_the_history_as_server_sent_events_and_ends_with_the_run(server):
    httpd, broadcast = server
    broadcast.emit("episode", {"episode": {"player": "fly"}, "track": {"seed": 1001}})
    broadcast.emit("frame", {"player": "fly", "seed": 1001, "frame": {"row": 0, "answers": {"text": "line\nbreak </script>"}}})
    broadcast.emit("end", {"status": "completed"})
    broadcast.close()
    response, body = get(httpd, EVENTS_PATH)
    assert response.status == 200 and response.getheader("Content-Type") == "text/event-stream"
    assert response.getheader("Access-Control-Allow-Origin") is None  # other origins cannot read the stream
    events = [block.split("\n") for block in body.strip().split("\n\n")]
    assert [lines[0] for lines in events] == ["event: episode", "event: frame", "event: end"]
    assert all(len(lines) == 2 and lines[1].startswith("data: ") for lines in events)  # one line each, whatever the log says
    assert json.loads(events[1][1][6:])["frame"]["answers"]["text"] == "line\nbreak </script>"


def test_the_port_can_be_bound_before_the_page_exists():
    httpd = serve(None, Broadcast(), port=0)
    try:
        assert get(httpd, "/")[0].status == 503
        httpd.page = "<p>ready</p>"
        assert get(httpd, "/")[1] == "<p>ready</p>"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_nothing_else_is_served(server):
    httpd, _ = server
    assert get(httpd, "/runs/")[0].status == 404
    assert get(httpd, "/../pyproject.toml")[0].status == 404
    assert get(httpd, "/", host="evil.example")[0].status == 403  # a rebound DNS name is not us
    assert get(httpd, "/", host=f"localhost:{httpd.server_address[1]}")[0].status == 200
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("POST", "/", body="x")
    assert connection.getresponse().status == 501
    connection.close()
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_live_server.py`
Expected:

```text
ERROR tests/test_live_server.py
1 error
```

- [ ] **Step 3: Write the implementation**

Create `bakeoff/live_server.py`:

```python
"""The server of `bakeoff live`: loopback only, standard library only. It serves the player page and
the event stream (Server-Sent Events) and nothing else: no files, no other method, no other host."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bakeoff.live import Broadcast

EVENTS_PATH = "/events"
HOST = "127.0.0.1"


def serve(page: str | None, broadcast: Broadcast, port: int = 8000) -> ThreadingHTTPServer:
    """Starts serving in a daemon thread and returns the server (`shutdown()` stops it). Port 0 picks a
    free one. The port is bound before anything is written to disk, so the page may come later: set
    `server.page`; until then `/` answers 503."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (the base class names it)
            names = {f"{HOST}:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}"}
            if self.headers.get("Host") not in names:
                return self.send_error(403)  # a page elsewhere that points a DNS name at us gets nothing
            if self.path == "/" and self.server.page is None:
                self.send_error(503)
            elif self.path == "/":
                body = self.server.page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif self.path == EVENTS_PATH:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    for event in broadcast.listen():
                        if event is None:
                            self.wfile.write(b": keep-alive\n\n")
                        else:
                            name, data = event  # json.dumps escapes every newline, so an event is always two lines
                            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the page was closed
            else:
                self.send_error(404)

        def log_message(self, format, *args):  # noqa: A002
            pass  # the terminal belongs to the run's own output

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    httpd.page = page
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
```

Apply to `bakeoff/view.py`:

```diff
@@ -40,11 +40,19 @@ def _stylesheet(path: Path) -> str:
     return _CSS_URL.sub(embed, css)
 
 
-def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR) -> str:
+def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | None = None) -> str:
+    """`live`: the path of the event stream of `bakeoff live`. The page then also listens there; a
+    replay file has no such attribute and never looks for a server."""
     viewer_dir = Path(viewer_dir)
     page = (viewer_dir / "index.html").read_text(encoding="utf-8")
     if page.count(DATA_SLOT) != 1:
         raise ValueError(f"{viewer_dir / 'index.html'} must contain the replay data slot exactly once")
+    if live is not None:
+        if not re.fullmatch(r"/[a-z]+", live):
+            raise ValueError(f"live must be a path like /events, not {live!r}")
+        if page.count("<body>") != 1:
+            raise ValueError(f"{viewer_dir / 'index.html'} must contain <body> exactly once")
+        page = page.replace("<body>", f'<body data-live="{live}">')
     # lambdas, so that a backslash in a file is never read as a regex group reference
     page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
     page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_live_server.py`
Expected: `5 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `286 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live_server.py bakeoff/view.py tests/test_live_server.py
git commit -F <message file>   # feat: a loopback server for the page and its event stream; render_html can mark the page as live
```

---

### Task 4: The `live` command

**Files:**
- Modify: `bakeoff/__main__.py`
- Test: `tests/test_cli_live.py`

**Interfaces:**
- Consumes: `LiveRun`, `serve`, `render_html(live=)`.
- Produces: `python -m bakeoff live [--players] [--seed] [--max-rows] [--out] [--max-requests] [--cache] [--tournament] [--port] [--no-wait]`; `_players` and `_spends_on_tournament_seeds` shared with `run`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_live.py`:

```python
"""`bakeoff live` from the command line, with free players only. `--no-wait` neither waits for a
browser before the run nor keeps serving after it."""

import json
import socket

from bakeoff.__main__ import _parser, main


def live_args(tmp_path, *extra, players="solver,random"):
    return ["live", "--players", players, "--max-rows", "30", "--port", "0", "--no-wait",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]


def test_the_defaults_are_the_demos_three_on_a_practice_seed_with_no_budget():
    args = _parser().parse_args(["live"])
    assert (args.players, args.seed, args.max_requests, args.port, args.tournament) == ("fly,jev_composed,llm", 1001, 0, 8000, False)


def test_a_live_run_leaves_a_normal_run_directory_and_prints_where_to_watch(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001")) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "status: completed" in out and "| solver |" in out
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["command"] == "live" and meta["args"]["max_requests"] == 0
    assert main(["view", str(run_dir), "--output", str(tmp_path / "replay.html")]) == 0  # and it replays afterwards


def test_a_paid_cap_on_a_tournament_seed_is_refused_before_anything_exists(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "7", "--max-requests", "5", players="solver,jev_composed")) == 2
    assert "paid players may not spend requests on seeds below 1000" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_without_a_cap_a_paid_player_can_only_replay_the_cache(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", players="solver,jev_composed")) == 1
    captured = capsys.readouterr()
    assert "run budget_exhausted: request cap of 0 reached" in captured.err
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert json.loads((run_dir / "meta.json").read_text())["requests"] == {"jev_composed": {"max": 0, "used": 0}}


def test_usage_errors(tmp_path, capsys):
    assert main(live_args(tmp_path, players="solver,nobody")) == 2
    assert "unknown player 'nobody'" in capsys.readouterr().err
    assert main(live_args(tmp_path, players="solver,solver")) == 2
    assert "duplicate player names" in capsys.readouterr().err
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        args = [a if a != "0" else str(taken.getsockname()[1]) for a in live_args(tmp_path)]
        assert main(args) == 2
        assert "cannot listen on 127.0.0.1:" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_cli_live.py`
Expected:

```text
FAILED tests/test_cli_live.py::test_the_defaults_are_the_demos_three_on_a_practice_seed_with_no_budget
FAILED tests/test_cli_live.py::test_a_live_run_leaves_a_normal_run_directory_and_prints_where_to_watch
FAILED tests/test_cli_live.py::test_a_paid_cap_on_a_tournament_seed_is_refused_before_anything_exists
FAILED tests/test_cli_live.py::test_without_a_cap_a_paid_player_can_only_replay_the_cache
FAILED tests/test_cli_live.py::test_usage_errors - SystemExit: 2
5 failed
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `bakeoff/__main__.py` with:

```python
"""uv run python -m bakeoff run|report|view|live"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
from bakeoff.game.track import MAX_ROWS
from bakeoff.live import LiveRun
from bakeoff.live_server import EVENTS_PATH, HOST, serve
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.replay import build_replay
from bakeoff.report import format_table, load_meta, load_steps, summarize
from bakeoff.runner import RunAborted, Runner
from bakeoff.view import render_html

# tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
FIRST_PRACTICE_SEED = 1000


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
    run.add_argument("--max-requests", type=int, default=0,
                     help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only replays "
                          "the cache. Worst case a run spends this many requests per paid player")
    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    run.add_argument("--tournament", action="store_true",
                     help="allows live paid requests on seeds below 1000; for the phase 5 tournament only")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
    live = sub.add_parser("live", help="play one track in real time and watch it in the browser (loopback only); "
                                       "the run is recorded like any other")
    live.add_argument("--players", default="fly,jev_composed,llm", help=f"comma-separated; available: {sorted(REGISTRY)}")
    live.add_argument("--seed", type=int, default=1001, help="the track; practice seeds are 1000 and up")
    live.add_argument("--max-rows", type=int, default=MAX_ROWS)
    live.add_argument("--out", default="runs")
    live.add_argument("--max-requests", type=int, default=0,
                      help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only "
                           "replays the cache, which makes a free live run of a track that was already played")
    live.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    live.add_argument("--tournament", action="store_true", help="allows live paid requests on seeds below 1000")
    live.add_argument("--port", type=int, default=8000, help="the page is served on 127.0.0.1 only (default port 8000)")
    live.add_argument("--no-wait", action="store_true",
                      help="do not wait for a browser before the run, and do not keep serving after it")
    return parser


def _players(names: str, cache: DiskCache, max_requests: int) -> list:
    # one budget per paid player: the providers bill separately, and one must not starve the other
    return [make_player(name, cache=cache, budget=RequestBudget(max_requests)) if name in PAID
            else make_player(name) for name in (n.strip() for n in names.split(","))]


def _spends_on_tournament_seeds(players: list, max_requests: int, first_seed: int, tournament: bool) -> bool:
    return (max_requests > 0 and any(p.name in PAID for p in players)
            and first_seed < FIRST_PRACTICE_SEED and not tournament)


SEED_RULE = ("paid players may not spend requests on seeds below 1000 (tournament seeds); "
             "use {flag} 1000 or higher, or pass --tournament")


def _live(args) -> int:
    try:
        players = _players(args.players, DiskCache(args.cache), args.max_requests)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_tournament_seeds(players, args.max_requests, args.seed, args.tournament):
        print(SEED_RULE.format(flag="--seed"), file=sys.stderr)
        return 2
    run_args = {"command": "live", "players": args.players, "seed": args.seed, "max_rows": args.max_rows,
                "max_requests": args.max_requests, "cache": args.cache, "tournament": args.tournament, "port": args.port}
    try:
        live = LiveRun(players, args.seed, out_root=args.out, max_rows=args.max_rows, args=run_args)
        server = serve(None, live.broadcast, args.port)  # before anything is on disk: a busy port leaves nothing behind
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    except OSError as e:
        print(f"cannot listen on {HOST}:{args.port}: {e}", file=sys.stderr)
        return 2
    try:
        try:
            server.page = render_html(live.prepare(), live=EVENTS_PATH)
        except FileExistsError:
            print(f"run directory already exists: {live.run_dir}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        print(f"watch: http://{HOST}:{server.server_address[1]}/", flush=True)
        try:
            if not args.no_wait:
                print("waiting for a browser to open the page (Ctrl-C to give up)", flush=True)
                live.broadcast.wait_for_listener()
        except KeyboardInterrupt:
            live.cancel()
            print("run interrupted before it began", file=sys.stderr)
            return 1
        live.run()
        if live.status != "completed":
            print(f"run {live.status}" + (f": {live.error}" if live.error else ""), file=sys.stderr)
        print(f"run directory: {live.run_dir}")
        _print_report(live.run_dir)
        if not args.no_wait and live.status != "interrupted":
            print(f"still serving the page; Ctrl-C to stop. Replay it later: python -m bakeoff view {live.run_dir}", flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
        return 0 if live.status == "completed" else 1
    finally:
        server.shutdown()
        server.server_close()


def _print_report(run_dir) -> None:
    meta = load_meta(run_dir)
    print(f"status: {meta.get('status', 'unknown') if meta else 'unknown'}")
    print(format_table(summarize(load_steps(run_dir), meta)))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "report":
        try:
            _print_report(args.run_dir)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 2
        return 0
    if args.command == "view":
        try:
            replay = build_replay(args.run_dirs)
        except (FileNotFoundError, ValueError) as e:
            print(e, file=sys.stderr)
            return 2
        if not replay["episodes"]:
            print("no step records in " + ", ".join(args.run_dirs), file=sys.stderr)
            return 2
        output = Path(args.output)
        try:
            output.write_text(render_html(replay), encoding="utf-8")
        except OSError as e:
            print(f"cannot write {output}: {e}", file=sys.stderr)
            return 2
        print(f"replay: {output} ({len(replay['episodes'])} episodes, {output.stat().st_size / 1e6:.1f} MB)")
        return 0
    if args.command == "live":
        return _live(args)
    try:
        players = _players(args.players, DiskCache(args.cache), args.max_requests)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_tournament_seeds(players, args.max_requests, args.seed_start, args.tournament):
        print(SEED_RULE.format(flag="--seed-start"), file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
                "tournament": args.tournament}
    status = 0
    try:
        runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
    except FileExistsError:
        print(f"run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    except RunAborted as e:
        print(f"run {e.status}: {e}", file=sys.stderr)
        status = 1
    print(f"run directory: {run_dir}")
    _print_report(run_dir)
    return status


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_cli_live.py`
Expected: `5 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `291 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/__main__.py tests/test_cli_live.py
git commit -F <message file>   # feat: bakeoff live: watch the minds play one track in real time
```

---

### Task 5: Every live runner is shown; documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/REPLAY_DATA.md`
- Modify: `viewer/app.js`

**Interfaces:**
- Produces: nothing new for later tasks.

No new test: the one changed line of `viewer/app.js` is glue (checked in the browser by the controller); the rest is documentation. Run the full suite before committing.

- [ ] **Step 1: Write the implementation**

Apply to `CLAUDE.md`:

```diff
@@ -58,6 +58,11 @@ its own plan.
   `viewer/fonts/` are embedded as base64 by `bakeoff/view.py`). The page is the user's brand: tokens from
   `~/Documents/PROJECTS/BRAND/brand.css`, blue only for the cursor (the mind in focus and its tiles), mono for short
   labels only, deaths and errors `--bad`, warnings `--warn`. Frames reach `app.js` through `Feed` alone.
+- `bakeoff live` (`bakeoff/live.py`, `bakeoff/live_server.py`) plays one track in lockstep by row, records a
+  normal run directory and streams it to the page over Server-Sent Events on `127.0.0.1` only (standard
+  library, no dependency). It builds one fly brain in its own process: never start it next to another fly run.
+  Its records come from `runner.play_row` and its frames from `replay.frame_of`, the same functions `run` and
+  `view` use; keep it that way.
 - Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
   raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
   request on a seed below 1000 before the tournament; the CLI refuses a live paid run on seeds
```

Apply to `README.md`:

```diff
@@ -23,6 +23,16 @@ are in `docs/COSTS.md`.
     uv run python -m bakeoff report runs/<run_id>
     uv run python -m bakeoff view runs/<run_id> [runs/<other_run_id> ...]   # writes replay.html
 
+    uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 300   # watch it happen
+
+`live` plays one track in real time: every mind decides the same row before anyone moves on (a jumper skips
+the next row; the slowest mind sets the pace, about a row a second with the fly), each decision goes into a
+normal run directory and, through a server on `127.0.0.1` only, into the same page as it happens. It waits
+for a browser to open the page before it starts and keeps serving afterwards until Ctrl-C (`--no-wait` does
+neither). The cap works as in `run`: per paid player, default 0, which makes a free live run of a track whose
+answers are already cached; a live paid run on a seed below 1000 is refused without `--tournament`. `live`
+builds one fly brain; do not start a second fly process next to it. Afterwards `view` replays the directory.
+
 Paid players (`jev`, `jev_composed`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
 file at the repo root (template: `.env.example`). They spend nothing unless told to:
 
```

Apply to `docs/REPLAY_DATA.md`:

```diff
@@ -46,7 +46,23 @@ Frames are sorted by `row`. A jump advances two rows, so rows are not consecutiv
 ## How the viewer uses it
 
 The page never reads this object directly: `viewer/feed.js` hands it over as calls (`onMeta`, then
-`onEpisode` and `onFrame` per episode), the same calls a live run will make, so the two cannot drift apart.
+`onEpisode` and `onFrame` per episode), the same calls a live run makes, so the two cannot drift apart.
+
+## The live stream
+
+`bakeoff live` serves the page with an empty replay (`episodes: []`, the run's entry in `runs`) and
+`<body data-live="/events">`, and streams Server-Sent Events from `/events`, built by the same functions as
+this object (`bakeoff.replay.frame_of`, `summary_of`):
+
+| event | data |
+| --- | --- |
+| `episode` | `{episode, track}`: an episode as above without `frames` (`complete` false, `rows_survived` 0), sent once, just before the player's first frame |
+| `frame` | `{player, seed, frame, summary}`: one frame as above; `summary` is `{complete, finished, death_cause, rows_survived}` after it |
+| `end` | `{status, runs, scoreboard}`: the run's final status and the replay's `runs` and `scoreboard` |
+| `error` | `{message}`: why the run stopped early (a request cap, a provider that kept failing) |
+
+A page that connects late or reconnects gets the whole history again; `viewer/feed.js` drops what it
+already has. After `end` the page closes the stream.
 
 Replay time is measured in rows and every player is on the same clock: at time `t` every runner
 still alive is at row `t`, so they all run the same stretch of one tunnel. The frame on screen is
```

Apply to `viewer/app.js`:

```diff
@@ -94,9 +94,9 @@
     view.shown = new Set(shown.length ? shown : here);
   }
 
-  function arrived(episode) { // live: a runner joins
+  function arrived(episode) { // live: a runner joins. The operator chose who plays, so everyone is shown.
     if (view.seed == null) view.seed = episode.seed;
-    if (episode.seed === view.seed && (DEMO.includes(episode.player) || !view.shown.size)) view.shown.add(episode.player);
+    if (episode.seed === view.seed) view.shown.add(episode.player);
     renderAll();
   }
 
```

- [ ] **Step 2: Run all tests**

Run: `uv run pytest -q`
Expected: `291 passed, 9 deselected`

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md docs/REPLAY_DATA.md viewer/app.js
git commit -F <message file>   # docs: bakeoff live in README, CLAUDE.md and the replay format; a live page shows every runner that arrives
```

---

### Task 6: One real go-live run (spends money, builds the fly brain: controller only)

Inside decision 19's ceilings: at most 300 Claude Haiku requests and what is left of the 1,000 Jev requests (232 used in phase 5a). A fresh practice seed, never played: 1001. No other fly process may be running.

- [ ] `uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 300`, the page open in a browser. Expected pace: about one row a second (the fly). Watch the first rows arrive, the focus cut to a runner in danger, a fall, and the end (`completed`, or `budget_exhausted` if the LLM is still alive after 300 rows, which is an honest ending, not an error to retry).
- [ ] `uv run python -m bakeoff view runs/<run_id> --output live-1001.html` replays it.
- [ ] Record in `docs/COSTS.md` (requests, tokens, cost, the pace), `docs/DECISIONS.md` and `CLAUDE.md`. Never rerun a paid command to "see it again": the replay is free.

## Self-review against the spec

| Spec, phase 5c | Where |
| --- | --- |
| the command line and its defaults | Task 4 (`test_the_defaults_are_the_demos_three_on_a_practice_seed_with_no_budget`) |
| `127.0.0.1` only, standard library only; `GET /` the page with an empty replay and `data-live`; `GET /events` streams `episode`, `frame`, `end`, `error` in the replay's own shapes | Task 3; shapes: Task 2 (`test_the_stream_is_the_replay_in_the_replays_own_shapes`) |
| lockstep by row; one `Game` per player on the same track; records by the runner's own builder into a normal directory; a jumper skips the next row | Tasks 1 and 2 |
| ends when everyone is dead or finished, on Ctrl-C (`interrupted`), at a cap (`budget_exhausted`); the directory is a valid replay in every case | Task 2 (four tests), Task 4 (`view` on the directory) |
| cap per paid player, default 0; refusal below seed 1000 without `--tournament`; one fly brain; keys as today; serves nothing but the page and the stream | Tasks 3 and 4 |
| `Runner.run_seed`'s record building extracted; the runner's behaviour and tests unchanged | Task 1 (no existing test is edited) |
| tests: the loop with fake players (a jumper, a death, a finisher, a budget stop), the stream's shapes, the server on an ephemeral port, the refusal rules | Tasks 2, 3, 4 |

## Rulings on the task reviews (controller, after Task 5)

- **Task 2, Important, fixed:** the `episode` event carried the episode's list of question sets by reference, and later frames append to that list, so what a listener had already been sent could change while it was being serialised in another thread. `Broadcast.emit` now stores a snapshot of every event.
- **Task 2, Important, fixed:** `Broadcast.listeners` only ever grew. A listener that has gone (the page was closed, the run ended) is no longer counted.
