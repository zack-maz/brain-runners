# Brain Battle b, the screens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `bakeoff live` opens on the Brain Battle front and runs the whole show from it:
- home;
- the Smash-style character select, where the skins are the players;
- the track select, which now holds the worst-case cost and its confirmation;
- the race;
- results, which open by themselves;
- Records, with the leaderboard, head to head, past runs and the whole "what is ours" section.

The old lobby grid goes. `bakeoff view` keeps its replay page.

**Architecture:**
- **Python (task 1):**
  - Records ranks on the track select's practice tracks 1000–1019 only (decision 46).
  - Records carries the blocks the "what is ours" lists are written from (`runner.ours_meta`).
  - A result names its fatal move.
- **Pure JavaScript, each tested under `node --test` (tasks 2–6):**
  - `viewer/screens.js`: the screens as a rule;
  - `viewer/select.js`: the character select;
  - `viewer/trackpick.js`: the track select and the money;
  - `viewer/results.js`;
  - `viewer/records.js`.
  Each returns markup as strings, with sprites left as empty `canvas.sprite[data-player]` elements.
- **DOM glue (tasks 7–9):**
  - `viewer/front.js` does the fetching and the screens. It is live only, and returns at once in a replay file.
  - `app.js` keeps the run screen and exposes `window.Race`: `setShown`, `watch`, `watching`, `load`, `rewind`, `atEnd`.
  - `app.js` calls `Front.start`, `Front.ended(end)` and `Front.reachedEnd()`.
  - `viewer/front.css` styles everything under `#front`, plus the run screen's bar.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript with `node --test` (run by `uv run pytest` through `tests/test_viewer_js.py`); no new dependency, no build step, no npm package, nothing loaded from the network (`bakeoff/view.py` inlines every script and stylesheet the page names).

**Spec:** `docs/superpowers/specs/2026-09-25-brain-battle-design.md` (binding; decision 45), sections C and G, with decision 46 (Records' tracks, fly2's mark, the skins' wording). Plan a (`docs/superpowers/plans/2026-09-25-brain-battle-a.md`) is built and reviewed: it provides the roster, `results.py`, `records.py`, the routes (`/state` with `seeds_played` and `track`, `/results`, `/records`, `/replay`), and the tunnel in skin colours. The approved look is in the mock-ups in `docs/mockups/brain-battle/` (not viewer code); the request and answers are in `docs/FRONTEND.md`.

**Branch:** `brain-battle`, in the git worktree `../brain-battle`. The main checkout is on `fly2-settle` and another session uses it: never write there, never switch its branch.

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network.**
- **Implementers run the fast suite only** (`uv run pytest -q`). Never run `uv run pytest -m slow`, `bakeoff run` or `bakeoff live` (with a fly or otherwise). The controller runs the page and the one fly smoke that covers plans a and b (decision 46), once no other session holds a fly brain.
- **This plan spends no money:** no paid player, no `--max-requests`, no `pytest -m live`.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Viewer rules:**
  - Plain JavaScript, no build step, and the page loads nothing from the network.
  - Every string that comes from the server or a log goes through `Minds.esc` before it becomes markup.
  - The page never contains the text `data-live` outside the live page's `<body>` attribute: a test checks a replay file has none.
  - Blue is the cursor (the portrait, slot, track and leaderboard rows in focus, the mind in focus). A skin's own colour is the one other use, and so is the home logo's pulsing brain: both the user's call.
  - Deaths and errors use `--bad`, money and warnings `--warn`. A finish is not a death.
  - Mono is for short labels.
- **The run path stays one path:** runs start through `POST /run`, and their frames come through `Feed` alone.
- **Money (spec G):** the worst case is `Lobby.estimate`'s. A lineup that can spend is confirmed once, with the worst case on the RUN button. Run again goes through the same confirmation. Nothing on the page can raise the ceiling.
- **Honesty:** the whole "What is the fly's and what is ours" section moves into Records' panel unchanged, under the mock-up's three paragraphs. fly2's rows are marked "tuned on these tracks" (decision 46).
- Every code block below was run in a prototype and passes as written: 580 fast tests pass with 16 deselected. Every screen was looked at in a browser against a live server. If a test fails, suspect a transcription slip before redesigning.
- `viewer/index.html`, `viewer/app.js` and `viewer/front.js` are long. Apply each hunk exactly where its context lines are, and never move a block elsewhere, even when the tests would still pass. The result is byte-compared with the prototype.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included. The implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards. Stage only the task's files: `docs/research/` holds the user's own uncommitted edits.

## Review Focus

Inputs and conditions the spec implies that are most likely to bite, and where each is pinned:

1. **A run that ends before `POST /run` answers.** Free players can finish a track that fast, so the state already says `finished`. The page must still watch the run it started and show the run screen. `applyState(state, started)` watches `run.run_id === started`. This was found in the prototype, and the controller's browser check pins it; no unit test sees the DOM.
2. **One skin twice, a ninth fighter, or every skin of a character already in.** These must never happen, whatever is clicked or typed. Pinned by `select.test.js`: "a character whose skins are all in takes no more tokens", "the eight-slot limit", "X and Y cycle … skipping skins another slot has", "a dot sets a skin, never one another slot has".
3. **A lineup that can spend, and one that cannot.** The first needs a second press, with the worst case on the button. The second starts at once, and so does a paid lineup with no cap left. Pinned by `trackpick.test.js` "RUN asks once, with the worst case on it, before a run that can spend".
4. **Ties, a stopped runner, and a finish.** Ties share a place. A stopped runner comes last and is never a death. A finish is not drawn in `--bad`. Pinned by `results.test.js` "ties share a place, and a stopped runner comes last and is never a death".
5. **Two elements with one id.** The screens share one page with the replay's own sections: `#board`, `#runs` and `#ceiling` were all taken or reused. Pinned by `test_every_id_on_the_page_is_unique` (task 9).

## Decisions this plan makes beyond the spec

1. **Portraits light Jev's slit.** On the screens (portraits, slots, the lineup, result cards) Jev's visor shows three lit cells, as the approved mock-ups draw it, and the Map skin shows its blue. A portrait is not a decision. Only the tunnel's slit reads Jev's probability, and there a skin with no number shows no gauge (plan a).
2. **Random picks a track from 1000 to 9999,** as the mock-up does; the practice tiles stay 1000–1019.
3. **Head to head:** the chips offer up to six ranked pairs, those with a verdict first. Any two leaderboard rows can also be picked, so any pair is reachable, as the spec's "pick two players" asks.
4. **Money is written by `Lobby.usd`,** the page's one way to write it. That gives "0.08 USD", not the mock-up's "0.0828 USD".
5. **Results for a run of several tracks** show means ("rows a track") and deaths counted by cause.
6. **A past run's Watch** loads it with `GET /replay` into the run screen. Watch live (this session's run only) returns to the stream the page already has.
7. **The track select's footnote is `Lobby.ceilingText`:** the cap and the seed rule, from the state. It replaces the mock-up's fixed sentence.
8. **The lobby's player grid and its tests go** (spec G). `lobby.js` keeps `usd`, `estimate`, `estimateText`, `whyNot`, `ceilingText` and `spends`.

---

### Task 1: Records on tracks 1000 to 1019, what is ours, the fatal move

**Files:**
- Modify: `bakeoff/records.py`
- Modify: `bakeoff/results.py`
- Modify: `bakeoff/runner.py`
- Modify: `bakeoff/session.py`
- Test: `tests/test_records.py`
- Test: `tests/test_results.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: plan a's `records_of`, `results_of`, `session.FIRST_PRACTICE_SEED`.
- Produces: `session.PRACTICE_TRACKS = 20` and `state()['practice_tracks']`; `runner.ours_meta(rules) -> {game, fly, fly2}` (new_meta uses it); `records.TRACKS = (1000, 1019)`; `records_of` returns `tracks` (`[1000, 1019]`) and `ours` (`ours_meta(rules)`) and ranks only seeds in TRACKS; each result track gains `fatal`: `None` or `{row, move, safe: [actions]}`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_records.py`:

```diff
@@ -47,7 +47,8 @@ def test_records_say_why_instead_of_failing(tmp_path):
     assert records_of(tmp_path / "missing", V2)["why"] == "no run has been recorded yet."
     write_run(tmp_path, "20260921-090010", episode("fly", 999, 3), {"game": V2_BLOCK})
     out = records_of(tmp_path, V2)
-    assert out["bench"] is None and out["why"] == "no completed practice track of game v2 has been recorded yet."
+    assert out["bench"] is None
+    assert out["why"] == "no completed practice track (1000 to 1019) of game v2 has been recorded yet."
     bad = write_run(tmp_path, "20260921-090011", episode("fly", 1000, 3), {"game": V2_BLOCK})
     (bad / "fly.jsonl").write_text("not json\n{}\n")  # broken before its last line
     assert records_of(tmp_path, V2)["unreadable"] == ["20260921-090011"]
@@ -91,3 +92,21 @@ def test_records_marks_the_seeds_fly2_was_tuned_on(tmp_path):
     assert records_of(tmp_path / "missing", V2)["tuned_on"] == tuned
     write_run(tmp_path, "20260921-090024", episode("fly", 1000, 3), {"game": V2_BLOCK})
     assert records_of(tmp_path, V2)["tuned_on"] == tuned
+
+
+def test_the_leaderboard_ranks_on_the_track_selects_practice_tracks_only(tmp_path):
+    """Decision 46: the flies' calibration and settle runs cover 1000 to 1199; Records ranks on 1000 to 1019."""
+    write_run(tmp_path, "20260921-090030", episode("fly", 1019, 4) + episode("fly", 1020, 9) + episode("fly", 1199, 9),
+              {"game": V2_BLOCK})
+    out = records_of(tmp_path, V2)
+    assert out["tracks"] == [1000, 1019]
+    (fly,) = out["bench"]["players"]
+    assert fly["seeds"] == 1 and fly["mean_rows"] == 4
+
+
+def test_records_carry_what_the_what_is_ours_panel_is_written_from(tmp_path):
+    from bakeoff.runner import ours_meta
+
+    for out in (records_of(tmp_path / "missing", V2), records_of(tmp_path, V2)):
+        assert out["ours"] == ours_meta(V2)
+        assert set(out["ours"]) == {"game", "fly", "fly2"} and out["ours"]["game"]["looming"]["falloff"] is not None
```

Apply to `tests/test_results.py`:

```diff
@@ -41,9 +41,12 @@ def test_one_entry_per_player_in_the_runs_order_with_how_its_track_ended(tmp_pat
     solver, stayer = out["players"]
     assert (solver["player"], stayer["player"]) == ("solver", "stayer")
     assert solver["tracks"] == [{"seed": 1001, "rows": 40, "complete": True, "finished": True, "death_cause": None,
-                                 "trapped": False}]
+                                 "trapped": False, "fatal": None}]
     (track,) = stayer["tracks"]
     assert track["complete"] and not track["finished"] and track["death_cause"] == "ran_into_gap"
+    # the fatal move, named: the row it died on, what it did, and what would have gone furthest instead
+    assert track["fatal"]["row"] == track["rows"] and track["fatal"]["move"] == "stay"
+    assert track["fatal"]["safe"] and "stay" not in track["fatal"]["safe"]
     assert track["rows"] == stayer["mean_rows"] < 40
     assert stayer["fatal_wrong_moves"] == 1 and stayer["wrong_moves"] >= 1  # the solver would have lived
     assert solver["wrong_moves"] == 0
@@ -98,5 +101,5 @@ def test_a_death_where_every_move_falls_is_trapped(tmp_path):
               "solver_depths": {"stay": 0, "left": 0, "right": 0, "jump": 0}}]
     (run_dir / "p.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps))
     (player,) = results_of(run_dir)["players"]
-    assert player["tracks"][0]["trapped"] is True
+    assert player["tracks"][0]["trapped"] is True and player["tracks"][0]["fatal"] is None
     assert player["fatal_wrong_moves"] == 0 and player["wrong_moves"] == 1  # the wrong move was row 0's stay
```

Apply to `tests/test_runner.py`:

```diff
@@ -287,3 +287,11 @@ def test_new_meta_is_what_run_writes_first(tmp_path):
     assert meta["status"] == "running" and meta["finished_at"] is None
     for key in ("run_id", "schema_version", "players", "seeds", "game", "fly", "models", "args", "versions"):
         assert written[key] == meta[key]
+
+
+def test_what_is_ours_is_the_same_blocks_a_run_records():
+    from bakeoff.runner import new_meta, ours_meta
+
+    rules = V2.variant(max_rows=40)
+    meta = new_meta("r", [make_player("solver")], [5], rules, None)
+    assert ours_meta(rules) == {key: meta[key] for key in ("game", "fly", "fly2")}
```

Apply to `tests/test_session.py`:

```diff
@@ -31,6 +31,7 @@ def test_a_fresh_session_is_in_the_lobby_and_lists_every_player_with_its_price(t
     state = session(tmp_path).state(seed=1001)
     assert state["status"] == "lobby" and state["run"] is None
     assert state["game"]["version"] == "v2" and state["max_rows"] == 12 and state["requests_per_row"] == 1
+    assert state["first_practice_seed"] == 1000 and state["practice_tracks"] == 20  # the track select's 1000 to 1019
     by_name = {p["name"]: p for p in state["players"]}
     assert by_name["solver"]["paid"] is False and by_name["solver"]["requests_left"] is None
     assert by_name["haiku_plain"]["paid"] is True and by_name["haiku_plain"]["price_usd"] == 0.0006
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_records.py tests/test_results.py tests/test_runner.py tests/test_session.py`
Expected:

```text
FAILED tests/test_records.py::test_records_say_why_instead_of_failing - Asser...
FAILED tests/test_records.py::test_the_leaderboard_ranks_on_the_track_selects_practice_tracks_only
FAILED tests/test_records.py::test_records_carry_what_the_what_is_ours_panel_is_written_from
FAILED tests/test_results.py::test_one_entry_per_player_in_the_runs_order_with_how_its_track_ended
FAILED tests/test_results.py::test_a_death_where_every_move_falls_is_trapped
FAILED tests/test_runner.py::test_what_is_ours_is_the_same_blocks_a_run_records
FAILED tests/test_session.py::test_a_fresh_session_is_in_the_lobby_and_lists_every_player_with_its_price
7 failed, 73 passed in 2.36s
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `bakeoff/records.py` with:

```python
"""Records, for the Brain Battle records screen (docs/superpowers/specs/2026-09-25-brain-battle-design.md,
section F): the leaderboard and the pairs over the recorded practice tracks 1000 to 1019 of this game, and
the past runs. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here adds a statistic.

A live session replays tracks, so one (player, seed) can sit in several run directories, which `bench.load`
rightly refuses. Records takes each pair from the newest run that completed it and leaves the older copies
out, and says how many it left out.

It ranks on the track select's own practice tracks only (decision 46): the flies' calibration and settle runs
cover 1000 to 1199, and a mean over 120 tracks beside a mean over 5 is not the same comparison."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, benchmark, load
from bakeoff.fly.fly2_rule import PRACTICE_SEEDS  # cheap: no brian2 (bakeoff/fly/__init__.py imports nothing)
from bakeoff.game.rules import Rules
from bakeoff.report import load_meta, load_steps
from bakeoff.runner import ours_meta
from bakeoff.session import FIRST_PRACTICE_SEED, PRACTICE_TRACKS, RUN_ID

# the tracks Records ranks on: the track select's practice tracks
TRACKS = (FIRST_PRACTICE_SEED, FIRST_PRACTICE_SEED + PRACTICE_TRACKS - 1)

# fly2's frozen numbers were fitted on these seeds (calibration/FLY2_REPORT.md, decision 43): a leaderboard
# mean over them is in-sample for fly2 in a way it is not for anyone else, so `records_of` marks it.
TUNED_ON = {"fly2": [min(PRACTICE_SEEDS), max(PRACTICE_SEEDS)]}


def _run_key(name: str) -> tuple[str, int]:
    """(the timestamp, the counter or 0), so `-10` sorts after `-9` (ten runs started in one second, the
    tenth naming itself last)."""
    match = RUN_ID.fullmatch(name)
    suffix = match.group(1) or "" if match else ""
    return (name[: len(name) - len(suffix)] if suffix else name, int(suffix[1:]) if suffix else 0)


def _run_dirs(out_root: Path) -> list[Path]:
    """Every run directory, newest first: only a name shaped like a run id (`session.RUN_ID`) holding a
    meta.json is one; a renamed directory is not a run this page can offer to watch."""
    return sorted((d for d in out_root.iterdir() if d.is_dir() and RUN_ID.fullmatch(d.name) and (d / "meta.json").is_file()),
                  key=lambda d: _run_key(d.name), reverse=True)


def _same_game(meta: dict, rules: Rules) -> bool:
    try:
        recorded = Rules.from_json(meta["game"])
    except (KeyError, TypeError, ValueError):
        return False  # a run from before game versions, or a game block this code cannot read
    return recorded.same_game(rules) and recorded.max_rows == rules.max_rows


def pick(out_root: Path | str, rules: Rules) -> tuple[list[Source], int, list[str]]:
    """(the sources to score, how many older complete episodes were left out, the run ids that could not be
    read). Only the practice tracks in TRACKS, only runs of this game and length, only complete episodes."""
    taken: set[tuple[str, int]] = set()
    sources, left_out, unreadable = [], 0, []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir)
        if meta is None:
            unreadable.append(run_dir.name)  # meta.json exists (_run_dirs required it) but cannot be read
            continue
        if not _same_game(meta, rules):
            continue
        try:
            steps = load_steps(run_dir)
            last: dict[tuple[str, int], dict] = {}
            for s in steps:
                key = (s["player"], s["seed"])
                if TRACKS[0] <= s["seed"] <= TRACKS[1] and (key not in last or s["row"] > last[key]["row"]):
                    last[key] = s
            complete = [(key, step) for key, step in last.items() if step["finished"] or not step["alive"]]
        except Exception:
            # a record that parses but is not one of ours (a missing key, a value of the wrong shape): this
            # run cannot be scored, but it must not take the others down with it (nothing is committed yet)
            unreadable.append(run_dir.name)
            continue
        mine = set()
        for key, _ in complete:
            if key in taken:
                left_out += 1
            else:
                taken.add(key)
                mine.add(key)
        if mine:
            sources.append(Source(run_dir, episodes=frozenset(mine)))
    return sources, left_out, unreadable


def past_runs(out_root: Path | str, current: str | None = None) -> list[dict]:
    """Every run directory's meta.json, newest first. `current` is the run this session is playing: only it can
    be watched live, since the page cannot stream another process's run."""
    runs = []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir) or {}
        game, players, seeds = meta.get("game"), meta.get("players"), meta.get("seeds")
        runs.append({"run_id": run_dir.name, "status": meta.get("status"), "started_at": meta.get("started_at"),
                     "finished_at": meta.get("finished_at"), "seeds": seeds if isinstance(seeds, list) else [],
                     "players": players if isinstance(players, list) else [],
                     "game": game.get("version") if isinstance(game, dict) else None,
                     "current": run_dir.name == current})
    return runs


def records_of(out_root: Path | str, rules: Rules, current: str | None = None) -> dict:
    """{game, max_rows, tracks, bench (bench.benchmark's numbers, or None), why, left_out, unreadable, runs,
    tuned_on, ours}. Like `benchmark_of`, it answers with a reason instead of failing. `tracks` is the first and
    last track ranked; `tuned_on` names the seeds any frozen player's numbers were fitted on, so a leaderboard
    can mark them in-sample for that player; `ours` is what the "what is ours" panel is written from."""
    about = {"tracks": list(TRACKS), "tuned_on": TUNED_ON, "ours": ours_meta(rules)}
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "bench": None, "why": "no run has been recorded yet.",
                "left_out": 0, "unreadable": [], "runs": [], **about}
    sources, left_out, unreadable = pick(out_root, rules)
    numbers, why = None, None
    if not sources:
        why = f"no completed practice track ({TRACKS[0]} to {TRACKS[1]}) of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(sources))
        except (OSError, ValueError) as e:
            why = f"the records could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "bench": numbers, "why": why, "left_out": left_out,
            "unreadable": unreadable, "runs": past_runs(out_root, current), **about}
```

Apply to `bakeoff/results.py`:

```diff
@@ -17,13 +17,19 @@ from bakeoff.session import PRICE_USD
 
 def _ending(steps: list[dict]) -> dict:
     """How one track ended for one player, from its last record. `trapped`: it died on a row where every move
-    fell, so no move there was wrong (the wrong move came earlier)."""
+    fell, so no move there was wrong (the wrong move came earlier). `fatal`: a death on a wrong move, named: the
+    row, the move made, and the moves that reached furthest from there (the report's `fatal_wrong_moves`)."""
     last = max(steps, key=lambda s: s["row"])
     complete = bool(last["finished"] or not last["alive"])
     depths = last.get("solver_depths") or {}
+    best = max(depths.values()) if depths else 0
+    fatal = None
+    if not last["alive"] and best > 0 and depths.get(last["executed_action"], best) < best:
+        fatal = {"row": last["row"], "move": last["executed_action"],
+                 "safe": [action for action, depth in depths.items() if depth == best]}
     return {"seed": last["seed"], "rows": last["rows_survived"], "complete": complete, "finished": bool(last["finished"]),
-            "death_cause": last["death_cause"],
-            "trapped": bool(not last["alive"] and depths and max(depths.values()) == 0)}
+            "death_cause": last["death_cause"], "trapped": bool(not last["alive"] and depths and best == 0),
+            "fatal": fatal}
 
 
 def results_of(run_dir: Path | str) -> dict:
```

Apply to `bakeoff/runner.py`:

```diff
@@ -132,12 +132,11 @@ def fly2_meta() -> dict:
             "controls": fly2.CONTROLS}
 
 
-def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], rules: Rules, args: dict | None) -> dict:
-    """meta.json as a run starts: status `running`, no finish time yet."""
+def ours_meta(rules: Rules) -> dict:
+    """The game with the looming constants, and both flies' frozen numbers: the blocks of meta.json that say
+    what is ours. The page's "what is ours" lists are written from them (Minds.ours, Minds.oursFly2), from a
+    run's meta.json or, on the records screen, from this."""
     return {
-        "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
-        "started_at": _now(), "finished_at": None, "status": "running",
-        "players": [p.name for p in players], "seeds": list(seeds),
         "game": {**rules.to_json(),
                  "looming": {"gain_hz": LOOMING_GAIN_HZ, "falloff": LOOMING_FALLOFF, "step_hz": LOOMING_STEP_HZ,
                              "max_hz": MAX_HZ, "provisional": not fly.CALIBRATED}},
@@ -145,6 +144,16 @@ def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], rules: Ru
                 "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                 "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
         "fly2": fly2_meta(),
+    }
+
+
+def new_meta(run_id: str, players: list[Player], seeds: Sequence[int], rules: Rules, args: dict | None) -> dict:
+    """meta.json as a run starts: status `running`, no finish time yet."""
+    return {
+        "run_id": run_id, "schema_version": SCHEMA_VERSION, "git_sha": _git_sha(), "git_dirty": _git_dirty(),
+        "started_at": _now(), "finished_at": None, "status": "running",
+        "players": [p.name for p in players], "seeds": list(seeds),
+        **ours_meta(rules),
         "models": {p.name: p.model for p in players if getattr(p, "model", None)},
         "requests": _requests(players),
         "args": args or {}, "python": platform.python_version(),
```

Apply to `bakeoff/session.py`:

```diff
@@ -26,6 +26,8 @@ from bakeoff.replay import CONTESTANTS
 
 # tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
 FIRST_PRACTICE_SEED = 1000
+# the practice tracks the track select offers, 1000 to 1019, and the ones Records ranks on (decision 46)
+PRACTICE_TRACKS = 20
 
 # USD per live request, measured in docs/COSTS.md (update 2a) and rounded up, because this number is what
 # the page asks the user to agree to: it must never be lower than what a request really costs. A price per
@@ -182,9 +184,9 @@ class LiveSession:
                 "requests_left": self.budgets[name].remaining if paid else None,
                 "played_before": seed is not None and seed in played.get(name, []),
                 # the track select's own practice tracks it has a recorded run of, for its marks: a
-                # tournament seed or a bulk-run seed past the track select's own 20 is not offered there
+                # tournament seed or a bulk-run seed past the track select's own tracks is not offered there
                 "seeds_played": [s for s in played.get(name, [])
-                                 if FIRST_PRACTICE_SEED <= s < FIRST_PRACTICE_SEED + 20],
+                                 if FIRST_PRACTICE_SEED <= s < FIRST_PRACTICE_SEED + PRACTICE_TRACKS],
                 # why this player cannot play this track, so the page can say so before anything is asked
                 "why_not": None if seed is None else self.why_not(name, seed),
             })
@@ -194,7 +196,7 @@ class LiveSession:
             "game": self.rules.to_json(), "max_rows": self.rules.max_rows,
             "requests_per_row": REQUESTS_PER_ROW,
             "max_requests": self.max_requests, "tournament": self.tournament,
