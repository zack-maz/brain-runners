# Phase 4: The Replay Viewer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `uv run python -m bakeoff view <run_dir>...` writes one self-contained HTML file in which the players of a seeded track run side by side through the tunnel, each with its "mind" visible (the fly's spikes and read-out signals, Jev's probabilities, the LLM's answer), next to a table of rows survived per track, the scoreboard, and a plain statement of what in the fly's set-up is ours rather than the fly's.

**Architecture:** Python keeps the rules of the game. `bakeoff/replay.py` merges one or more run directories into one replay object (frames with their landing tiles, complete or cut-off episodes, the report's scoreboard) and `bakeoff/view.py` inlines that object and the files of `viewer/` into one HTML file. The JavaScript only draws: `viewer/timeline.js` (where a runner is at replay time t), `viewer/tunnel.js` (the ring of lanes as a tube, on a canvas) and `viewer/minds.js` (mind panels as escaped HTML strings) are pure and tested with node's built-in test runner, which `uv run pytest` starts; `viewer/app.js` is the glue.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript (no build step, no npm packages, no framework), `node --test` for the JavaScript tests (node 18 or later; the tests are skipped without node). No new Python dependency.

**Spec:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (binding; sections "Goal", "Senses", "Fly player" with its known weaknesses, "Architecture", "Step record", "Report"). The log format the replay is built from: `docs/STEP_RECORD.md`. Background: `docs/DECISIONS.md`.

**Branch:** `phase4-replay-viewer` (already created; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add` in this phase, and no `npm`: the viewer has no packages.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network** and nothing in this phase needs a key, the fly data or a paid request.
- **This phase spends no money.** It reads logs only. Do not run `bakeoff run` with `jev` or `llm`, do not pass `--max-requests`, do not run `pytest -m live`, do not run `pytest -m slow`.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command. Nothing in this phase needs it.
- **Frozen:** do not touch `bakeoff/senses.py`, `bakeoff/game/`, `bakeoff/fly/`, `bakeoff/players/`, `bakeoff/clients/`, `bakeoff/runner.py`, `bakeoff/report.py` or `calibration/`. The step record does not change; `schema_version` stays 1.
- **The page must work offline from disk:** no CDN, no web font, no `fetch`, no external `src` or `href`. System fonts only.
- **Text from a log is never markup.** An LLM's answer, an error message and a question reach the page only through `Minds.esc`, and the embedded JSON writes every `<` as `\u003c`.
- **Honesty rule for the fly (spec):** untrained, innate wiring only. The looming weighting and the two thresholds are ours and are labelled as ours on the page, with the numbers read from the run's `meta.json`; the spec's known weaknesses are on the page.
- Every code block below was run in a prototype and passes as written (final state: 235 fast tests, 9 deselected; 19 node tests inside one of them). The page was opened in a browser against the real practice runs (fly, Jev and the LLM on seed 1000; the fly and three baselines on seeds 0 to 19) at desktop and phone width, with no console errors. If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **One self-contained HTML file, built by Python.** The spec says "static HTML replay reading a run's JSONL". A page opened from disk cannot read files next to it without a server or a file picker, and the JSONL needs the rules of the game to be drawn (where a move lands, which run is complete). So `bakeoff view` reads the JSONL in Python, where those rules already live and are tested, and embeds the result. The file opens with a double click, works offline and can be sent to someone. The spec's Architecture table is updated in Task 6.
2. **Several run directories are merged.** The fly runs alone (one process, 1 GB) and the paid players run apart from it, so a side-by-side replay always spans runs. One (player, seed) may appear in only one of them: two versions of an episode are an error (exit 2), never a silent pick.
3. **Players are lined up by row, not by decision.** Replay time is measured in rows; at time t everyone still alive is at row t, so every column shows the same stretch of track. A jump covers two rows and takes two ticks, and its frame stays on screen for both.
4. **The tunnel is drawn as a tube seen from behind the runner** (the look of the original game): the runner's lane is at the bottom, changing lane turns the tube, a gap is a missing tile. The tiles the player was shown (6 rows ahead, 3 lanes either side) are brighter, and the same senses are drawn as a small grid in every mind panel, so what each player knew is always on screen.
5. **A run that was cut off is not a death.** The report's complete-runs-only rule carries over: such an episode is marked `complete: false`, the table marks it with an ellipsis and the column says "Run stopped ... (not a death)".
6. **The scoreboard is the report's, per run, unchanged** (`summarize`), with a `run_id` column. When the players did not all play the same seeds, the page says their means are not a fair comparison and points at the per-track table.
7. **Slimming:** a frame is a step record without `senses` (kept as `ahead`, the six `gaps_relative` lists), `questions` (stored once per episode, frames point at it with `q`) and `track` (stored once per seed). The three-player practice replay is 2.9 MB; 20 seeds of four players are 6.4 MB.
8. **JavaScript tests run under pytest.** `tests/test_viewer_js.py` runs `node --test viewer/tests/*.test.js` and is skipped when node is not installed, so `uv run pytest` stays the one command. Canvas painting and `app.js` have no unit tests; Task 7 is looking at the page.
9. **Output file:** `--output`, default `replay.html` in the current directory; `/replay*.html` is git-ignored. A replay meant to be published goes wherever `--output` says.
10. **Look:** chart-recorder paper with the tunnels as dark round windows in it; one colour per contestant (fly amber, Jev teal, LLM violet), grey for the baselines; system fonts; the controls stick to the bottom of the window like a media player; with reduced motion the runner moves row by row. Left, right, space: step and play.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/replay.py` | `landing`, `build_replay(run_dirs)`: merged runs, frames, episodes, scoreboard | 1 |
| `docs/REPLAY_DATA.md` | The replay object: the contract between `replay.py` and `viewer/` | 1 |
| `docs/STEP_RECORD.md` | Opening paragraph: who reads the step record now | 1 |
| `viewer/timeline.js` | `frameIndexAt`, `laneShift`, `endRow`, `stateAt` (pure) | 2 |
| `tests/test_viewer_js.py` | Runs `node --test viewer/tests/*.test.js` under pytest | 2 |
| `viewer/tunnel.js` | `isGap`, `offset`, `wasSeen`, `quads` (pure) and `draw` (canvas) | 3 |
| `viewer/minds.js` | `esc`, `sensesGrid`, `verdict`, `flyMind`, `jevMind`, `llmMind`, `cost`, `asked`, `mind`, `statusLine` (pure, HTML strings) | 4 |
| `viewer/tests/*.test.js` | node tests of the three pure modules | 2, 3, 4 |
| `viewer/index.html`, `viewer/viewer.css`, `viewer/app.js` | The page, its look, the glue | 5 |
| `bakeoff/view.py` | `embed_json`, `render_html`: everything inlined into one file | 5 |
| `bakeoff/__main__.py`, `.gitignore` | The `view` subcommand; replay files ignored | 5 |
| `README.md`, `CLAUDE.md`, `docs/DECISIONS.md`, the spec | Documentation | 6 |

All three pure JavaScript modules use the same wrapper: an IIFE that builds an `api` object and ends with `if (typeof module !== "undefined" && module.exports) module.exports = api; else root.<Name> = api;`, so the same file is a CommonJS module under node and a global (`Timeline`, `Tunnel`, `Minds`) in the page. There is no `package.json`.

---
### Task 1: Replay data: run directories merged into one object

**Files:**
- Create: `bakeoff/replay.py`, `docs/REPLAY_DATA.md`
- Modify: `docs/STEP_RECORD.md` (opening paragraph)
- Test: `tests/test_replay.py`

**Interfaces:**
- Consumes: `bakeoff.report.load_steps(run_dir) -> list[dict]` (raises `FileNotFoundError("no such run directory: ...")`), `load_meta(run_dir) -> dict | None`, `summarize(steps, meta) -> list[dict]`, `COLUMNS`; the step record of `docs/STEP_RECORD.md`.
- Produces: `bakeoff.replay.landing(row, lane, executed_action, lanes) -> [row, lane]`; `bakeoff.replay.build_replay(run_dirs) -> dict` with keys `replay_version`, `runs`, `players`, `seeds`, `tracks`, `episodes`, `scoreboard` (exact shape: `docs/REPLAY_DATA.md`, created in this task). Raises `ValueError("<player> on seed <n> is in both <run a> and <run b>; pass only one of them")` and lets `FileNotFoundError` through. Later tasks rely on these frame keys: `row`, `lane`, `landing`, `ahead`, `q`, `alive`, `finished`, and on the episode keys `player`, `seed`, `run_id`, `complete`, `finished`, `death_cause`, `rows_survived`, `max_rows`, `questions`, `frames`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_replay.py`:

````python
import json

import pytest

from bakeoff.players import make_player
from bakeoff.replay import build_replay, landing
from bakeoff.report import COLUMNS
from bakeoff.runner import Runner


def record(player="p", seed=0, row=0, lane=6, executed="stay", alive=True, finished=False, death_cause=None,
           track=None, **extra):
    """A hand-made step record with every key the runner writes."""
    senses = {"lane": lane, "lanes": 12, "rows_survived": row,
              "ahead": [{"row": r, "gaps_relative": [r] if r < 3 else []} for r in range(1, 7)], "actions": {}}
    rec = {"run_id": "r", "player": player, "seed": seed, "row": row, "lane": lane, "senses": senses,
           "looming": {"left_hz": 0.0, "right_hz": 25.0}, "questions": None, "answers": None,
           "chosen_action": executed, "executed_action": executed, "solver_action": "stay",
           "solver_depths": {"stay": 6, "left": 6, "right": 6, "jump": 6}, "gated": False, "invalid": False,
           "error": None, "ground_truth": {"gap_ahead": False, "left_safe": True}, "alive": alive,
           "finished": finished, "death_cause": death_cause, "rows_survived": row + 1, "latency_ms": None,
           "usage": None, "cache_hit": False, "info": None, "track": track}
    rec.update(extra)
    return rec


def write_run(root, run_id, records, meta=None):
    run_dir = root / run_id
    run_dir.mkdir()
    by_player = {}
    for rec in records:
        by_player.setdefault(rec["player"], []).append(rec)
    for player, recs in by_player.items():
        (run_dir / f"{player}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    if meta is not None:
        (run_dir / "meta.json").write_text(json.dumps({"run_id": run_id, **meta}))
    return run_dir


TRACK = {"seed": 0, "lanes": 12, "max_rows": 10, "gaps": [[] for _ in range(18)]}


def test_landing_follows_the_step_record_rules():
    assert landing(4, 6, "stay", 12) == [5, 6]
    assert landing(4, 6, "jump", 12) == [6, 6]
    assert landing(4, 0, "left", 12) == [5, 11]  # lanes wrap
    assert landing(4, 11, "right", 12) == [5, 0]


def test_every_landing_matches_the_engine(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("random"), make_player("always_jump"), make_player("solver")],
                                   range(3), max_rows=40, run_id="real")
    replay = build_replay([run_dir])
    assert len(replay["episodes"]) == 9
    for episode in replay["episodes"]:
        gaps = replay["tracks"][str(episode["seed"])]["gaps"]
        frames = episode["frames"]
        for frame, following in zip(frames, frames[1:]):
            assert frame["landing"] == [following["row"], following["lane"]]
        row, lane = frames[-1]["landing"]
        assert (row < len(gaps) and lane in gaps[row]) == (not frames[-1]["alive"])  # only a gap kills
        assert episode["complete"] and episode["max_rows"] == 40
        assert episode["rows_survived"] == frames[-1]["rows_survived"]


def test_a_frame_is_the_record_without_the_bulky_keys(tmp_path):
    run_dir = write_run(tmp_path, "a", [record(track=TRACK), record(row=1, executed="left")])
    (episode,) = build_replay([run_dir])["episodes"]
    first, second = episode["frames"]
    for dropped in ("run_id", "player", "seed", "senses", "questions", "track"):
        assert dropped not in first
    assert first["ahead"] == [[1], [2], [], [], [], []]
    assert first["looming"] == {"left_hz": 0.0, "right_hz": 25.0} and first["q"] is None
    assert second["landing"] == [2, 5] and second["solver_depths"]["jump"] == 6
    assert (episode["player"], episode["seed"], episode["run_id"]) == ("p", 0, "a")


def test_questions_are_stored_once_per_episode(tmp_path):
    ask, other = {"system": "rules"}, {"system": "edited rules"}
    run_dir = write_run(tmp_path, "a", [record(track=TRACK, questions=ask), record(row=1, questions=ask),
                                        record(row=2, questions=other), record(row=3)])
    (episode,) = build_replay([run_dir])["episodes"]
    assert episode["questions"] == [ask, other]
    assert [f["q"] for f in episode["frames"]] == [0, 0, 1, None]


def test_a_run_cut_off_midway_is_incomplete_not_a_death(tmp_path):
    run_dir = write_run(tmp_path, "a", [
        record(seed=0, track=TRACK), record(seed=0, row=1, alive=False, death_cause="ran_into_gap"),
        record(seed=1, track=TRACK), record(seed=1, row=1)])
    dead, cut = build_replay([run_dir])["episodes"]
    assert dead["complete"] and dead["death_cause"] == "ran_into_gap"
    assert not cut["complete"] and cut["death_cause"] is None


def test_runs_are_merged_with_the_contestants_first(tmp_path):
    a = write_run(tmp_path, "a", [record("solver", track=TRACK), record("llm", track=TRACK)],
                  meta={"status": "completed", "players": ["solver", "llm"], "seeds": [0],
                        "models": {"llm": "claude-haiku-4-5-20251001"}})
    b = write_run(tmp_path, "b", [record("fly", seed=0, track=TRACK), record("fly", seed=1, track=TRACK)],
                  meta={"status": "interrupted", "players": ["fly"], "seeds": [0, 1],
                        "fly": {"turn_threshold_hz": 0.0, "jump_threshold_hz": 200.0}})
    replay = build_replay([a, b])
    assert replay["replay_version"] == 1
    assert replay["players"] == ["fly", "llm", "solver"] and replay["seeds"] == [0, 1]
    assert [(e["seed"], e["player"]) for e in replay["episodes"]] == [(0, "fly"), (0, "llm"), (0, "solver"), (1, "fly")]
    assert [r["run_id"] for r in replay["runs"]] == ["a", "b"]
    assert replay["runs"][1]["status"] == "interrupted" and replay["runs"][1]["fly"]["jump_threshold_hz"] == 200.0
    assert replay["runs"][0]["fly"] is None  # a run from before phase 2 has no fly block
    board = replay["scoreboard"]
    assert board["columns"] == ["run_id", *COLUMNS]
    assert [(r["player"], r["run_id"]) for r in board["rows"]] == [("fly", "b"), ("llm", "a"), ("solver", "a")]
    assert board["same_seeds"] is False  # the fly played a seed the others did not


def test_other_players_keep_the_order_the_run_planned(tmp_path):
    run_dir = write_run(tmp_path, "a", [record("solver", track=TRACK), record("always_jump", track=TRACK),
                                        record("fly", track=TRACK)],
                        meta={"players": ["solver", "never_started", "fly", "always_jump"], "seeds": [0]})
    assert build_replay([run_dir])["players"] == ["fly", "solver", "always_jump"]


def test_same_seeds_is_true_when_everyone_played_the_same_tracks(tmp_path):
    run_dir = write_run(tmp_path, "a", [record("fly", track=TRACK), record("llm", track=TRACK)])
    assert build_replay([run_dir])["scoreboard"]["same_seeds"] is True


def test_the_same_episode_in_two_runs_is_an_error(tmp_path):
    a = write_run(tmp_path, "a", [record("jev", track=TRACK)])
    b = write_run(tmp_path, "b", [record("jev", track=TRACK)])
    with pytest.raises(ValueError, match="jev on seed 0 is in both a and b"):
        build_replay([a, b])


def test_the_longest_track_of_a_seed_is_kept(tmp_path):
    short = {**TRACK, "max_rows": 4, "gaps": [[] for _ in range(12)]}
    a = write_run(tmp_path, "a", [record("fly", track=short)])
    b = write_run(tmp_path, "b", [record("llm", track=TRACK)])
    replay = build_replay([a, b])
    assert len(replay["tracks"]["0"]["gaps"]) == 18
    assert [e["max_rows"] for e in replay["episodes"]] == [4, 10]


def test_a_run_without_meta_is_named_after_its_directory(tmp_path):
    run_dir = write_run(tmp_path, "nometa", [record(track=TRACK)])
    (run,) = build_replay([run_dir])["runs"]
    assert run["run_id"] == "nometa" and run["status"] is None


def test_a_missing_run_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such run directory"):
        build_replay([tmp_path / "nope"])
````

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_replay.py -q`
Expected: 1 error, `ModuleNotFoundError: No module named 'bakeoff.replay'`

- [ ] **Step 3: Write the module**

Create `bakeoff/replay.py`:

````python
"""Run directories -> one replay object for the viewer. Reads files only.

The viewer is JavaScript and cannot import Python, so everything that needs the rules of the game
(where a move lands, which run is complete, the scoreboard) is worked out here and tested here.
The format is described in docs/REPLAY_DATA.md."""

from __future__ import annotations

from pathlib import Path

from bakeoff.report import COLUMNS, load_meta, load_steps, summarize

REPLAY_VERSION = 1
CONTESTANTS = ("fly", "jev", "llm")  # shown first, in this order; everyone else in order of appearance
# what a frame leaves out of its step record: the first three name the episode, the others are
# replaced by `ahead`, `q` and the replay's `tracks`
DROPPED = ("run_id", "player", "seed", "senses", "questions", "track")
META_KEYS = ("status", "git_sha", "git_dirty", "started_at", "finished_at", "players", "seeds", "game", "fly",
             "models", "requests")


def landing(row: int, lane: int, executed_action: str, lanes: int) -> list[int]:
    """The tile a move lands on (docs/STEP_RECORD.md, "The landing tile"). On a death the runner
    never reaches it; the viewer draws the fall there."""
    advance = 2 if executed_action == "jump" else 1
    shift = {"left": -1, "right": 1}.get(executed_action, 0)
    return [row + advance, (lane + shift) % lanes]


def _episode(player: str, seed: int, run_id: str, steps: list[dict]) -> tuple[dict, dict | None]:
    steps = sorted(steps, key=lambda s: s["row"])
    track = next((s["track"] for s in steps if s.get("track")), None)
    lanes = track["lanes"] if track else steps[0]["senses"]["lanes"]
    questions: list[dict] = []
    frames = []
    for s in steps:
        frame = {k: v for k, v in s.items() if k not in DROPPED}
        frame["ahead"] = [entry["gaps_relative"] for entry in s["senses"]["ahead"]]
        frame["landing"] = landing(s["row"], s["lane"], s["executed_action"], lanes)
        frame["q"] = None
        if s.get("questions") is not None:
            if s["questions"] not in questions:
                questions.append(s["questions"])
            frame["q"] = questions.index(s["questions"])
        frames.append(frame)
    last = steps[-1]
    episode = {"player": player, "seed": seed, "run_id": run_id,
               # a run cut off mid-way (abort, budget stop, Ctrl-C) is incomplete, not a death
               "complete": bool(last["finished"] or not last["alive"]),
               "finished": last["finished"], "death_cause": last["death_cause"],
               "rows_survived": last["rows_survived"], "max_rows": track["max_rows"] if track else None,
               "questions": questions, "frames": frames}
    return episode, track


def build_replay(run_dirs: list[Path | str]) -> dict:
    """Merge one or more run directories (the fly and the paid players usually run separately).
    A player may appear in several runs, but one (player, seed) only once: two versions of the
    same episode would let the viewer show either, so that is an error, not a silent pick."""
    runs, episodes, tracks, scoreboard = [], [], {}, []
    owner: dict[tuple[str, int], str] = {}
    for run_dir in map(Path, run_dirs):
        steps = load_steps(run_dir)
        meta = load_meta(run_dir)
        run_id = (meta or {}).get("run_id") or run_dir.name
        runs.append({"run_id": run_id, **{k: (meta or {}).get(k) for k in META_KEYS}})
        grouped: dict[tuple[str, int], list[dict]] = {}
        for s in steps:
            grouped.setdefault((s["player"], s["seed"]), []).append(s)
        for (player, seed), group in grouped.items():
            if (player, seed) in owner:
                raise ValueError(f"{player} on seed {seed} is in both {owner[(player, seed)]} and {run_id}; "
                                 "pass only one of them")
            owner[(player, seed)] = run_id
            episode, track = _episode(player, seed, run_id, group)
            episodes.append(episode)
            # a run with a smaller max_rows plays a prefix of the same track: keep the longest
            if track and len(track["gaps"]) > len(tracks.get(str(seed), {}).get("gaps", ())):
                tracks[str(seed)] = track
        scoreboard += [{"run_id": run_id, **row} for row in summarize(steps, meta)]

    # the order the runs planned them in (the log files alone would give alphabetical order)
    planned = [p for run in runs for p in run["players"] or ()] + [e["player"] for e in episodes]
    seen = [p for p in dict.fromkeys(planned) if any(e["player"] == p for e in episodes)]
    players = [p for p in CONTESTANTS if p in seen] + [p for p in seen if p not in CONTESTANTS]
    episodes.sort(key=lambda e: (e["seed"], players.index(e["player"])))
    scoreboard.sort(key=lambda r: players.index(r["player"]) if r["player"] in players else len(players))
    seeds_of = {p: {e["seed"] for e in episodes if e["player"] == p} for p in players}
    return {
        "replay_version": REPLAY_VERSION, "runs": runs, "players": players,
        "seeds": sorted({e["seed"] for e in episodes}), "tracks": tracks, "episodes": episodes,
        "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": scoreboard,
                       # means over different seeds are not a fair comparison; the viewer says so
                       "same_seeds": len({frozenset(s) for s in seeds_of.values()}) <= 1},
    }
````

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_replay.py -q` — Expected: 12 passed.
Run: `uv run pytest -q` — Expected: 227 passed, 9 deselected.

- [ ] **Step 5: Document the format**

Create `docs/REPLAY_DATA.md`:

````markdown
# Replay data (replay version 1)

The contract between `bakeoff/replay.py` (Python, which knows the rules of the game) and the
viewer in `viewer/` (JavaScript, which only draws). `uv run python -m bakeoff view <run_dir>...`
builds this object from one or more run directories and embeds it in one HTML file. The step
records it is built from are described in `docs/STEP_RECORD.md`.

## Top level

| key | type | meaning |
| --- | --- | --- |
| `replay_version` | int | 1. Bumped on any breaking change to this object |
| `runs` | object[] | one per run directory, in the order given: `run_id` plus these keys of its `meta.json`, null when absent: `status`, `git_sha`, `git_dirty`, `started_at`, `finished_at`, `players`, `seeds`, `game`, `fly`, `models`, `requests`. A directory without `meta.json` is named after the directory |
| `players` | string[] | players with at least one episode: `fly`, `jev`, `llm` first, the others in the order the runs planned them |
| `seeds` | int[] | every seed with at least one episode, ascending |
| `tracks` | object | `{"<seed>": track}`, the step record's `track`. When runs played the same seed with different `max_rows`, the longest is kept (the shorter one is its prefix) |
| `episodes` | object[] | one per (player, seed), sorted by seed, then by `players` order |
| `scoreboard` | object | `columns`: `run_id` followed by the report's columns; `rows`: the report's rows, one per player per run, in `players` order; `same_seeds`: false when the players did not all play the same seeds, so their means are not a fair comparison and the viewer says so |

One (player, seed) may appear in only one of the run directories. Two versions of the same episode
are an error (`ValueError`, exit 2 from the CLI), never a silent pick.

## Episode

`player`, `seed`, `run_id`, `complete` (false for a run that was cut off: no death, no finish),
`finished`, `death_cause`, `rows_survived` (all three from the last record), `max_rows` of the run
that played it, `questions` and `frames`.

`questions` lists the distinct `questions` objects of the episode's records, normally one. A frame
points into it with `q`, so the briefing text is stored once and not once per row.

## Frame

A frame is a step record without `run_id`, `player`, `seed`, `senses`, `questions` and `track`,
plus three keys:

| key | type | meaning |
| --- | --- | --- |
| `ahead` | int[][] | the `gaps_relative` lists of `senses.ahead`, nearest row first: what the player was shown |
| `landing` | `[row, lane]` | the tile the executed move lands on, by the rules in `docs/STEP_RECORD.md` ("The landing tile"). For every frame but the last it is the next frame's `row` and `lane`; after a fatal move it is the gap the runner fell into |
| `q` | int or null | index into the episode's `questions`; null when nothing was asked |

Frames are sorted by `row`. A jump advances two rows, so rows are not consecutive.

## How the viewer uses it

Replay time is measured in rows and every player is on the same clock: at time `t` every runner
still alive is at row `t`, so the columns show the same stretch of track. The frame on screen is
the last one with `row <= t`; between `row` and `landing[0]` the runner moves from one to the
other (a jump takes two ticks). After the last frame's landing the episode is `dead`, `finished`
or, when `complete` is false, `cut`.

All text from a log (an LLM's answer, an error message, a question) is escaped before it is put
on the page, and the embedded JSON writes every `<` as `<` so nothing in it can end its
`<script>` element. The page loads nothing from the network.
````

Edit `docs/STEP_RECORD.md` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -1,7 +1,9 @@
 # Step record and `meta.json` (schema version 1)
 
-The contract between the runner (Python) and the phase 4 replay viewer (JavaScript, which cannot
-import Python). The code that writes it is `bakeoff/runner.py`; the spec's "Step record" section
-is the short version and points here.
+The contract between the runner and everything that reads a run: the report and
+`bakeoff/replay.py`, which turns run directories into the replay viewer's data
+(`docs/REPLAY_DATA.md`; the viewer is JavaScript and cannot import Python, so the rules below are
+applied once, in Python). The code that writes it is `bakeoff/runner.py`; the spec's "Step record"
+section is the short version and points here.
 
 ## Files in a run directory
````

- [ ] **Step 6: Commit**

```bash
git add bakeoff/replay.py tests/test_replay.py docs/REPLAY_DATA.md docs/STEP_RECORD.md
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `feat: replay data: run directories merged into one object for the viewer`.

### Task 2: Viewer timeline, and JavaScript tests under pytest

**Files:**
- Create: `viewer/timeline.js`
- Test: `viewer/tests/timeline.test.js`, `tests/test_viewer_js.py`

**Interfaces:**
- Consumes: an episode `{frames: [{row, lane, landing: [row, lane], alive, finished}, ...]}` sorted by `row`, first row 0 (Task 1).
- Produces: global `Timeline` in the page, CommonJS module under node: `frameIndexAt(episode, t) -> int`; `laneShift(frame, lanes) -> -1 | 0 | 1`; `endRow(episode) -> int` (the last frame's `landing[0]`); `stateAt(episode, t, lanes) -> {index, frame, status, row, lane, air, since}` with `status` one of `"running"`, `"dead"`, `"finished"`, `"cut"`; `lane` is not wrapped (a step from lane 0 to lane 11 reads 0 to -1); `air` is 0..1; `since` is the time since the episode ended. `tests/test_viewer_js.py` runs every `viewer/tests/*.test.js`, so Tasks 3 and 4 only add test files.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/timeline.test.js`:

````javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { frameIndexAt, laneShift, endRow, stateAt } = require("../timeline.js");

const frame = (row, lane, landing, extra) => ({ row, lane, landing, alive: true, finished: false, ...extra });
// stay, jump (rows 1 -> 3), step left round the ring, then a fatal step right
const episode = {
  frames: [
    frame(0, 0, [1, 0]),
    frame(1, 0, [3, 0]),
    frame(3, 0, [4, 11]),
    frame(4, 11, [5, 0], { alive: false }),
  ],
};

test("the frame on screen is the last one decided at or before t", () => {
  assert.deepEqual([0, 0.9, 1, 2.5, 3, 4.2, 99].map((t) => frameIndexAt(episode, t)), [0, 0, 1, 1, 2, 3, 3]);
});

test("a jump takes two ticks, peaks half way and keeps its frame", () => {
  const mid = stateAt(episode, 2, 12);
  assert.equal(mid.index, 1);
  assert.equal(mid.row, 2);
  assert.equal(mid.air, 1);
  assert.equal(stateAt(episode, 1, 12).air, 0);
  assert.equal(stateAt(episode, 0.5, 12).air, 0); // a stay never leaves the floor
});

test("lane steps go the short way round the ring", () => {
  assert.equal(laneShift(episode.frames[2], 12), -1);
  assert.equal(laneShift(episode.frames[3], 12), 1);
  assert.equal(laneShift(episode.frames[0], 12), 0);
  assert.equal(stateAt(episode, 3.5, 12).lane, -0.5); // not wrapped: 0 -> -1, never 0 -> 11
});

test("a fatal move runs until it lands, then the runner is dead", () => {
  assert.equal(stateAt(episode, 4.5, 12).status, "running");
  const dead = stateAt(episode, 6, 12);
  assert.equal(dead.status, "dead");
  assert.equal(dead.row, 5);
  assert.equal(dead.since, 1);
  assert.equal(endRow(episode), 5);
});

test("an episode ends finished or cut, never dead, when its last frame is alive", () => {
  const finished = { frames: [frame(0, 6, [1, 6], { finished: true })] };
  const cut = { frames: [frame(0, 6, [1, 6])] };
  assert.equal(stateAt(finished, 1, 12).status, "finished");
  assert.equal(stateAt(cut, 1, 12).status, "cut");
  assert.equal(stateAt(cut, 0.5, 12).status, "running");
});
````

Create `tests/test_viewer_js.py`:

````python
"""The viewer's pure JavaScript (timeline, tunnel geometry, mind panels) has its own tests, run by
node's built-in test runner. No npm packages. Skipped when node is not installed."""

import shutil
import subprocess
from pathlib import Path

import pytest

VIEWER = Path(__file__).resolve().parent.parent / "viewer"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_viewer_javascript():
    tests = sorted(str(p) for p in (VIEWER / "tests").glob("*.test.js"))
    assert tests, "no viewer tests found"
    result = subprocess.run(["node", "--test", *tests], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
````

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_viewer_js.py -q`
Expected: 1 failed; the output contains `Error: Cannot find module '../timeline.js'`. (If it says `1 skipped`, node is not installed: stop and tell the controller.)

- [ ] **Step 3: Write the module**

Create `viewer/timeline.js`:

````javascript
// Where a runner is at replay time t. Pure: no DOM, so `node --test viewer/tests` can run it.
//
// Time is measured in rows and every player's clock is the track: at time t everyone still running
// is at row t, so the columns show the same stretch of tunnel. A jump covers two rows, so it takes
// two ticks and the frame that decided it stays on screen for both.
(function (root) {
  "use strict";

  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (p) => p * p * (3 - 2 * p);

  // index of the last frame decided at or before time t (frames are sorted by row, first row is 0)
  function frameIndexAt(episode, t) {
    const frames = episode.frames;
    let lo = 0, hi = frames.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (frames[mid].row <= t) lo = mid; else hi = mid - 1;
    }
    return lo;
  }

  // -1, 0 or 1: the way the move went round the ring (lane 0 going left lands on the last lane)
  function laneShift(frame, lanes) {
    const delta = (((frame.landing[1] - frame.lane) % lanes) + lanes) % lanes;
    return delta === lanes - 1 ? -1 : delta;
  }

  // the row at which the episode's last move lands: where it died, finished or was cut off
  function endRow(episode) {
    return episode.frames[episode.frames.length - 1].landing[0];
  }

  // status: "running", or once the last move has landed "dead", "finished" or "cut" (a run that was
  // stopped, not a death). `lane` is not wrapped, so a step from lane 0 to lane 11 reads 0 -> -1 and
  // the tunnel turns the short way. `air` is 0..1, the height of a jump. `since` is the time since
  // the episode ended (0 while running); the view uses it to draw the fall.
  function stateAt(episode, t, lanes) {
    const index = frameIndexAt(episode, t);
    const frame = episode.frames[index];
    const advance = frame.landing[0] - frame.row;
    const p = clamp01((t - frame.row) / advance);
    const last = index === episode.frames.length - 1;
    let status = "running";
    if (last && p >= 1) status = !frame.alive ? "dead" : frame.finished ? "finished" : "cut";
    return {
      index, frame, status,
      row: frame.row + advance * p,
      lane: frame.lane + laneShift(frame, lanes) * smooth(p),
      air: advance === 2 ? Math.sin(Math.PI * p) : 0,
      since: status === "running" ? 0 : t - frame.landing[0],
    };
  }

  const api = { frameIndexAt, laneShift, endRow, stateAt };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Timeline = api;
})(typeof window !== "undefined" ? window : globalThis);
````

- [ ] **Step 4: Run the tests**

Run: `node --test viewer/tests/*.test.js` — Expected: `pass 5`, `fail 0`.
Run: `uv run pytest -q` — Expected: 228 passed, 9 deselected.

- [ ] **Step 5: Commit**

```bash
git add viewer/timeline.js viewer/tests/timeline.test.js tests/test_viewer_js.py
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `feat: viewer timeline: where a runner is at replay time t, tested through node`.

### Task 3: The tunnel: a ring of lanes drawn as a tube

**Files:**
- Create: `viewer/tunnel.js`
- Test: `viewer/tests/tunnel.test.js`

**Interfaces:**
- Consumes: a track `{lanes, max_rows, gaps}` where `gaps[r]` lists the gap lanes of row `r` and a row past the list is floor (`docs/STEP_RECORD.md`, "`track`"); a state from `Timeline.stateAt` (`row`, `lane`, `air`, `status`, `since`).
- Produces: global `Tunnel`: `DEPTH` (rows drawn ahead, 20); `isGap(track, row, lane) -> bool` (lane wrapped); `offset(lane, from, lanes) -> int` in `-lanes/2 .. lanes/2 - 1`; `wasSeen(row, lane, seen, lanes) -> bool` with `seen = {row, lane, lookahead, window}`; `quads(track, cam, seen, size, maxRows) -> [{row, lane, kind, depth, points}]`, far to near, gaps left out, `kind` one of `"seen"`, `"floor"`, `"finish"`; `draw(ctx, size, track, state, seen, maxRows, colours)` with `colours = {space, floor, seen, finish, runner}`, each `[r, g, b]`.

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/tunnel.test.js`:

````javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { DEPTH, isGap, offset, wasSeen, quads } = require("../tunnel.js");

const track = { lanes: 12, max_rows: 300, gaps: [[], [], [5, 6], [0, 11]] };
const seen = { row: 0, lane: 6, lookahead: 6, window: 3 };
const SIZE = 400;
const centreX = (quad) => quad.points.reduce((sum, p) => sum + p[0], 0) / 4;
const centreY = (quad) => quad.points.reduce((sum, p) => sum + p[1], 0) / 4;

test("gaps wrap round the ring and rows past the list are floor", () => {
  assert.equal(isGap(track, 2, 5), true);
  assert.equal(isGap(track, 3, -1), true); // lane -1 is lane 11
  assert.equal(isGap(track, 3, 12), true); // lane 12 is lane 0
  assert.equal(isGap(track, 2, 4), false);
  assert.equal(isGap(track, 99, 5), false);
});

test("offsets are wrapped the way the senses wrap them", () => {
  assert.deepEqual([6, 7, 5, 0, 11].map((lane) => offset(lane, 6, 12)), [0, 1, -1, -6, 5]);
  assert.equal(offset(11, 0, 12), -1);
});

test("the player saw six rows ahead and three lanes either side", () => {
  assert.equal(wasSeen(1, 6, seen, 12), true);
  assert.equal(wasSeen(6, 9, seen, 12), true);
  assert.equal(wasSeen(0, 6, seen, 12), false); // its own row is not ahead
  assert.equal(wasSeen(7, 6, seen, 12), false);
  assert.equal(wasSeen(1, 10, seen, 12), false);
  assert.equal(wasSeen(1, 10, { ...seen, lane: 0 }, 12), true); // lane 10 is two to the left of lane 0
});

test("a gap is a missing tile and every other tile of the drawn rows is there", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 300);
  assert.equal(all.length, (DEPTH + 1) * 12 - 4);
  assert.equal(all.some((q) => q.row === 2 && (q.lane === 5 || q.lane === 6)), false);
  assert.equal(all[0].row, DEPTH); // far to near, so near tiles paint over far ones
  assert.equal(all[all.length - 1].row, 0);
});

test("the runner's lane is at the bottom and the lane to its right is on the right", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 300);
  const tile = (row, lane) => all.find((q) => q.row === row && q.lane === lane);
  assert.ok(Math.abs(centreX(tile(0, 6)) - SIZE / 2) < 1e-6);
  assert.ok(centreY(tile(0, 6)) > SIZE / 2);
  assert.ok(centreX(tile(0, 7)) > centreX(tile(0, 6)));
  assert.ok(centreX(tile(0, 5)) < centreX(tile(0, 6)));
  assert.ok(centreY(tile(0, 0)) < SIZE / 2); // the opposite lane is the ceiling
  assert.ok(centreY(tile(5, 6)) < centreY(tile(0, 6))); // further away is nearer the middle
});

test("tiles are marked as seen, floor or finish", () => {
  const all = quads(track, { row: 0, lane: 6 }, seen, SIZE, 4);
  const kind = (row, lane) => all.find((q) => q.row === row && q.lane === lane).kind;
  assert.equal(kind(1, 6), "seen");
  assert.equal(kind(1, 11), "floor");
  assert.equal(kind(0, 6), "floor");
  assert.equal(kind(4, 6), "finish");
});
````

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_viewer_js.py -q`
Expected: 1 failed; the five timeline tests pass and the output contains `Cannot find module '../tunnel.js'`.

- [ ] **Step 3: Write the module**

`draw` and `drawRunner` paint on a canvas and have no unit test; they are checked by eye in Task 7. Copy them exactly.

Create `viewer/tunnel.js`:

````javascript
// The tunnel as seen from behind the runner. `quads` is pure geometry (tested under node);
// `draw` paints it on a canvas.
//
// The track is a ring of lanes, so it is drawn as a tube: the runner's lane is at the bottom, the
// lane to its right is to the right, and changing lane turns the tube. A gap is a missing tile.
(function (root) {
  "use strict";

  const DEPTH = 20; // rows drawn ahead of the runner
  const PERSPECTIVE = 0.32; // a tile d rows away is drawn at scale 1 / (1 + PERSPECTIVE * d)
  const RADIUS = 0.43; // tube radius at the runner, as a share of the canvas size

  const wrap = (lane, lanes) => ((lane % lanes) + lanes) % lanes;

  function isGap(track, row, lane) {
    return row >= 0 && row < track.gaps.length && track.gaps[row].includes(wrap(lane, track.lanes));
  }

  // lane offset from the runner, -lanes/2 .. lanes/2 - 1, the way the senses wrap it
  function offset(lane, from, lanes) {
    return wrap(lane - from + lanes / 2, lanes) - lanes / 2;
  }

  // Was tile (row, lane) in the senses of the decision taken at `seen` = {row, lane, lookahead, window}?
  function wasSeen(row, lane, seen, lanes) {
    const ahead = row - seen.row;
    return ahead >= 1 && ahead <= seen.lookahead && Math.abs(offset(lane, seen.lane, lanes)) <= seen.window;
  }

  // Floor tiles from far to near, each {row, lane, kind, depth, points}. kind: "seen" (the player was
  // shown this tile), "floor", or "finish" (past the last row). cam = {row, lane}, both may be fractions.
  function quads(track, cam, seen, size, maxRows) {
    const centre = size / 2;
    const step = (2 * Math.PI) / track.lanes;
    const point = (angle, d) => {
      const radius = (RADIUS * size) / (1 + PERSPECTIVE * d);
      return [centre + radius * Math.cos(angle), centre + radius * Math.sin(angle)];
    };
    const out = [];
    const first = Math.floor(cam.row);
    for (let row = first + DEPTH; row >= first; row--) {
      const near = Math.max(row - cam.row, -1), far = row + 1 - cam.row;
      for (let lane = 0; lane < track.lanes; lane++) {
        if (isGap(track, row, lane)) continue;
        // canvas y points down, so the bottom of the tube is angle pi/2 and "right" is a smaller angle
        const angle = Math.PI / 2 - offset(lane, cam.lane, track.lanes) * step;
        const a = angle + step / 2, b = angle - step / 2;
        const kind = row >= maxRows ? "finish" : wasSeen(row, lane, seen, track.lanes) ? "seen" : "floor";
        out.push({ row, lane, kind, depth: near, points: [point(a, near), point(b, near), point(b, far), point(a, far)] });
      }
    }
    return out;
  }

  const rgb = (colour) => "rgb(" + colour.join(",") + ")";

  function mix(from, to, share) {
    return "rgb(" + from.map((c, i) => Math.round(c + (to[i] - c) * share)).join(",") + ")";
  }

  // state comes from Timeline.stateAt; colours are [r, g, b]
  function draw(ctx, size, track, state, seen, maxRows, colours) {
    ctx.fillStyle = rgb(colours.space);
    ctx.fillRect(0, 0, size, size);
    const cam = { row: state.row, lane: state.lane };
    for (const quad of quads(track, cam, seen, size, maxRows)) {
      const fog = Math.min(1, Math.max(0, quad.depth) / DEPTH);
      const base = quad.kind === "seen" ? colours.seen : quad.kind === "finish" ? colours.finish : colours.floor;
      ctx.fillStyle = mix(base, colours.space, fog * 0.85);
      ctx.strokeStyle = mix(colours.space, base, 0.25);
      ctx.lineWidth = 1;
      ctx.beginPath();
      quad.points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
    drawRunner(ctx, size, state, colours);
  }

  // The runner stands at the bottom of the tube. A jump lifts it towards the middle; a death drops it
  // through the floor and fades it out over one row of time.
  function drawRunner(ctx, size, state, colours) {
    const fall = state.status === "dead" ? Math.min(1, state.since) : 0;
    if (fall >= 1) return;
    const floor = size / 2 + RADIUS * size * 0.92;
    const height = size * 0.075;
    const y = floor - state.air * size * 0.2 + fall * size * 0.16;
    ctx.globalAlpha = 1 - fall;
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.beginPath();
    ctx.ellipse(size / 2, floor, height * (0.5 - state.air * 0.2), height * 0.14, 0, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = rgb(colours.runner);
    ctx.strokeStyle = rgb(colours.space); // an outline, so a grey baseline runner shows on grey tiles
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(size / 2 - height * 0.3, y - height * 0.95, height * 0.6, height * 0.7, height * 0.2);
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(size / 2, y - height * 1.2, height * 0.27, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  const api = { DEPTH, isGap, offset, wasSeen, quads, draw };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tunnel = api;
})(typeof window !== "undefined" ? window : globalThis);
````

- [ ] **Step 4: Run the tests**

Run: `node --test viewer/tests/*.test.js` — Expected: `pass 11`, `fail 0`.
Run: `uv run pytest -q` — Expected: 228 passed, 9 deselected.

- [ ] **Step 5: Commit**

```bash
git add viewer/tunnel.js viewer/tests/tunnel.test.js
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `feat: viewer tunnel: the ring of lanes drawn as a tube from behind the runner`.

### Task 4: Mind panels as escaped HTML

**Files:**
- Create: `viewer/minds.js`
- Test: `viewer/tests/minds.test.js`

**Interfaces:**
- Consumes: frames and episodes of `docs/REPLAY_DATA.md`; the fly's `info`, Jev's and the LLM's `answers` as described in `docs/STEP_RECORD.md`.
- Produces: global `Minds`: `esc(value) -> string` (the only way log text reaches the page); `mind(episode, frame, windowMs) -> html` (the whole panel: senses grid, verdict, the player's own part, cost line, "What it was asked"); `statusLine(episode, state, lanes) -> html`; and the parts, exported for the tests: `bar`, `sensesGrid`, `verdict`, `spikeRaster`, `flyMind`, `jevMind`, `llmMind`, `cost`, `asked`. CSS class names used: `bar`, `fill`, `tick`, `centred`, `senses`, `tile`, `gap`, `me`, `verdict`, `muted`, `warn`, `eyes`, `signal`, `raster`, `spike`, `left`, `right`, `probs`, `picked`, `answer`, `saw` (styled in Task 5).

- [ ] **Step 1: Write the failing tests**

Create `viewer/tests/minds.test.js`:

````javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const Minds = require("../minds.js");

const depths = { stay: 6, left: 6, right: 0, jump: 3 };
const frame = (extra) => ({
  row: 3, lane: 6, landing: [4, 6], ahead: [[0, 1], [], [-3], [], [], []], chosen_action: "stay", executed_action: "stay",
  solver_depths: depths, gated: false, invalid: false, error: null, ground_truth: { gap_ahead: true, left_safe: true },
  answers: null, q: null, info: null, latency_ms: null, usage: null, cache_hit: false, ...extra,
});
const count = (html, needle) => html.split(needle).length - 1;

test("text from a log is escaped, never markup", () => {
  assert.equal(Minds.esc('<img src=x onerror="alert(1)">&\''), "&#60;img src=x onerror=&#34;alert(1)&#34;&#62;&#38;&#39;");
  const evil = "</pre><script>alert(1)</script>";
  const html = Minds.mind({ player: "llm", questions: [{ system: evil }] },
    frame({ answers: { text: evil, stop_reason: evil }, chosen_action: evil, error: evil, q: 0 }), 100);
  assert.equal(html.includes("<script>"), false);
  assert.equal(count(html, "&#60;script&#62;"), 5); // the move, the error, the answer, the stop reason, the question
});

test("the senses grid has a dark cell for every gap the player was shown", () => {
  const html = Minds.sensesGrid(frame());
  assert.equal(count(html, 'class="gap"'), 3);
  assert.equal(count(html, 'class="tile"'), 6 * 7 - 3);
});

test("the verdict rates the choice against the solver's depths", () => {
  assert.match(Minds.verdict(frame()), /as good as any move \(6 rows seen safe\)/);
  assert.match(Minds.verdict(frame({ chosen_action: "jump", executed_action: "jump" })),
    /solver preferred left or stay \(6 rows safe, this move 3\)/);
  assert.match(Minds.verdict(frame({ solver_depths: { stay: 0, left: 0, right: 0, jump: 0 } })), /no move was known to be safe/);
});

test("a fallback says why the game ran something else", () => {
  assert.match(Minds.verdict(frame({ chosen_action: "teleport", invalid: true })), /not a valid move, so the game ran stay/);
  assert.match(Minds.verdict(frame({ chosen_action: null, error: "APIError: 503" })), /no move.*error, so the game ran stay.*APIError: 503/s);
});

test("the fly's panel draws one line per spike and both thresholds", () => {
  const info = {
    left_hz: 250, right_hz: 0, total_spikes: 13207, turn_signal_hz: 30, jump_signal_hz: 210, jump_threshold_hz: 200,
    turn_threshold_hz: 0, spike_times_ms: { DNp01_left: [1, 50, 99], DNa01_right: [20] },
  };
  const html = Minds.mind({ player: "fly", questions: [] }, frame({ info }), 100);
  assert.equal(count(html, 'class="spike'), 4);
  assert.match(html, /left eye 250 Hz/);
  assert.match(html, /jumps above 200 Hz, our threshold/);
  assert.match(html, /13207 spikes in the whole brain in 100 ms/);
});

test("Jev's panel shows the four probabilities and scores the two questions against the truth", () => {
  const answers = {
    action: { choice: "left", confidence: 0.09, probabilities: { left: 0.33, stay: 0.21, right: 0.21, jump: 0.25 } },
    gap_ahead: { noul: 0.03 }, left_safe: { noul: 0.98 },
  };
  const html = Minds.jevMind(frame({ answers }));
  assert.match(html, /<tr class="picked"><th>left<\/th>.*33%/);
  assert.match(html, /confidence 9%/);
  assert.match(html, /3% yes<\/td><td class="warn">truth: yes/); // it said no gap, there was one
  assert.match(html, /98% yes<\/td><td class="muted">truth: yes/);
  assert.equal(Minds.jevMind(frame()), ""); // after a provider error there are no answers
});

test("the cost line tells a live answer from a cached one", () => {
  assert.match(Minds.cost(frame({ latency_ms: 717.9, usage: { input_tokens: 540, output_tokens: 9 } })), /answered in 718 ms, 540 tokens in, 9 out/);
  assert.match(Minds.cost(frame({ cache_hit: true, usage: { input_tokens: 540, output_tokens: 9 } })), /replayed from the cache/);
  assert.equal(Minds.cost(frame()), "");
});

test("the status line says how an episode ended", () => {
  const episode = { rows_survived: 23, death_cause: "dodged_into_gap" };
  assert.match(Minds.statusLine(episode, { status: "dead" }, 12), /Fell after 23 rows: stepped sideways into a gap/);
  assert.match(Minds.statusLine(episode, { status: "cut" }, 12), /Run stopped after 23 rows \(not a death\)/);
  assert.match(Minds.statusLine(episode, { status: "finished" }, 12), /Reached the finish line/);
  assert.equal(Minds.statusLine(episode, { status: "running", row: 4.5, lane: -0.6 }, 12), "row 4, lane 11");
});
````

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_viewer_js.py -q`
Expected: 1 failed; the output contains `Cannot find module '../minds.js'`.

- [ ] **Step 3: Write the module**

Create `viewer/minds.js`:

````javascript
// What each player had in mind for one decision, as HTML strings (pure, tested under node).
// Everything that comes from a log goes through esc(): an LLM's answer is text, never markup.
(function (root) {
  "use strict";

  const ACTIONS = ["left", "stay", "right", "jump"];
  const FLY_GROUPS = [
    ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
  ];
  const DEATHS = {
    ran_into_gap: "ran straight into a gap",
    jumped_into_gap: "jumped into a gap",
    dodged_into_gap: "stepped sideways into a gap",
  };

  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
  const percent = (p) => Math.round(p * 100) + "%";
  const hz = (value) => Math.round(value) + " Hz";

  // a horizontal bar, share 0..1, with an optional tick at `mark` (0..1)
  function bar(share, mark) {
    const width = Math.max(0, Math.min(1, share)) * 100;
    const tick = mark == null ? "" : '<i class="tick" style="left:' + Math.max(0, Math.min(1, mark)) * 100 + '%"></i>';
    return '<span class="bar"><i class="fill" style="width:' + width.toFixed(1) + '%"></i>' + tick + "</span>";
  }

  // The senses as the player got them: 6 rows ahead (far at the top), 3 lanes either side, gaps dark.
  function sensesGrid(frame) {
    let cells = "";
    for (let r = frame.ahead.length - 1; r >= 0; r--) {
      for (let off = -3; off <= 3; off++) {
        const gap = frame.ahead[r].includes(off);
        cells += '<rect x="' + (off + 3) * 12 + '" y="' + (frame.ahead.length - 1 - r) * 8 +
          '" width="11" height="7" class="' + (gap ? "gap" : "tile") + '"/>';
      }
    }
    const height = frame.ahead.length * 8;
    return '<svg class="senses" viewBox="0 0 84 ' + (height + 8) + '" role="img" aria-label="the six rows it was shown">' +
      cells + '<circle cx="41.5" cy="' + (height + 4) + '" r="3" class="me"/></svg>';
  }

  // chosen, executed and the reference solver's verdict on the same senses
  function verdict(frame) {
    const best = Math.max(...Object.values(frame.solver_depths));
    const safe = ACTIONS.filter((a) => frame.solver_depths[a] === best);
    const chosen = frame.chosen_action == null ? "no move" : esc(frame.chosen_action);
    let line = "<strong>" + chosen + "</strong>";
    if (frame.chosen_action !== frame.executed_action) {
      const why = frame.error != null ? "error" : frame.invalid ? "not a valid move" : frame.gated ? "held back" : "no move";
      line += ' <span class="warn">' + why + ", so the game ran " + esc(frame.executed_action) + "</span>";
    }
    const depth = frame.solver_depths[frame.chosen_action];
    const rating = best === 0 ? "no move was known to be safe"
      : depth === best ? "as good as any move (" + best + " rows seen safe)"
      : "solver preferred " + safe.join(" or ") + " (" + best + " rows safe, this move " + (depth || 0) + ")";
    return '<p class="verdict">' + line + '<br><span class="muted">' + rating + "</span></p>" +
      (frame.error != null ? '<p class="warn">' + esc(frame.error) + "</p>" : "");
  }

  function spikeRaster(info, windowMs) {
    const rowHeight = 9, width = 200;
    let rows = "";
    FLY_GROUPS.forEach(([group], g) => {
      ["left", "right"].forEach((side, s) => {
        const y = (g * 2 + s) * rowHeight + g * 4;
        const times = (info.spike_times_ms || {})[group + "_" + side] || [];
        rows += '<text x="0" y="' + (y + 7) + '">' + group + " " + side[0].toUpperCase() + "</text>";
        rows += times.map((t) => '<line class="spike ' + side + '" x1="' + (52 + (t / windowMs) * width).toFixed(1) +
          '" x2="' + (52 + (t / windowMs) * width).toFixed(1) + '" y1="' + y + '" y2="' + (y + rowHeight - 2) + '"/>').join("");
      });
    });
    const height = FLY_GROUPS.length * (2 * rowHeight + 4);
    return '<svg class="raster" viewBox="0 0 256 ' + height + '" role="img" aria-label="spikes of the read-out neurons over the ' +
      windowMs + ' ms window">' + rows + "</svg>";
  }

  function flyMind(frame, windowMs) {
    const info = frame.info;
    if (!info) return "";
    const turn = info.turn_signal_hz, limit = 100; // the turn bar spans -100 .. +100 Hz
    const turnShare = 0.5 + Math.max(-limit, Math.min(limit, turn)) / (2 * limit);
    return '<div class="eyes"><span>left eye ' + hz(info.left_hz) + bar(info.left_hz / 250) + "</span>" +
      "<span>right eye " + hz(info.right_hz) + bar(info.right_hz / 250) + "</span></div>" +
      '<p class="muted">Looming input to the LPLC2 and LC4 cells of each eye. The weighting of gaps is ours.</p>' +
      spikeRaster(info, windowMs) +
      '<p class="muted">' + info.total_spikes + " spikes in the whole brain in " + windowMs + " ms</p>" +
      '<div class="signal">turn signal ' + hz(turn) + ' <span class="muted">(right minus left steering)</span>' +
      '<span class="bar centred"><i class="fill" style="left:' + (Math.min(turnShare, 0.5) * 100).toFixed(1) + "%;width:" +
      (Math.abs(turnShare - 0.5) * 100).toFixed(1) + '%"></i><i class="tick" style="left:50%"></i></span></div>' +
      '<div class="signal">jump signal ' + hz(info.jump_signal_hz) + ' <span class="muted">(Giant Fiber; jumps above ' +
      hz(info.jump_threshold_hz) + ", our threshold)</span>" + bar(info.jump_signal_hz / 250, info.jump_threshold_hz / 250) + "</div>";
  }

  function jevMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    const action = answers.action || {};
    const probabilities = action.probabilities || {};
    let html = '<table class="probs">' + ACTIONS.map((a) => "<tr" + (a === action.choice ? ' class="picked"' : "") + "><th>" + a +
      "</th><td>" + bar(probabilities[a] || 0) + "</td><td>" + percent(probabilities[a] || 0) + "</td></tr>").join("") + "</table>";
    if (typeof action.confidence === "number") html += '<p class="muted">confidence ' + percent(action.confidence) + "</p>";
    const nouls = [["gap_ahead", "Gap straight ahead?"], ["left_safe", "Left lane safe?"]];
    html += '<table class="probs">' + nouls.filter(([key]) => answers[key] && typeof answers[key].noul === "number").map(([key, label]) => {
      const truth = (frame.ground_truth || {})[key];
      const right = (answers[key].noul >= 0.5) === truth;
      return "<tr><th>" + label + "</th><td>" + bar(answers[key].noul) + "</td><td>" + percent(answers[key].noul) +
        ' yes</td><td class="' + (right ? "muted" : "warn") + '">truth: ' + (truth ? "yes" : "no") + "</td></tr>";
    }).join("") + "</table>";
    return html + '<p class="muted">The two yes/no questions are asked alongside the move and never influence it.</p>';
  }

  function llmMind(frame) {
    const answers = frame.answers;
    if (!answers) return "";
    return '<pre class="answer">' + esc(answers.text == null ? "" : answers.text) + "</pre>" +
      (answers.stop_reason === "end_turn" ? "" : '<p class="warn">stopped: ' + esc(answers.stop_reason) + "</p>");
  }

  function cost(frame) {
    if (frame.cache_hit) return '<p class="muted">answer replayed from the cache</p>';
    if (frame.latency_ms == null) return "";
    const usage = frame.usage || {};
    return '<p class="muted">answered in ' + Math.round(frame.latency_ms) + " ms, " + (usage.input_tokens || 0) + " tokens in, " +
      (usage.output_tokens || 0) + " out</p>";
  }

  function asked(episode, frame) {
    if (frame.q == null || !episode.questions[frame.q]) return "";
    return "<details><summary>What it was asked</summary><pre>" + esc(JSON.stringify(episode.questions[frame.q], null, 2)) +
      "</pre></details>";
  }

  // the whole panel for one decision; windowMs is the fly's simulated window from the run's meta
  function mind(episode, frame, windowMs) {
    const body = episode.player === "fly" ? flyMind(frame, windowMs || 100)
      : episode.player === "jev" ? jevMind(frame)
      : episode.player === "llm" ? llmMind(frame) : "";
    return '<div class="saw">' + sensesGrid(frame) + verdict(frame) + "</div>" + body + cost(frame) + asked(episode, frame);
  }

  // one line under the tunnel: where the runner is, or how the episode ended
  function statusLine(episode, state, lanes) {
    const rows = episode.rows_survived;
    if (state.status === "dead") return '<span class="warn">Fell after ' + rows + " rows: " + (DEATHS[episode.death_cause] || "fell") + "</span>";
    if (state.status === "finished") return "Reached the finish line, " + rows + " rows";
    if (state.status === "cut") return '<span class="warn">Run stopped after ' + rows + " rows (not a death)</span>";
    return "row " + Math.floor(state.row) + ", lane " + (((Math.round(state.lane) % lanes) + lanes) % lanes);
  }

  const api = { esc, bar, sensesGrid, verdict, spikeRaster, flyMind, jevMind, llmMind, cost, asked, mind, statusLine };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Minds = api;
})(typeof window !== "undefined" ? window : globalThis);
````

- [ ] **Step 4: Run the tests**

Run: `node --test viewer/tests/*.test.js` — Expected: `pass 19`, `fail 0`.
Run: `uv run pytest -q` — Expected: 228 passed, 9 deselected.

- [ ] **Step 5: Commit**

```bash
git add viewer/minds.js viewer/tests/minds.test.js
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `feat: viewer mind panels: spikes, probabilities and answers as escaped HTML`.

### Task 5: The page, and `bakeoff view` bundling it into one file

**Files:**
- Create: `bakeoff/view.py`, `viewer/index.html`, `viewer/viewer.css`, `viewer/app.js`
- Modify: `bakeoff/__main__.py`, `.gitignore`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `bakeoff.replay.build_replay` (Task 1); globals `Timeline` (Task 2), `Tunnel` (Task 3), `Minds` (Task 4); the replay object of `docs/REPLAY_DATA.md`.
- Produces: `bakeoff.view.VIEWER_DIR`, `DATA_SLOT`, `embed_json(value) -> str`, `render_html(replay, viewer_dir=VIEWER_DIR) -> str` (raises `ValueError` when `index.html` lacks the data slot); CLI `python -m bakeoff view RUN_DIR [RUN_DIR ...] [--output replay.html]`, exit 0 and a line `replay: <file> (<n> episodes, <size> MB)`, exit 2 with the message on stderr for a missing directory, a duplicate episode or no step records. `index.html` must keep `<script type="application/json" id="replay-data">null</script>` exactly once and reference its files only as `<link rel="stylesheet" href="NAME">` and `<script src="NAME"></script>`: those are the patterns `render_html` inlines.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_view.py`:

````python
import json
import re

import pytest

from bakeoff.__main__ import main
from bakeoff.view import DATA_SLOT, VIEWER_DIR, embed_json, render_html

DATA = re.compile(r'<script type="application/json" id="replay-data">(.*?)</script>', re.S)


def test_embedded_json_cannot_close_its_script_element():
    value = {"text": "</script><script>alert(1)</script><!--", "n": 1}
    embedded = embed_json(value)
    assert "<" not in embedded
    assert json.loads(embedded) == value


def test_render_inlines_every_file_and_the_data():
    replay = {"replay_version": 1, "episodes": [], "note": "</script>"}
    page = render_html(replay)
    assert "<link" not in page and "<script src" not in page  # one file: nothing left to fetch
    for name in ("timeline.js", "tunnel.js", "minds.js", "app.js", "viewer.css"):
        assert (VIEWER_DIR / name).read_text() in page
    (data,) = DATA.findall(page)
    assert json.loads(data) == replay
    assert DATA_SLOT not in page


def test_the_page_makes_no_network_request():
    page = render_html({"episodes": []})
    assert not re.search(r"""(src|href)=["']?(https?:)?//""", page)
    assert "@import" not in page and "url(" not in page


def test_a_backslash_in_a_viewer_file_survives(tmp_path):
    (tmp_path / "index.html").write_text('<link rel="stylesheet" href="a.css"><script src="a.js"></script>' + DATA_SLOT)
    (tmp_path / "a.css").write_text('i::before { content: "\\1F41D"; }')
    (tmp_path / "a.js").write_text('const s = "\\n\\1";')
    page = render_html({}, tmp_path)
    assert 'content: "\\1F41D"' in page and 'const s = "\\n\\1";' in page


def test_a_page_without_the_data_slot_is_an_error(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    with pytest.raises(ValueError, match="replay data slot"):
        render_html({}, tmp_path)


def test_view_writes_one_html_file_with_the_runs_in_it(tmp_path, capsys):
    assert main(["run", "--players", "solver,random", "--seeds", "2", "--max-rows", "30", "--out", str(tmp_path)]) == 0
    (run_dir,) = tmp_path.iterdir()
    output = tmp_path / "out.html"
    capsys.readouterr()
    assert main(["view", str(run_dir), "--output", str(output)]) == 0
    assert f"replay: {output} (4 episodes" in capsys.readouterr().out
    (data,) = DATA.findall(output.read_text())
    replay = json.loads(data)
    assert replay["players"] == ["solver", "random"] and replay["seeds"] == [0, 1]
    assert replay["runs"][0]["run_id"] == run_dir.name


def test_view_usage_errors(tmp_path, capsys):
    assert main(["view", str(tmp_path / "nope"), "--output", str(tmp_path / "out.html")]) == 2
    assert "no such run directory" in capsys.readouterr().err
    (tmp_path / "empty").mkdir()
    assert main(["view", str(tmp_path / "empty"), "--output", str(tmp_path / "out.html")]) == 2
    assert "no step records" in capsys.readouterr().err
    assert main(["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path / "runs")]) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert main(["view", str(run_dir), str(run_dir), "--output", str(tmp_path / "out.html")]) == 2
    assert "solver on seed 0 is in both" in capsys.readouterr().err
    assert not (tmp_path / "out.html").exists()
````

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_view.py -q`
Expected: 1 error, `ModuleNotFoundError: No module named 'bakeoff.view'`

- [ ] **Step 3: Write the bundler**

Create `bakeoff/view.py`:

````python
"""Replay object + viewer/ -> one self-contained HTML file: no server, no network, opens from disk."""

from __future__ import annotations

import json
import re
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
DATA_SLOT = '<script type="application/json" id="replay-data">null</script>'
_STYLESHEET = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
_SCRIPT = re.compile(r'<script src="([^"]+)"></script>')


def embed_json(value) -> str:
    """JSON that is safe inside a <script> element. A logged answer may contain `</script>` or
    `<!--`; with every `<` written as \\u003c nothing in the data can end the element."""
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR) -> str:
    viewer_dir = Path(viewer_dir)
    page = (viewer_dir / "index.html").read_text()
    if page.count(DATA_SLOT) != 1:
        raise ValueError(f"{viewer_dir / 'index.html'} must contain the replay data slot exactly once")
    # lambdas, so that a backslash in a file is never read as a regex group reference
    page = _STYLESHEET.sub(lambda m: "<style>\n" + (viewer_dir / m.group(1)).read_text() + "</style>", page)
    page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text() + "</script>", page)
    return page.replace(DATA_SLOT, '<script type="application/json" id="replay-data">' + embed_json(replay) + "</script>")
````

- [ ] **Step 4: Write the page**

The copy on this page is part of the honesty rule (what is the fly's, what is ours, the known weaknesses, the Jev and LLM asymmetry). Copy it exactly; do not shorten or rephrase it.

Create `viewer/index.html`:

````html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tunnel Run replay</title>
<link rel="stylesheet" href="viewer.css">
</head>
<body>
<header>
  <h1>Tunnel Run</h1>
  <p id="runs" class="muted"></p>
</header>

<main id="app" hidden>
  <section aria-label="Tracks">
    <h2>Rows survived on each track</h2>
    <p class="muted">Pick a track to watch it. Pick a player to show or hide its column.</p>
    <div class="scroll"><table id="matrix"></table></div>
  </section>

  <section aria-label="Replay">
    <div id="stage"></div>
    <div id="transport">
      <button id="play" type="button">Play</button>
      <button id="back" type="button" aria-label="Back one row">&#9664;</button>
      <button id="forward" type="button" aria-label="Forward one row">&#9654;</button>
      <label>Speed
        <select id="speed">
          <option value="1">1 row a second</option>
          <option value="3" selected>3 rows a second</option>
          <option value="8">8 rows a second</option>
          <option value="20">20 rows a second</option>
        </select>
      </label>
      <input id="scrub" type="range" min="0" max="1" step="0.01" value="0" aria-label="Position on the track">
      <output id="clock"></output>
    </div>
    <p class="muted">Every player gets the same track and sees the same six rows ahead, three lanes either side
      (the brighter tiles). Players are lined up by row: a jump covers two rows, so it takes two ticks.</p>
  </section>

  <section aria-label="Scoreboard">
    <h2>Scoreboard</h2>
    <p id="fairness" class="warn" hidden>These players did not all play the same tracks, so their averages are not
      a fair comparison. Compare them track by track in the table at the top.</p>
    <div class="scroll"><table id="scoreboard"></table></div>
    <p class="muted">Same columns as <code>python -m bakeoff report</code>. Only complete runs count; a run that was
      stopped is listed as incomplete, not as a death.</p>
  </section>

  <section id="honesty" aria-label="What is ours and what is the fly's">
    <h2>What is the fly's and what is ours</h2>
    <p>The fly is the published whole-brain model of the adult <i>Drosophila</i> connectome (Shiu et al., Nature 2024;
      FlyWire v783, 138,639 neurons), untrained, with default parameters. Gaps stimulate the looming detectors of
      each eye (LPLC2 and LC4); the steering neurons DNa01 and DNb01 are read as left and right, the Giant Fiber
      (DNp01) as jump. The wiring is the fly's. These numbers are ours:</p>
    <ul id="ours"></ul>
    <p>Known weaknesses:</p>
    <ul>
      <li>The fly does not plan. It flees gaps by reflex and may dodge into another gap.</li>
      <li>Its input is crude: a whole eye is stimulated at one rate. Stimulating part of the visual field was not tested.</li>
      <li>On equal input to both eyes its deciding read-out leans right (0 to +20 Hz, never negative; the model's
        left eye has 162 looming cells, its right eye 152). With our turn threshold of 0 Hz that lean decides moves:
        a gap straight ahead that does not trigger a jump usually becomes a step to the right. The lean is the fly's,
        the threshold that exposes it is ours.</li>
      <li>The wiring also has a mild left bias in DNa02, which is logged but never decides.</li>
      <li>The model has no spontaneous activity and no memory between decisions; trial-to-trial spread comes only
        from input noise.</li>
      <li>That DNa01, DNa02 and DNb01 turn the fly towards their own side comes from published steering studies,
        not from anything verified in this project.</li>
      <li>Giant Fiber rates of 100 to 200 Hz are not realistic (a real one fires about once per escape); the rate
        is used as a graded signal.</li>
    </ul>
    <p>Jev and the LLM are told the same rules in the same words. Jev's request also carries two yes/no questions
      for calibration; TypeSafe runs the questions of one request in parallel and they cannot see one another's
      answers, so they are not a scaffold for its move. The LLM answers one question.</p>
  </section>
</main>

<p id="empty">This page has no replay in it. Make one with
  <code>uv run python -m bakeoff view runs/&lt;run_id&gt;</code> and open the file it writes.</p>

<script type="application/json" id="replay-data">null</script>
<script src="timeline.js"></script>
<script src="tunnel.js"></script>
<script src="minds.js"></script>
<script src="app.js"></script>
</body>
</html>
````

Create `viewer/viewer.css`:

````css
:root {
  --paper: #edf0ec;
  --grid: #dde3dd;
  --panel: #f9faf7;
  --ink: #17232b;
  --muted: #56666f;
  --rule: #c4cec8;
  --warn: #b3261e;
  --space: #0e1822;
  --player: #606c74;
}

* { box-sizing: border-box; }

body {
  margin: 0 auto;
  max-width: 1240px;
  padding: 24px 20px 64px;
  color: var(--ink);
  /* chart-recorder paper: the page is a lab record, the tunnels are the windows in it */
  background: var(--paper) repeating-linear-gradient(0deg, transparent 0 23px, var(--grid) 23px 24px);
  font: 15px/1.6 "Avenir Next", Avenir, "Segoe UI", system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}

h1 { margin: 0; font-size: 2.4rem; line-height: 1.2; font-weight: 600; letter-spacing: -0.01em; }
h2 { margin: 48px 0 0; font-size: 1.25rem; line-height: 24px; font-weight: 600; }
h3 { margin: 0; font-size: 1.25rem; line-height: 24px; font-weight: 600; color: var(--player); }
p, ul { margin: 0 0 12px; max-width: 76ch; }
section > p { margin-top: 0; }
.muted { color: var(--muted); }
.warn { color: var(--warn); }
code, pre { font: 13px/1.5 ui-monospace, Menlo, Consolas, monospace; }

button, select, input { font: inherit; color: inherit; }
button, select {
  padding: 4px 12px; border: 1px solid var(--ink); border-radius: 3px; background: var(--panel); cursor: pointer;
}
:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

.scroll { overflow-x: auto; background: var(--panel); border: 1px solid var(--rule); }
table { border-collapse: collapse; width: 100%; white-space: nowrap; }
th, td { padding: 3px 10px; text-align: right; font-weight: 400; border-bottom: 1px solid var(--grid); }
tbody th, thead th:first-child { text-align: left; }
thead th { color: var(--muted); border-bottom: 1px solid var(--rule); }

#matrix button { border: 0; padding: 0 4px; background: none; }
#matrix thead button[aria-current] { background: var(--ink); color: var(--panel); border-radius: 2px; }
#matrix td.current { background: var(--grid); }
#matrix tbody button { color: var(--player); font-weight: 600; }
#matrix tbody button::before { content: "● "; }
#matrix tbody button[aria-pressed="false"] { color: var(--muted); font-weight: 400; }
#matrix tbody button[aria-pressed="false"]::before { content: "○ "; }

#transport {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin: 0 0 12px;
  /* like a media player: the controls stay at the bottom of the window while the columns scroll */
  position: sticky; bottom: 0; z-index: 1; padding: 8px 0; background: var(--paper); border-top: 1px solid var(--rule);
}
#play { min-width: 5.5em; background: var(--ink); color: var(--panel); }
#scrub { flex: 1 1 240px; accent-color: var(--ink); }
#clock { min-width: 8em; text-align: right; }