-            "first_practice_seed": FIRST_PRACTICE_SEED,
+            "first_practice_seed": FIRST_PRACTICE_SEED, "practice_tracks": PRACTICE_TRACKS,
             "seed": seed,
             # the real track, for the track select's preview: the rules stay in Python. A tournament seed
             # is locked until the session is one, same as `why_not` locks paid players off it
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_records.py tests/test_results.py tests/test_runner.py tests/test_session.py`
Expected: `80 passed in 1.51s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 40.45s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/records.py bakeoff/results.py bakeoff/runner.py bakeoff/session.py tests/test_records.py tests/test_results.py tests/test_runner.py tests/test_session.py
git commit -F <message file>   # records rank on tracks 1000 to 1019 and carry what is ours; results name the fatal move
```

---

### Task 2: The screens as a rule

**Files:**
- Create: `viewer/screens.js`
- Test: `viewer/tests/screens.test.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `viewer/screens.js` (global `Screens`, or `require`): `NAMES` = home, select, track, run, results, records; `select(current, wanted)`; `back(screen, from)`; `stateOf(screen) -> [{name, hidden}]`.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/screens.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Screens = require("../screens.js");

test("the screens, in the order the flow goes through them", () => {
  assert.deepEqual(Screens.NAMES, ["home", "select", "track", "run", "results", "records"]);
});

test("a screen that does not exist leaves the one shown, and a page that opens on nothing opens on home", () => {
  assert.equal(Screens.select("track", "results"), "results");
  assert.equal(Screens.select("track", "lobby"), "track");
  assert.equal(Screens.select(undefined, "nowhere"), "home");
});

test("Back walks the flow backwards, and Records returns to where it was opened from", () => {
  assert.equal(Screens.back("select"), "home");
  assert.equal(Screens.back("track"), "select");
  assert.equal(Screens.back("run"), "home");
  assert.equal(Screens.back("results"), "home");
  assert.equal(Screens.back("records", "home"), "home");
  assert.equal(Screens.back("records", "results"), "results");
  assert.equal(Screens.back("home"), "home");
});

test("exactly one screen is shown", () => {
  const state = Screens.stateOf("track");
  assert.deepEqual(state.filter((s) => !s.hidden).map((s) => s.name), ["track"]);
  assert.equal(state.length, Screens.NAMES.length);
  assert.deepEqual(Screens.stateOf("bogus").filter((s) => !s.hidden).map((s) => s.name), ["home"]);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/screens.test.js`
Expected:

```text
✖ viewer/tests/screens.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/screens.js`:

```javascript
// The Brain Battle screens of `bakeoff live`, as a rule rather than a router, like the tabs: one page, one
// screen shown at a time, no navigation, nothing kept in the URL. Pure, tested.
//
//   home ─Launch─▶ select ─Ready─▶ track ─RUN─▶ run ─(the run ends)─▶ results
//   Records opens from home and from results, and Back returns to where it was opened from.
(function (root) {
  "use strict";

  const NAMES = ["home", "select", "track", "run", "results", "records"];

  // The screen to show: the one asked for when it exists, otherwise the one already shown, otherwise home.
  function select(current, wanted) {
    if (NAMES.includes(wanted)) return wanted;
    return NAMES.includes(current) ? current : NAMES[0];
  }

  // Where Back (the ‹ link, or Escape) leads from a screen. `from` is the screen Records was opened from.
  function back(screen, from) {
    if (screen === "select") return "home";
    if (screen === "track") return "select";
    if (screen === "records") return from === "results" ? "results" : "home";
    if (screen === "run" || screen === "results") return "home";
    return "home";
  }

  // What each screen's section should be: hidden unless it is the one shown. Returned rather than applied,
  // so the rule can be tested without a DOM.
  function stateOf(screen) {
    const shown = select(screen, screen);
    return NAMES.map((name) => ({ name, hidden: name !== shown }));
  }

  const api = { NAMES, select, back, stateOf };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Screens = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/screens.test.js`
Expected: `pass 4, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 42.08s`

- [ ] **Step 6: Commit**

```bash
git add viewer/screens.js viewer/tests/screens.test.js
git commit -F <message file>   # screens: the Brain Battle screens as a rule
```

---

### Task 3: The character select

**Files:**
- Create: `viewer/select.js`
- Test: `viewer/tests/select.test.js`

**Interfaces:**
- Consumes: the roster JSON (plan a), `Minds.esc`, `Lobby.usd`.
- Produces: `viewer/select.js` (global `Select`): `MAX` (8), `make(roster, players)`, `add(sel, roster, c)`, `setSkin(sel, i, k)`, `cycle(sel, roster, dir)`, `remove(sel, i)`, `focusSlot(sel, i)`, `moveCursor(sel, roster, dir)`, `players(sel, roster)`, `ready(sel)`, `onKey(sel, roster, key) -> {sel, go} | null`, `priceText(character, entry)`, `portraitsHtml(sel, roster)`, `slotsHtml(sel, roster)`, `infoHtml(sel, roster, entries)`. A selection is `{slots: [{c, s}], focus, cursor}`, never changed in place.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/select.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Select = require("../select.js");

// a slice of bakeoff/roster.py's JSON: a character with two skins, one with three, one with one
const skin = (player, name, color) => ({ player, name, about: name + " does <this>.", color, inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly", "Looming", "#AEB4BA"), skin("fly2", "Sideways", "#F7768E")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_plain", "Plain", "#B9BEC4"), skin("jev_guided", "Guided", "#5FA35A"),
                                                      skin("jev_step1", "Step 1", "#E6B422")] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [skin("random", "Random", "#8A9097")] },
];
const empty = () => Select.make(ROSTER, []);

test("a click drops the next token, in the character's first skin not already in a slot", () => {
  let sel = Select.add(empty(), ROSTER, 1);
  sel = Select.add(sel, ROSTER, 1);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_guided"]);
  assert.equal(sel.focus, 1); // the new slot takes the focus
  assert.equal(sel.cursor, 1);
});

test("a character whose skins are all in takes no more tokens, and neither does a ninth slot", () => {
  let sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0);
  assert.deepEqual(Select.add(sel, ROSTER, 0), sel);
  sel = empty();
  for (let i = 0; i < 12; i++) sel = Select.add(sel, ROSTER, i % 3);
  assert.equal(sel.slots.length, 6); // 2 + 3 + 1 skins: every one in, none twice
  assert.equal(new Set(Select.players(sel, ROSTER)).size, 6);
});

test("the eight-slot limit", () => {
  const big = [{ id: "many", name: "Many", sprite: "bot", skins: Array.from({ length: 10 }, (_, k) => skin("p" + k, "S" + k, "#8A9097")) }];
  let sel = Select.make(big, []);
  for (let i = 0; i < 10; i++) sel = Select.add(sel, big, 0);
  assert.equal(sel.slots.length, Select.MAX);
  assert.equal(Select.MAX, 8);
});

test("X and Y cycle the focused slot's skin, skipping skins another slot has", () => {
  let sel = Select.add(Select.add(empty(), ROSTER, 1), ROSTER, 1); // jev_plain, jev_guided (focused)
  sel = Select.cycle(sel, ROSTER, 1);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_step1"]);
  sel = Select.cycle(sel, ROSTER, 1); // plain is taken by P1: it wraps past it to guided
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_guided"]);
  sel = Select.cycle(sel, ROSTER, -1); // backwards: plain is taken, so step 1
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_step1"]);
});

test("a dot sets a skin, never one another slot has", () => {
  const sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0); // fly, fly2
  assert.deepEqual(Select.setSkin(sel, 1, 0), sel); // fly is P1's
  const one = Select.add(empty(), ROSTER, 0);
  assert.deepEqual(Select.players(Select.setSkin(one, 0, 1), ROSTER), ["fly2"]);
});

test("removing a slot keeps the focus on a slot that exists", () => {
  let sel = Select.add(Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 1), ROSTER, 2); // focus on P3
  sel = Select.remove(sel, 2);
  assert.deepEqual(Select.players(sel, ROSTER), ["fly", "jev_plain"]);
  assert.equal(sel.focus, 1);
  assert.equal(Select.remove(Select.remove(sel, 0), 0).slots.length, 0);
  assert.deepEqual(Select.remove(sel, 7), sel);
});

test("ready from one fighter on", () => {
  assert.equal(Select.ready(empty()), false);
  assert.equal(Select.ready(Select.add(empty(), ROSTER, 2)), true);
});

test("the keys: arrows move the cursor, Space adds, Backspace removes, Enter goes on only when ready", () => {
  let out = Select.onKey(empty(), ROSTER, "ArrowLeft");
  assert.equal(out.sel.cursor, 2); // it wraps
  out = Select.onKey(out.sel, ROSTER, " ");
  assert.deepEqual(Select.players(out.sel, ROSTER), ["random"]);
  assert.equal(Select.onKey(out.sel, ROSTER, "Enter").go, "track");
  assert.equal(Select.onKey(empty(), ROSTER, "Enter").go, null);
  assert.equal(Select.onKey(out.sel, ROSTER, "Escape").go, "back");
  assert.equal(Select.onKey(out.sel, ROSTER, "Backspace").sel.slots.length, 0);
  assert.equal(Select.onKey(out.sel, ROSTER, "q"), null);
});

test("the command line's players open the select, as far as the roster has them", () => {
  const sel = Select.make(ROSTER, ["jev_step1", "nobody", "fly", "jev_step1"]);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_step1", "fly"]);
  assert.equal(sel.cursor, 1);
});

test("a skin's price, as the select screen says it", () => {
  assert.equal(Select.priceText(ROSTER[1], { paid: true, price_usd: 0.00004 }), "paid · 0.00004 USD / request");
  assert.equal(Select.priceText(ROSTER[1], { paid: true, price_usd: 0 }), "free tier");
  assert.equal(Select.priceText(ROSTER[0], { paid: false }), "free · simulated");
  assert.equal(Select.priceText(ROSTER[2], { paid: false }), "free");
});

test("the markup: portraits with tokens, slots with dots, taken dots disabled, every text escaped", () => {
  const sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0);
  const portraits = Select.portraitsHtml(sel, ROSTER);
  assert.match(portraits, /data-char="0" aria-current="true" aria-disabled="true"/); // both fly skins are in
  assert.equal((portraits.match(/class="token( focus)?"/g) || []).length, 2);
  assert.match(portraits, /data-player="fly" data-px="13"/); // the portrait is the default skin
  const slots = Select.slotsHtml(sel, ROSTER);
  assert.equal((slots.match(/class="slot empty"/g) || []).length, 6);
  assert.match(slots, /data-slot="1" data-skin="0" style="background:#AEB4BA" disabled aria-label="Looming \(already in\)"/);
  const info = Select.infoHtml(sel, ROSTER, [{ name: "fly2", paid: false, why_not: "not <now>" }]);
  assert.match(info, /Fly · Sideways · fly2/);
  assert.match(info, /Sideways does &#60;this&#62;\./);
  assert.match(info, /not &#60;now&#62;/);
  assert.match(Select.infoHtml(empty(), ROSTER, []), /Click a fighter/);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/select.test.js`
Expected:

```text
✖ viewer/tests/select.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/select.js`:

```javascript
// The character select, Smash-style: five portraits, eight slots, a skin per slot. The rules are here and
// tested; the markup is returned as strings and app.js puts it in the page. Sprites are left as empty
// canvases (`canvas.sprite[data-player]`) that app.js paints (Sprites.paint), so this file needs no DOM.
//
// `roster` is bakeoff/roster.py's JSON: [{id, name, sprite, skins: [{player, name, about, color, inks}]}].
// A selection is {slots: [{c, s}], focus, cursor}: `c` a character's index, `s` its skin's index, `focus`
// the slot the skin keys act on, `cursor` the portrait the arrow keys are on. Selections are never changed
// in place: every function returns a new one.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  const MAX = 8; // the slots, P1 to P8

  const key = (c, s) => c + ":" + s;

  // The skins already in a slot, except slot `except` (the one being changed).
  function used(sel, except) {
    return new Set(sel.slots.filter((_, i) => i !== except).map((slot) => key(slot.c, slot.s)));
  }

  // The selection the page opens with: the players the command line offered (`--players`), in order, as far
  // as the roster has them; an old or unknown name, a duplicate, or a ninth is left out.
  function make(roster, players) {
    const slots = [];
    for (const player of players || []) {
      if (slots.length >= MAX) break;
      roster.forEach((character, c) => character.skins.forEach((skin, s) => {
        if (skin.player === player && !slots.some((slot) => slot.c === c && slot.s === s)) slots.push({ c, s });
      }));
    }
    return { slots: slots.slice(0, MAX), focus: 0, cursor: slots.length ? slots[0].c : 0 };
  }

  // A click on a portrait, or Space on the cursor's: the next free slot, in that character's first skin not
  // already taken. Nothing happens when the slots are full or every skin is in.
  function add(sel, roster, c) {
    if (sel.slots.length >= MAX || !roster[c]) return sel;
    const taken = used(sel, -1);
    const s = roster[c].skins.findIndex((_, k) => !taken.has(key(c, k)));
    if (s < 0) return sel;
    return { slots: sel.slots.concat([{ c, s }]), focus: sel.slots.length, cursor: c };
  }

  // A slot's dot: that skin, unless another slot already has it (one player cannot run twice on a track).
  function setSkin(sel, i, k) {
    const slot = sel.slots[i];
    if (!slot || used(sel, i).has(key(slot.c, k))) return sel;
    return { ...sel, slots: sel.slots.map((x, j) => (j === i ? { c: x.c, s: k } : x)), focus: i };
  }

  // X (dir 1) or Y (dir -1): the focused slot's next skin that no other slot has, wrapping around.
  function cycle(sel, roster, dir) {
    const slot = sel.slots[sel.focus];
    if (!slot) return sel;
    const n = roster[slot.c].skins.length;
    const taken = used(sel, sel.focus);
    for (let step = 1; step < n; step++) {
      const k = (((slot.s + dir * step) % n) + n) % n;
      if (!taken.has(key(slot.c, k))) return setSkin(sel, sel.focus, k);
    }
    return sel;
  }

  // A slot's ✕, or Backspace on the focused slot. The focus stays on a slot that still exists.
  function remove(sel, i) {
    if (!sel.slots[i]) return sel;
    const slots = sel.slots.filter((_, j) => j !== i);
    return { ...sel, slots, focus: Math.max(0, Math.min(sel.focus, slots.length - 1)) };
  }

  function focusSlot(sel, i) {
    return sel.slots[i] ? { ...sel, focus: i } : sel;
  }

  function moveCursor(sel, roster, dir) {
    return { ...sel, cursor: (((sel.cursor + dir) % roster.length) + roster.length) % roster.length };
  }

  // The players chosen, in slot order: what the track select and POST /run are given.
  function players(sel, roster) {
    return sel.slots.map((slot) => roster[slot.c].skins[slot.s].player);
  }

  const ready = (sel) => sel.slots.length >= 1;

  // A key on the select screen: the new selection, and where to go (`track` when ready and Enter is
  // pressed, `back` on Escape), or null for a key this screen does not use.
  function onKey(sel, roster, name) {
    if (name === "ArrowRight") return { sel: moveCursor(sel, roster, 1), go: null };
    if (name === "ArrowLeft") return { sel: moveCursor(sel, roster, -1), go: null };
    if (name === " ") return { sel: add(sel, roster, sel.cursor), go: null };
    if (name === "x" || name === "X") return { sel: cycle(sel, roster, 1), go: null };
    if (name === "y" || name === "Y") return { sel: cycle(sel, roster, -1), go: null };
    if (name === "Backspace") return { sel: remove(sel, sel.focus), go: null };
    if (name === "Enter") return { sel, go: ready(sel) ? "track" : null };
    if (name === "Escape") return { sel, go: "back" };
    return null;
  }

  // What a skin costs, as the select screen says it. `entry` is the player's line in GET /state.
  function priceText(character, entry) {
    if (entry && entry.paid) {
      return entry.price_usd > 0 ? "paid · " + Lobby_.usd(entry.price_usd) + " / request" : "free tier";
    }
    return character.id === "fly" ? "free · simulated" : "free";
  }

  // ---- the markup --------------------------------------------------------------------------------
  const sprite = (player, px) => '<canvas class="sprite" data-player="' + esc(player) + '" data-px="' + px + '"></canvas>';

  // The five portraits, each in its default skin, with the tokens of the slots that chose it.
  function portraitsHtml(sel, roster) {
    const taken = used(sel, -1);
    return roster.map((character, c) => {
      const free = character.skins.filter((_, k) => !taken.has(key(c, k))).length;
      const full = free === 0 || sel.slots.length >= MAX;
      const tokens = sel.slots.map((slot, i) => ({ slot, i })).filter((x) => x.slot.c === c)
        .map((x) => '<span class="token' + (x.i === sel.focus ? " focus" : "") + '">P' + (x.i + 1) + "</span>").join("");
      const count = character.skins.length + (character.skins.length === 1 ? " skin" : " skins");
      return '<button type="button" class="portrait" data-char="' + c + '"' +
        (c === sel.cursor ? ' aria-current="true"' : "") + (full ? ' aria-disabled="true"' : "") +
        ' aria-label="Add ' + esc(character.name) + '">' +
        '<span class="label count">' + esc(count) + '</span><span class="tokens">' + tokens + "</span>" +
        '<span class="art">' + sprite(character.skins[0].player, 13) + "</span>" +
        '<span class="name">' + esc(character.name) + "</span></button>";
    }).join("");
  }

  // The eight slots: a filled one shows its fighter in its skin and a dot per skin; an empty one says so.
  function slotsHtml(sel, roster) {
    let html = "";
    for (let i = 0; i < MAX; i++) {
      const slot = sel.slots[i];
      if (!slot) {
        html += '<div class="slot empty"><span class="label">P' + (i + 1) + "</span><span>Empty</span></div>";
        continue;
      }
      const character = roster[slot.c];
      const skin = character.skins[slot.s];
      const taken = used(sel, i);
      const dots = character.skins.map((other, k) => {
        const off = taken.has(key(slot.c, k));
        return '<button type="button" class="dot' + (k === slot.s ? " on" : "") + '" data-slot="' + i + '" data-skin="' + k + '"' +
          ' style="background:' + esc(other.color) + '"' + (off ? " disabled" : "") +
          ' aria-label="' + esc(other.name) + (off ? " (already in)" : "") + '"></button>';
      }).join("");
      html += '<div class="slot' + (i === sel.focus ? " focus" : "") + '" data-slot="' + i + '">' +
        '<div class="slot-top"><button type="button" class="label slot-label" data-focus="' + i + '">P' + (i + 1) + "</button>" +
        '<button type="button" class="remove" data-remove="' + i + '" aria-label="Remove P' + (i + 1) + '">✕</button></div>' +
        '<button type="button" class="slot-art" data-focus="' + i + '" aria-label="Select P' + (i + 1) + '">' +
        sprite(skin.player, 6) + "</button>" +
        '<span class="name">' + esc(character.name) + '</span><span class="skin">' + esc(skin.name) + "</span>" +
        '<span class="dots">' + dots + "</span></div>";
    }
    return html;
  }

  // The line about the focused slot: who it is, what it does, what it costs, and why it may not play.
  // `entries` is GET /state's players.
  function infoHtml(sel, roster, entries) {
    const slot = sel.slots[sel.focus];
    if (!slot) {
      return '<span class="hint">Click a fighter to put it in the next free slot. Up to eight; one character can come in several skins.</span>';
    }
    const character = roster[slot.c];
    const skin = character.skins[slot.s];
    const entry = (entries || []).find((p) => p.name === skin.player);
    const price = priceText(character, entry);
    return '<span class="label who">P' + (sel.focus + 1) + "</span>" +
      '<span class="swatch" style="background:' + esc(skin.color) + '"></span>' +
      '<span class="title">' + esc(character.name + " · " + skin.name + " · " + skin.player) + "</span>" +
      '<span class="about">' + esc(skin.about) + "</span>" +
      (entry && entry.why_not ? '<span class="why warn">' + esc(entry.why_not) + "</span>" : "") +
      '<span class="label price' + (entry && entry.paid && entry.price_usd > 0 ? " paid" : "") + '">' + esc(price) + "</span>";
  }

  const api = { MAX, make, used, add, setSkin, cycle, remove, focusSlot, moveCursor, players, ready, onKey, priceText,
                portraitsHtml, slotsHtml, infoHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Select = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/select.test.js`
Expected: `pass 11, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 43.69s`

- [ ] **Step 6: Commit**

```bash
git add viewer/select.js viewer/tests/select.test.js
git commit -F <message file>   # select: the character select's rules and markup
```

---

### Task 4: The track select and its worst case

**Files:**
- Create: `viewer/trackpick.js`
- Test: `viewer/tests/trackpick.test.js`

**Interfaces:**
- Consumes: GET /state's shape (with task 1's `practice_tracks`), `Lobby.estimate/usd/whyNot/spends`.
- Produces: `viewer/trackpick.js` (global `TrackPick`): `lowest(state)`, `clampSeed(seed, state)`, `randomSeed(state, rng)`, `tiles(state, players, seed)`, `lineup(state, roster, players)`, `previewSvg(track, game)`, `gapTiles(track)`, `runButton(state, players, seed, armed) -> {label, sub, why, armed}`, `capText(state)`, `onKey(seed, state, key, rng)`, `tilesHtml(list)`, `lineupHtml(lines)`. (Task 8 gives `capText` a `players` argument.)

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/trackpick.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const TrackPick = require("../trackpick.js");

const skin = (player, name) => ({ player, name, about: "", color: "#8A9097", inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly2", "Sideways")] },
  { id: "haiku", name: "Haiku", sprite: "chat", skins: [skin("haiku_guided", "Guided")] },
  { id: "glm", name: "GLM Flash", sprite: "ox", skins: [skin("glm_plain", "Plain")] },
];
// the shape of GET /state?seed=1001 (bakeoff/session.py)
const state = (extra) => ({
  status: "lobby", max_rows: 150, requests_per_row: 1, max_requests: 200, tournament: false,
  first_practice_seed: 1000, practice_tracks: 20, seed: 1001,
  players: [
    { name: "fly2", paid: false, price_usd: 0, requests_left: null, played_before: true, seeds_played: [1000, 1001], why_not: null },
    { name: "haiku_guided", paid: true, price_usd: 0.0009, requests_left: 200, played_before: false, seeds_played: [1000], why_not: null },
    { name: "glm_plain", paid: true, price_usd: 0, requests_left: 200, played_before: false, seeds_played: [], why_not: null },
  ],
  ...extra,
});
const LINEUP = ["haiku_guided", "fly2"];

test("a track number is whole and never below the lowest the command allows", () => {
  assert.equal(TrackPick.clampSeed(1004.4, state()), 1004);
  assert.equal(TrackPick.clampSeed(7, state()), 1000);
  assert.equal(TrackPick.clampSeed(7, state({ tournament: true })), 7);
  assert.equal(TrackPick.clampSeed("nope", state()), 1000);
});

test("Random picks a practice track, 1000 to 9999", () => {
  assert.equal(TrackPick.randomSeed(state(), () => 0), 1000);
  assert.equal(TrackPick.randomSeed(state(), () => 0.9999999), 9999);
});

test("the practice tracks, each marked with how many of this lineup played it", () => {
  const tiles = TrackPick.tiles(state(), LINEUP, 1001);
  assert.equal(tiles.length, 20);
  assert.deepEqual([tiles[0].seed, tiles[19].seed], [1000, 1019]);
  assert.deepEqual(tiles.slice(0, 3).map((t) => t.mark), ["2 / 2 played", "1 / 2 played", "new"]);
  assert.deepEqual(tiles.filter((t) => t.current).map((t) => t.seed), [1001]);
});

test("the lineup: each fighter's worst case, free ones said so", () => {
  const [haiku, fly] = TrackPick.lineup(state(), ROSTER, LINEUP);
  assert.deepEqual(haiku, { label: "P1", player: "haiku_guided", title: "Haiku · Guided", played: "new track",
                            cost: "0.14 USD", requests: "150 requests", paid: true, why: null });
  assert.deepEqual(fly, { label: "P2", player: "fly2", title: "Fly · Sideways", played: "played before",
                          cost: "free", requests: "simulated", paid: false, why: null });
  const [glm] = TrackPick.lineup(state(), ROSTER, ["glm_plain"]);
  assert.equal(glm.cost, "free tier");
  assert.equal(glm.paid, false);
  const [capped] = TrackPick.lineup(state({ players: state().players.map((p) => ({ ...p, requests_left: p.paid ? 12 : null })) }),
    ROSTER, ["haiku_guided"]);
  assert.equal(capped.requests, "12 requests"); // the worst case stops where the cap does
});

test("RUN asks once, with the worst case on it, before a run that can spend", () => {
  assert.deepEqual(TrackPick.runButton(state(), LINEUP, 1001, false), { label: "RUN", sub: "Enter", why: null, armed: false });
  assert.deepEqual(TrackPick.runButton(state(), LINEUP, 1001, true),
    { label: "CONFIRM", sub: "spend at most 0.14 USD", why: null, armed: true });
  // a lineup that spends nothing starts at once, armed or not
  assert.equal(TrackPick.runButton(state(), ["fly2"], 1001, true).label, "RUN");
  assert.equal(TrackPick.runButton(state({ max_requests: 0, players: state().players.map((p) => ({ ...p, requests_left: p.paid ? 0 : null })) }),
    LINEUP, 1001, true).label, "RUN");
});

test("RUN cannot be pressed while a run is going or a fighter is refused, and says why", () => {
  assert.equal(TrackPick.runButton(state({ status: "running" }), LINEUP, 1001, false).why, "a run is already going");
  const refused = state({ players: state().players.map((p) => (p.name === "haiku_guided" ? { ...p, why_not: "no <cap> left" } : p)) });
  assert.equal(TrackPick.runButton(refused, LINEUP, 1001, true).why, "no <cap> left");
  assert.match(TrackPick.lineupHtml(TrackPick.lineup(refused, ROSTER, LINEUP)), /no &#60;cap&#62; left/);
});

test("the cap line comes from the state", () => {
  assert.match(TrackPick.capText(state()), /until its cap of 200 runs out/);
  assert.match(TrackPick.capText(state({ max_requests: 0 })), /spends nothing/);
});

test("the preview draws the real track: one dark cell per gap on its rows", () => {
  const track = { seed: 1001, lanes: 12, max_rows: 3, gaps: [[], [0, 7], [11], [4]] }; // the last row is past the end
  const svg = TrackPick.previewSvg(track, { runway_rows: 1 });
  assert.equal((svg.match(/class="gap"/g) || []).length, 3);
  assert.match(svg, /viewBox="0 0 12 60"/);
  assert.match(svg, /class="runway"/);
  assert.equal(TrackPick.gapTiles(track), 3);
  assert.equal(TrackPick.previewSvg(null), "");
});

test("the keys: arrows step the track, R picks one, Enter runs, Escape goes back", () => {
  assert.deepEqual(TrackPick.onKey(1001, state(), "ArrowRight"), { seed: 1002, go: null });
  assert.deepEqual(TrackPick.onKey(1000, state(), "ArrowLeft"), { seed: 1000, go: null });
  assert.deepEqual(TrackPick.onKey(1001, state(), "r", () => 0.5), { seed: 5500, go: null });
  assert.equal(TrackPick.onKey(1001, state(), "Enter").go, "run");
  assert.equal(TrackPick.onKey(1001, state(), "Escape").go, "back");
  assert.equal(TrackPick.onKey(1001, state(), "q"), null);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/trackpick.test.js`
Expected:

```text
✖ viewer/tests/trackpick.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/trackpick.js`:

```javascript
// The track select: which track, what it looks like, who has played it, and what the run can cost at worst.
// This is where the lobby's money confirmation lives now (spec section G): the worst case is Lobby.estimate's,
// shown per fighter and in total, and a run that can spend is confirmed once before it starts. Pure and
// tested; the markup is returned as strings and app.js puts it in the page (sprites as empty canvases).
//
// `state` is GET /state?seed= (bakeoff/session.py); `roster` is bakeoff/roster.py's JSON; `players` the
// lineup chosen on the character select, in slot order.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  // The lowest track this command may play: the tournament's seeds only with --tournament.
  const lowest = (state) => (state.tournament ? 0 : state.first_practice_seed);

  // A track number the command allows: a whole number, never below the lowest.
  function clampSeed(seed, state) {
    const whole = Math.round(Number(seed));
    return Number.isFinite(whole) ? Math.max(lowest(state), whole) : state.first_practice_seed;
  }

  // Random: a practice track, first_practice_seed to 9999. `rng` is Math.random or a test's stand-in.
  function randomSeed(state, rng) {
    const first = state.first_practice_seed;
    return first + Math.floor(rng() * (10000 - first));
  }

  // The practice tracks the screen offers (1000 to 1019), each with how many of this lineup played it.
  function tiles(state, players, seed) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const out = [];
    for (let s = state.first_practice_seed; s < state.first_practice_seed + state.practice_tracks; s++) {
      const n = players.filter((name) => ((byName.get(name) || {}).seeds_played || []).includes(s)).length;
      out.push({ seed: s, current: s === seed, mark: n === 0 ? "new" : n + " / " + players.length + " played" });
    }
    return out;
  }

  // One line per fighter: who, whether this track was played before, and its worst case.
  function lineup(state, roster, players) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const worst = new Map(Lobby_.estimate(state, players).lines.map((line) => [line.player, line]));
    const skinOf = new Map();
    for (const character of roster) for (const skin of character.skins) skinOf.set(skin.player, { character, skin });
    return players.map((name, i) => {
      const found = skinOf.get(name);
      const entry = byName.get(name) || {};
      const line = worst.get(name);
      let cost = "free", requests = found && found.character.id === "fly" ? "simulated" : "";
      if (line) {
        cost = line.free ? "free tier" : Lobby_.usd(line.usd);
        requests = line.requests + (line.requests === 1 ? " request" : " requests");
      }
      return { label: "P" + (i + 1), player: name, title: found ? found.character.name + " · " + found.skin.name : name,
               played: entry.played_before ? "played before" : "new track", cost, requests,
               paid: !!(line && !line.free), why: entry.why_not || null };
    });
  }

  // The whole track as a picture: one column per row, one cell per lane, the gaps dark. The runway (the
  // rows before any gap may fall) is lighter, as in the approved mock-up. An SVG, since 1,800 cells as
  // elements would be slow for no gain.
  function previewSvg(track, game) {
    if (!track) return "";
    const rows = track.max_rows, lanes = track.lanes, cw = 4, ch = 5;
    const runway = (game && game.runway_rows) || 0;
    let cells = '<rect width="' + rows * cw + '" height="' + lanes * ch + '" class="floor"/>';
    if (runway) cells += '<rect width="' + runway * cw + '" height="' + lanes * ch + '" class="runway"/>';
    for (let row = 0; row < rows; row++) {
      for (const lane of track.gaps[row] || []) {
        cells += '<rect x="' + row * cw + '" y="' + lane * ch + '" width="' + cw + '" height="' + ch + '" class="gap"/>';
      }
    }
    return '<svg class="preview" viewBox="0 0 ' + rows * cw + " " + lanes * ch + '" role="img" aria-label="Track ' +
      esc(track.seed) + ", row 0 to " + esc(rows) + '">' + cells + "</svg>";
  }

  // How many gap tiles the track has on its rows.
  function gapTiles(track) {
    if (!track) return 0;
    return track.gaps.slice(0, track.max_rows).reduce((n, row) => n + row.length, 0);
  }

  // The RUN button: what it says, and why it cannot be pressed. `armed`: the worst case was shown on the
  // button and one more press starts the run.
  function runButton(state, players, seed, armed) {
    const why = Lobby_.whyNot(state, players, seed);
    if (why) return { label: "RUN", sub: "", why, armed: false };
    const cost = Lobby_.estimate(state, players);
    if (armed && Lobby_.spends(state, players)) {
      return { label: "CONFIRM", sub: "spend at most " + Lobby_.usd(cost.total_usd), why: null, armed: true };
    }
    return { label: "RUN", sub: "Enter", why: null, armed: false };
  }

  // The line under the total: the cap and what a row costs, from /state, never typed in.
  function capText(state) {
    if (!state.max_requests) {
      return "This command has no cap: the paid fighters replay answers already cached and stop at their first " +
        "uncached question, so this run spends nothing.";
    }
    return "Every row costs " + state.requests_per_row + " request for every paid fighter, until its cap of " +
      state.max_requests + " runs out. Cached answers are free, so the real cost is usually lower.";
  }

  // A key on the track select: the new seed, and where to go.
  function onKey(seed, state, name, rng) {
    if (name === "ArrowLeft") return { seed: clampSeed(seed - 1, state), go: null };
    if (name === "ArrowRight") return { seed: clampSeed(seed + 1, state), go: null };
    if (name === "r" || name === "R") return { seed: randomSeed(state, rng), go: null };
    if (name === "Enter") return { seed, go: "run" };
    if (name === "Escape") return { seed, go: "back" };
    return null;
  }

  // ---- the markup --------------------------------------------------------------------------------
  function tilesHtml(list) {
    return list.map((t) => '<button type="button" class="tile' + (t.current ? " current" : "") + '" data-seed="' + t.seed +
      '" aria-label="Track ' + t.seed + '"><span class="seed">' + t.seed + '</span><span class="mark">' + esc(t.mark) +
      "</span></button>").join("");
  }

  function lineupHtml(lines) {
    return lines.map((l) => '<div class="fighter"><span class="label who">' + l.label + "</span>" +
      '<span class="art"><canvas class="sprite" data-player="' + esc(l.player) + '" data-px="4"></canvas></span>' +
      '<span class="what"><span class="title">' + esc(l.title) + '</span><span class="sub">' + esc(l.player) + " · " +
      esc(l.played) + "</span>" + (l.why ? '<span class="sub warn">' + esc(l.why) + "</span>" : "") + "</span>" +
      '<span class="cost"><span class="usd' + (l.paid ? " paid" : "") + '">' + esc(l.cost) + '</span><span class="sub">' +
      esc(l.requests) + "</span></span></div>").join("");
  }

  const api = { lowest, clampSeed, randomSeed, tiles, lineup, previewSvg, gapTiles, runButton, capText, onKey, tilesHtml, lineupHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TrackPick = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/trackpick.test.js`
Expected: `pass 9, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 42.60s`

- [ ] **Step 6: Commit**

```bash
git add viewer/tests/trackpick.test.js viewer/trackpick.js
git commit -F <message file>   # trackpick: the track select's rules, its worst case and its markup
```

---

### Task 5: The results screen's ranking and words

**Files:**
- Create: `viewer/results.js`
- Test: `viewer/tests/results.test.js`

**Interfaces:**
- Consumes: plan a's results JSON (with task 1's `fatal`), `Minds.esc`, `Lobby.usd`.
- Produces: `viewer/results.js` (global `Results`): `percent`, `perRow`, `rank(results)`, `death(entry, single)`, `wrongText(entry, single)`, `header(results) -> {left, right}`, `cards(results, roster)`, `bars(results, roster)`, `warning`, `table(results, roster) -> {heads, rows}`, `failures`, `note`, `cardsHtml(cards, more)`, `barsHtml(bars, colourOf)`, `tableHtml(table)`. (Task 9 renames the bar class and adds `finished` to a card.)

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/results.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Results = require("../results.js");

const skin = (player, name) => ({ player, name, about: "", color: "#5FA35A", inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly2", "Sideways")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_guided", "Guided")] },
  { id: "haiku", name: "Haiku", sprite: "chat", skins: [skin("haiku_guided", "Guided")] },
  { id: "glm", name: "GLM Flash", sprite: "ox", skins: [skin("glm_plain", "Plain")] },
];
// the shape of bakeoff/results.py's players (the report's row, plus the results' own keys)
const entry = (player, track, extra) => ({
  player, runs: track && track.complete ? 1 : 0, incomplete: track && !track.complete ? 1 : 0,
  mean_rows: track && track.complete ? track.rows : null, finished: track && track.finished ? 1 : 0,
  ran_into_gap: 0, jumped_into_gap: 0, dodged_into_gap: 0, jump_share: 0.1728, wrong_moves: 1, fatal_wrong_moves: 1,
  fallback_rate: 0, invalid_rate: 0, error_rate: 0, requests: 81, cache_hits: 0, input_tokens: 68752, output_tokens: 3645,
  paid: true, price_usd: 0.00004, cost_estimate_usd: 0.00324, s_per_row: 0.1754, tracks: track ? [track] : [], ...extra,
});
const track = (rows, extra) => ({ seed: 1000, rows, complete: true, finished: false, death_cause: "jumped_into_gap",
                                  trapped: false, fatal: { row: rows - 1, move: "jump", safe: ["stay"] }, ...extra });
const RESULTS = {
  run_id: "20260921-165433", status: "completed", seeds: [1000], game: { version: "v2", max_rows: 150 },
  players: [
    entry("fly2", track(72), { paid: false, price_usd: 0, requests: 0, input_tokens: 0, output_tokens: 0, s_per_row: 0.494 }),
    entry("jev_guided", track(94)),
    entry("haiku_guided", track(93, { death_cause: "dodged_into_gap" }), { price_usd: 0.0009, cost_estimate_usd: 0.0828, s_per_row: 0.75 }),
  ],
};

test("the cards are ranked by rows survived, each keeping its slot's label", () => {
  const cards = Results.cards(RESULTS, ROSTER);
  assert.deepEqual(cards.map((c) => [c.place, c.label, c.title, c.rows]),
    [[1, "P2", "Jev · Guided", 94], [2, "P3", "Haiku · Guided", 93], [3, "P1", "Fly · Sideways", 72]]);
  assert.deepEqual(cards[0], { place: 1, top: true, label: "P2", player: "jev_guided", title: "Jev · Guided", rows: 94,
                               rowsWord: "rows", death: "Jumped into a gap · row 94", stopped: false, perRow: "175 ms",
                               requests: "81", cost: "0.0032 USD", paid: true }); // Lobby.usd, the page's one way to write money
  assert.equal(cards[2].requests, "none (simulated)");
  assert.equal(cards[2].cost, "free");
});

test("ties share a place, and a stopped runner comes last and is never a death", () => {
  const tied = { ...RESULTS, players: [
    entry("jev_guided", track(150, { finished: true, death_cause: null, fatal: null })),
    entry("haiku_guided", track(150, { finished: true, death_cause: null, fatal: null })),
    entry("fly2", track(140, { complete: false, death_cause: null, fatal: null })),
    entry("glm_plain", track(12)),
  ] };
  const cards = Results.cards(tied, ROSTER);
  assert.deepEqual(cards.map((c) => [c.player, c.place]), [["jev_guided", 1], ["haiku_guided", 1], ["glm_plain", 3], ["fly2", 4]]);
  assert.equal(cards[0].death, "Reached the finish line");
  assert.equal(cards[3].death, "Stopped at row 140: not a death");
  assert.equal(cards[3].stopped, true);
  assert.equal(cards[3].top, false);
});

test("free tier and a fighter that never started", () => {
  const out = { ...RESULTS, players: [entry("glm_plain", null, { price_usd: 0, cost_estimate_usd: 0 })] };
  const [card] = Results.cards(out, ROSTER);
  assert.equal(card.cost, "free tier");
  assert.equal(card.death, "Never started");
});

test("a bar per fighter against the track's length, and the solver's line when it did not run", () => {
  const bars = Results.bars(RESULTS, ROSTER);
  assert.deepEqual(bars.map((b) => [b.name, b.rows]), [["Jev · Guided", 94], ["Haiku · Guided", 93],
    ["Fly · Sideways", 72], ["Solver (yardstick)", 150]]);
  assert.equal(bars[0].width, 94 / 150);
  assert.equal(bars[3].yardstick, true);
});

test("the warning names the two best numbers", () => {
  assert.equal(Results.warning(RESULTS, ROSTER),
    "One track is not a result: 94 against 93 rows can be this track's luck. Records holds the benchmark over many tracks.");
  assert.match(Results.warning({ ...RESULTS, players: [RESULTS.players[0]] }, ROSTER), /^One track is not a result\. /);
});

test("More numbers: the wrong moves name the fatal one and what was safe", () => {
  const t = Results.table(RESULTS, ROSTER);
  assert.deepEqual(t.heads, ["Jev · Guided", "Haiku · Guided", "Fly · Sideways"]);
  const row = (name) => t.rows.find((r) => r.name === name).vals;
  assert.deepEqual(row("Wrong moves")[0], "1 · fatal, row 93: jump (stay safe)");
  assert.deepEqual(row("Moves that were jumps"), ["17%", "17%", "17%"]);
  assert.deepEqual(row("Asked live"), ["81", "81", "none (simulated)"]);
  assert.deepEqual(row("Tokens")[0], "68,752 / 3,645");
  assert.deepEqual(row("Cost"), ["0.0032 USD", "0.08 USD", "free"]);
  const trapped = entry("jev_guided", track(20, { trapped: true, fatal: null }), { wrong_moves: 2 });
  assert.equal(Results.wrongText(trapped, true), "2 · trapped at the end: no move there was safe");
});

test("failures appear only when there were any", () => {
  assert.deepEqual(Results.failures(RESULTS, ROSTER), []);
  const failing = { ...RESULTS, players: [entry("haiku_guided", track(9), { fallback_rate: 0.03, error_rate: 0.01, invalid_rate: 0.02 })] };
  assert.deepEqual(Results.failures(failing, ROSTER),
    ["Haiku · Guided: 3.0% of its rows fell back to the default move (errors 1.0%, unreadable answers 2.0%)."]);
});

test("the note says what is left out and what is ours, from the lineup", () => {
  assert.match(Results.note(RESULTS, ROSTER), /The fly is asked nothing; how gaps become its input is ours\./);
  assert.match(Results.note(RESULTS, ROSTER), /an estimate, not a bill/);
  assert.doesNotMatch(Results.note({ ...RESULTS, players: [RESULTS.players[1]] }, ROSTER), /fly/);
});

test("a run of several tracks shows means and deaths counted by cause", () => {
  const many = { ...RESULTS, seeds: [1000, 1001, 1002], players: [entry("jev_guided", null,
    { runs: 3, mean_rows: 71.33, jumped_into_gap: 2, dodged_into_gap: 1, incomplete: 0, finished: 0 })] };
  const [card] = Results.cards(many, ROSTER);
  assert.equal(card.rows, "71.3");
  assert.equal(card.rowsWord, "rows a track");
  assert.equal(card.death, "2 jumped into a gap, 1 dodged into a gap");
  assert.deepEqual(Results.header(many), { left: "Run ended · 1 fighter", right: "Tracks 1000–1002 (3) · game v2 · 150 rows" });
});

test("the header and the markup, every text escaped", () => {
  assert.deepEqual(Results.header(RESULTS), { left: "Run ended · 3 fighters", right: "Track 1000 · game v2 · 150 rows" });
  assert.equal(Results.header({ ...RESULTS, status: "interrupted" }).left, "Run interrupted · 3 fighters");
  const evil = { ...RESULTS, players: [entry("<b>x</b>", track(3))] };
  const html = Results.cardsHtml(Results.cards(evil, ROSTER), false) + Results.tableHtml(Results.table(evil, ROSTER)) +
    Results.barsHtml(Results.bars(evil, ROSTER), () => "#5FA35A");
  assert.equal(html.includes("<b>"), false);
  assert.match(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true), /^<article class="card top"/);
  assert.equal(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true).includes("canvas"), false); // More numbers hides the art
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/results.test.js`
Expected:

```text
✖ viewer/tests/results.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/results.js`:

```javascript
// The results screen: a card per fighter ranked by rows survived, a bar each against the track's length,
// and More numbers. Every number comes from bakeoff/results.py (the end event, or GET /results); this file
// only ranks and words them. Pure and tested; the markup is returned as strings (sprites as empty canvases).
// No winner banner: one track is not a result, and the screen says so.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  const DEATHS = { ran_into_gap: "Ran into a gap", jumped_into_gap: "Jumped into a gap", dodged_into_gap: "Dodged into a gap" };

  const labelOf = (roster, player) => {
    for (const character of roster || []) {
      for (const skin of character.skins) if (skin.player === player) return character.name + " · " + skin.name;
    }
    return player;
  };
  const isFly = (roster, player) => (roster || []).some((c) => c.id === "fly" && c.skins.some((s) => s.player === player));

  // A share as the page writes it: one decimal below 10%, none above.
  function percent(share) {
    if (share == null) return "-";
    const p = share * 100;
    return (p > 0 && p < 10 ? p.toFixed(1) : Math.round(p)) + "%";
  }

  // Seconds a row as the page writes it.
  function perRow(seconds) {
    if (seconds == null) return "-";
    return seconds < 1 ? Math.round(seconds * 1000) + " ms" : seconds.toFixed(1) + " s";
  }

  // How far an entry got, for the ranking: on one track its rows (a stopped runner counts below every
  // complete one), over several its mean over the complete tracks.
  function score(entry, single) {
    if (single) {
      const track = entry.tracks[0];
      return track ? { value: track.rows, stopped: !track.complete } : { value: -1, stopped: true };
    }
    return { value: entry.mean_rows == null ? -1 : entry.mean_rows, stopped: entry.mean_rows == null };
  }

  // The fighters in rank order, each with its place. Ties share a place (two finishers are both 1st); a
  // stopped runner comes after every one that finished or fell, and is never ranked above one.
  function rank(results) {
    const single = (results.seeds || []).length <= 1;
    const scored = results.players.map((entry, slot) => ({ entry, slot, ...score(entry, single) }));
    scored.sort((a, b) => (a.stopped - b.stopped) || (b.value - a.value) || (a.slot - b.slot));
    let place = 0;
    return scored.map((s, i) => {
      const prev = scored[i - 1];
      if (!prev || prev.stopped !== s.stopped || prev.value !== s.value) place = i + 1;
      return { ...s, place };
    });
  }

  // How a fighter's run ended, in words.
  function death(entry, single) {
    if (single) {
      const track = entry.tracks[0];
      if (!track) return "Never started";
      if (!track.complete) return "Stopped at row " + track.rows + ": not a death";
      if (track.finished) return "Reached the finish line";
      return (DEATHS[track.death_cause] || "Fell") + " · row " + track.rows;
    }
    const causes = Object.keys(DEATHS).filter((c) => entry[c] > 0).map((c) => entry[c] + " " + DEATHS[c].toLowerCase());
    const parts = [];
    if (entry.finished) parts.push(entry.finished + " finished");
    if (causes.length) parts.push(causes.join(", "));
    if (entry.incomplete) parts.push(entry.incomplete + " stopped");
    return parts.join(" · ") || "No complete track";
  }

  function requestsText(entry, roster) {
    if (!entry.paid) return isFly(roster, entry.player) ? "none (simulated)" : "none";
    return String(entry.requests);
  }

  function costText(entry) {
    if (!entry.paid) return "free";
    if (!(entry.price_usd > 0)) return "free tier";
    return Lobby_.usd(entry.cost_estimate_usd);
  }

  // The wrong moves, as More numbers says them: the count, and the fatal one named with what was safe.
  function wrongText(entry, single) {
    const count = String(entry.wrong_moves);
    const track = single ? entry.tracks[0] : null;
    if (track && track.fatal) {
      return count + " · fatal, row " + track.fatal.row + ": " + track.fatal.move + " (" + track.fatal.safe.join(" or ") + " safe)";
    }
    if (track && track.trapped) return count + " · trapped at the end: no move there was safe";
    if (!single && entry.fatal_wrong_moves) return count + " · " + entry.fatal_wrong_moves + " fatal";
    return count;
  }

  function header(results) {
    const seeds = results.seeds || [];
    const n = results.players.length;
    const ended = results.status === "completed" ? "Run ended" : "Run " + (results.status || "ended");
    const where = seeds.length <= 1 ? "Track " + seeds[0]
      : "Tracks " + Math.min(...seeds) + "–" + Math.max(...seeds) + " (" + seeds.length + ")";
    return { left: ended + " · " + n + (n === 1 ? " fighter" : " fighters"),
             right: where + " · game " + results.game.version + " · " + results.game.max_rows + " rows" };
  }

  // The cards, in rank order.
  function cards(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const slotOf = new Map(results.players.map((e, i) => [e.player, i]));
    return rank(results).map((r) => ({
      place: r.place, top: r.place === 1 && !r.stopped, label: "P" + (slotOf.get(r.entry.player) + 1), player: r.entry.player,
      title: labelOf(roster, r.entry.player),
      rows: single ? (r.entry.tracks[0] ? r.entry.tracks[0].rows : 0) : (r.entry.mean_rows == null ? "-" : r.entry.mean_rows.toFixed(1)),
      rowsWord: single ? "rows" : "rows a track", death: death(r.entry, single), stopped: r.stopped,
      perRow: perRow(r.entry.s_per_row), requests: requestsText(r.entry, roster), cost: costText(r.entry),
      paid: !!(r.entry.paid && r.entry.price_usd > 0),
    }));
  }

  // One bar per fighter against the track's length, and the solver's line, which is the whole track (every
  // track can be finished), unless the solver ran.
  function bars(results, roster) {
    const max = results.game.max_rows;
    const single = (results.seeds || []).length <= 1;
    const out = rank(results).map((r) => {
      const rows = single ? (r.entry.tracks[0] ? r.entry.tracks[0].rows : 0) : (r.entry.mean_rows || 0);
      return { player: r.entry.player, name: labelOf(roster, r.entry.player), rows, width: max ? rows / max : 0, yardstick: false };
    });
    if (!results.players.some((e) => e.player === "solver")) {
      out.push({ player: "solver", name: "Solver (yardstick)", rows: max, width: 1, yardstick: true });
    }
    return out;
  }

  // The warning that one track is not a result, with the two best numbers in it.
  function warning(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const ranked = cards(results, roster).filter((c) => !c.stopped);
    if (!single) return "A few tracks are not a result either. Records holds the benchmark over many tracks.";
    if (ranked.length < 2) return "One track is not a result. Records holds the benchmark over many tracks.";
    return "One track is not a result: " + ranked[0].rows + " against " + ranked[1].rows +
      " rows can be this track's luck. Records holds the benchmark over many tracks.";
  }

  // More numbers: one row per number, one column per fighter in rank order.
  function table(results, roster) {
    const single = (results.seeds || []).length <= 1;
    const order = rank(results).map((r) => r.entry);
    const col = (fn) => order.map(fn);
    return {
      heads: order.map((e) => labelOf(roster, e.player)),
      rows: [
        { name: "Rows survived", hint: single ? "of " + results.game.max_rows : "mean, of " + results.game.max_rows,
          vals: col((e) => (single ? (e.tracks[0] ? String(e.tracks[0].rows) : "-") : (e.mean_rows == null ? "-" : e.mean_rows.toFixed(1)))) },
        { name: "Death", hint: "", vals: col((e) => death(e, single)) },
        { name: "Moves that were jumps", hint: "", vals: col((e) => percent(e.jump_share)) },
        { name: "Wrong moves", hint: "worse than the best", vals: col((e) => wrongText(e, single)) },
        { name: "Asked live", hint: "requests", vals: col((e) => requestsText(e, roster)) },
        { name: "From cache", hint: "replayed, free", vals: col((e) => (e.paid ? String(e.cache_hits) : "none")) },
        { name: "Time per row", hint: "mean", vals: col((e) => perRow(e.s_per_row)) },
        { name: "Tokens", hint: "in / out", vals: col((e) => (e.requests ? e.input_tokens.toLocaleString("en-US") + " / " +
          e.output_tokens.toLocaleString("en-US") : "none")) },
        { name: "Cost", hint: "estimate", vals: col(costText) },
      ],
    };
  }

  // Failed or unreadable answers, only when there were any: one line per fighter that had them.
  function failures(results, roster) {
    return results.players.filter((e) => e.fallback_rate > 0).map((e) => labelOf(roster, e.player) + ": " +
      percent(e.fallback_rate) + " of its rows fell back to the default move (errors " + percent(e.error_rate) +
      ", unreadable answers " + percent(e.invalid_rate) + ").");
  }

  // The note under More numbers: what is left out and why, and what is ours, from this lineup.
  function note(results, roster) {
    const parts = ["Probability scores are left out; the benchmark in Records has none either."];
    if (results.players.some((e) => isFly(roster, e.player))) {
      parts.push("The fly is asked nothing; how gaps become its input is ours.");
    }
    if (results.players.some((e) => e.paid && e.price_usd > 0)) {
      parts.push("Costs are live requests times the page's price per request: an estimate, not a bill.");
    }
    return parts.join(" ");
  }

  // ---- the markup --------------------------------------------------------------------------------
  function cardsHtml(list, more) {
    return list.map((c, i) => '<article class="card' + (c.top ? " top" : "") + (c.stopped ? " stopped" : "") + '" style="animation-delay:' +
      i * 90 + 'ms"><div class="card-top"><span class="place">' + c.place + '</span><span class="label who">' + esc(c.label) +
      "</span></div>" + (more ? "" : '<div class="art"><canvas class="sprite" data-player="' + esc(c.player) + '" data-px="11"></canvas></div>') +
      '<span class="title">' + esc(c.title) + '</span><span class="player">' + esc(c.player) + "</span>" +
      '<div class="rows"><span class="n">' + esc(c.rows) + '</span><span class="word">' + esc(c.rowsWord) + '</span><span class="death' +
      (c.stopped ? " warn" : " bad") + '">' + esc(c.death) + "</span></div>" +
      '<div class="stats"><span><span class="label">Per row</span>' + esc(c.perRow) + '</span><span><span class="label">Requests</span>' +
      esc(c.requests) + '</span><span><span class="label">Cost</span><span class="' + (c.paid ? "warn" : "muted") + '">' + esc(c.cost) +
      "</span></span></div></article>").join("");
  }

  function barsHtml(list, colourOf) {
    return list.map((b) => '<div class="bar' + (b.yardstick ? " yardstick" : "") + '"><span class="name">' + esc(b.name) + "</span>" +
      '<span class="track"><span class="fill" style="width:' + (b.width * 100).toFixed(2) + "%" +
      (b.yardstick ? "" : ";background:" + esc(colourOf(b.player) || "#3A4046")) + '"></span></span>' +
      '<span class="n">' + esc(typeof b.rows === "number" && !Number.isInteger(b.rows) ? b.rows.toFixed(1) : b.rows) + "</span></div>").join("");
  }

  function tableHtml(t) {
    return '<table class="numbers"><thead><tr><th></th>' + t.heads.map((h) => "<th>" + esc(h) + "</th>").join("") +
      "</tr></thead><tbody>" + t.rows.map((r) => '<tr><th>' + esc(r.name) + (r.hint ? ' <span class="muted">' + esc(r.hint) + "</span>" : "") +
      "</th>" + r.vals.map((v) => "<td>" + esc(v) + "</td>").join("") + "</tr>").join("") + "</tbody></table>";
  }

  const api = { percent, perRow, rank, death, wrongText, header, cards, bars, warning, table, failures, note, cardsHtml, barsHtml, tableHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Results = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/results.test.js`
Expected: `pass 10, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 41.79s`

- [ ] **Step 6: Commit**

```bash
git add viewer/results.js viewer/tests/results.test.js
git commit -F <message file>   # results: the results screen's ranking, words and markup
```

---

### Task 6: The records screen's leaderboard, head to head and past runs

**Files:**
- Create: `viewer/records.js`
- Test: `viewer/tests/records.test.js`

**Interfaces:**
- Consumes: GET /records' shape (plan a, with task 1's `tracks` and `ours`), `Minds.esc`.
- Produces: `viewer/records.js` (global `Records`): `SHOWN_RUNS` (10), `tunedHere(records, player)`, `board(records, roster)`, `boardNotes(records, roster)`, `pairOf(records, a, b)`, `chips(records, roster)`, `pairView(pair, roster, maxRows)`, `when(iso)`, `tracksText(seeds)`, `playersText(roster, players)`, `pastRuns(records, roster, all) -> {total, rows}`, `boardHtml(rows, chosen)`, `chipsHtml(list, a, b)`, `pairHtml(view)`, `runsHtml(rows)`. (Task 9 renames the live-watch marker to `data-now`.)

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/records.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Records = require("../records.js");

const skin = (player, name, color, inks) => ({ player, name, about: "", color, inks: inks || {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly", "Looming", "#AEB4BA"), skin("fly2", "Sideways", "#F7768E")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_step2", "Step 2", "#B8404F"), skin("jev_map", "Map", "#1E2227", { V: "#7AA2F7" })] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [skin("solver", "Solver", "#7AA2F7")] },
];
// the shape of GET /records (bakeoff/records.py, with bench.benchmark's numbers)
const player = (name, seeds, mean, lo, hi) => ({ player: name, seeds, mean_rows: mean, ci_low: lo, ci_high: hi, ranked: lo != null });
const RECORDS = {
  game: "v2", max_rows: 150, tracks: [1000, 1019], why: null, left_out: 3, unreadable: [], tuned_on: { fly2: [1000, 1199] },
  bench: {
    players: [player("solver", 20, 150, 150, 150), player("jev_step2", 5, 144.6, 129.6, 150), player("fly2", 20, 78.2, 61.8, 94.6),
              player("jev_map", 2, 49.6, null, null)],
    pairs: [
      { a: "jev_step2", b: "fly2", common_seeds: 5, mean_diff: 66.4, ci_low: 11.8, ci_high: 121.0, wins: 5, ties: 0, losses: 0,
        verdict: "jev_step2 ahead", seeds_needed: 5 },
      { a: "fly2", b: "jev_map", common_seeds: 2, mean_diff: 20, ci_low: null, ci_high: null, wins: 2, ties: 0, losses: 0,
        verdict: "too few tracks (2)", seeds_needed: null },
    ],
    notes: [],
  },
  runs: [
    { run_id: "20260925-163957", status: "running", started_at: "2026-09-25T16:39:57", seeds: [1400, 1401, 1402], players: ["fly", "fly2"], game: "v2", current: true },
    { run_id: "20260924-211656", status: "budget_exhausted", started_at: "2026-09-24T21:16:56", seeds: [1001], players: ["jev_step2", "jev_map", "fly"], game: "v2", current: false },
    { run_id: "20260924-100000", status: "running", started_at: null, seeds: [], players: ["<b>x</b>"], game: "v2", current: false },
  ],
  ours: {},
};

test("the leaderboard: ranked players numbered, yardsticks greyed and never ranked, too few tracks said so", () => {
  const rows = Records.board(RECORDS, ROSTER);
  assert.deepEqual(rows.map((r) => [r.rank, r.name, r.tracks, r.value]), [
    ["", "Bot · Solver (yardstick)", "20 tracks", "150.0"], ["1", "Jev · Step 2", "5 tracks", "144.6"],
    ["2", "Fly · Sideways", "20 tracks", "78.2"], ["", "Jev · Map", "2 tracks", "not ranked"]]);
  assert.equal(rows[0].yardstick, true);
  assert.equal(rows[1].lo, (129.6 / 150) * 100);
  assert.equal(rows[3].span, 0);
});

test("fly2 is marked on the tracks it was tuned on (decision 46)", () => {
  const rows = Records.board(RECORDS, ROSTER);
  assert.deepEqual(rows.filter((r) => r.tuned).map((r) => r.player), ["fly2"]);
  assert.equal(Records.tunedHere({ ...RECORDS, tracks: [1200, 1219] }, "fly2"), false);
  assert.match(Records.boardHtml(rows, []), /Fly · Sideways <span class="warn">tuned on these tracks<\/span>/);
});

test("a black skin gets an edge in its own ink, so it can be seen", () => {
  const map = Records.board(RECORDS, ROSTER).find((r) => r.player === "jev_map");
  assert.equal(map.edge, "#7AA2F7");
  assert.equal(Records.board(RECORDS, ROSTER).find((r) => r.player === "fly2").edge, null);
});

test("the notes: the order is no verdict, what is in-sample, what was left out and what could not be read", () => {
  const notes = Records.boardNotes({ ...RECORDS, unreadable: ["20260101-000000"] }, ROSTER);
  assert.match(notes[0], /^Most players have \d+ tracks?: their intervals overlap/);
  assert.match(notes[1], /Fly · Sideways's numbers were tuned on tracks 1000–1199/);
  assert.equal(notes[2], "3 older copies of a track left out: each player's track counts once, from its newest run.");
  assert.equal(notes[3], "Could not be read, so not counted: 20260101-000000.");
});

test("a pair reads the same either way round, with its numbers turned", () => {
  const turned = Records.pairOf(RECORDS, "fly2", "jev_step2");
  assert.deepEqual([turned.a, turned.b, turned.mean_diff, turned.ci_low, turned.ci_high, turned.wins, turned.losses],
    ["fly2", "jev_step2", -66.4, -121.0, -11.8, 0, 5]);
  assert.equal(turned.verdict, "jev_step2 ahead");
  assert.equal(Records.pairOf(RECORDS, "fly2", "nobody"), null);
});

test("the head to head: a verdict only when the interval leaves out 0, in the players' labels", () => {
  const v = Records.pairView(Records.pairOf(RECORDS, "jev_step2", "fly2"), ROSTER, 150);
  assert.equal(v.verdict, "Jev · Step 2 ahead");
  assert.equal(v.tell, true);
  assert.equal(v.diff, "+66.4");
  assert.equal(v.interval, "11.8 to 121.0");
  assert.equal(v.needed, "about 5");
  const few = Records.pairView(Records.pairOf(RECORDS, "fly2", "jev_map"), ROSTER, 150);
  assert.equal(few.tell, false);
  assert.equal(few.lo, null);
  assert.equal(few.note, "Too few tracks in common for an interval.");
});

test("chips offer ranked pairs only, the verdicts first", () => {
  assert.deepEqual(Records.chips(RECORDS, ROSTER).map((c) => c.label), ["Jev · Step 2 vs Fly · Sideways"]);
});

test("past runs: only this session's run is live; another that says running is not ours to stream", () => {
  const { total, rows } = Records.pastRuns(RECORDS, ROSTER, true);
  assert.equal(total, 3);
  assert.deepEqual(rows.map((r) => [r.status, r.kind, r.watch]), [["running now", "live", "Watch live"],
    ["budget used up", "warn", "Watch"], ["running elsewhere, or stopped without closing", "warn", "Watch"]]);
  assert.equal(rows[0].tracks, "1400–1402 (3)");
  assert.equal(rows[0].when, "25 Sep 16:39");
  assert.equal(rows[1].players, "Jev · Step 2, Map; Fly · Looming");
  assert.equal(rows[2].when, "-");
  const html = Records.runsHtml(rows);
  assert.equal(html.includes("<b>"), false);
  assert.match(html, /data-watch="20260925-163957" data-live="true"/);
});

test("the first ten past runs, then all of them when asked", () => {
  const many = { ...RECORDS, runs: Array.from({ length: 12 }, (_, i) => ({ ...RECORDS.runs[1], run_id: "r" + i })) };
  assert.equal(Records.pastRuns(many, ROSTER, false).rows.length, Records.SHOWN_RUNS);
  assert.equal(Records.pastRuns(many, ROSTER, true).rows.length, 12);
  assert.equal(Records.SHOWN_RUNS, 10);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `node --test viewer/tests/records.test.js`
Expected:

```text
✖ viewer/tests/records.test.js
ℹ pass 0
ℹ fail 1
```

- [ ] **Step 3: Write the implementation**

Create `viewer/records.js`:

```javascript
// The records screen: the leaderboard, the head to head, and the past runs. Every number is `bakeoff
// bench`'s, worked out by bakeoff/records.py (GET /records); this file only orders, words and draws them. Pure
// and tested; the markup is returned as strings.
//
// `records` is {game, max_rows, tracks, bench: {players, pairs, notes} | null, why, left_out, unreadable, runs,
// tuned_on, ours}; `roster` is bakeoff/roster.py's JSON.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const esc = Minds_.esc;

  const SHOWN_RUNS = 10; // past runs listed before "Show all"
  const DARK = "#1E2227"; // a skin this dark needs an edge to be seen on the page (the Map skins' black)

  function skinOf(roster, player) {
    for (const character of roster || []) {
      for (const skin of character.skins) if (skin.player === player) return { character, skin };
    }
    return null;
  }
  const labelOf = (roster, player) => {
    const found = skinOf(roster, player);
    return found ? found.character.name + " · " + found.skin.name : player;
  };
  // the yardsticks are the Bot's skins: shown for scale, greyed, never ranked
  const isYardstick = (roster, player) => {
    const found = skinOf(roster, player);
    return !!found && found.character.id === "bot";
  };

  // Did this player's frozen numbers come from the tracks ranked here? (fly2 was tuned on 1000 to 1199.)
  function tunedHere(records, player) {
    const on = (records.tuned_on || {})[player];
    const tracks = records.tracks || [];
    return !!on && tracks.length === 2 && on[0] <= tracks[1] && on[1] >= tracks[0];
  }

  // The leaderboard, in bench's order: ranked players first by mean rows, then those with too few tracks
  // for an interval. Only a ranked non-yardstick gets a place number.
  function board(records, roster) {
    const players = (records.bench && records.bench.players) || [];
    const max = records.max_rows || 1;
    const pct = (x) => Math.max(0, Math.min(100, (x / max) * 100));
    let place = 0;
    return players.map((p) => {
      const yardstick = isYardstick(roster, p.player);
      const ranked = p.ranked && !yardstick;
      if (ranked) place += 1;
      const found = skinOf(roster, p.player);
      const colour = found ? found.skin.color : "#3A4046";
      const edge = colour === DARK && found ? Object.values(found.skin.inks)[0] || "#2A2F35" : null;
      return {
        player: p.player, rank: ranked ? String(place) : "", name: labelOf(roster, p.player) + (yardstick ? " (yardstick)" : ""),
        yardstick, tracks: p.seeds + (p.seeds === 1 ? " track" : " tracks"), colour, edge,
        lo: pct(p.ci_low == null ? p.mean_rows : p.ci_low), span: p.ci_low == null ? 0 : pct(p.ci_high) - pct(p.ci_low),
        mean: pct(p.mean_rows), value: p.ci_low == null ? "not ranked" : p.mean_rows.toFixed(1),
        tuned: tunedHere(records, p.player),
      };
    });
  }

  // The notes under the leaderboard: that its order is no verdict, which rows are in-sample, what was left out.
  function boardNotes(records, roster) {
    const rows = board(records, roster).filter((r) => !r.yardstick);
    const notes = [];
    if (rows.length) {
      const counts = rows.map((r) => Number.parseInt(r.tracks, 10));
      const common = counts.slice().sort((a, b) => counts.filter((c) => c === b).length - counts.filter((c) => c === a).length)[0];
      notes.push("Most players have " + common + (common === 1 ? " track" : " tracks") + ": their intervals overlap, so this " +
        "order is not a verdict. Pick a pair to see what the numbers can tell apart.");
    }
    for (const r of rows.filter((x) => x.tuned)) {
      const on = records.tuned_on[r.player];
      notes.push(labelOf(roster, r.player) + "'s numbers were tuned on tracks " + on[0] + "–" + on[1] +
        ", these tracks included: its mean here is in-sample.");
    }
    if (records.left_out) {
      notes.push(records.left_out + " older " + (records.left_out === 1 ? "copy" : "copies") + " of a track left out: each " +
        "player's track counts once, from its newest run.");
    }
    if ((records.unreadable || []).length) {
      notes.push("Could not be read, so not counted: " + records.unreadable.join(", ") + ".");
    }
    return notes;
  }

  // The pair from bench's list, whichever way round it was asked for: (a, b) or (b, a) with the sign flipped.
  function pairOf(records, a, b) {
    const pairs = (records.bench && records.bench.pairs) || [];
    const found = pairs.find((p) => p.a === a && p.b === b);
    if (found) return found;
    const turned = pairs.find((p) => p.a === b && p.b === a);
    if (!turned) return null;
    // the verdict names its player ("jev_step2 ahead"), so it reads the same whichever way round
    const flip = (x) => (x == null ? null : -x);
    return { ...turned, a, b, mean_diff: flip(turned.mean_diff), ci_low: flip(turned.ci_high), ci_high: flip(turned.ci_low),
             wins: turned.losses, losses: turned.wins };
  }

  // Up to six pairs to offer as chips: among the players ranked here (no yardsticks), the pairs with a verdict
  // first, then the ones with the most tracks in common, then the largest differences.
  function chips(records, roster) {
    const ranked = new Set(board(records, roster).filter((r) => r.rank).map((r) => r.player));
    const pairs = ((records.bench && records.bench.pairs) || []).filter((p) => ranked.has(p.a) && ranked.has(p.b));
    const clear = (p) => p.verdict.endsWith(" ahead");
    return pairs.slice().sort((x, y) => (clear(y) - clear(x)) || (y.common_seeds - x.common_seeds) ||
      (Math.abs(y.mean_diff || 0) - Math.abs(x.mean_diff || 0))).slice(0, 6)
      .map((p) => ({ a: p.a, b: p.b, label: labelOf(roster, p.a) + " vs " + labelOf(roster, p.b) }));
  }

  // One pair, as the head to head shows it. The axis runs from the whole track behind to the whole track ahead.
  function pairView(pair, roster, maxRows) {
    const R = maxRows || 150;
    const ax = (x) => ((Math.max(-R, Math.min(R, x)) + R) / (2 * R)) * 100;
    const a = labelOf(roster, pair.a), b = labelOf(roster, pair.b);
    const tell = pair.verdict.endsWith(" ahead");
    const sign = (x) => (x >= 0 ? "+" : "") + x.toFixed(1);
    return {
      a, b, tracks: pair.common_seeds, diff: pair.mean_diff == null ? "-" : sign(pair.mean_diff),
      lo: pair.ci_low == null ? null : ax(pair.ci_low), span: pair.ci_low == null ? 0 : ax(pair.ci_high) - ax(pair.ci_low),
      mean: pair.mean_diff == null ? null : ax(pair.mean_diff),
      interval: pair.ci_low == null ? "-" : pair.ci_low.toFixed(1) + " to " + pair.ci_high.toFixed(1),
      wtl: pair.wins + " / " + pair.ties + " / " + pair.losses,
      needed: pair.seeds_needed == null ? "-" : "about " + pair.seeds_needed,
      verdict: pair.verdict.replace(pair.a + " ahead", a + " ahead").replace(pair.b + " ahead", b + " ahead"), tell,
      note: tell ? "The interval stays clear of 0 on the tracks both played."
        : pair.ci_low == null ? "Too few tracks in common for an interval."
          : "The interval crosses 0: on these tracks either could be ahead.",
    };
  }

  // When a run started, as the list says it: "25 Sep 16:39", in the viewer's own time zone.
  function when(iso) {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "-";
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const two = (n) => String(n).padStart(2, "0");
    return d.getDate() + " " + months[d.getMonth()] + " " + two(d.getHours()) + ":" + two(d.getMinutes());
  }

  function tracksText(seeds) {
    if (!seeds.length) return "-";
    if (seeds.length === 1) return String(seeds[0]);
    return Math.min(...seeds) + "–" + Math.max(...seeds) + " (" + seeds.length + ")";
  }

  // "Jev · Step 1, Guided; Fly · Looming": each character once, its skins after it, in the run's own order.
  function playersText(roster, players) {
    const groups = [];
    for (const player of players) {
      const found = skinOf(roster, player);
      const name = found ? found.character.name : player;
      const group = groups.find((g) => g.name === name);
      if (group) { if (found) group.skins.push(found.skin.name); } else groups.push({ name, skins: found ? [found.skin.name] : [] });
    }
    return groups.map((g) => g.name + (g.skins.length ? " · " + g.skins.join(", ") : "")).join("; ");
  }

  const STATUS = { completed: ["completed", "ok"], interrupted: ["interrupted", "warn"], budget_exhausted: ["budget used up", "warn"],
                   aborted: ["aborted", "warn"], crashed: ["crashed", "bad"] };

  // The past runs, newest first: the first ten unless all are asked for. Only this session's run pulses and
  // can be watched live; another run whose meta.json says running is not this page's to stream.
  function pastRuns(records, roster, all) {
    const runs = records.runs || [];
    return { total: runs.length, rows: (all ? runs : runs.slice(0, SHOWN_RUNS)).map((r) => {
      let status = STATUS[r.status] || [r.status || "status unknown", "warn"];
      if (r.status === "running") status = r.current ? ["running now", "live"] : ["running elsewhere, or stopped without closing", "warn"];
      return { run_id: r.run_id, when: when(r.started_at), tracks: tracksText(r.seeds), players: playersText(roster, r.players),
               status: status[0], kind: status[1], watch: r.current ? "Watch live" : "Watch" };
    }) };
  }

  // ---- the markup --------------------------------------------------------------------------------
  function boardHtml(rows, chosen) {
    return rows.map((r) => '<button type="button" class="entry' + (r.yardstick ? " yardstick" : "") +
      (chosen.includes(r.player) ? " chosen" : "") + '" data-player="' + esc(r.player) + '">' +
      '<span class="rank">' + esc(r.rank) + '</span><span class="swatch" style="background:' + esc(r.colour) +
      (r.edge ? ";box-shadow:inset 0 0 0 1px " + esc(r.edge) : "") + '"></span><span class="name">' + esc(r.name) +
      (r.tuned ? ' <span class="warn">tuned on these tracks</span>' : "") + '</span><span class="tracks">' + esc(r.tracks) +
      '</span><span class="band"><span class="ci" style="left:' + r.lo.toFixed(2) + "%;width:" + r.span.toFixed(2) + '%"></span>' +
      '<span class="mean" style="left:calc(' + r.mean.toFixed(2) + '% - 1px)"></span></span><span class="value">' + esc(r.value) +
      "</span></button>").join("");
  }

  function chipsHtml(list, a, b) {
    return list.map((c) => '<button type="button" class="chip' + (c.a === a && c.b === b ? " on" : "") + '" data-a="' + esc(c.a) +
      '" data-b="' + esc(c.b) + '">' + esc(c.label) + "</button>").join("");
  }

  function pairHtml(v) {
    return '<div class="vs"><span class="who">' + esc(v.a) + '</span><span class="label">VS</span><span class="who">' + esc(v.b) +
      '</span></div><div class="diff"><span class="n">' + esc(v.diff) + "</span><span>rows a track, on " + esc(v.tracks) +
      " tracks both played</span></div>" +
      '<div class="axis"><span class="zero"></span>' +
      (v.lo == null ? "" : '<span class="ci' + (v.tell ? " tell" : "") + '" style="left:' + v.lo.toFixed(2) + "%;width:" + v.span.toFixed(2) + '%"></span>') +
      (v.mean == null ? "" : '<span class="mean" style="left:calc(' + v.mean.toFixed(2) + '% - 1px)"></span>') + "</div>" +
      '<div class="axis-labels"><span>' + esc(v.b) + " ahead</span><span>0</span><span>" + esc(v.a) + " ahead</span></div>" +
      '<div class="stats"><span><span class="label">95% interval</span>' + esc(v.interval) + '</span><span><span class="label">' +
      "Wins / ties / losses</span>" + esc(v.wtl) + '</span><span><span class="label">Tracks for a verdict</span>' + esc(v.needed) +
      '</span></div><div class="verdict' + (v.tell ? " tell" : "") + '"><span class="word">' + esc(v.verdict) + '</span><span class="note">' +
      esc(v.note) + "</span></div>";
  }

  function runsHtml(list) {
    return list.map((r) => '<div class="past"><span class="when">' + esc(r.when) + '</span><span>' + esc(r.tracks) + "</span>" +
      '<span class="players">' + esc(r.players) + '</span><span class="label status ' + r.kind + '">' + esc(r.status) + "</span>" +
      '<span class="actions"><button type="button" data-watch="' + esc(r.run_id) + '"' + (r.watch === "Watch live" ? ' data-live="true"' : "") +
      ">" + esc(r.watch) + '</button><button type="button" data-results="' + esc(r.run_id) + '">Results</button></span></div>').join("");
  }

  const api = { SHOWN_RUNS, tunedHere, board, boardNotes, pairOf, chips, pairView, when, tracksText, playersText, pastRuns,
                boardHtml, chipsHtml, pairHtml, runsHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Records = api;
})(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `node --test viewer/tests/records.test.js`
Expected: `pass 9, fail 0`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 43.39s`

- [ ] **Step 6: Commit**

```bash
git add viewer/records.js viewer/tests/records.test.js
git commit -F <message file>   # records: the records screen's leaderboard, head to head and past runs
```

---

### Task 7: The front: home and the character select

**Files:**
- Modify: `viewer/app.js`
- Create: `viewer/front.css`
- Create: `viewer/front.js`
- Modify: `viewer/index.html`
- Modify: `viewer/sprites.js`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `Screens`, `Select` (tasks 2–3), `Roster.make`, `Sprites`, the embedded roster.
- Produces: `Sprites.paint(canvas, name, px, options)`; `viewer/front.css`; `viewer/front.js` (global `Front` with `start()`, live only); `window.Race.setShown(on)` in app.js; the live page hides `.top` and `.tabs`, titles itself Brain Battle and calls `Front.start()`; `#front` with `#screen-home` and `#screen-select` in index.html; scripts `screens.js`, `select.js`, `front.js` before `app.js`.

This task leaves the old lobby code in app.js unused; task 8 removes it.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -76,7 +76,7 @@ def test_the_page_carries_the_chart_rules_the_analysis_tab_draws_with():
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
     assert names == ["timeline.js", "tunnel.js", "sprites.js", "roster.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
-                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "app.js"]
+                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "front.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
1 failed, 21 passed in 1.39s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -652,6 +652,18 @@
     if (!why) BenchView.mount($("bench"), benchData);
   }
 
+  // ---- the race, as the front drives it (front.js, live only) -----------------------------------
+  // The front owns the screens; the run screen is this page. It is shown and hidden through setShown, so
+  // the transport and its keys work only while the race is on screen.
+  window.Race = {
+    setShown(on) {
+      if (on) return showTab("run");
+      view.tab = "off";
+      $("transport").hidden = true;
+      setPlaying(false);
+    },
+  };
+
   // ---- start --------------------------------------------------------------------------------
   let ready = false;
   Feed.fromEmbedded(embedded, handlers);
@@ -669,7 +681,11 @@
     const clear = handlers.onFrame;
     // a frame means the stream is alive: the waiting or the lost-connection notice goes, a real error stays
     handlers.onFrame = (...args) => { if (store.error == null) notice(null); clear(...args); };
-    $("lobby").hidden = false; // the page runs the show; a replay file has no server and no controls
-    refreshState();
+    // the page runs the show through the Brain Battle front (front.js); a replay file has no server and no
+    // front, and keeps the two tabs
+    document.querySelector(".tabs").hidden = true;
+    document.querySelector(".top").hidden = true;
+    document.title = "Brain Battle";
+    Front.start();
   }
 })();
```

Create `viewer/front.css`:

```css
/* Brain Battle, the front of `bakeoff live` (front.js): the approved mock-ups (docs/mockups/brain-battle/) in
   the brand's tokens (viewer.css). Smash's layout and energy, the brand's dark palette and two fonts: the
   shouts are the body font at 900, italic and skewed; mono stays for short labels. Blue is the cursor (the
   portrait, slot and track in focus); the home logo's pulsing brain is its one other use, the user's call.
   Money is --warn, deaths --bad. Everything is scoped to #front, so the run screen and a replay file are
   untouched. */

/* the live page drops the replay's own header and tabs (app.js hides them; their display rules would win) */
.top[hidden], .tabs[hidden] { display: none; }

#front { --shout-skew: skewX(-9deg); max-width: 1200px; margin: 0 auto; }
#front[hidden], #front .screen[hidden] { display: none; }
#front .screen { min-height: calc(100vh - 48px); display: flex; flex-direction: column; margin: 0; border: 0; padding: 0 0 24px; }
#front button { font-family: var(--font-body); color: inherit; }
#front .shout { margin: 0; font: italic 900 40px/1 var(--font-body); letter-spacing: -0.02em; color: var(--bright);
  transform: var(--shout-skew); }
#front .bright { color: var(--text); }
#front .blink { animation: bb-blink 1.1s steps(1) infinite; }
@keyframes bb-blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }
@keyframes bb-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes bb-pulse {
  0%, 100% { filter: drop-shadow(0 0 6px rgba(122, 162, 247, .35)); }
  50% { filter: drop-shadow(0 0 28px rgba(122, 162, 247, .9)) drop-shadow(0 0 60px rgba(122, 162, 247, .45)); }
}
@keyframes bb-in { from { transform: translateX(-40px) skewX(-12deg); opacity: 0; } to { transform: translateX(0) skewX(-12deg); opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  #front .blink, #front .bob, #front .brain, #front .banner { animation: none; }
}
#front canvas.sprite { display: block; image-rendering: pixelated; }

/* the head every screen but home has: back, the shout, a short label */
#front .screen-head { display: flex; justify-content: space-between; align-items: center; min-height: 76px; gap: 16px; }
#front .back { padding: 0; border: 0; background: none; cursor: pointer; color: var(--muted); }
#front .back:hover { color: var(--bright); }

/* ---- home -------------------------------------------------------------------------------------- */
#front .home { position: relative; overflow: hidden; }
#front .rings { position: absolute; inset: 0; display: flex; justify-content: center; align-items: center; pointer-events: none; }
#front .rings span { position: absolute; border: 1px solid var(--hairline); border-radius: 50%; }
#front .rings span:nth-child(1) { width: 1600px; height: 1600px; }
#front .rings span:nth-child(2) { width: 1100px; height: 1100px; }
#front .rings span:nth-child(3) { width: 640px; height: 640px; }
#front .rings .slash { width: 2px; height: 1600px; border: 0; border-radius: 0; background: var(--hairline); transform: rotate(-14deg); }
#front .home-top { position: relative; display: flex; justify-content: space-between; padding: 24px 0; }
#front .home-middle { position: relative; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 28px; }
#front .logo { position: relative; display: flex; justify-content: center; align-items: center; width: min(700px, 100%); height: 390px; }
#front .brain { position: absolute; left: 50%; top: 30px; transform: translateX(-50%); opacity: 0.7; image-rendering: pixelated;
  animation: bb-pulse 2.4s ease-in-out infinite; }
#front .logo h1 { position: relative; display: flex; flex-direction: column; align-items: center; font-size: clamp(72px, 12vw, 156px);
  letter-spacing: -0.04em; line-height: 0.82; }
#front .logo .outline { margin-top: -6px; color: transparent; -webkit-text-stroke: 3px var(--bright); }
#front .home-fighters { display: flex; align-items: flex-end; gap: 56px; }
#front .home-fighters figure { margin: 0; display: flex; flex-direction: column; align-items: center; gap: 12px; }
#front .home-fighters .bob { animation: bb-bob 1.6s ease-in-out infinite; }
#front .menu { display: flex; flex-direction: column; align-items: center; gap: 10px; }
#front .launch { display: flex; align-items: center; justify-content: center; gap: 14px; min-width: 280px; padding: 14px 28px;
  background: transparent; border: 2px solid var(--accent); color: var(--bright); font: italic 800 28px/1.2 var(--font-body);
  letter-spacing: 0.02em; cursor: pointer; }
#front .launch span { color: var(--accent); font-style: normal; font-size: 18px; }
#front .secondary { min-width: 280px; padding: 10px 28px; background: transparent; border: 1px solid var(--hairline);
  color: var(--muted); font: 600 18px/1.4 var(--font-body); cursor: pointer; }
#front .secondary:hover { color: var(--bright); border-color: var(--line-strong); }
#front .menu .blink { margin-top: 14px; color: var(--text); }
#front .home-foot { position: relative; display: flex; justify-content: space-between; gap: 16px; padding: 20px 0 0;
  border-top: 1px solid var(--hairline); font-size: var(--size-small); color: var(--muted); }