#stage { margin-top: 48px; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 12px; }
#stage article { min-width: 0; padding: 12px; background: var(--panel); border: 1px solid var(--rule); border-top: 4px solid var(--player); }
#stage canvas { display: block; width: 100%; max-width: 360px; aspect-ratio: 1; margin: 8px auto; border-radius: 50%; background: var(--space); }
.status { min-height: 24px; text-align: center; font-weight: 600; }

.saw { display: flex; gap: 12px; align-items: flex-start; }
.senses { flex: 0 0 96px; }
.senses .tile { fill: var(--rule); }
.senses .gap { fill: var(--space); }
.senses .me { fill: var(--player); }
.verdict { margin: 0 0 12px; }
.verdict strong { font-size: 1.25rem; color: var(--player); }

.bar { position: relative; display: block; height: 8px; min-width: 80px; background: var(--grid); }
.bar .fill { position: absolute; top: 0; bottom: 0; left: 0; background: var(--player); }
.bar .tick { position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px; background: var(--ink); }
.eyes { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.signal { margin-bottom: 12px; }
.raster { display: block; width: 100%; margin: 4px 0; }
.raster text { font-size: 7px; fill: var(--muted); }
.raster .spike { stroke: var(--player); stroke-width: 1; }
.probs { margin-bottom: 12px; }
.probs th, .probs td { padding: 1px 8px 1px 0; border: 0; }
.probs th { text-align: left; color: var(--muted); }
.probs td:nth-child(2) { width: 50%; }
.probs .picked th, .probs .picked td { color: var(--ink); font-weight: 600; }
.answer { margin: 0 0 12px; padding: 8px; white-space: pre-wrap; overflow-wrap: anywhere; background: var(--grid); }
details pre { max-height: 260px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
summary { cursor: pointer; color: var(--muted); }

#honesty li { margin-bottom: 6px; max-width: 76ch; }
#empty { margin-top: 48px; }
````

Create `viewer/app.js`:

````javascript
// The page: track table, transport, one column per player, scoreboard. Glue only; the parts with
// rules in them are timeline.js, tunnel.js and minds.js, which have tests.
(function () {
  "use strict";

  const replay = JSON.parse(document.getElementById("replay-data").textContent);
  if (!replay) return;
  document.getElementById("empty").hidden = true;
  document.getElementById("app").hidden = false;

  const $ = (id) => document.getElementById(id);
  const esc = Minds.esc;
  const CONTESTANTS = ["fly", "jev", "llm"];
  const COLOURS = { fly: [176, 116, 0], jev: [11, 134, 128], llm: [94, 82, 204] };
  const BASELINE = [96, 108, 116];
  const ABOUT = {
    fly: "Fruit fly connectome, untrained",
    jev: "Jev, TypeSafe System One",
    llm: "Large language model",
    random: "Random moves, the floor",
    always_jump: "Always jumps, the second floor",
    solver: "Scripted solver, the reference (not a contestant)",
  };
  const TAIL = 1.5; // rows of time after the last landing, so the last fall is seen
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const runOf = (episode) => replay.runs.find((run) => run.run_id === episode.run_id) || {};
  const episodeOf = (player, seed) => replay.episodes.find((e) => e.player === player && e.seed === seed);
  const colourOf = (player) => COLOURS[player] || BASELINE;
  const blend = (a, b, share) => a.map((c, i) => Math.round(c + (b[i] - c) * share));

  const contestants = replay.players.filter((p) => CONTESTANTS.includes(p));
  const view = {
    seed: replay.seeds[0],
    shown: new Set(contestants.length ? contestants : replay.players),
    t: 0, playing: false, speed: 3, columns: [], duration: 1, lastRow: 1,
  };

  // ---- header -------------------------------------------------------------------------------
  $("runs").innerHTML = "Replay of " + replay.runs.map((run) => {
    const sha = run.git_sha ? run.git_sha.slice(0, 7) + (run.git_dirty ? ", uncommitted changes" : "") : "unknown commit";
    const status = run.status === "completed" ? "completed" : '<span class="warn">' + esc(run.status || "status unknown") + "</span>";
    return "run " + esc(run.run_id) + " (" + status + ", " + esc(sha) + ")";
  }).join("; ");

  // ---- track table --------------------------------------------------------------------------
  function renderMatrix() {
    let html = "<thead><tr><th>track</th>" + replay.seeds.map((seed) =>
      '<th><button type="button" data-seed="' + seed + '"' + (seed === view.seed ? ' aria-current="true"' : "") + ">" + seed +
      "</button></th>").join("") + "</tr></thead><tbody>";
    for (const player of replay.players) {
      html += '<tr style="--player:rgb(' + colourOf(player).join(",") + ')"><th><button type="button" data-player="' + esc(player) +
        '" aria-pressed="' + view.shown.has(player) + '">' + esc(player) + "</button></th>";
      for (const seed of replay.seeds) {
        const episode = episodeOf(player, seed);
        const mark = !episode ? "" : !episode.complete ? " …" : episode.finished ? " ✓" : "";
        html += "<td" + (seed === view.seed ? ' class="current"' : "") + ">" + (episode ? episode.rows_survived + mark : "") + "</td>";
      }
      html += "</tr>";
    }
    $("matrix").innerHTML = html + "</tbody>";
  }

  $("matrix").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.seed != null) {
      view.seed = Number(button.dataset.seed);
      view.t = 0;
      setPlaying(false);
    } else if (view.shown.has(button.dataset.player)) view.shown.delete(button.dataset.player);
    else view.shown.add(button.dataset.player);
    renderMatrix();
    renderStage();
  });

  // ---- stage --------------------------------------------------------------------------------
  function renderStage() {
    const track = replay.tracks[String(view.seed)];
    const episodes = replay.episodes.filter((e) => e.seed === view.seed && view.shown.has(e.player));
    const stage = $("stage");
    stage.innerHTML = "";
    view.columns = [];
    if (!track || !episodes.length) {
      stage.innerHTML = '<p class="muted">None of the players shown ran track ' + view.seed + ". Pick a player above to show it.</p>";
    }
    for (const episode of episodes) {
      const run = runOf(episode);
      const colour = colourOf(episode.player);
      const model = (run.models || {})[episode.player];
      const column = document.createElement("article");
      column.style.setProperty("--player", "rgb(" + colour.join(",") + ")");
      column.innerHTML = "<h3>" + esc(episode.player) + '</h3><p class="muted">' + esc(ABOUT[episode.player] || "") +
        (model ? " (" + esc(model) + ")" : "") + '</p><canvas></canvas><p class="status"></p><div class="mind"></div>';
      stage.appendChild(column);
      const canvas = column.querySelector("canvas");
      const size = 360, ratio = window.devicePixelRatio || 1;
      canvas.width = canvas.height = size * ratio;
      const ctx = canvas.getContext("2d");
      ctx.scale(ratio, ratio);
      const game = run.game || {};
      view.columns.push({
        episode, track, ctx, size, index: -1,
        status: column.querySelector(".status"), mind: column.querySelector(".mind"),
        lookahead: game.lookahead || 6, window: game.window || 3, windowMs: (run.fly || {}).window_ms || 100,
        colours: { space: [14, 24, 34], floor: [104, 120, 130], finish: [236, 224, 180],
                   seen: blend([214, 224, 226], colour, 0.3), runner: blend(colour, [255, 255, 255], 0.35) },
      });
    }
    view.duration = Math.max(1, ...episodes.map(Timeline.endRow)) + TAIL;
    // a jump over the finish line lands one row past it; the clock stops at the line
    view.lastRow = Math.min(view.duration - TAIL, track ? track.max_rows : 1);
    $("scrub").max = view.duration;
    draw();
  }

  function draw() {
    const t = still ? Math.floor(view.t) : view.t;
    for (const column of view.columns) {
      const { episode, track } = column;
      const state = Timeline.stateAt(episode, t, track.lanes);
      const seen = { row: state.frame.row, lane: state.frame.lane, lookahead: column.lookahead, window: column.window };
      Tunnel.draw(column.ctx, column.size, track, state, seen, episode.max_rows || track.max_rows, column.colours);
      const status = Minds.statusLine(episode, state, track.lanes);
      if (column.status.innerHTML !== status) column.status.innerHTML = status;
      if (state.index !== column.index) {
        const open = !!(column.mind.querySelector("details") || {}).open;
        column.mind.innerHTML = Minds.mind(episode, state.frame, column.windowMs);
        if (open && column.mind.querySelector("details")) column.mind.querySelector("details").open = true;
        column.index = state.index;
      }
    }
    $("scrub").value = view.t;
    $("clock").textContent = "row " + Math.min(Math.floor(view.t), view.lastRow) + " of " + view.lastRow;
  }

  // ---- transport ----------------------------------------------------------------------------
  let lastTick = null;
  function tick(now) {
    if (!view.playing) return;
    view.t = Math.min(view.duration, view.t + ((now - lastTick) / 1000) * view.speed);
    lastTick = now;
    draw();
    if (view.t >= view.duration) setPlaying(false);
    else requestAnimationFrame(tick);
  }

  function setPlaying(playing) {
    if (playing && view.t >= view.duration) view.t = 0;
    view.playing = playing;
    $("play").textContent = playing ? "Pause" : "Play";
    if (playing) {
      lastTick = performance.now();
      requestAnimationFrame(tick);
    }
  }

  function stepRows(rows) {
    setPlaying(false);
    view.t = Math.max(0, Math.min(view.duration, Math.round(view.t) + rows));
    draw();
  }

  $("play").addEventListener("click", () => setPlaying(!view.playing));
  $("back").addEventListener("click", () => stepRows(-1));
  $("forward").addEventListener("click", () => stepRows(1));
  $("speed").addEventListener("change", (event) => { view.speed = Number(event.target.value); });
  $("scrub").addEventListener("input", (event) => { view.t = Number(event.target.value); draw(); });
  document.addEventListener("keydown", (event) => {
    if (event.target.closest("button, select, input, summary")) return;
    if (event.key === " ") { event.preventDefault(); setPlaying(!view.playing); }
    if (event.key === "ArrowLeft") stepRows(-1);
    if (event.key === "ArrowRight") stepRows(1);
  });

  // ---- scoreboard ---------------------------------------------------------------------------
  function cell(value) {
    if (value == null) return "–";
    if (typeof value !== "number" || Number.isInteger(value)) return esc(value);
    return Math.abs(value) > 0 && Math.abs(value) < 0.1 ? value.toFixed(4) : value.toFixed(2);
  }
  const board = replay.scoreboard;
  $("scoreboard").innerHTML = "<thead><tr>" + board.columns.map((c) => "<th>" + esc(c.replace(/_/g, " ")) + "</th>").join("") +
    "</tr></thead><tbody>" + board.rows.map((row) => "<tr>" + board.columns.map((c) =>
      (c === "player" ? "<th>" + cell(row[c]) + "</th>" : "<td>" + cell(row[c]) + "</td>")).join("") + "</tr>").join("") + "</tbody>";
  $("fairness").hidden = board.same_seeds;

  // ---- what is ours -------------------------------------------------------------------------
  const flyRun = replay.runs.find((run) => run.fly && (run.players || []).includes("fly")) || replay.runs.find((run) => run.fly);
  const looming = flyRun && flyRun.game && flyRun.game.looming;
  $("ours").innerHTML = !flyRun || !looming || looming.falloff == null
    ? "<li>The runs in this replay did not record the fly's constants.</li>"
    : "<li>Each gap the fly can see adds " + cell(looming.gain_hz) + " / row<sup>" + cell(looming.falloff) + "</sup> Hz to the eye on its side " +
      "(a gap in the runner's own lane: both eyes), capped at " + cell(looming.max_hz) + " Hz and rounded to " + cell(looming.step_hz) +
      " Hz steps. A gap one row away counts " + Math.pow(2, looming.falloff) + " times as much as one two rows away.</li>" +
      "<li>A turn signal beyond " + cell(flyRun.fly.turn_threshold_hz) + " Hz turns; a Giant Fiber mean above " +
      cell(flyRun.fly.jump_threshold_hz) + " Hz jumps, and a jump wins over a turn. Each decision simulates " +
      cell(flyRun.fly.window_ms) + " ms from a clean brain.</li>" +
      (flyRun.fly.provisional
        ? '<li class="warn">These values were provisional when this run was made: not yet calibrated.</li>'
        : "<li>All four numbers were chosen once, by a rule fixed beforehand, on practice tracks 1000 to 1199 that are not in " +
          "the tournament, then frozen (calibration/REPORT.md).</li>");

  renderMatrix();
  renderStage();
})();
````