/* ---- character select ------------------------------------------------------------------------- */
#front .portraits { display: flex; justify-content: center; gap: 16px; margin-top: 8px; flex-wrap: wrap; }
#front .portrait { position: relative; width: 208px; height: 250px; padding: 0; display: flex; flex-direction: column;
  overflow: hidden; background: var(--panel); border: 2px solid var(--hairline); cursor: pointer; }
#front .portrait[aria-current="true"] { border-color: var(--accent); }
#front .portrait[aria-disabled="true"] { opacity: 0.45; cursor: not-allowed; }
#front .portrait .count { position: absolute; top: 10px; left: 12px; font-size: var(--size-label-sm); }
#front .portrait .tokens { position: absolute; top: 8px; right: 8px; display: flex; gap: 4px; }
#front .token { padding: 2px 6px; border-radius: 10px; background: var(--bright); color: var(--void);
  font: 600 var(--size-label-sm)/1.4 var(--font-mono); }
#front .token.focus { background: var(--accent); }
#front .portrait .art { flex: 1; display: flex; align-items: center; justify-content: center; }
#front .portrait .name { height: 48px; display: flex; align-items: center; justify-content: center; background: #15181C;
  border-top: 1px solid var(--hairline); font: italic 900 24px/1 var(--font-body); color: var(--bright); }
#front .info { min-height: 52px; margin-top: 14px; display: flex; align-items: center; gap: 16px; padding: 0 16px;
  border: 1px solid var(--hairline); background: var(--panel); }
#front .info .who { color: var(--accent); flex: none; }
#front .info .swatch { width: 12px; height: 12px; border-radius: 50%; flex: none; box-shadow: inset 0 0 0 1px var(--line-strong); }
#front .info .title { font-weight: 600; color: var(--bright); flex: none; }
#front .info .about { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--size-small); }
#front .info .why { font-size: var(--size-small); flex: none; }
#front .info .price { font-size: var(--size-label-sm); flex: none; }
#front .info .price.paid { color: var(--warn); }
#front .info .hint { font-size: var(--size-small); color: var(--muted); }
#front .banner-row { height: 76px; margin-top: 14px; display: flex; align-items: center; justify-content: center; }
#front .banner { width: 100%; height: 64px; display: flex; align-items: center; justify-content: center; gap: 28px; border: 0;
  background: var(--bright); color: var(--void); cursor: pointer; transform: skewX(-12deg); animation: bb-in 260ms var(--ease); }
#front .banner[hidden], #front .banner-empty[hidden] { display: none; }
#front .banner .shout { font-size: 44px; color: var(--void); transform: none; }
#front .banner .label { color: var(--void); }
#front .banner-empty { width: 100%; height: 64px; display: flex; align-items: center; justify-content: center;
  border: 1px dashed var(--line-strong); transform: skewX(-12deg); }
#front .slots { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
#front .slot { height: 196px; display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 8px 6px 10px;
  background: var(--panel); border: 2px solid var(--hairline); }
#front .slot.focus { border-color: var(--accent); }
#front .slot.empty { justify-content: center; background: none; border: 1px dashed var(--line-strong); font-size: 13px; color: var(--muted); }
#front .slot.empty .label { color: var(--line-strong); font-weight: 600; }
#front .slot-top { align-self: stretch; display: flex; justify-content: space-between; align-items: center; }
#front .slot-label { padding: 2px 0; border: 0; background: none; cursor: pointer; font-weight: 600; color: var(--text); }
#front .slot.focus .slot-label { color: var(--accent); }
#front .remove { width: 24px; height: 24px; padding: 0; border: 0; background: none; cursor: pointer; color: var(--muted); }
#front .slot-art { height: 72px; padding: 0; border: 0; background: none; cursor: pointer; display: flex; align-items: center; justify-content: center; }
#front .slot .name { font: italic 900 17px/1.1 var(--font-body); color: var(--bright); }
#front .slot .skin { font-size: 13px; line-height: 1.1; color: var(--text); }
#front .dots { display: flex; gap: 5px; margin-top: auto; }
#front .dot { width: 14px; height: 14px; padding: 0; border-radius: 50%; border: 2px solid var(--panel); cursor: pointer;
  box-shadow: 0 0 0 1px var(--line-strong); }
#front .dot.on { border-color: var(--bright); }
#front .dot[disabled] { opacity: 0.25; cursor: not-allowed; }
#front .keys { margin-top: auto; padding-top: 16px; display: flex; justify-content: center; gap: 28px; flex-wrap: wrap;
  font-size: var(--size-label-sm); }

@media (max-width: 720px) {
  #front .shout { font-size: 28px; }
  #front .home-fighters { gap: 24px; }
  #front .portrait { width: calc(50% - 8px); height: 200px; }
  #front .slots { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  #front .info { flex-wrap: wrap; padding: 10px 16px; }
  #front .info .about { white-space: normal; }
}
```

Create `viewer/front.js`:

```javascript
// Brain Battle, the front of `bakeoff live`: home, the character select, the track select, results and
// records around the run screen (#app, app.js). Glue only: the rules are in screens.js, select.js,
// trackpick.js, results.js and records.js, which have tests. It talks to the server through the control
// routes (GET /state, POST /run, POST /cancel, GET /results, /records, /replay), every request carrying the
// session's token, and drives the run screen through window.Race. A replay file has no server and no front.
(function (root) {
  "use strict";

  const liveUrl = document.body.dataset.live || null;
  if (!liveUrl) return; // a replay file: no server, no front, the two tabs as before

  const $ = (id) => document.getElementById(id);
  const token = document.body.dataset.token || null;
  const rosterSlot = document.getElementById("roster-data");
  const roster = (rosterSlot && JSON.parse(rosterSlot.textContent)) || [];
  const looks = Roster.make(roster);

  // the pixel brain behind the logo (the approved home mock-up); its rows are padded to one width
  const BRAIN = ["..........BBBBBBBBB", "......BBBBBBBBBBBBBBBBB", "....BBBBBBBBBBBBBBBBBBBBB", "...BBBBBBBBBBBBBBBBBBBBBBBB",
    "..BBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB", ".BBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "..BBBBBBBBBBBBBBBBBBBBBBBBBB", "...BBBBBBBBBBBBBBBBBBBBBBBB", ".....BBBBBBBBBBBBBBBBBBBBBB",
    ".................BBBBBBBBBBB", "..................BBBBBBBBB", "....................BBB", "....................BBB"];
  const ACCENT = "#7AA2F7"; // --accent: the brain is the one use of blue that is not the cursor (docs/FRONTEND.md)

  const front = {
    screen: "home", from: "home", state: null, sel: Select.make(roster, []), seed: null, armed: false, refusal: null,
  };

  async function control(path, options) {
    const settings = options || {};
    try {
      const response = await fetch(path, { ...settings, headers: { "X-Bakeoff-Token": token, ...(settings.headers || {}) } });
      const body = await response.json().catch(() => ({ error: "the server answered something that is not JSON" }));
      return { ok: response.ok, body };
    } catch (e) { // the command was stopped, or the machine went to sleep
      return { ok: false, body: { error: "no answer from the run: is `bakeoff live` still going?" } };
    }
  }

  // Every empty sprite canvas under `el` gets its fighter, in its skin. The fly shows its wings open, as on the
  // approved screens. A portrait is not a decision, so Jev's slit is no gauge here: it is lit as the mock-ups
  // light it (three cells), and the Map skin shows its blue; only the tunnel's slit reads Jev's probability.
  const PORTRAIT_P = 0.6;
  function paintSprites(el) {
    for (const canvas of el.querySelectorAll("canvas.sprite[data-player]")) {
      const look = looks.look(canvas.dataset.player);
      const p = look.sprite === "visor" && !(look.inks || {}).V ? PORTRAIT_P : null;
      Sprites.paint(canvas, look.sprite, Number(canvas.dataset.px) || 4,
                    { color: look.color, inks: look.inks, open: look.sprite === "fly", p });
    }
  }

  // ---- the screens ---------------------------------------------------------------------------------
  function show(screen) {
    const next = Screens.select(front.screen, screen);
    if (next === "records" && front.screen !== "records") front.from = front.screen;
    front.screen = next;
    for (const s of Screens.stateOf(next)) {
      const el = s.name === "run" ? $("app") : $("screen-" + s.name);
      if (el) el.hidden = s.hidden;
    }
    $("front").hidden = next === "run";
    Race.setShown(next === "run");
    render();
    window.scrollTo(0, 0);
  }

  function render() {
    if (front.screen === "home") renderHome();
    if (front.screen === "select") renderSelect();
  }

  // ---- home ------------------------------------------------------------------------------------------
  function paintBrain() {
    const canvas = $("brain"), px = 18, width = Math.max(...BRAIN.map((row) => row.length));
    canvas.width = width * px;
    canvas.height = BRAIN.length * px;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = ACCENT;
    BRAIN.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (row[x] === "B") ctx.fillRect(x * px, y * px, px, px); });
  }

  function renderHome() {
    const state = front.state;
    $("home-where").textContent = location.host + (state ? " · ceiling " + state.max_requests + " requests" : "");
    $("home-game").textContent = state ? "Game " + state.game.version + " · " + state.max_rows + " rows" : "";
    // the four contestants, each in its default skin; the yardsticks are not on the title screen
    $("home-fighters").innerHTML = roster.filter((c) => c.id !== "bot").map((c, i) =>
      '<figure><span class="bob" style="animation-delay:' + (i * 0.2).toFixed(1) + 's"><canvas class="sprite" data-player="' +
      Minds.esc(c.skins[0].player) + '" data-px="8"></canvas></span><figcaption class="label">' + Minds.esc(c.name) +
      "</figcaption></figure>").join("");
    paintSprites($("home-fighters"));
  }

  $("launch").addEventListener("click", () => show("select"));

  // ---- the character select ------------------------------------------------------------------------
  function renderSelect() {
    const sel = front.sel;
    $("select-count").textContent = sel.slots.length + " / " + Select.MAX + " fighters";
    $("portraits").innerHTML = Select.portraitsHtml(sel, roster);
    $("slots").innerHTML = Select.slotsHtml(sel, roster);
    $("select-info").innerHTML = Select.infoHtml(sel, roster, front.state ? front.state.players : []);
    $("fight").hidden = !Select.ready(sel);
    $("not-ready").hidden = Select.ready(sel);
    paintSprites($("portraits"));
    paintSprites($("slots"));
  }

  function setSel(sel) {
    front.sel = sel;
    front.armed = false; // another lineup: another worst case to confirm
    renderSelect();
  }

  $("portraits").addEventListener("click", (event) => {
    const portrait = event.target.closest("button[data-char]");
    if (portrait) setSel(Select.add(front.sel, roster, Number(portrait.dataset.char)));
  });
  $("slots").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.remove != null) setSel(Select.remove(front.sel, Number(button.dataset.remove)));
    else if (button.dataset.skin != null) setSel(Select.setSkin(front.sel, Number(button.dataset.slot), Number(button.dataset.skin)));
    else if (button.dataset.focus != null) setSel(Select.focusSlot(front.sel, Number(button.dataset.focus)));
  });
  $("fight").addEventListener("click", () => { if (Select.ready(front.sel)) show("track"); });

  // ---- keys and Back -------------------------------------------------------------------------------
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-back]")) show(Screens.back(front.screen, front.from));
  });
  document.addEventListener("keydown", (event) => {
    if (front.screen === "run" || event.metaKey || event.ctrlKey || event.altKey) return;
    // a focused button already answers Enter and Space with a click; typing in a field is not a command
    if (event.target instanceof Element && event.target.closest("input, select, textarea") ||
        (event.target instanceof Element && event.target.closest("button") && (event.key === "Enter" || event.key === " "))) return;
    let out = null;
    if (front.screen === "home") {
      if (event.key === "Enter") out = { go: "select" };
    } else if (front.screen === "select") {
      out = Select.onKey(front.sel, roster, event.key);
      if (out && out.sel !== front.sel) setSel(out.sel);
    } else if (event.key === "Escape") {
      out = { go: "back" };
    }
    if (!out) return;
    event.preventDefault();
    if (out.go === "back") show(Screens.back(front.screen, front.from));
    else if (out.go) show(out.go);
  });

  // ---- the state ------------------------------------------------------------------------------------
  async function refreshState() {
    const seed = front.seed == null ? "" : String(front.seed);
    const { ok, body } = await control("/state?seed=" + encodeURIComponent(seed));
    if (!ok) { front.refusal = body.error; return render(); }
    applyState(body);
  }

  function applyState(state) {
    if (front.state == null) { // the first answer: the select opens with what the command line offered
      front.sel = Select.make(roster, (state.ready || {}).players || []);
      front.seed = (state.ready || {}).seed != null ? state.ready.seed : state.first_practice_seed;
    }
    front.state = state;
    render();
  }

  // app.js calls this once the run screen is ready (live only).
  function start() {
    paintBrain();
    show("home");
    refreshState();
  }

  root.Front = { start };
})(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/index.html`:

```diff
@@ -6,6 +6,7 @@
 <title>Tunnel Run</title>
 <link rel="stylesheet" href="viewer.css">
 <link rel="stylesheet" href="bench.css">
+<link rel="stylesheet" href="front.css">
 </head>
 <body>
 <header class="top">
@@ -13,6 +14,42 @@
   <p class="label" id="mode"></p>
 </header>
 
+<!-- Brain Battle, the front of `bakeoff live` (front.js): one screen at a time, the run screen being #app.
+     A replay file never shows it. -->
+<div id="front" hidden>
+<section id="screen-home" class="screen home" aria-label="Brain Battle">
+  <div class="rings" aria-hidden="true"><span></span><span></span><span></span><span class="slash"></span></div>
+  <div class="home-top label"><span>Bakeoff live</span><span id="home-where"></span></div>
+  <div class="home-middle">
+    <div class="logo">
+      <canvas id="brain" class="brain" aria-hidden="true"></canvas>
+      <h1 class="shout"><span>BRAIN</span><span class="outline">BATTLE</span></h1>
+    </div>
+    <div id="home-fighters" class="home-fighters"></div>
+    <div class="menu">
+      <button type="button" id="launch" class="launch"><span aria-hidden="true">&#9654;</span>LAUNCH</button>
+      <button type="button" id="open-records" class="secondary">Records</button>
+      <span class="label blink">Press enter</span>
+    </div>
+  </div>
+  <div class="home-foot"><span>An untrained fruit-fly connectome, Jev and two chat models run the same seeded tunnels.</span>
+    <span class="label" id="home-game"></span></div>
+</section>
+
+<section id="screen-select" class="screen select" hidden aria-label="Choose your fighters">
+  <div class="screen-head"><button type="button" class="back label" data-back>&lsaquo; Home</button>
+    <h2 class="shout">CHOOSE YOUR FIGHTERS</h2><span class="label bright" id="select-count"></span></div>
+  <div id="portraits" class="portraits"></div>
+  <div id="select-info" class="info"></div>
+  <div class="banner-row">
+    <button type="button" id="fight" class="banner" hidden><span class="shout">READY TO FIGHT</span><span class="label blink">Press enter</span></button>
+    <div id="not-ready" class="banner-empty label">Pick at least one fighter</div>
+  </div>
+  <div id="slots" class="slots"></div>
+  <div class="keys label"><span>Click &middot; add fighter</span><span>Dot or X / Y &middot; change skin</span><span>&larr; &rarr; &middot; move cursor</span><span>Enter &middot; fight</span></div>
+</section>
+</div>
+
 <main id="app" hidden>
 <div class="tabs" role="tablist" aria-label="The run and the analysis">
   <button type="button" class="label" role="tab" id="tab-run" data-tab="run" aria-controls="panel-run" aria-selected="true">Run</button>
@@ -175,6 +212,9 @@
 <script src="lobby.js"></script>
 <script src="bench.js"></script>
 <script src="bench_view.js"></script>
+<script src="screens.js"></script>
+<script src="select.js"></script>
+<script src="front.js"></script>
 <script src="app.js"></script>
 </body>
 </html>
```

Apply to `viewer/sprites.js`:

```diff
@@ -110,7 +110,17 @@
     ctx.drawImage(image, -Math.round(image.width / 2), -image.height);
   }
 