- [ ] **Step 5: Add the `view` subcommand**

Edit `bakeoff/__main__.py` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -1,3 +1,3 @@
-"""uv run python -m bakeoff run|report"""
+"""uv run python -m bakeoff run|report|view"""
 
 from __future__ import annotations
@@ -6,10 +6,13 @@ import argparse
 import sys
 import time
+from pathlib import Path
 
 from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
 from bakeoff.game.track import MAX_ROWS
 from bakeoff.players import PAID, REGISTRY, make_player
+from bakeoff.replay import build_replay
 from bakeoff.report import format_table, load_meta, load_steps, summarize
 from bakeoff.runner import RunAborted, Runner
+from bakeoff.view import render_html
 
 # tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
@@ -35,4 +38,7 @@ def _parser() -> argparse.ArgumentParser:
     report = sub.add_parser("report", help="summarize an existing run directory")
     report.add_argument("run_dir")
+    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
+    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
+    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
     return parser
 
@@ -53,4 +59,17 @@ def main(argv: list[str] | None = None) -> int:
             return 2
         return 0
+    if args.command == "view":
+        try:
+            replay = build_replay(args.run_dirs)
+        except (FileNotFoundError, ValueError) as e:
+            print(e, file=sys.stderr)
+            return 2
+        if not replay["episodes"]:
+            print("no step records in " + ", ".join(args.run_dirs), file=sys.stderr)
+            return 2
+        output = Path(args.output)
+        output.write_text(render_html(replay))
+        print(f"replay: {output} ({len(replay['episodes'])} episodes, {output.stat().st_size / 1e6:.1f} MB)")
+        return 0
     cache = DiskCache(args.cache)
     try:
````

Edit `.gitignore` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -10,2 +10,4 @@ runs/
 data/
 .superpowers/
+/replay*.html
+.playwright-mcp/
````

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_view.py -q` — Expected: 7 passed.
Run: `uv run pytest -q` — Expected: 235 passed, 9 deselected.

- [ ] **Step 7: Build a replay from free players and check the file**

```bash
out=$(mktemp -d)
uv run python -m bakeoff run --players solver,random,always_jump --seeds 3 --max-rows 60 --out "$out/runs"
uv run python -m bakeoff view "$out"/runs/* --output "$out/replay.html"
```

Expected: the last command prints `replay: <that directory>/replay.html (9 episodes, 0.2 MB)`. Nothing is written inside the repository. If you can open a browser, open the file: three columns, Play moves the runners, no console errors. If you cannot, say so in your report; the controller checks it in Task 7.

- [ ] **Step 8: Commit**

```bash
git add bakeoff/view.py bakeoff/__main__.py viewer/index.html viewer/viewer.css viewer/app.js tests/test_view.py .gitignore
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `feat: view command: the replay page bundled into one offline HTML file`.

### Task 6: Documentation

**Files:**
- Modify: `README.md`, `CLAUDE.md`, `docs/DECISIONS.md`, `docs/superpowers/specs/2026-09-19-tunnel-run-design.md`

**Interfaces:**
- Consumes: everything above. Produces: nothing code reads.

- [ ] **Step 1: README**

Edit `README.md` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -13,5 +13,5 @@ replays with each player's "mind" shown next to the game (Jev's probabilities, t
 answer, the fly's neurons firing) and a scoreboard across games.
 
-Status: phase 3 of 5 built. The untrained fly plays: on seeds 0–19 it survives 127 rows
+Status: phase 4 of 5 built. The untrained fly plays: on seeds 0–19 it survives 127 rows
 on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`). Jev and the LLM
 (Claude Haiku 4.5) play behind a response cache and a hard request cap; first measured costs
@@ -22,4 +22,5 @@ are in `docs/COSTS.md`.
     uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
     uv run python -m bakeoff report runs/<run_id>
+    uv run python -m bakeoff view runs/<run_id> [runs/<other_run_id> ...]   # writes replay.html
 
 Paid players (`jev`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
@@ -36,3 +37,11 @@ ends there, so later players in the list do not play: put free players first, or
 alone.
 
+`view` writes one self-contained HTML file (no server, no network): the players of a track side by
+side in the tunnel, each with what it had in mind (the fly's spikes and read-out signals, Jev's
+probabilities, the LLM's answer), a table of rows survived per track, the scoreboard, and what in
+the fly's set-up is ours rather than the fly's. Several run directories are merged, since the fly and
+the paid players usually run separately; one (player, seed) may appear only once. Viewing costs
+nothing: it reads logs only. The viewer's JavaScript has its own tests, which `uv run pytest` runs
+through `node --test` (skipped when node is not installed).
+
 See `docs/DECISIONS.md` for what has been decided and what comes next.
````

- [ ] **Step 2: CLAUDE.md**

Edit `CLAUDE.md` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -19,5 +19,8 @@ scoreboard in `calibration/RESULTS.md`. Phase 3 built (plan:
 `docs/superpowers/plans/2026-09-20-phase3-paid-players.md`): `jev` and `llm` players behind
 `bakeoff/clients/core.py` (disk cache, hard cap per paid player, no SDK retries). First costs in
-`docs/COSTS.md`. Next: write the phase 4 plan (replay viewer). Each phase gets its own plan.
+`docs/COSTS.md`. Phase 4 built (plan: `docs/superpowers/plans/2026-09-20-phase4-replay-viewer.md`):
+`bakeoff/replay.py` merges run directories into one replay object (`docs/REPLAY_DATA.md`) and
+`python -m bakeoff view` embeds it with `viewer/` in one offline HTML file. Next: write the phase 5
+plan (tournament run and write-up). Each phase gets its own plan.
 
 ## How we work here
@@ -40,4 +43,8 @@ scoreboard in `calibration/RESULTS.md`. Phase 3 built (plan:
 - `uv run pytest` runs the fast tests only. `uv run pytest -m slow` builds the real fly brain (about 1 GB,
   one minute); never run two fly processes at once.
+- The viewer is plain JavaScript with no build step and no npm packages. Rules of the game stay in
+  Python (`bakeoff/replay.py`); the pure JavaScript (`timeline.js`, `tunnel.js`, `minds.js`) is tested by
+  `viewer/tests/*.test.js`, which `uv run pytest` runs through `node --test`. Text from a log is always
+  escaped (`Minds.esc`) and the page must never load anything from the network.
 - Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
   raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
````

- [ ] **Step 3: Decisions**

Edit `docs/DECISIONS.md` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -50,4 +50,14 @@
     gap; the prompts stay as written, because tuning them on a track is what the seed rule forbids.
 
+13. **Replay viewer (phase 4):** `python -m bakeoff view <run_dir>...` writes one self-contained HTML
+    file, so a replay opens from disk, works offline and can be sent to someone. Python
+    (`bakeoff/replay.py`) merges the run directories and applies the rules of the game (landing
+    tiles, complete or cut off, scoreboard); the JavaScript only draws (`docs/REPLAY_DATA.md`). Players
+    are lined up by row, not by decision, so every column shows the same stretch of track and a jump
+    takes two ticks. The tiles a player was shown are drawn brighter. The same (player, seed) in two
+    run directories is an error. When the players did not all play the same seeds, the scoreboard
+    says its means are not a fair comparison. The fly's four numbers, the looming formula and the
+    known weaknesses are on the page, with what is ours labelled as ours.
+
 ## Open
 
@@ -65,5 +75,6 @@
 ## Next step
 
-Phases 1 to 3 are built and the first costs are measured. Write the phase 4 plan (replay viewer).
+Phases 1 to 4 are built. Write the phase 5 plan (tournament run and write-up); it starts by settling
+the first open item above (which seeds).
 
 ## Prior art to reuse
````

- [ ] **Step 4: The spec's Architecture table**

Edit `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (apply these hunks; lines starting with `-` go, lines starting with `+` come in):

````diff
@@ -163,6 +163,8 @@ Python package `bakeoff/` in this repo, managed with `uv`, tests with `pytest`.
 | `bakeoff/runner.py` | Players × seeds, streaming JSONL step log, `meta.json` with `schema_version`, `git_sha`, run arguments and final `status` | all above |
 | `bakeoff/report.py` | Logs → scoreboard (reads files only) | — |
-| `bakeoff/__main__.py` | `uv run python -m bakeoff run|report` | runner, report |
-| `viewer/` | Static HTML replay reading a run's JSONL | — |
+| `bakeoff/replay.py` | Run directories → one replay object: merged runs, landing tiles, scoreboard (reads files only; `docs/REPLAY_DATA.md`) | report |
+| `bakeoff/view.py` | Replay object + `viewer/` → one self-contained HTML file | — |
+| `bakeoff/__main__.py` | `uv run python -m bakeoff run|report|view` | runner, report, replay, view |
+| `viewer/` | Static page that draws the replay object: tunnels side by side, each player's mind, scoreboard. Plain JavaScript, no build step, no network | — |
 
 Carry over from `jev-testing` PR #1, adapting names: `Decision`/`Policy`, the runner's
````

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q` — Expected: 235 passed, 9 deselected.

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md docs/DECISIONS.md docs/superpowers/specs/2026-09-19-tunnel-run-design.md
git commit -F <the message file the controller gave you>
git log -1 --format=%B
```

The message's first line is `docs: replay viewer in README, CLAUDE.md, decisions and the spec`.

### Task 7: Watch the practice replay (controller and user; free, no subagent)

Nothing here spends money: `view` reads logs only. The run directories are git-ignored and exist only on the user's machine.

- [ ] **Step 1: Build the three-contestant replay of practice seed 1000**

```bash
uv run python -m bakeoff view runs/20260919-151934 runs/20260920-102909 runs/20260920-102919 --output replay-practice.html
```

Expected: `replay: replay-practice.html (22 episodes, 2.9 MB)`. (`runs/20260920-103208` replays the same Jev and LLM episodes from the cache; passing it as well must exit 2 with `jev on seed 1000 is in both ...`.)

- [ ] **Step 2: Build the fly-and-baselines replay of seeds 0 to 19**

```bash
uv run python -m bakeoff view runs/20260919-154809 --output replay-seeds0.html
```

Expected: `replay: replay-seeds0.html (80 episodes, 6.4 MB)`.

- [ ] **Step 3: Look at both** (the user opens the files; the controller may serve the directory on localhost for a browser tool, which blocks `file:` URLs)

Check: on track 1000 Jev falls after 23 rows stepping sideways, the LLM after 199, the fly after 58; around row 23 the fly's Giant Fiber raster is dense and it jumps (250 Hz to both eyes, jump signal about 210 Hz); the brighter tiles match the small senses grid; the scoreboard shows the not-a-fair-comparison note on the practice replay (the fly played 20 tracks, the others 1) and not on the seeds 0 to 19 replay; "What it was asked" shows the briefing; phone width has no sideways scroll; no console errors.

- [ ] **Step 4: Final whole-branch review, aimed at the design, not the transcription**

Questions for the reviewer: Can any log text reach the page unescaped? Does anything load from the network? Is every number that is ours labelled as ours, and does the page say anything about the fly the spec does not support? Can the merged scoreboard or the per-track table mislead (different seeds, cut-off runs, cached replays showing 0 requests)? Does the row-synchronised clock misrepresent anyone (a jumper, a dead player, a cut-off run)?

## Self-review against the spec

- **Goal, "replays showing the three runners side by side with each one's mind visible ... and a scoreboard across tracks":** Tasks 3 to 5 (columns per player, mind panels, scoreboard, per-track table).
- **Senses, "the exact weighting ... shown in the viewer"; Fly player, "[the four numbers] are displayed on screen"; "Known weaknesses, to be stated in the viewer":** Task 5, section "What is the fly's and what is ours" (numbers read from `meta.json`, a warning when they were provisional); each fly panel repeats that the weighting and the jump threshold are ours.
- **Fly player step 5, "so the viewer can draw the neurons firing":** Task 4, `spikeRaster` from `info.spike_times_ms`, the eye inputs, the turn and jump signals with their thresholds.
- **Jev's two calibration Nouls with ground truth; the LLM's answer; `invalid`, `error`, fallback to `stay`:** Task 4 (`jevMind`, `llmMind`, `verdict`).
- **`chosen_action`, `executed_action` and `solver_action` logged separately:** Task 4, `verdict` shows the choice, what the game ran when it differs and why, and the solver's depths.
- **Report: "only complete runs count; interrupted ones are shown as incomplete":** Task 1 (`complete`), Task 4 (`statusLine`), Task 5 (the ellipsis in the table).
- **Decision 11's asymmetry between Jev and the LLM "is named":** Task 5, last paragraph of the page.
- **Architecture, `viewer/` "static HTML replay reading a run's JSONL":** changed by decision 1 above; the table is updated in Task 6.
- **Testing, "no test touches the network":** holds; one test asserts the page itself references nothing external.
- Not in this phase: the tournament and the write-up (phase 5); choosing the tournament seeds (open item in `docs/DECISIONS.md`).