-  const api = { GRIDS, INKS, BODY, visorCells, pixels, sizeOf, drawSprite };
+  // Paints the sprite into a canvas of its own, sized to it: the screens' portraits, slots and cards.
+  function paint(canvas, name, px, options) {
+    const image = bitmap(name, px, options);
+    canvas.width = image.width;
+    canvas.height = image.height;
+    const ctx = canvas.getContext("2d");
+    ctx.imageSmoothingEnabled = false;
+    ctx.drawImage(image, 0, 0);
+  }
+
+  const api = { GRIDS, INKS, BODY, paint, visorCells, pixels, sizeOf, drawSprite };
   if (typeof module !== "undefined" && module.exports) module.exports = api;
   else root.Sprites = api;
 })(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py`
Expected: `22 passed in 0.42s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 43.17s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/front.css viewer/front.js viewer/index.html viewer/sprites.js
git commit -F <message file>   # the Brain Battle front: home and the character select
```

---

### Task 8: The track select starts the run; the lobby goes

**Files:**
- Modify: `viewer/app.js`
- Modify: `viewer/front.css`
- Modify: `viewer/front.js`
- Modify: `viewer/index.html`
- Modify: `viewer/lobby.js`
- Modify: `viewer/picker.js`
- Modify: `viewer/trackpick.js`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`
- Test: `viewer/tests/lobby.test.js`
- Test: `viewer/tests/trackpick.test.js`

**Interfaces:**
- Consumes: `TrackPick` (task 4), `Lobby`, POST /run, POST /cancel.
- Produces: `#screen-track` and the run screen's `#run-bar` (`#run-home`, `#run-what`, `#run-cancel`, `#run-results`); `Race.watch(run)`, `Race.watching()`; `Front.ended(end)`; `TrackPick.capText(state, players)`; the lobby's markup, CSS, grid code (`playerList` and its helpers) and tests removed; app.js's lobby section replaced by `watch`/`resetTo`.

Deletions in `viewer/lobby.js`, `viewer/app.js`, `viewer/viewer.css` and `viewer/tests/lobby.test.js` are large: apply the hunks as given.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -76,7 +76,7 @@ def test_the_page_carries_the_chart_rules_the_analysis_tab_draws_with():
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
     assert names == ["timeline.js", "tunnel.js", "sprites.js", "roster.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
-                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "front.js", "app.js"]
+                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "trackpick.js", "front.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
```

Replace the whole of `viewer/tests/lobby.test.js` with:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Lobby = require("../lobby.js");

const player = (name, extra) => ({ name, paid: false, price_usd: 0, requests_left: null, played_before: false,
                                   why_not: null, ...extra });
const state = (extra) => ({
  status: "lobby", game: { version: "v2" }, max_rows: 150, requests_per_row: 1, max_requests: 0,
  tournament: false, first_practice_seed: 1000, seed: 1001, run: null,
  players: [player("fly"), player("solver"),
            player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 200 }),
            player("jev_step1", { paid: true, price_usd: 0.00003, requests_left: 200 }),
            player("glm_step1", { paid: true, price_usd: 0, requests_left: 200 })],
  ...extra,
});

test("the estimate is the worst case: every row a request, until the budget runs out", () => {
  const { rows, lines, total_usd } = Lobby.estimate(state(), ["fly", "haiku_plain", "jev_step1"]);
  assert.equal(rows, 150);
  assert.deepEqual(lines.map((l) => [l.player, l.requests]), [["haiku_plain", 150], ["jev_step1", 150]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.0006 + 150 * 0.00003).toFixed(4));
  // a budget smaller than the track caps the estimate: the run stops when the cap is reached
  const short = Lobby.estimate(state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 20 })] }), ["haiku_plain"]);
  assert.deepEqual(short.lines.map((l) => l.requests), [20]);
  assert.equal(short.total_usd.toFixed(4), "0.0120");
});

test("a run of free players says it spends nothing, and the free tier says so too", () => {
  assert.match(Lobby.estimateText(state(), ["fly", "solver"]), /spends nothing/);
  const text = Lobby.estimateText(state(), ["glm_step1"]);
  assert.match(text, /0 USD \(free tier\)/);
  assert.match(text, /GLM STEP 1 150 requests at worst/);
});

test("the estimate names each paid player, its worst case and whether the track was played before", () => {
  const played = state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0006, requests_left: 150, played_before: true })] });
  const text = Lobby.estimateText(played, ["haiku_plain"]);
  assert.match(text, /At worst this run of 150 rows spends 0.09 USD/);
  assert.match(text, /HAIKU PLAIN 150 requests at worst, 0.09 USD, played before \(some answers may be cached\)/);
});

test("money is written so that a fraction of a cent is still readable", () => {
  assert.equal(Lobby.usd(0), "0.00 USD");
  assert.equal(Lobby.usd(0.00003), "0.00003 USD"); // a price far below a cent keeps its digits
  assert.equal(Lobby.usd(1e-12), "less than 0.00000001 USD");
  assert.equal(Lobby.usd(0.0045), "0.0045 USD");
  assert.equal(Lobby.usd(1.5), "1.50 USD");
});

test("the page says why a run cannot be started, before anyone presses anything", () => {
  assert.equal(Lobby.whyNot(state(), ["fly"], 1001), null);
  assert.equal(Lobby.whyNot(state(), [], 1001), "choose at least one player");
  assert.equal(Lobby.whyNot(state(), ["fly"], -1), "the track must be a whole number, 0 or more");
  assert.equal(Lobby.whyNot(state(), ["fly"], 1.5), "the track must be a whole number, 0 or more");
  assert.equal(Lobby.whyNot(state({ status: "running" }), ["fly"], 1001), "a run is already going");
  const refused = state({ players: [player("haiku_plain", { paid: true, why_not: "no requests left" })] });
  assert.equal(Lobby.whyNot(refused, ["haiku_plain"], 7), "no requests left");
});

test("a name from the server is text, never markup", () => {
  const evil = "</label><script>alert(1)</script>";
  assert.equal(Lobby.estimateText(state({ players: [player(evil, { paid: true, price_usd: 1, requests_left: 2 })] }),
                                  [evil]).includes("<script>"), false);
});

test("with nothing left of the cap the page says what a paid player can still do, and asks nothing", () => {
  // a cap of 0 is the default: paid players replay what is cached and stop at their first uncached
  // question, so the run cannot spend and there is nothing to confirm
  const spent = state({ players: [player("haiku_plain", { paid: true, price_usd: 0.0065, requests_left: 0 })] });
  assert.match(Lobby.estimateText(spent, ["haiku_plain"]), /No request left of this command's cap/);
  assert.match(Lobby.estimateText(spent, ["haiku_plain"]), /stop at their first uncached question/);
  assert.equal(Lobby.spends(spent, ["haiku_plain"]), false);
  assert.equal(Lobby.spends(state(), ["haiku_plain"]), true);
  assert.equal(Lobby.spends(state(), ["fly", "solver"]), false);
});

test("the ceiling is written out, cap or no cap", () => {
  assert.match(Lobby.ceilingText(state()), /without a cap, so paid players only replay answers that are already cached/);
  assert.match(Lobby.ceilingText(state()), /may only play seeds 1000 and up/);
  assert.match(Lobby.ceilingText(state({ max_requests: 700 })), /cap is 700 requests for each paid player/);
  assert.match(Lobby.ceilingText(state({ tournament: true })), /Seeds below 1000 are allowed here/);
  assert.match(Lobby.ceilingText(state()), /Nothing on this page can raise either\./);
});
```

Apply to `viewer/tests/trackpick.test.js`:

```diff
@@ -73,8 +73,9 @@ test("RUN cannot be pressed while a run is going or a fighter is refused, and sa
 });
 
 test("the cap line comes from the state", () => {
-  assert.match(TrackPick.capText(state()), /until its cap of 200 runs out/);
-  assert.match(TrackPick.capText(state({ max_requests: 0 })), /spends nothing/);
+  assert.match(TrackPick.capText(state(), LINEUP), /until its cap of 200 runs out/);
+  assert.match(TrackPick.capText(state({ max_requests: 0 }), LINEUP), /no cap: the paid fighters replay/);
+  assert.equal(TrackPick.capText(state(), ["fly2"]), "No paid fighter: this run spends nothing.");
 });
 
 test("the preview draws the real track: one dark cell per gap on its rows", () => {
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ es...
2 failed, 21 passed in 1.97s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -90,7 +90,7 @@
       if (end.bench) benchData = end.bench; // the numbers for the run that just ended, scored by the server
       notice(end.status === "completed" ? null : "The run ended: " + end.status, false);
       renderAll();
-      if (liveUrl) refreshState(); // the run is over: the lobby comes back, with the run still on screen
+      if (window.Front) Front.ended(end); // the run is over: the front says what happened
     },
     onError(message) {
       if (store.ended) return;
@@ -490,47 +490,16 @@
     if (nth) focusOn(nth.episode.player, true);
   });
 
-  // ---- the lobby: the page starts the runs ----------------------------------------------------
-  const lobby = { state: null, chosen: [], armed: false, refusal: null, watching: null, source: null, timer: null };
-
-  async function control(path, options) {
-    const settings = options || {};
-    try {
-      const response = await fetch(path, { ...settings, headers: { "X-Bakeoff-Token": token, ...(settings.headers || {}) } });
-      const body = await response.json().catch(() => ({ error: "the server answered something that is not JSON" }));
-      return { ok: response.ok, body };
-    } catch (e) { // the command was stopped, or the machine went to sleep
-      return { ok: false, body: { error: "no answer from the run: is `bakeoff live` still going?" } };
-    }
-  }
-
-  // an empty box is no track at all, not track 0: Number("") is 0 and would silently start a run
-  const chosenSeed = () => ($("seed").value.trim() === "" ? NaN : Math.round(Number($("seed").value)));
-
-  async function refreshState() {
-    const { ok, body } = await control("/state?seed=" + encodeURIComponent(chosenSeed()));
-    if (ok) applyState(body);
-    else { lobby.refusal = body.error; renderLobby(); }
-  }
-
-  function applyState(state) {
-    if (lobby.state == null) { // the first answer: the lobby opens with what the command line offered
-      lobby.chosen = (state.ready || {}).players || [];
-      if ((state.ready || {}).seed != null) $("seed").value = state.ready.seed;
-    }
-    lobby.state = state;
-    const run = state.run;
-    if (run && run.replay && lobby.watching !== run.run_id) watch(run);
-    renderLobby();
-  }
+  // ---- a live run: the front starts it (front.js), this page watches it ------------------------------
+  const race = { watching: null, source: null };
 
   function watch(run) { // one stream per run, so a stream never runs on into the next one
-    lobby.watching = run.run_id;
-    if (lobby.source) lobby.source.close();
+    race.watching = run.run_id;
+    if (race.source) race.source.close();
     resetTo(run.replay);
     notice("Waiting for the first decision…", false);
-    lobby.source = Feed.fromStream(liveUrl + "?run=" + encodeURIComponent(run.run_id) +
-                                   "&token=" + encodeURIComponent(token), handlers);
+    race.source = Feed.fromStream(liveUrl + "?run=" + encodeURIComponent(run.run_id) +
+                                  "&token=" + encodeURIComponent(token), handlers);
   }
 
   function resetTo(replay) { // a new run: the page starts again from that run's empty replay
@@ -543,67 +512,6 @@
     renderAll();
   }
 
-  function renderLobby() {
-    const state = lobby.state;
-    if (!state) return;
-    const running = state.status === "running";
-    $("picks").innerHTML = Lobby.playerList(state, lobby.chosen);
-    $("estimate").textContent = Lobby.estimateText(state, lobby.chosen);
-    $("ceiling").textContent = Lobby.ceilingText(state);
-    const why = lobby.refusal || Lobby.whyNot(state, lobby.chosen, chosenSeed());
-    $("lobby-why").hidden = !why;
-    $("lobby-why").textContent = why || "";
-    const cost = Lobby.estimate(state, lobby.chosen);
-    $("start").disabled = !!why;
-    $("start").textContent = !lobby.armed ? "Start"
-      : "Confirm: start and spend at most " + Lobby.usd(cost.total_usd);
-    $("start").dataset.armed = String(lobby.armed);
-    $("cancel").hidden = !running;
-    $("seed").disabled = running;
-  }
-
-  function pressedStart() {
-    const state = lobby.state;
-    if (!state || Lobby.whyNot(state, lobby.chosen, chosenSeed())) return;
-    // a run that can really spend is confirmed once, with its worst case on the button
-    if (Lobby.spends(state, lobby.chosen) && !lobby.armed) {
-      lobby.armed = true;
-      return renderLobby();
-    }
-    startRun();
-  }
-
-  async function startRun() {
-    lobby.armed = false;
-    lobby.refusal = null;
-    const { ok, body } = await control("/run", { method: "POST", headers: { "Content-Type": "application/json" },
-                                                 body: JSON.stringify({ seed: chosenSeed(), players: lobby.chosen }) });
-    if (!ok) lobby.refusal = body.error || "the run was refused";
-    if (ok && body.state) applyState(body.state);
-    else renderLobby();
-  }
-
-  $("lobby-form").addEventListener("submit", (event) => { event.preventDefault(); pressedStart(); });
-  $("picks").addEventListener("change", () => {
-    lobby.chosen = [...$("picks").querySelectorAll("input[name=player]:checked")].map((input) => input.value);
-    lobby.armed = false;
-    lobby.refusal = null;
-    renderLobby();
-  });
-  $("seed").addEventListener("input", () => { // another track: another set of prices and refusals
-    lobby.armed = false;
-    lobby.refusal = null;
-    renderLobby();
-    clearTimeout(lobby.timer);
-    lobby.timer = setTimeout(refreshState, 300);
-  });
-  $("cancel").addEventListener("click", async () => {
-    const { ok, body } = await control("/cancel", { method: "POST" });
-    if (!ok) lobby.refusal = body.error || "the run could not be stopped";
-    if (ok && body.state) applyState(body.state);
-    else renderLobby();
-  });
-
   // ---- the sections underneath --------------------------------------------------------------
   function renderBelow() {
     const board = store.scoreboard || { columns: [], rows: [], same_seeds: true };
@@ -662,6 +570,8 @@
       $("transport").hidden = true;
       setPlaying(false);
     },
+    watch,
+    watching: () => race.watching,
   };
 
   // ---- start --------------------------------------------------------------------------------
```

Apply to `viewer/front.css`:

```diff
@@ -117,6 +117,60 @@
 #front .keys { margin-top: auto; padding-top: 16px; display: flex; justify-content: center; gap: 28px; flex-wrap: wrap;
   font-size: var(--size-label-sm); }
 
+/* ---- track select ------------------------------------------------------------------------------ */
+#front .panel { padding: 16px 24px 18px; border: 1px solid var(--hairline); background: var(--panel); }
+#front .small { font-size: 13px; line-height: 1.45; }
+#front .row { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
+#front .track-body { flex: 1; display: flex; gap: 24px; min-height: 0; padding-bottom: 8px; }
+#front .track-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 18px; }
+#front .seed-row { display: flex; align-items: center; gap: 20px; }
+#front .seed-what { display: flex; flex-direction: column; gap: 2px; }
+#front .step { width: 48px; height: 48px; flex: none; background: transparent; border: 1px solid var(--line-strong);
+  color: var(--bright); font-size: 24px; cursor: pointer; }
+#front .seed { width: 300px; text-align: center; font: italic 900 104px/1 var(--font-body); letter-spacing: -0.03em;
+  color: var(--bright); transform: var(--shout-skew); }
+#front .random { margin-left: auto; height: 48px; padding: 0 20px; background: transparent; border: 1px solid var(--line-strong);
+  color: var(--text); font-weight: 600; font-size: 16px; cursor: pointer; }
+#front .preview-box { display: flex; flex-direction: column; gap: 8px; }
+#front .preview { display: block; width: 100%; height: auto; max-width: 600px; }
+#front .preview .floor { fill: var(--line-strong); }
+#front .preview .runway { fill: #3A4046; }
+#front .preview .gap { fill: var(--void); }
+#front .practice { display: flex; flex-direction: column; gap: 10px; }
+#front .tiles { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 8px; }
+#front .tile { height: 56px; padding: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
+  background: var(--panel); border: 2px solid var(--hairline); cursor: pointer; color: var(--text); }
+#front .tile.current { border-color: var(--accent); color: var(--bright); }
+#front .tile .seed { width: auto; font: italic 800 18px/1 var(--font-body); letter-spacing: 0; transform: none; color: inherit; }
+#front .tile .mark { font: 10px/1 var(--font-mono); letter-spacing: 0.06em; color: var(--muted); }
+#front .track-side { width: 400px; flex: none; display: flex; flex-direction: column; gap: 14px; }
+#front .lineup { flex: 1; display: flex; flex-direction: column; gap: 12px; padding: 18px 20px; }
+#front .fighter { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--hairline); }
+#front .fighter .who { width: 22px; font-weight: 600; color: var(--text); }
+#front .fighter .art { width: 48px; display: flex; justify-content: center; }
+#front .fighter .what { flex: 1; min-width: 0; display: flex; flex-direction: column; }
+#front .fighter .title { font-weight: 800; font-style: italic; color: var(--bright); }
+#front .fighter .sub { font: var(--size-label-sm)/1.4 var(--font-mono); color: var(--muted); }
+#front .fighter .cost { display: flex; flex-direction: column; align-items: flex-end; }
+#front .fighter .usd { font: 12px/1.4 var(--font-mono); color: var(--muted); }
+#front .fighter .usd.paid { color: var(--warn); }
+#front .total { margin-top: auto; display: flex; flex-direction: column; gap: 6px; }
+#front .total .usd { font: italic 900 28px/1 var(--font-body); color: var(--warn); }
+#front .run { height: 76px; gap: 22px; }
+#front .run .shout { font-size: 48px; }
+#front .run[disabled] { opacity: 0.4; cursor: not-allowed; }
+#front .run[data-armed="true"] { background: var(--warn); }
+#front .run[data-armed="true"] .shout { font-size: 36px; }
+
+/* ---- the run screen's bar (outside #front: the run screen is the replay's own page) ---------------- */
+.run-bar { display: flex; align-items: center; gap: 16px; min-height: 56px; }
+.run-bar[hidden] { display: none; }
+.run-bar button { min-height: 36px; padding: 0 12px; background: var(--panel); border: 1px solid var(--hairline); cursor: pointer; }
+.run-bar button:hover { color: var(--bright); border-color: var(--line-strong); }
+.run-bar button[hidden] { display: none; }
+#run-home { margin-right: auto; }
+#run-results { border-color: var(--bright); color: var(--bright); }
+
 @media (max-width: 720px) {
   #front .shout { font-size: 28px; }
   #front .home-fighters { gap: 24px; }
@@ -124,4 +178,8 @@
   #front .slots { grid-template-columns: repeat(4, minmax(0, 1fr)); }
   #front .info { flex-wrap: wrap; padding: 10px 16px; }
   #front .info .about { white-space: normal; }
+  #front .track-body { flex-direction: column; }
+  #front .track-side { width: auto; }
+  #front .seed { width: auto; font-size: 64px; }
+  #front .tiles { grid-template-columns: repeat(5, minmax(0, 1fr)); }
 }
```

Apply to `viewer/front.js`:

```diff
@@ -26,6 +26,7 @@
 
   const front = {
     screen: "home", from: "home", state: null, sel: Select.make(roster, []), seed: null, armed: false, refusal: null,
+    timer: null, leaving: false,
   };
 
   async function control(path, options) {
@@ -70,6 +71,8 @@
   function render() {
     if (front.screen === "home") renderHome();
     if (front.screen === "select") renderSelect();
+    if (front.screen === "track") renderTrack();
+    renderRunBar();
   }
 
   // ---- home ------------------------------------------------------------------------------------------
@@ -128,6 +131,98 @@
   });
   $("fight").addEventListener("click", () => { if (Select.ready(front.sel)) show("track"); });
 
+  // ---- the track select ------------------------------------------------------------------------------
+  const players = () => Select.players(front.sel, roster);
+
+  function renderTrack() {
+    const state = front.state;
+    if (!state) return;
+    const seed = front.seed;
+    const fresh = state.seed === seed; // the state answers for the track on screen, not the one before
+    $("track-game").textContent = "Run · game " + state.game.version + " · " + state.max_rows + " rows";
+    $("seed-rule").textContent = state.tournament ? "Tournament seeds are open (--tournament)"
+      : "Practice seeds are " + state.first_practice_seed + " and up";
+    $("seed-shown").textContent = seed;
+    $("preview-what").textContent = "The track, row 0 to " + state.max_rows;
+    $("preview").innerHTML = fresh ? TrackPick.previewSvg(state.track, state.game) : "";
+    $("preview-gaps").textContent = fresh && state.track ? TrackPick.gapTiles(state.track) + " gap tiles" : "";
+    $("tiles").innerHTML = TrackPick.tilesHtml(TrackPick.tiles(state, players(), seed));
+    $("ceiling").textContent = Lobby.ceilingText(state);
+    $("lineup").innerHTML = TrackPick.lineupHtml(TrackPick.lineup(state, roster, players()));
+    paintSprites($("lineup"));
+    $("total").textContent = Lobby.usd(Lobby.estimate(state, players()).total_usd);
+    $("cap").textContent = TrackPick.capText(state, players());
+    const button = TrackPick.runButton(state, players(), seed, front.armed);
+    const why = front.refusal || button.why || (fresh ? null : "Looking up track " + seed + "…");
+    $("run-why").hidden = !why;
+    $("run-why").textContent = why || "";
+    $("run").disabled = !!why;
+    $("run").dataset.armed = String(button.armed);
+    $("run-label").textContent = button.label;
+    $("run-sub").textContent = button.sub;
+  }
+
+  function setSeed(seed) {
+    if (!front.state) return;
+    front.seed = TrackPick.clampSeed(seed, front.state);
+    front.armed = false; // another track: another worst case to confirm
+    front.refusal = null;
+    renderTrack();
+    clearTimeout(front.timer);
+    front.timer = setTimeout(refreshState, 250);
+  }
+
+  // RUN: a lineup that can spend is confirmed once, with its worst case on the button; then it starts.
+  function pressedRun() {
+    const state = front.state;
+    if (!state || state.seed !== front.seed || Lobby.whyNot(state, players(), front.seed)) return;
+    if (Lobby.spends(state, players()) && !front.armed) {
+      front.armed = true;
+      return renderTrack();
+    }
+    startRun();
+  }
+
+  async function startRun() {
+    front.armed = false;
+    front.refusal = null;
+    const { ok, body } = await control("/run", { method: "POST", headers: { "Content-Type": "application/json" },
+                                                 body: JSON.stringify({ seed: front.seed, players: players() }) });
+    if (!ok) { front.refusal = body.error || "the run was refused"; return render(); }
+    applyState(body.state, body.run_id);
+  }
+
+  $("seed-prev").addEventListener("click", () => setSeed(front.seed - 1));
+  $("seed-next").addEventListener("click", () => setSeed(front.seed + 1));
+  $("seed-random").addEventListener("click", () => setSeed(TrackPick.randomSeed(front.state, Math.random)));
+  $("tiles").addEventListener("click", (event) => {
+    const tile = event.target.closest("button[data-seed]");
+    if (tile) setSeed(Number(tile.dataset.seed));
+  });
+  $("run").addEventListener("click", pressedRun);
+
+  // ---- the run screen's bar ------------------------------------------------------------------------
+  const running = () => !!front.state && front.state.status === "running";
+
+  function renderRunBar() {
+    const run = front.state && front.state.run;
+    $("run-bar").hidden = false;
+    $("run-what").textContent = run ? "Track " + run.seed + (running() ? " · live" : " · " + run.status) : "";
+    $("run-cancel").hidden = !running();
+    $("run-home").textContent = front.leaving ? "Home? The run keeps going" : "‹ Home";
+  }
+
+  // Going home does not cancel the run, so while one is going the first press says so and the second goes.
+  $("run-home").addEventListener("click", () => {
+    if (running() && !front.leaving) { front.leaving = true; return renderRunBar(); }
+    front.leaving = false;
+    show("home");
+  });
+  $("run-cancel").addEventListener("click", async () => {
+    const { ok, body } = await control("/cancel", { method: "POST" });
+    if (ok && body.state) applyState(body.state);
+  });
+
   // ---- keys and Back -------------------------------------------------------------------------------
   document.addEventListener("click", (event) => {
     if (event.target.closest("[data-back]")) show(Screens.back(front.screen, front.from));
@@ -143,6 +238,10 @@
     } else if (front.screen === "select") {
       out = Select.onKey(front.sel, roster, event.key);
       if (out && out.sel !== front.sel) setSel(out.sel);
+    } else if (front.screen === "track" && front.state) {
+      out = TrackPick.onKey(front.seed, front.state, event.key, Math.random);
+      if (out && out.seed !== front.seed) setSeed(out.seed);
+      if (out && out.go === "run") { pressedRun(); out = { go: null }; }
     } else if (event.key === "Escape") {
       out = { go: "back" };
     }
@@ -160,15 +259,33 @@
     applyState(body);
   }
 
-  function applyState(state) {
-    if (front.state == null) { // the first answer: the select opens with what the command line offered
+  // `started`: the run this page just started, watched even when it is already over (free players can finish
+  // a track before the answer to POST /run arrives).
+  function applyState(state, started) {
+    const first = front.state == null;
+    if (first) { // the first answer: the select opens with what the command line offered
       front.sel = Select.make(roster, (state.ready || {}).players || []);
       front.seed = (state.ready || {}).seed != null ? state.ready.seed : state.first_practice_seed;
     }
     front.state = state;
+    const run = state.run;
+    // a run that is going and not watched yet: this page started it, or the command line did (--start), or
+    // the page was reloaded while it ran. Watch it, on the run screen.
+    if (run && run.replay && (state.status === "running" || run.run_id === started) && Race.watching() !== run.run_id) {
+      Race.watch(run);
+      front.leaving = false;
+      return show("run");
+    }
+    if (first && front.seed !== state.seed) return refreshState(); // the state for the track on screen
     render();
   }
 
+  // app.js calls this when a run has ended: the state says so, and the bar stops offering Cancel.
+  function ended() {
+    front.leaving = false;
+    refreshState();
+  }
+
   // app.js calls this once the run screen is ready (live only).
   function start() {
     paintBrain();
@@ -176,5 +293,5 @@
     refreshState();
   }
 
-  root.Front = { start };
+  root.Front = { start, ended };
 })(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/index.html`:

```diff
@@ -48,6 +48,41 @@
   <div id="slots" class="slots"></div>
   <div class="keys label"><span>Click &middot; add fighter</span><span>Dot or X / Y &middot; change skin</span><span>&larr; &rarr; &middot; move cursor</span><span>Enter &middot; fight</span></div>
 </section>
+
+<section id="screen-track" class="screen track" hidden aria-label="Choose your track">
+  <div class="screen-head"><button type="button" class="back label" data-back>&lsaquo; Fighters</button>
+    <h2 class="shout">CHOOSE YOUR TRACK</h2><span class="label bright" id="track-game"></span></div>
+  <div class="track-body">
+    <div class="track-main">
+      <div class="panel seed-row">
+        <div class="seed-what"><span class="label">Track</span><span class="muted small" id="seed-rule"></span></div>
+        <button type="button" class="step" id="seed-prev" aria-label="Previous track">&lsaquo;</button>
+        <output id="seed-shown" class="seed"></output>
+        <button type="button" class="step" id="seed-next" aria-label="Next track">&rsaquo;</button>
+        <button type="button" class="random" id="seed-random">Random</button>
+      </div>
+      <div class="panel preview-box">
+        <div class="label row"><span id="preview-what"></span><span id="preview-gaps"></span></div>
+        <div id="preview"></div>
+      </div>
+      <div class="practice">
+        <div class="label row"><span>Practice tracks</span><span>Mark &middot; this lineup played it before</span></div>
+        <div id="tiles" class="tiles"></div>
+        <p class="muted small" id="ceiling"></p>
+      </div>
+    </div>
+    <div class="track-side">
+      <div class="panel lineup">
+        <span class="label">The lineup</span>
+        <div id="lineup"></div>
+        <div class="total"><div class="row"><span class="label">At worst</span><span id="total" class="usd"></span></div>
+          <p class="muted small" id="cap"></p></div>
+      </div>
+      <p class="warn small" id="run-why" hidden></p>
+      <button type="button" id="run" class="banner run"><span class="shout" id="run-label">RUN</span><span class="label blink" id="run-sub">Enter</span></button>
+    </div>
+  </div>
+</section>
 </div>
 
 <main id="app" hidden>
@@ -57,6 +92,12 @@
 </div>
 
 <div id="panel-run" role="tabpanel" aria-labelledby="tab-run">
+  <div id="run-bar" class="run-bar" hidden>
+    <button type="button" id="run-home" class="label">&lsaquo; Home</button>
+    <span class="label" id="run-what"></span>
+    <button type="button" id="run-cancel" class="label" hidden>Cancel the run</button>
+    <button type="button" id="run-results" class="label" hidden>Results &#9654;</button>
+  </div>
   <section id="player" aria-label="The run">
     <div id="tunnel">
       <canvas id="canvas" aria-label="Three runners in one tunnel. The same information is in the panels below."></canvas>
@@ -72,22 +113,6 @@
   <section id="players" aria-label="Players">
     <h2 class="label">Players</h2>
 
-    <div id="lobby" hidden>
-      <form id="lobby-form">
-        <div class="lobby-top">
-          <label class="label" for="seed">Track</label>
-          <input id="seed" type="number" min="0" step="1" value="1001" inputmode="numeric">
-          <button id="start" type="submit" class="label">Start</button>
-          <button id="cancel" type="button" class="label" hidden>Cancel the run</button>
-        </div>
-        <h3 class="label row-label" id="runs-next">Who runs next</h3>
-        <div id="picks" role="group" aria-labelledby="runs-next"></div>
-        <p class="note" id="estimate"></p>
-        <p class="note warn" id="lobby-why" hidden></p>
-        <p class="note" id="ceiling"></p>
-      </form>
-    </div>
-
     <div id="picker">
       <h3 class="label row-label" id="in-tunnel">Who is in the tunnel</h3>
       <div id="picks-replay" role="group" aria-labelledby="in-tunnel"></div>
@@ -214,6 +239,7 @@
 <script src="bench_view.js"></script>
 <script src="screens.js"></script>
 <script src="select.js"></script>
+<script src="trackpick.js"></script>
 <script src="front.js"></script>
 <script src="app.js"></script>
 </body>
```

Replace the whole of `viewer/lobby.js` with:

```javascript
// What a run may cost and whether it may start: the rules the old lobby had, kept for the Brain Battle
// track select (trackpick.js), which shows the worst case and confirms it (spec section G). The lobby's own
// player grid is gone: the character select replaced it. Pure and tested under node. What it writes is plain
// text, for textContent: a player name or a refusal from the server is never markup.
//
// `state` is what GET /state answers (bakeoff/session.py): {status, game, max_rows, requests_per_row,
// max_requests, tournament, first_practice_seed, seed, players: [{name, paid, price_usd,
// requests_left, played_before, why_not}], run}.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const tagOf = Minds_.tagOf;

  // USD, as the page writes it: 0 is free, and a price far below a cent keeps enough digits to be read
  // (Jev is 0.00003 USD a request), so nothing that costs money is ever written as 0.00.
  function usd(amount) {
    if (!(amount > 0)) return "0.00 USD";
    if (amount >= 0.01) return amount.toFixed(2) + " USD";
    const digits = Math.min(8, Math.max(4, 1 - Math.floor(Math.log10(amount))));
    const written = amount.toFixed(digits).replace(/0+$/, "");
    return Number(written) > 0 ? written + " USD" : "less than 0.00000001 USD";
  }

  // The worst case of the run about to be asked for: every row of the track costs a request for every
  // paid player, until its budget runs out. Nothing here is a bill; it is the most it could come to.
  function estimate(state, chosen) {
    const byName = new Map((state.players || []).map((p) => [p.name, p]));
    const rows = state.max_rows || 0;
    const lines = [];
    let total = 0;
    for (const name of chosen) {
      const player = byName.get(name);
      if (!player || !player.paid) continue;
      const requests = Math.min(rows * (state.requests_per_row || 1), player.requests_left || 0);
      const cost = requests * (player.price_usd || 0);
      total += cost;
      lines.push({ player: name, requests, usd: cost, free: !(player.price_usd > 0),
                   played_before: !!player.played_before });
    }
    return { rows, lines, total_usd: total };
  }

  // What the page says before it starts a run, and what the user confirms.
  function estimateText(state, chosen) {
    const { rows, lines, total_usd } = estimate(state, chosen);
    if (!lines.length) return "No paid player: this run spends nothing.";
    const each = lines.map((line) => tagOf(line.player) + " " + line.requests + " request" +
      (line.requests === 1 ? "" : "s") + " at worst, " + (line.free ? "0 USD (free tier)" : usd(line.usd)) +
      (line.played_before ? ", played before (some answers may be cached)" : ""));
    if (!lines.some((line) => line.requests > 0)) {
      return "No request left of this command's cap: the paid players replay what is already cached and stop " +
        "at their first uncached question. This run spends nothing.";
    }
    return "At worst this run of " + rows + " rows spends " + usd(total_usd) + ": " + each.join(" · ") +
      ". Cached answers are free, so the real cost is usually lower.";
  }

  // Why this run cannot be started, or null. The server decides again on /run; this is so the page
  // can say so before anyone presses anything.
  function whyNot(state, chosen, seed) {
    if (state.status === "running") return "a run is already going";
    if (!Number.isInteger(seed) || seed < 0) return "the track must be a whole number, 0 or more";
    if (!chosen.length) return "choose at least one player";
    const blocked = (state.players || []).filter((p) => chosen.includes(p.name) && p.why_not);
    if (blocked.length) return blocked[0].why_not;
    return null;
  }

  // The ceiling the command set, and the seed rule: the line under the track select.
  function ceilingText(state) {
    const cap = state.max_requests === 0
      ? "This command was started without a cap, so paid players only replay answers that are already cached."
      : "This command's cap is " + state.max_requests + " requests for each paid player, for the whole session.";
    const seeds = state.tournament
      ? "Seeds below " + state.first_practice_seed + " are allowed here (--tournament)."
      : "Paid players may only play seeds " + state.first_practice_seed + " and up; the tournament seeds are kept unseen.";
    return cap + " " + seeds + " Nothing on this page can raise either.";
  }

  // Does starting this run need confirming? Only when it can really spend: a run that has no request
  // left of the cap spends nothing whatever it asks for.
  const spends = (state, chosen) => estimate(state, chosen).lines.some((line) => line.requests > 0);

  const api = { usd, estimate, estimateText, whyNot, ceilingText, spends };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lobby = api;
})(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/picker.js`:

```diff
@@ -1,5 +1,5 @@
-// Who is in the tunnel. One control governs both: in a replay it shows and hides the runners, and in
-// a live command, while nothing is running, the lobby's own list (lobby.js) chooses who runs instead.
+// Who is in the tunnel: it shows and hides the runners, live or replay. Who runs is chosen on the Brain
+// Battle character select (select.js).
 // Pure and tested under node; app.js does the DOM. Every player name goes through esc().
 (function (root) {
   "use strict";
```

Apply to `viewer/trackpick.js`:

```diff
@@ -96,7 +96,8 @@
   }
 
   // The line under the total: the cap and what a row costs, from /state, never typed in.
-  function capText(state) {
+  function capText(state, players) {
+    if (!Lobby_.estimate(state, players).lines.length) return "No paid fighter: this run spends nothing.";
     if (!state.max_requests) {
       return "This command has no cap: the paid fighters replay answers already cached and stop at their first " +
         "uncached question, so this run spends nothing.";
```

Apply to `viewer/viewer.css`:

```diff
@@ -164,59 +164,3 @@ table { border-collapse: collapse; font-size: var(--size-small); font-variant-nu
   #speeds button[data-speed="1"], #speeds button[data-speed="20"] { display: none; }
   #auto { margin-left: auto; }
 }
-
-/* ---- the lobby: the page starts the runs ------------------------------------------------------ */
-#lobby form { max-width: 900px; }
-.lobby-top { display: flex; align-items: center; gap: 12px; margin-bottom: var(--gutter); }
-.lobby-top input { width: 9ch; padding: 6px 8px; background: var(--panel); color: var(--bright);
-  border: 1px solid var(--line-strong); font: inherit; }
-#lobby button { padding: 8px 14px; background: var(--panel); color: var(--bright);
-  border: 1px solid var(--line-strong); cursor: pointer; }
-#lobby button[disabled] { color: var(--muted); cursor: not-allowed; }
-#lobby button[data-armed="true"] { border-color: var(--warn); color: var(--warn); }
-#cancel { border-color: var(--bad); color: var(--bad); }
-/* who runs next: question sets down, models across, and the players that are apart below */
-#picks { overflow-x: auto; }
-table.players { border-collapse: collapse; width: 100%; }
-table.players th, table.players td { vertical-align: top; padding: 10px; border: 1px solid var(--hairline); }
-table.players thead th { background: var(--panel); text-align: left; width: 22%; }
-table.players th.what { background: var(--panel); text-align: left; width: 22%; min-width: 180px; }
-table.players th .label { display: block; color: var(--bright); margin-bottom: 4px; }
-table.players th .note { display: block; margin: 0; font-size: var(--size-label-sm); max-width: 34ch; }
-/* the model a column really asks for: a short label, so mono, and above the prose */
-table.players th .note.mono { font-family: var(--font-mono); color: var(--text); margin-bottom: 6px;
-  letter-spacing: var(--tracking-label); overflow-wrap: anywhere; }
-table.players td { min-width: 170px; }
-table.players td.none { color: var(--muted); text-align: center; vertical-align: middle; }
-.apart { margin-top: 20px; }
-.apart .note { margin: 0 0 8px; max-width: var(--measure); }
-.picks-row { display: flex; flex-wrap: wrap; gap: 8px; }
-.picks-row .pick { border: 1px solid var(--hairline); min-width: 170px; }
-.pick { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; align-items: baseline;
-  padding: 10px 12px; background: var(--panel); border: 1px solid transparent; cursor: pointer; }
-.pick:has(input:checked) { border-color: var(--text); color: var(--bright); }
-.pick input { grid-row: span 3; align-self: center; accent-color: var(--accent); }
-.pick-name { font: 400 var(--size-small)/1.4 var(--font-mono); color: var(--text); }
-.pick:has(input:checked) .pick-name { color: var(--bright); }
-.pick .note { grid-column: 2; margin-top: 0; font-size: var(--size-label-sm); }
-.pick.blocked { opacity: 0.55; cursor: not-allowed; }
-
-/* the two tabs: plain buttons over one page, no routing */
-.tabs { display: flex; gap: 4px; padding: 0 16px; border-bottom: 1px solid var(--hairline); }
-.tabs button { min-height: 44px; padding: 0 16px; background: none; border: 0; border-bottom: 2px solid transparent;
-  color: var(--muted); cursor: pointer; }
-.tabs button[aria-selected="true"] { color: var(--bright); border-bottom-color: var(--bright); }
-.tabs button:hover { color: var(--text); }
-/* the tab strip is the rule above the first section of either panel */
-[role="tabpanel"] > section:first-child { margin-top: 0; border-top: 0; }
-
-/* the players: two rows of one control — who runs next (live, before a run) and who is in the tunnel */
-.row-label { color: var(--muted); margin: 20px 0 8px; }
-#lobby .lobby-top + .row-label { margin-top: 16px; }
-#picker { margin-top: 24px; }
-#picks-replay { display: flex; flex-wrap: wrap; gap: 8px; }
-.pick-player { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 12px;
-  background: var(--panel); border: 1px solid var(--hairline); color: var(--muted); cursor: pointer; }
-.pick-player[aria-pressed="true"] { color: var(--bright); border-color: var(--text); }
-.pick-player[disabled] { opacity: 0.45; cursor: default; }
-.pick-player .note { font-size: var(--size-small); }
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected: `23 passed in 1.17s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `579 passed, 16 deselected in 42.85s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/front.css viewer/front.js viewer/index.html viewer/lobby.js viewer/picker.js viewer/tests/lobby.test.js viewer/tests/trackpick.test.js viewer/trackpick.js viewer/viewer.css
git commit -F <message file>   # the Brain Battle front: the track select starts the run; the lobby goes
```

---

### Task 9: Results, records, and watching a run again

**Files:**
- Modify: `viewer/app.js`
- Modify: `viewer/front.css`
- Modify: `viewer/front.js`
- Modify: `viewer/index.html`
- Modify: `viewer/records.js`
- Modify: `viewer/results.js`
- Test: `tests/test_view.py`
- Test: `viewer/tests/records.test.js`
- Test: `viewer/tests/results.test.js`

**Interfaces:**
- Consumes: `Results`, `Records` (tasks 5–6), GET /results, /records, /replay.
- Produces: `#screen-results` and `#screen-records` (with `#ours-panel`, into which `#honesty` is moved); `Race.load(replay)`, `Race.rewind()`, `Race.atEnd()`; app.js calls `Front.reachedEnd()` when the tunnel shows the last row and leaves the honesty lists to the front when live; `Front.reachedEnd`; results cards' `finished` and the `leader`/`result-bar` classes; records' `data-now`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -76,10 +76,17 @@ def test_the_page_carries_the_chart_rules_the_analysis_tab_draws_with():
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
     assert names == ["timeline.js", "tunnel.js", "sprites.js", "roster.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
-                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "trackpick.js", "front.js", "app.js"]
+                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "trackpick.js", "results.js", "records.js", "front.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
+def test_every_id_on_the_page_is_unique():
+    """The Brain Battle screens share one page with the replay's own sections: two elements with one id would
+    let a screen write into another's (getElementById answers the first)."""
+    ids = re.findall(r'\bid="([^"]+)"', (VIEWER_DIR / "index.html").read_text())
+    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})
+
+
 def test_the_two_brand_fonts_are_embedded_not_fetched():
     page = render_html({"episodes": []})
     fonts = re.findall(r"@font-face\s*{[^}]*}", page)
```

Apply to `viewer/tests/records.test.js`:

```diff
@@ -98,7 +98,7 @@ test("past runs: only this session's run is live; another that says running is n
   assert.equal(rows[2].when, "-");
   const html = Records.runsHtml(rows);
   assert.equal(html.includes("<b>"), false);
-  assert.match(html, /data-watch="20260925-163957" data-live="true"/);
+  assert.match(html, /data-watch="20260925-163957" data-now="true"/);
 });
 
 test("the first ten past runs, then all of them when asked", () => {
```

Apply to `viewer/tests/results.test.js`:

```diff
@@ -33,7 +33,7 @@ test("the cards are ranked by rows survived, each keeping its slot's label", ()
   assert.deepEqual(cards.map((c) => [c.place, c.label, c.title, c.rows]),
     [[1, "P2", "Jev · Guided", 94], [2, "P3", "Haiku · Guided", 93], [3, "P1", "Fly · Sideways", 72]]);
   assert.deepEqual(cards[0], { place: 1, top: true, label: "P2", player: "jev_guided", title: "Jev · Guided", rows: 94,
-                               rowsWord: "rows", death: "Jumped into a gap · row 94", stopped: false, perRow: "175 ms",
+                               rowsWord: "rows", death: "Jumped into a gap · row 94", stopped: false, finished: false, perRow: "175 ms",
                                requests: "81", cost: "0.0032 USD", paid: true }); // Lobby.usd, the page's one way to write money
   assert.equal(cards[2].requests, "none (simulated)");
   assert.equal(cards[2].cost, "free");
@@ -49,6 +49,8 @@ test("ties share a place, and a stopped runner comes last and is never a death",
   const cards = Results.cards(tied, ROSTER);
   assert.deepEqual(cards.map((c) => [c.player, c.place]), [["jev_guided", 1], ["haiku_guided", 1], ["glm_plain", 3], ["fly2", 4]]);
   assert.equal(cards[0].death, "Reached the finish line");
+  assert.equal(cards[0].finished, true);
+  assert.match(Results.cardsHtml(cards, false), /<span class="death">Reached the finish line<\/span>/); // not --bad
   assert.equal(cards[3].death, "Stopped at row 140: not a death");
   assert.equal(cards[3].stopped, true);
   assert.equal(cards[3].top, false);
@@ -118,6 +120,6 @@ test("the header and the markup, every text escaped", () => {
   const html = Results.cardsHtml(Results.cards(evil, ROSTER), false) + Results.tableHtml(Results.table(evil, ROSTER)) +
     Results.barsHtml(Results.bars(evil, ROSTER), () => "#5FA35A");
   assert.equal(html.includes("<b>"), false);
-  assert.match(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true), /^<article class="card top"/);
+  assert.match(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true), /^<article class="card leader"/);
   assert.equal(Results.cardsHtml(Results.cards(RESULTS, ROSTER), true).includes("canvas"), false); // More numbers hides the art
 });
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ es...
2 failed, 22 passed in 1.94s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -420,8 +420,10 @@
     view.t = Math.min(end, view.t + ((now - lastTick) / 1000) * view.speed);
     lastTick = now;
     draw();
-    if (view.t >= end && store.ended) setPlaying(false);
-    else requestAnimationFrame(tick);
+    if (view.t >= end && store.ended) {
+      setPlaying(false);
+      if (window.Front) Front.reachedEnd(); // the tunnel on screen has shown the last row
+    } else requestAnimationFrame(tick);
   }
 
   function setPlaying(on) {
@@ -520,11 +522,13 @@
         (c === "player" ? "<th>" + cell(row[c]) + "</th>" : "<td>" + cell(row[c]) + "</td>")).join("") + "</tr>").join("") + "</tbody>";
     $("fairness").hidden = board.same_seeds;
     $("board").hidden = !board.rows.length; // a live run has no scoreboard until it ends
-    const flyRun = store.runs.find((run) => run.fly && (run.players || []).includes("fly")) || store.runs.find((run) => run.fly);
-    $("ours").innerHTML = Minds.ours(flyRun);
-    const fly2Run = store.runs.find((run) => run.fly2 && (run.players || []).includes("fly2"));
-    $("ours-fly2").innerHTML = Minds.oursFly2(fly2Run);
-    $("honesty-fly2").hidden = !fly2Run;
+    if (!liveUrl) { // live, the front writes these from the records' numbers, on the records screen
+      const flyRun = store.runs.find((run) => run.fly && (run.players || []).includes("fly")) || store.runs.find((run) => run.fly);
+      $("ours").innerHTML = Minds.ours(flyRun);
+      const fly2Run = store.runs.find((run) => run.fly2 && (run.players || []).includes("fly2"));
+      $("ours-fly2").innerHTML = Minds.oursFly2(fly2Run);
+      $("honesty-fly2").hidden = !fly2Run;
+    }
     $("runs").innerHTML = store.runs.map((run) => {
       const sha = run.git_sha ? run.git_sha.slice(0, 7) + (run.git_dirty ? ", uncommitted changes" : "") : "unknown commit";
       const status = run.status === "completed" ? "completed" : '<span class="warn">' + esc(run.status || "status unknown") + "</span>";
@@ -572,6 +576,24 @@
     },
     watch,
     watching: () => race.watching,
+    // a recorded run, from the start (Records' Watch): no stream, nothing more will arrive
+    load(replay) {
+      if (race.source) race.source.close();
+      race.source = null;
+      race.watching = null;
+      resetTo(replay);
+      store.ended = true;
+      setFollowingOff();
+      notice(null);
+      renderAll();
+    },
+    rewind() { // Watch the replay: the run just played, from row 0
+      setPlaying(false);
+      if (liveUrl) setFollowingOff();
+      view.t = 0;
+      draw();
+    },
+    atEnd: () => store.ended && view.t >= horizon(),
   };
 
   // ---- start --------------------------------------------------------------------------------
```

Apply to `viewer/front.css`:

```diff
@@ -162,6 +162,116 @@
 #front .run[data-armed="true"] { background: var(--warn); }
 #front .run[data-armed="true"] .shout { font-size: 36px; }
 
+/* ---- results ------------------------------------------------------------------------------------ */
+#front .shout.big { font-size: 48px; }
+#front .grow { flex: 1; }
+#front .toggle { flex: none; min-height: 36px; padding: 0 14px; background: transparent; border: 1px solid var(--line-strong);
+  color: var(--bright); font-weight: 600; font-size: var(--size-small); cursor: pointer; }
+@keyframes bb-rise { from { transform: translateY(24px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
+#front .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
+#front .cards[data-count="1"] { grid-template-columns: minmax(0, 400px); justify-content: center; }
+#front .cards[data-count="2"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
+#front .cards[data-count="4"] { grid-template-columns: repeat(4, minmax(0, 1fr)); }
+#front .card { position: relative; display: flex; flex-direction: column; min-height: 236px; padding: 16px 20px 18px; overflow: hidden;
+  background: var(--panel); border: 2px solid var(--hairline); animation: bb-rise 420ms var(--ease) both; }
+#front .card.leader { border-color: var(--bright); }
+#front .card-top { display: flex; justify-content: space-between; align-items: flex-start; }
+#front .card .place { font: italic 900 88px/0.9 var(--font-body); color: #3A4046; transform: var(--shout-skew); }
+#front .card.leader .place { color: var(--bright); }
+#front .card .who { font-weight: 600; color: var(--text); }
+#front .card .art { height: 120px; display: flex; align-items: center; justify-content: center; }
+#front .card .title { font: italic 900 26px/1.1 var(--font-body); color: var(--bright); }
+#front .card .player { margin-top: 2px; font: var(--size-label-sm)/1.4 var(--font-mono); color: var(--muted); }
+#front .card .rows { display: flex; align-items: baseline; gap: 8px; margin-top: 12px; }
+#front .card .rows .n { font: italic 900 44px/1 var(--font-body); color: var(--bright); }
+#front .card .rows .word { font-size: 15px; color: var(--text); }
+#front .card .rows .death { margin-left: auto; font-size: var(--size-small); text-align: right; }
+#front .card .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: auto; padding-top: 12px;
+  border-top: 1px solid var(--hairline); font-size: 15px; color: var(--bright); }
+#front .card .stats > span, #front .pair .stats > span { display: flex; flex-direction: column; gap: 2px; }
+#front .card .stats .label, #front .pair .stats .label { font-size: 10px; }
+#front .numbers-box { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; padding: 14px 20px 16px; }
+#front .numbers-head { display: flex; align-items: center; gap: 16px; }
+#front .result-bar { display: flex; align-items: center; gap: 12px; }
+#front .result-bar .name { width: 150px; flex: none; font-size: 13px; color: var(--text); }
+#front .result-bar.yardstick .name { color: var(--muted); }
+#front .result-bar .track { position: relative; flex: 1; height: 10px; background: #15181C; }
+#front .result-bar .fill { position: absolute; left: 0; top: 0; bottom: 0; background: #3A4046; box-shadow: inset 0 0 0 1px var(--line-strong); }
+#front .result-bar .n { width: 40px; text-align: right; font: 12px/1.4 var(--font-mono); color: var(--text); }
+#front table.numbers { width: 100%; font-size: 13px; }
+#front table.numbers th, #front table.numbers td { padding: 4px 8px; text-align: left; border-bottom: 1px solid var(--hairline); font-weight: 400; }
+#front table.numbers thead th { font-weight: 800; font-style: italic; color: var(--bright); border-bottom-color: var(--line-strong); }
+#front table.numbers tbody th { padding-left: 0; color: var(--text); white-space: nowrap; }
+#front table.numbers td { font: 12px/1.4 var(--font-mono); color: var(--bright); }
+#front .results-actions { margin-top: auto; padding-top: 16px; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }
+#front .small-launch { min-width: 0; padding: 0 28px; height: 52px; font-size: 20px; }
+#front .small-launch span { font-size: 13px; }
+#front .plain { height: 52px; padding: 0 24px; background: transparent; border: 1px solid var(--line-strong); color: var(--text);
+  font-weight: 600; font-size: 16px; cursor: pointer; }
+#front .plain:hover { color: var(--bright); }
+
+/* ---- records ------------------------------------------------------------------------------------ */
+#front .records { position: relative; }
+#front .records-top { display: flex; gap: 20px; }
+#front .board-box { width: 660px; flex: none; display: flex; flex-direction: column; gap: 4px; padding: 14px 18px 12px; }
+#front .board { display: flex; flex-direction: column; margin-top: 6px; }
+#front .entry { display: grid; grid-template-columns: 22px 14px minmax(0, 1fr) 64px minmax(0, 200px) 76px; align-items: center; gap: 10px;
+  height: 26px; padding: 0; background: none; border: 0; border-left: 2px solid transparent; cursor: pointer; text-align: left; }
+#front .entry.chosen { border-left-color: var(--accent); }
+#front .entry .rank { font: var(--size-label-sm)/1 var(--font-mono); color: var(--muted); text-align: right; }
+#front .entry .swatch { width: 12px; height: 12px; }
+#front .entry .name { font-size: var(--size-small); color: var(--bright); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
+#front .entry.yardstick .name { color: var(--muted); }
+#front .entry .name .warn { font-size: var(--size-label-sm); }
+#front .entry .tracks { font: var(--size-label-sm)/1 var(--font-mono); color: var(--muted); }
+#front .entry .band, #front .axis { position: relative; height: 12px; background: #15181C; }
+#front .entry .ci { position: absolute; top: 3px; height: 6px; background: #3A4046; }
+#front .entry.yardstick .ci { background: var(--line-strong); }
+#front .entry .mean, #front .axis .mean { position: absolute; top: 0; height: 12px; width: 2px; background: var(--bright); }
+#front .entry .value { font: 12px/1 var(--font-mono); color: var(--bright); text-align: right; }
+#front .board-notes p { margin-top: 6px; }
+#front .pair-box { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; padding: 14px 18px 16px; }
+#front .chips { display: flex; flex-wrap: wrap; gap: 6px; }
+#front .chip { height: 32px; padding: 0 10px; background: transparent; border: 1px solid var(--line-strong); color: var(--text);
+  font-size: 13px; cursor: pointer; }
+#front .chip.on { border-color: var(--accent); color: var(--bright); }
+#front .pair { display: flex; flex-direction: column; gap: 12px; flex: 1; }
+#front .vs { display: flex; align-items: center; gap: 12px; }
+#front .vs .who { font: italic 900 24px/1.1 var(--font-body); color: var(--bright); }
+#front .diff { display: flex; align-items: baseline; gap: 10px; font-size: 15px; color: var(--text); }
+#front .diff .n { font: italic 900 44px/1 var(--font-body); color: var(--bright); }
+#front .axis { height: 26px; }
+#front .axis .zero { position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--muted); }
+#front .axis .ci { position: absolute; top: 9px; height: 8px; background: #3A4046; }
+#front .axis .ci.tell { background: var(--good); }
+#front .axis .mean { top: 3px; height: 20px; }
+#front .axis-labels { display: flex; justify-content: space-between; font: var(--size-label-sm)/1.4 var(--font-mono); color: var(--muted); }
+#front .pair .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; font-size: 15px; color: var(--bright); }
+#front .verdict { margin-top: auto; padding: 12px 14px; display: flex; align-items: center; gap: 12px; border: 1px solid var(--line-strong); }
+#front .verdict .word { font: italic 900 22px/1.1 var(--font-body); text-transform: uppercase; color: var(--warn); }
+#front .verdict.tell { border-color: var(--good); }
+#front .verdict.tell .word { color: var(--good); }
+#front .verdict .note { margin: 0; font-size: 13px; color: var(--muted); }
+#front .runs-box { margin-top: 16px; display: flex; flex-direction: column; gap: 2px; padding: 12px 18px; }
+#front .past { display: grid; grid-template-columns: 110px 120px minmax(0, 1fr) 190px 176px; align-items: center; gap: 12px;
+  min-height: 32px; border-top: 1px solid var(--hairline); font-size: 13px; color: var(--text); }
+#front .past .when { font: 12px/1.4 var(--font-mono); }
+#front .past .players { color: var(--bright); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
+#front .past .status { font-size: var(--size-label-sm); }
+#front .past .status.warn { color: var(--warn); }
+#front .past .status.bad { color: var(--bad); }
+#front .past .status.live { color: var(--bright); animation: bb-live 1.4s ease-in-out infinite; }
+@keyframes bb-live { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
+#front .past .actions { display: flex; gap: 6px; justify-content: flex-end; }
+#front .past .actions button { height: 26px; padding: 0 10px; background: transparent; border: 1px solid var(--line-strong);
+  color: var(--text); font-size: 12px; cursor: pointer; }
+#front .ours-panel { position: absolute; top: 76px; right: 0; z-index: 3; width: min(560px, 100%); max-height: calc(100vh - 120px);
+  overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding: 18px 20px; background: var(--panel);
+  border: 1px solid var(--line-strong); box-shadow: 0 16px 48px rgba(0, 0, 0, .6); font-size: var(--size-small); line-height: 1.5; }
+#front .ours-panel[hidden] { display: none; }
+#front .ours-panel #honesty { margin: 0; padding: 0; border: 0; }
+#front .ours-panel .toggle { align-self: flex-start; }
+
 /* ---- the run screen's bar (outside #front: the run screen is the replay's own page) ---------------- */
 .run-bar { display: flex; align-items: center; gap: 16px; min-height: 56px; }
 .run-bar[hidden] { display: none; }
@@ -173,6 +283,11 @@
 
 @media (max-width: 720px) {
   #front .shout { font-size: 28px; }
+  #front .shout.big { font-size: 32px; }
+  #front .screen-head { flex-wrap: wrap; padding: 12px 0; }
+  #front .screen-head .shout { order: -1; width: 100%; text-align: center; }
+  #front .seed-row { flex-wrap: wrap; gap: 12px; }
+  #front .random { margin-left: 0; }
   #front .home-fighters { gap: 24px; }
   #front .portrait { width: calc(50% - 8px); height: 200px; }
   #front .slots { grid-template-columns: repeat(4, minmax(0, 1fr)); }
@@ -182,4 +297,8 @@
   #front .track-side { width: auto; }
   #front .seed { width: auto; font-size: 64px; }
   #front .tiles { grid-template-columns: repeat(5, minmax(0, 1fr)); }
+  #front .cards, #front .cards[data-count] { grid-template-columns: 1fr; }
+  #front .records-top { flex-direction: column; }
+  #front .board-box { width: auto; }
+  #front .past { grid-template-columns: 1fr 1fr; }
 }
```

Apply to `viewer/front.js`:

```diff
@@ -27,6 +27,8 @@
   const front = {
     screen: "home", from: "home", state: null, sel: Select.make(roster, []), seed: null, armed: false, refusal: null,
     timer: null, leaving: false,
+    results: null, more: false, autoResults: false, // the results on screen, and whether the run's end opens them
+    records: null, pair: [], allRuns: false, // the records on screen, and the two players compared
   };
 
   async function control(path, options) {
@@ -72,6 +74,8 @@
     if (front.screen === "home") renderHome();
     if (front.screen === "select") renderSelect();
     if (front.screen === "track") renderTrack();
+    if (front.screen === "results") renderResults();
+    if (front.screen === "records") renderRecords();
     renderRunBar();
   }
 
@@ -210,6 +214,8 @@
     $("run-what").textContent = run ? "Track " + run.seed + (running() ? " · live" : " · " + run.status) : "";
     $("run-cancel").hidden = !running();
     $("run-home").textContent = front.leaving ? "Home? The run keeps going" : "‹ Home";
+    // the results of the run on screen, for a viewer who scrubbed back and was not taken there
+    $("run-results").hidden = !(front.results && !front.results.why && run && front.results.run_id === run.run_id && !running());
   }
 
   // Going home does not cancel the run, so while one is going the first press says so and the second goes.
@@ -223,6 +229,145 @@
     if (ok && body.state) applyState(body.state);
   });
 
+  $("run-results").addEventListener("click", () => show("results"));
+
+  // ---- results --------------------------------------------------------------------------------------
+  function renderResults() {
+    const results = front.results;
+    $("results-why").hidden = !(results && results.why);
+    $("results-why").textContent = results && results.why ? results.why : "";
+    if (!results || results.why) {
+      for (const id of ["cards", "numbers", "failures"]) $(id).innerHTML = "";
+      return;
+    }
+    const head = Results.header(results);
+    $("results-left").textContent = head.left;
+    $("results-right").textContent = head.right;
+    const more = front.more;
+    $("cards").innerHTML = Results.cardsHtml(Results.cards(results, roster), more);
+    $("cards").dataset.count = String(Math.min(4, results.players.length));
+    paintSprites($("cards"));
+    $("numbers-title").textContent = more ? "The numbers" : "How far each got";
+    $("results-warning").textContent = Results.warning(results, roster);
+    $("more").textContent = more ? "Fewer numbers" : "More numbers";
+    $("more").setAttribute("aria-expanded", String(more));
+    $("numbers").innerHTML = more ? Results.tableHtml(Results.table(results, roster))
+      : Results.barsHtml(Results.bars(results, roster), looks.colour);
+    const failures = more ? Results.failures(results, roster) : [];
+    $("failures").innerHTML = failures.map((line) => '<p class="warn small">' + Minds.esc(line) + "</p>").join("");
+    $("results-note").hidden = !more;
+    $("results-note").textContent = Results.note(results, roster);
+  }
+
+  // The lineup and track of the results on screen, for Run again, New track and Fighters: a past run's
+  // results start from its own lineup, as the run just played does.
+  function takeLineup() {
+    const results = front.results;
+    if (!results || results.why) return;
+    front.sel = Select.make(roster, results.players.map((p) => p.player));
+    if ((results.seeds || []).length) front.seed = results.seeds[0];
+    front.armed = false;
+    front.refusal = null;
+  }
+
+  async function goTrack() {
+    takeLineup();
+    show("track");
+    await refreshState();
+  }
+
+  $("more").addEventListener("click", () => { front.more = !front.more; renderResults(); });
+  $("again").addEventListener("click", async () => { await goTrack(); pressedRun(); }); // straight to RUN's confirmation
+  $("new-track").addEventListener("click", goTrack);
+  $("to-fighters").addEventListener("click", () => { takeLineup(); show("select"); });
+  $("watch-replay").addEventListener("click", async () => {
+    const results = front.results;
+    if (results && Race.watching() !== results.run_id) { // a past run's results: load that run first
+      const { ok, body } = await control("/replay?run=" + encodeURIComponent(results.run_id));
+      if (!ok) { results.why = body.error || "the replay could not be read"; return renderResults(); }
+      Race.load(body);
+    }
+    show("run");
+    Race.rewind();
+  });
+  $("results-records").addEventListener("click", openRecords);
+  $("results-home").addEventListener("click", () => show("home"));
+
+  async function openResults(runId) {
+    const { ok, body } = await control("/results?run=" + encodeURIComponent(runId));
+    front.results = ok ? body : { why: body.error || "the results could not be read" };
+    front.autoResults = false;
+    front.more = false;
+    show("results");
+  }
+
+  // ---- records --------------------------------------------------------------------------------------
+  async function openRecords() {
+    show("records");
+    const { ok, body } = await control("/records");
+    front.records = ok ? body : { why: body.error || "the records could not be read", runs: [], bench: null };
+    const chips = ok ? Records.chips(front.records, roster) : [];
+    if (front.pair.length !== 2 && chips.length) front.pair = [chips[0].a, chips[0].b];
+    renderRecords();
+  }
+
+  function renderRecords() {
+    const records = front.records;
+    $("records-back").textContent = front.from === "results" ? "‹ Results" : "‹ Home";
+    if (!records) return;
+    $("records-why").hidden = !records.why;
+    $("records-why").textContent = records.why || "";
+    $("board-title").textContent = "Leaderboard · game " + records.game + " practice tracks" +
+      (records.tracks ? " " + records.tracks[0] + "–" + records.tracks[1] : "");
+    $("leaderboard").innerHTML = Records.boardHtml(Records.board(records, roster), front.pair);
+    $("board-notes").innerHTML = Records.boardNotes(records, roster).map((n) => '<p class="warn small">' + Minds.esc(n) + "</p>").join("");
+    const [a, b] = front.pair;
+    $("chips").innerHTML = Records.chipsHtml(Records.chips(records, roster), a, b);
+    const pair = a && b ? Records.pairOf(records, a, b) : null;
+    $("pair").innerHTML = pair ? Records.pairHtml(Records.pairView(pair, roster, records.max_rows))
+      : '<p class="muted small">Pick two players to compare them on the tracks both played.</p>';
+    const past = Records.pastRuns(records, roster, front.allRuns);
+    $("past").innerHTML = Records.runsHtml(past.rows);
+    $("all-runs").hidden = past.total <= Records.SHOWN_RUNS;
+    $("all-runs").textContent = front.allRuns ? "Show the newest " + Records.SHOWN_RUNS : "Show all " + past.total;
+    $("ours").innerHTML = Minds.ours(records.ours);
+    $("ours-fly2").innerHTML = Minds.oursFly2(records.ours);
+    $("honesty-fly2").hidden = !(records.ours && records.ours.fly2);
+  }
+
+  $("open-records").addEventListener("click", openRecords);
+  $("leaderboard").addEventListener("click", (event) => { // two rows make a pair: a third starts a new one
+    const row = event.target.closest("button[data-player]");
+    if (!row) return;
+    const player = row.dataset.player;
+    front.pair = front.pair.length === 1 && front.pair[0] !== player ? [front.pair[0], player] : [player];
+    renderRecords();
+  });
+  $("chips").addEventListener("click", (event) => {
+    const chip = event.target.closest("button[data-a]");
+    if (chip) { front.pair = [chip.dataset.a, chip.dataset.b]; renderRecords(); }
+  });
+  $("all-runs").addEventListener("click", () => { front.allRuns = !front.allRuns; renderRecords(); });
+  $("past").addEventListener("click", async (event) => {
+    const button = event.target.closest("button");
+    if (!button) return;
+    if (button.dataset.results) return openResults(button.dataset.results);
+    if (button.dataset.now) { // this session's run, playing now: the stream is already this page's
+      await refreshState();
+      return show("run");
+    }
+    const { ok, body } = await control("/replay?run=" + encodeURIComponent(button.dataset.watch));
+    if (!ok) { front.records.why = body.error || "the replay could not be read"; return renderRecords(); }
+    Race.load(body);
+    show("run");
+  });
+  const setOurs = (open) => {
+    $("ours-panel").hidden = !open;
+    $("ours-toggle").setAttribute("aria-expanded", String(open));
+  };
+  $("ours-toggle").addEventListener("click", () => setOurs($("ours-panel").hidden));
+  $("ours-close").addEventListener("click", () => setOurs(false));
+
   // ---- keys and Back -------------------------------------------------------------------------------
   document.addEventListener("click", (event) => {
     if (event.target.closest("[data-back]")) show(Screens.back(front.screen, front.from));
@@ -280,18 +425,31 @@
     render();
   }
 
-  // app.js calls this when a run has ended: the state says so, and the bar stops offering Cancel.
-  function ended() {
+  // app.js calls this when a run has ended, with its end event: the results arrive with it, and open by
+  // themselves once the tunnel on screen has shown the last row (reachedEnd). A viewer who scrubbed back is
+  // not pulled away: the bar offers "Results" instead.
+  function ended(end) {
     front.leaving = false;
+    front.results = end.results || { why: "the run ended without results" };
+    front.more = false;
+    front.autoResults = true;
     refreshState();
+    if (Race.atEnd()) reachedEnd();
+  }
+
+  function reachedEnd() {
+    if (!front.autoResults || front.screen !== "run") return;
+    front.autoResults = false;
+    setTimeout(() => { if (front.screen === "run") show("results"); }, 1200); // a moment on the last fall first
   }
 
   // app.js calls this once the run screen is ready (live only).
   function start() {
     paintBrain();
+    $("ours-slot").appendChild($("honesty")); // the whole "what is ours" section, moved into Records unchanged
     show("home");
     refreshState();
   }
 
-  root.Front = { start, ended };
+  root.Front = { start, ended, reachedEnd };
 })(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/index.html`:

```diff
@@ -83,6 +83,59 @@
     </div>
   </div>
 </section>
+
+<section id="screen-results" class="screen results" hidden aria-label="Results">
+  <div class="screen-head"><span class="label" id="results-left"></span><h2 class="shout big">RESULTS</h2>
+    <span class="label bright" id="results-right"></span></div>
+  <p class="warn" id="results-why" hidden></p>
+  <div id="cards" class="cards"></div>
+  <div class="panel numbers-box">
+    <div class="numbers-head"><span class="label" id="numbers-title"></span><span class="warn small grow" id="results-warning"></span>
+      <button type="button" id="more" class="toggle" aria-expanded="false"></button></div>
+    <div id="numbers"></div>
+    <div id="failures"></div>
+    <p class="muted small" id="results-note" hidden></p>
+  </div>
+  <div class="results-actions">
+    <button type="button" id="again" class="launch small-launch"><span aria-hidden="true">&#9654;</span>Run again</button>
+    <button type="button" id="new-track" class="plain">New track</button>
+    <button type="button" id="to-fighters" class="plain">Fighters</button>
+    <button type="button" id="watch-replay" class="plain">Watch the replay</button>
+    <button type="button" id="results-records" class="plain">Records</button>
+    <button type="button" id="results-home" class="plain">Home</button>
+  </div>
+</section>
+
+<section id="screen-records" class="screen records" hidden aria-label="Records">
+  <div class="screen-head"><button type="button" class="back label" data-back id="records-back">&lsaquo; Home</button>
+    <h2 class="shout big">RECORDS</h2><button type="button" id="ours-toggle" class="toggle" aria-expanded="false">What is ours</button></div>
+  <p class="warn" id="records-why" hidden></p>
+  <div class="records-top">
+    <div class="panel board-box">
+      <div class="row"><span class="label" id="board-title"></span><span class="muted small">mean rows &middot; bar is the 95% interval</span></div>
+      <div id="leaderboard" class="board"></div>
+      <div id="board-notes" class="board-notes"></div>
+    </div>
+    <div class="panel pair-box">
+      <span class="label">Head to head</span>
+      <div id="chips" class="chips"></div>
+      <p class="muted small">Or pick two rows of the leaderboard.</p>
+      <div id="pair" class="pair"></div>
+    </div>
+  </div>
+  <div class="panel runs-box">
+    <div class="row"><span class="label">Past runs &middot; newest first</span><button type="button" id="all-runs" class="toggle"></button></div>
+    <div id="past" class="past-list"></div>
+  </div>
+  <div id="ours-panel" class="ours-panel" hidden>
+    <span class="label">What is ours, not theirs</span>
+    <p>Every question Jev, Haiku and GLM Flash are asked, and the code rule that turns their answers into a move, are ours: a skin is a question set plus its rule.</p>
+    <p>The flies are untrained and use only their innate wiring. How gaps become input to their eyes, which neurons we read as a turn or a jump, and the thresholds are ours, fixed on practice tracks and frozen.</p>
+    <p>Prices are our estimates per request; Jev is not billed per request.</p>
+    <div id="ours-slot"></div>
+    <button type="button" id="ours-close" class="toggle">Close</button>
+  </div>
+</section>
 </div>
 
 <main id="app" hidden>
@@ -240,6 +293,8 @@
 <script src="screens.js"></script>
 <script src="select.js"></script>
 <script src="trackpick.js"></script>
+<script src="results.js"></script>
+<script src="records.js"></script>
 <script src="front.js"></script>
 <script src="app.js"></script>
 </body>
```

Apply to `viewer/records.js`:

```diff
@@ -206,7 +206,7 @@
   function runsHtml(list) {
     return list.map((r) => '<div class="past"><span class="when">' + esc(r.when) + '</span><span>' + esc(r.tracks) + "</span>" +
       '<span class="players">' + esc(r.players) + '</span><span class="label status ' + r.kind + '">' + esc(r.status) + "</span>" +
-      '<span class="actions"><button type="button" data-watch="' + esc(r.run_id) + '"' + (r.watch === "Watch live" ? ' data-live="true"' : "") +
+      '<span class="actions"><button type="button" data-watch="' + esc(r.run_id) + '"' + (r.watch === "Watch live" ? ' data-now="true"' : "") +
       ">" + esc(r.watch) + '</button><button type="button" data-results="' + esc(r.run_id) + '">Results</button></span></div>').join("");
   }
 
```

Apply to `viewer/results.js`:

```diff
@@ -115,6 +115,7 @@
       title: labelOf(roster, r.entry.player),
       rows: single ? (r.entry.tracks[0] ? r.entry.tracks[0].rows : 0) : (r.entry.mean_rows == null ? "-" : r.entry.mean_rows.toFixed(1)),
       rowsWord: single ? "rows" : "rows a track", death: death(r.entry, single), stopped: r.stopped,
+      finished: single ? !!(r.entry.tracks[0] && r.entry.tracks[0].finished) : false,
       perRow: perRow(r.entry.s_per_row), requests: requestsText(r.entry, roster), cost: costText(r.entry),
       paid: !!(r.entry.paid && r.entry.price_usd > 0),
     }));
@@ -189,19 +190,20 @@
 
   // ---- the markup --------------------------------------------------------------------------------
   function cardsHtml(list, more) {
-    return list.map((c, i) => '<article class="card' + (c.top ? " top" : "") + (c.stopped ? " stopped" : "") + '" style="animation-delay:' +
+    // a finish is not a death: only a fall is --bad, and a stopped run is --warn
+    return list.map((c, i) => '<article class="card' + (c.top ? " leader" : "") + (c.stopped ? " stopped" : "") + '" style="animation-delay:' +
       i * 90 + 'ms"><div class="card-top"><span class="place">' + c.place + '</span><span class="label who">' + esc(c.label) +
       "</span></div>" + (more ? "" : '<div class="art"><canvas class="sprite" data-player="' + esc(c.player) + '" data-px="11"></canvas></div>') +
       '<span class="title">' + esc(c.title) + '</span><span class="player">' + esc(c.player) + "</span>" +
       '<div class="rows"><span class="n">' + esc(c.rows) + '</span><span class="word">' + esc(c.rowsWord) + '</span><span class="death' +
-      (c.stopped ? " warn" : " bad") + '">' + esc(c.death) + "</span></div>" +
+      (c.stopped ? " warn" : c.finished ? "" : " bad") + '">' + esc(c.death) + "</span></div>" +
       '<div class="stats"><span><span class="label">Per row</span>' + esc(c.perRow) + '</span><span><span class="label">Requests</span>' +
       esc(c.requests) + '</span><span><span class="label">Cost</span><span class="' + (c.paid ? "warn" : "muted") + '">' + esc(c.cost) +
       "</span></span></div></article>").join("");
   }
 
   function barsHtml(list, colourOf) {
-    return list.map((b) => '<div class="bar' + (b.yardstick ? " yardstick" : "") + '"><span class="name">' + esc(b.name) + "</span>" +
+    return list.map((b) => '<div class="result-bar' + (b.yardstick ? " yardstick" : "") + '"><span class="name">' + esc(b.name) + "</span>" +
       '<span class="track"><span class="fill" style="width:' + (b.width * 100).toFixed(2) + "%" +
       (b.yardstick ? "" : ";background:" + esc(colourOf(b.player) || "#3A4046")) + '"></span></span>' +
       '<span class="n">' + esc(typeof b.rows === "number" && !Number.isInteger(b.rows) ? b.rows.toFixed(1) : b.rows) + "</span></div>").join("");
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected: `24 passed in 1.11s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `580 passed, 16 deselected in 43.12s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/front.css viewer/front.js viewer/index.html viewer/records.js viewer/results.js viewer/tests/records.test.js viewer/tests/results.test.js
git commit -F <message file>   # the Brain Battle front: results, records, and watching a run again
```

---

## After the tasks (controller only)

- [ ] **Look at every screen** against a live server on a copy of the recorded runs (`bakeoff live --out <copy>`):
  - home;
  - the select, with keys and dots;
  - the track select, with a paid lineup (to see the confirmation) and a free one;
  - a Bot run through to results that open by themselves;
  - More numbers;
  - Records, including the pair chips, "What is ours" and Watch on a past run;
  - the phone width.
  Restart the server after any change: it renders the page once, at startup.
- [ ] **The fly smoke that covers plans a and b** (decision 46), once `pgrep -fl bakeoff` shows no other fly: pick Fly · Looming and Bot · Solver on track 1001 in the page and play it through to results. Stop the command afterwards; never leave a fly running.
- [ ] **Docs:**
  - `CLAUDE.md`: the pure JavaScript list gains `screens.js`, `select.js`, `trackpick.js`, `results.js`, `records.js`, and `front.js` is the glue; the page-control paragraph describes the front instead of the lobby.
  - `docs/NEXT.md`, and `docs/FRONTEND.md`'s "Where this stands".
  - Read what any docs agent wrote before calling the docs done.
- [ ] **One whole-branch design review** (the most capable model) of plan b, aimed at:
  - money: the confirmation and Run again;
  - the honesty surface: the moved section, fly2's mark, the portraits' slit, the finish colour;
  - escaping;
  - the front's state handling: a run started elsewhere (`--start`), a reload during a run, a cancelled run, a past run's results.
