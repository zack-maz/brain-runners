# Update 3a: the page runs the show — the control channel and the lobby — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `bakeoff live` stops being one run chosen on the command line. The command binds the loopback port and sets the money ceiling; the lobby in the browser picks the track and the players, shows what the run would cost at worst, starts it, cancels it, and sets up another one when it ends — without restarting the command.

**Architecture:** `bakeoff/session.py` (new) is `LiveSession`: one per command, holding one `RequestBudget` per paid player for the whole session, the seed rule, the player list with prices and budgets (`state`), the refusal rules (`why_not`, `check`) and one `LiveRun` at a time (`start`, `cancel`, `find`). `bakeoff/clients/core.py` gains `RequestBudget.remaining` and `SharedBudget`, a run's view of a session budget: it spends from the session's cap, so nothing the page sends can raise the ceiling, but records only its own requests, so each run's `meta.json` stays an honest record of what that run spent. `bakeoff/live.py` gains `LiveRun.stop()` (checked between decisions) and keeps the empty replay it prepared; `bakeoff/replay.py` gains `empty_replay`. `bakeoff/live_server.py` grows the control routes (`GET /state`, `POST /run`, `POST /cancel`, `GET /events?run=`), all behind a token minted at startup and embedded in the page by `bakeoff/view.py`. `viewer/lobby.js` (new, pure and tested under node) is the lobby's arithmetic and markup; `viewer/app.js` does the fetching and the DOM, and resets the page to a new run's empty replay so one page can watch run after run.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript with `node --test` (run by `uv run pytest`). Standard library only: no new dependency, on either side.

**Spec:** `docs/superpowers/specs/2026-09-22-page-control-design.md`, sections A, B and C (binding). Background: `docs/DECISIONS.md` decision 35; `docs/UPDATES.md` items 4, 5, 8, 9. Update 3b (the logs in the mind panels, the Run and Analysis tabs, the player picker in a replay) is a separate plan and is **not** in scope here.

**Branch:** `phase6-updates` (already checked out; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network**: every test here uses free players (`solver`, `random`, and the slow fake in `tests/fakes.py`), and the only connections are to the loopback server under test.
- **This plan spends no money.** No `--max-requests` on a real command, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run`/`live` with a paid player or the fly. A paid or fly run is the controller's and the user's alone.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Frozen:** the players, the game, the fly, the senses and the step record (`schema_version` stays 1); `runner.play_row` and `replay.frame_of` stay the one source of a live run's records and frames; the response cache and every cache key.
- **Money safety is the point of this plan.** The command sets the ceiling and nothing the page sends may raise it: budgets live on the session, `/run` re-checks every rule the page checked, and a paid player may not play a seed below 1000 unless the command was started with `--tournament` — cap or no cap.
- **Viewer rules:** plain JavaScript, no build step, no npm packages; the page loads nothing from the network; everything that comes from the server (a player name, a refusal) is escaped before it becomes markup.
- Every code block below was run in a prototype and passes as written (final state: 415 fast tests, 9 deselected). If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **One stream per run.** `GET /events?run=<run_id>` picks the run, so a stream never runs on into the next one; without the parameter it is the run going now. A finished run still replays its history, because the broadcast keeps every event.
2. **The page resets from the run's own empty replay.** `LiveRun.prepare()` keeps what it built (`run.replay`) and `/state` hands it back inside the `run` block, so the page has one way in whether it started the run itself or the command line did (`--start`).
3. **The token** is minted per session (`secrets.token_urlsafe(16)`), embedded as `data-token` on `<body>`, sent as `X-Bakeoff-Token`, and as `?token=` on the event stream alone, because an `EventSource` cannot send headers. `/` itself needs no token: it is what carries the token to the page.
4. **Cancel is cooperative.** `stop()` is checked between decisions, so a decision already in flight (a paid request) is finished and recorded first; the run then closes as a normal directory with status `interrupted`.
5. **A session's runs never collide.** The run id is the usual timestamp with `-2`, `-3` appended when two runs land in the same second.
6. **`--max-requests` is per paid player for the whole session**, not per run, and `SharedBudget` keeps each run's `meta.json` honest: `max` is what was left when that run began, `used` is what that run spent.
7. **The command line's flags.** `--seed` and `--players` no longer have defaults: without them the lobby opens with the demo's three on track 1001 ready (`DEMO_PLAYERS`, `DEMO_SEED`) and starts nothing. The new `--start` plays that run at once, as before, and holds its first decision until a browser is listening. `--no-wait` needs `--start` (without a run to wait for it means nothing) and is a usage error otherwise.
8. **`--max-rows` belongs to the session's rules**, since the session plays every run of the command, so every run of that command is the same prefix of its track.
9. **The refusal rules live in one place.** `LiveSession.why_not(player, seed)` answers why a player may not play a track; `check` refuses with it and `/state` shows it, so the page can grey a player out and say why before anyone presses anything.
10. **What a run would cost is shown before it starts and confirmed in the page**: the Start button arms once (`Confirm: start and spend at most …`) whenever a paid player is in the run, and any change to the track or the players disarms it. The worst case is rows × requests per row × price, capped by what is left of the budget; prices are the measured ones in `docs/COSTS.md`, and GLM Flash is `0 USD (free tier)`.
11. **"Played before"** is read from the run directories' `meta.json` (same game version, same player, same seed), so it is coarse — a player that died on row 3 is listed for that track — and it never changes the estimate, which assumes nothing is cached.
12. **The lobby lists the contestants first** in `replay.CONTESTANTS` order, then the free yardsticks.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/session.py` | `LiveSession`, `LobbyError`, `Started`, `played_before`, `PRICE_USD`, `FIRST_PRACTICE_SEED` | 1 |
| `bakeoff/clients/core.py` | `RequestBudget.remaining`, `SharedBudget` | 1 |
| `bakeoff/live.py` | `Cancelled`, `LiveRun.stop`/`stopped`, `run.replay` | 1 |
| `bakeoff/replay.py` | `empty_replay` | 1 |
| `bakeoff/live_server.py` | the control routes, the token, one stream per run | 2 |
| `bakeoff/view.py` | `token=` on the live page | 2 |
| `bakeoff/__main__.py` | the lobby command: `--start`, no default seed or players, serving on | 3 |
| `viewer/lobby.js` | the lobby's arithmetic and markup (pure) | 4 |
| `viewer/app.js`, `viewer/index.html`, `viewer/viewer.css` | the controls, the fetching, resetting to a new run | 4 |
| `CLAUDE.md`, `docs/UPDATES.md` | what the command and the page now do | 5 |

---

### Task 1: The session: the ceiling, the lobby's rules, one run at a time

**Files:**
- Modify: `bakeoff/clients/core.py`
- Modify: `bakeoff/live.py`
- Modify: `bakeoff/replay.py`
- Create: `bakeoff/session.py`
- Test: `tests/fakes.py`
- Test: `tests/test_session.py`

**Interfaces:**
- `LiveSession(rules, out_root, cache_dir, max_requests, tournament, args, token, paid_blocked, ready)` — one per `bakeoff live` command.
  - `.state(seed=None) -> dict`: `{status, game, max_rows, requests_per_row, max_requests, tournament, first_practice_seed, seed, ready, players, run}`; `players` is one entry per registered player, `{name, paid, price_usd, requests_left, played_before, why_not}`, contestants first.
  - `.why_not(name, seed) -> str | None`: the one place the refusal rules live.
  - `.check(seed, names)`: raises `LobbyError` naming the first reason, and builds every question set so an impossible one is refused before anything exists.
  - `.start(seed, names, wait_for_page=False) -> Started(run, replay)`: prepares the run directory and plays it in a daemon thread; `wait_for_page` holds the first decision until a browser is listening.
  - `.cancel()`, `.wait(timeout=None)`, `.find(run_id) -> LiveRun | None`, `.status` (`lobby` | `running` | `finished`), `.budgets`, `.finished`.
- `SharedBudget(shared)` in `bakeoff/clients/core.py`: spends from the session's `RequestBudget` (so the ceiling holds) and counts its own (so a run's `meta.json` records that run). `RequestBudget.remaining`.
- `LiveRun.stop()` / `.stopped`, `Cancelled`, and `run.replay` (what `prepare()` built).
- `replay.empty_replay(rules) -> dict`: the replay a page starts from before anything has been played.

`tests/fakes.py` gains `SlowPlayer` and `slow_player(monkeypatch)`: a free player that sleeps, so a test can cancel a run while it is going. Nothing here touches a provider.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/fakes.py`:

```diff
@@ -89,3 +89,35 @@ def glm_reply(text='{"action": "stay"}', finish_reason="stop", model="glm-4.5-fl
     return {"id": "1", "model": model, "choices": [{"index": 0, "finish_reason": finish_reason,
                                                     "message": {"role": "assistant", "content": text}}],
             "usage": {"prompt_tokens": 480, "completion_tokens": 7, "total_tokens": 487}}
+
+
+class SlowPlayer:
+    """A free player that takes its time, so a test can cancel a run while it is going. Registered
+    under a name of its own by `slow_player()`; it never asks anyone anything."""
+
+    name = "slow"
+
+    def __init__(self, seconds: float = 0.05):
+        self.seconds = seconds
+
+    def reset(self, game, seed) -> None:
+        pass
+
+    def act(self, senses: dict):
+        import time
+
+        from bakeoff.players.base import Decision
+
+        time.sleep(self.seconds)
+        return Decision(chosen_action="stay")
+
+    def observe(self, executed_action: str) -> None:
+        pass
+
+
+def slow_player(monkeypatch, seconds: float = 0.05) -> str:
+    """Puts `SlowPlayer` in the registry for one test and gives back its name."""
+    from bakeoff.players import REGISTRY
+
+    monkeypatch.setitem(REGISTRY, SlowPlayer.name, lambda: SlowPlayer(seconds))
+    return SlowPlayer.name
```

Create `tests/test_session.py`:

```python
"""The session behind `bakeoff live`: what it lets the page start, and what the ceiling does.

Free players only, so nothing here touches a provider."""

import json

import pytest

from bakeoff.clients.core import RequestBudget, SharedBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.rules import rules_for
from bakeoff.players import REGISTRY
from bakeoff.session import LiveSession, LobbyError, played_before
from tests.fakes import slow_player

RULES = rules_for("v2").variant(max_rows=12)


def session(tmp_path, **options):
    return LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", **options)


def play(session, seed=1001, players=("solver", "random")):
    started = session.start(seed, list(players))
    session.wait(30)
    return started


def test_a_fresh_session_is_in_the_lobby_and_lists_every_player_with_its_price(tmp_path):
    state = session(tmp_path).state(seed=1001)
    assert state["status"] == "lobby" and state["run"] is None
    assert state["game"]["version"] == "v2" and state["max_rows"] == 12 and state["requests_per_row"] == 1
    by_name = {p["name"]: p for p in state["players"]}
    assert by_name["solver"]["paid"] is False and by_name["solver"]["requests_left"] is None
    assert by_name["llm"]["paid"] is True and by_name["llm"]["price_usd"] == 0.0006
    assert by_name["glm_composed"]["price_usd"] == 0.0  # the free tier costs nothing while it lasts
    assert by_name["llm"]["requests_left"] == 0  # the default cap spends nothing


def test_the_contestants_come_first_in_the_pages_own_order_and_the_yardsticks_last(tmp_path):
    names = [p["name"] for p in session(tmp_path).state()["players"]]
    assert names[:4] == ["fly", "jev_composed", "llm", "jev"]  # the demo's three, then the one-shot Jev
    assert names[-3:] == ["always_jump", "random", "solver"]  # the free yardsticks
    assert set(names) == set(REGISTRY)


def test_the_cap_the_command_set_is_per_paid_player_for_the_whole_session(tmp_path):
    state = session(tmp_path, max_requests=40).state()
    left = {p["name"]: p["requests_left"] for p in state["players"] if p["paid"]}
    assert set(left.values()) == {40} and state["max_requests"] == 40


def test_a_run_from_the_lobby_is_a_normal_run_directory_and_the_session_returns_to_it(tmp_path):
    lobby = session(tmp_path)
    started = play(lobby, seed=1001)
    assert lobby.status == "finished" and started.run.status == "completed"
    meta = json.loads((started.run.run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["seed"] == 1001 and meta["args"]["players"] == "solver,random"
    assert started.replay["seeds"] == [1001] and started.replay["episodes"] == []
    state = lobby.state(seed=1001)
    assert state["status"] == "finished" and state["run"]["run_id"] == started.run.run_id
    play(lobby, seed=1002, players=["solver"])  # and another track can be set up without restarting
    assert len(lobby.finished) == 2 and lobby.run.seed == 1002


def test_a_track_that_was_played_before_is_marked_so_the_page_knows_it_replays_for_free(tmp_path):
    lobby = session(tmp_path)
    play(lobby, seed=1001, players=["solver"])
    assert played_before(tmp_path / "runs", "v2") == {"solver": [1001]}
    assert played_before(tmp_path / "runs", "v1") == {}  # another game is another set of answers
    by_name = {p["name"]: p for p in lobby.state(seed=1001)["players"]}
    assert by_name["solver"]["played_before"] is True and by_name["random"]["played_before"] is False
    assert {p["name"] for p in lobby.state()["players"] if p["played_before"]} == set()  # no track, nothing to say


@pytest.mark.parametrize("seed, players, reason", [
    (1001, ["nobody"], "unknown player 'nobody'"),
    (1001, ["solver", "solver"], "duplicate player names"),
    (1001, [], "choose at least one player"),
    (-3, ["solver"], "must not be negative"),
    ("1001", ["solver"], "must be a whole number"),
    (7, ["solver", "llm"], "paid players may not play seeds below 1000"),
])
def test_every_refusal_names_its_reason(tmp_path, seed, players, reason):
    with pytest.raises(LobbyError, match=reason):
        session(tmp_path).check(seed, players)


def test_a_free_player_may_play_a_tournament_seed_and_a_paid_one_may_with_the_flag(tmp_path):
    session(tmp_path).check(7, ["solver"])  # nothing is spent, so nothing is at stake
    session(tmp_path, tournament=True).check(7, ["solver", "llm"])


def test_a_paid_player_with_no_request_left_of_the_session_cap_is_refused(tmp_path):
    lobby = session(tmp_path, max_requests=2)
    lobby.budgets["llm"].spend()
    lobby.check(1001, ["llm"])  # one left
    lobby.budgets["llm"].spend()
    with pytest.raises(LobbyError, match="llm has no requests left of this session's cap of 2"):
        lobby.check(1001, ["llm"])
    lobby.check(1001, ["jev"])  # the other paid players keep their own budget
    session(tmp_path).check(1001, ["llm"])  # a cap of 0 still replays the cache, as the command does


def test_only_one_run_at_a_time(tmp_path):
    lobby = session(tmp_path)
    lobby.start(1001, ["solver"])
    with pytest.raises(LobbyError, match="a run is already going"):
        lobby.check(1002, ["solver"])
    lobby.wait(30)
    lobby.check(1002, ["solver"])


def test_cancelling_closes_the_run_as_a_normal_interrupted_directory(tmp_path, monkeypatch):
    lobby = session(tmp_path)
    with pytest.raises(LobbyError, match="no run is going"):
        lobby.cancel()
    started = lobby.start(1001, [slow_player(monkeypatch)])
    lobby.cancel()
    lobby.wait(30)
    assert started.run.status == "interrupted"
    meta = json.loads((started.run.run_dir / "meta.json").read_text())
    assert meta["status"] == "interrupted" and meta["finished_at"]


def test_a_question_set_that_needs_more_vision_than_the_game_gives_is_refused_before_anything_exists(tmp_path):
    narrow = LiveSession(rules_for("v2").variant(lookahead=2), out_root=tmp_path / "runs",
                         cache_dir=tmp_path / "cache")
    with pytest.raises(LobbyError, match="jev_two_step"):
        narrow.start(1001, ["jev_two_step"])
    assert not (tmp_path / "runs").exists()


def test_a_run_spends_from_the_session_budget_but_records_only_its_own_requests():
    session_budget = RequestBudget(5)
    first, second = SharedBudget(session_budget), None
    first.spend()
    first.spend()
    second = SharedBudget(session_budget)
    second.spend()
    assert (first.max_requests, first.used) == (5, 2)  # what the first run could spend, and did
    assert (second.max_requests, second.used) == (3, 1)  # the second one starts from what was left
    assert session_budget.used == 3 and session_budget.remaining == 2
    for _ in range(2):
        second.spend()
    with pytest.raises(BudgetExhausted):
        second.spend()  # the ceiling the command set holds across the session
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_session.py`
Expected:

```text
ERROR tests/test_session.py
1 error in 0.08s
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/clients/core.py`:

```diff
@@ -64,12 +64,31 @@ class RequestBudget:
         self.max_requests = max_requests
         self.used = 0
 
+    @property
+    def remaining(self) -> int:
+        return max(0, self.max_requests - self.used)
+
     def spend(self) -> None:
         if self.used >= self.max_requests:
             raise BudgetExhausted(f"request cap of {self.max_requests} reached")
         self.used += 1
 
 
+class SharedBudget(RequestBudget):
+    """One run's view of a budget that outlives it (a `bakeoff live` session may play several runs).
+    It spends from the shared budget, so the ceiling the command set can never be raised, but counts
+    its own requests: the run's `meta.json` then records what that run spent, not the session's total.
+    Its own cap is what was left when the run began."""
+
+    def __init__(self, shared: RequestBudget):
+        super().__init__(shared.remaining)
+        self.shared = shared
+
+    def spend(self) -> None:
+        self.shared.spend()  # raises BudgetExhausted when the session's cap is reached
+        self.used += 1
+
+
 @dataclass
 class Reply:
     payload: dict
```

Apply to `bakeoff/live.py`:

```diff
@@ -16,13 +16,16 @@ from bakeoff.game.engine import Game
 from bakeoff.game.rules import Rules, resolve
 from bakeoff.game.track import generate_track
 from bakeoff.players.base import Player
-from bakeoff.replay import META_KEYS, REPLAY_VERSION, build_replay, frame_of, summary_of
-from bakeoff.report import COLUMNS
+from bakeoff.replay import META_KEYS, build_replay, empty_replay, frame_of, summary_of
 from bakeoff.runner import _close, _now, _preflight, _requests, new_meta, play_row
 
 MAX_CONSECUTIVE_ERRORS = 5  # as the runner: a provider that keeps failing ends the run
 
 
+class Cancelled(Exception):
+    """`stop()` was called: the operator, or the page, gave up on a run that had begun."""
+
+
 class Broadcast:
     """Every event of the run, in order. A listener gets the history first and then waits for more,
     so a page that connects late, or reconnects, misses nothing. Thread-safe."""
@@ -93,6 +96,8 @@ class LiveRun:
         self.args = args or {}
         self.broadcast = broadcast if broadcast is not None else Broadcast()
         self.status = "running"
+        self.replay: dict | None = None  # the empty replay a page starts from, filled by prepare()
+        self._stop = threading.Event()
         self.error: str | None = None  # why the run stopped early, when a cap or a failing provider stopped it
         self.meta: dict | None = None
 
@@ -102,10 +107,19 @@ class LiveRun:
         self.run_dir.mkdir(parents=True, exist_ok=False)
         self.meta = new_meta(self.run_id, self.players, [self.seed], self.rules, self.args)
         self._write_meta()
-        return {"replay_version": REPLAY_VERSION, "game": self.rules.to_json(),
-                "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}],
-                "players": [], "seeds": [self.seed], "tracks": {}, "episodes": [],
-                "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": [], "same_seeds": True}}
+        self.replay = {**empty_replay(self.rules), "seeds": [self.seed],
+                       "runs": [{"run_id": self.run_id, **{k: self.meta.get(k) for k in META_KEYS}}]}
+        return self.replay
+
+    @property
+    def stopped(self) -> bool:
+        return self._stop.is_set()
+
+    def stop(self) -> None:
+        """Ask a run that has begun to stop. It is checked between decisions, so a decision already
+        in flight (a paid request) is finished and recorded first; the run then closes as a normal
+        run directory with status `interrupted`."""
+        self._stop.set()
 
     def cancel(self) -> None:
         """The operator gave up before the run began (Ctrl-C while waiting for a browser)."""
@@ -132,6 +146,8 @@ class LiveRun:
             row = 0
             while not all(game.over for game in games.values()):
                 for player in self.players:
+                    if self._stop.is_set():
+                        raise Cancelled("cancelled")
                     game = games[player.name]
                     if game.over or game.row != row:
                         continue  # fallen, finished, or in the air over this row
@@ -156,6 +172,8 @@ class LiveRun:
         except RunAborted as abort:  # a cap was reached (budget_exhausted) or a provider kept failing
             self.status, self.error = abort.status, str(abort)
             self.broadcast.emit("error", {"message": self.error})
+        except Cancelled:  # the page pressed cancel, or the operator did
+            self.status = "interrupted"
         except BaseException as e:  # Ctrl-C, or our bug: the directory is still a valid, incomplete run
             self.status = "interrupted"
             if not isinstance(e, KeyboardInterrupt):
```

Apply to `bakeoff/replay.py`:

```diff
@@ -25,6 +25,14 @@ META_KEYS = ("status", "git_sha", "git_dirty", "started_at", "finished_at", "pla
              "models", "requests")
 
 
+def empty_replay(rules: Rules) -> dict:
+    """The replay a page starts from before anything has been played: the game and nothing else.
+    `bakeoff live` embeds it, and a run that begins fills it through the event stream."""
+    return {"replay_version": REPLAY_VERSION, "game": rules.to_json(), "runs": [], "players": [], "seeds": [],
+            "tracks": {}, "episodes": [],
+            "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": [], "same_seeds": True}}
+
+
 def landing(row: int, lane: int, executed_action: str, lanes: int) -> list[int]:
     """The tile a move lands on (docs/STEP_RECORD.md, "The landing tile"). On a death the runner
     never reaches it; the viewer draws the fall there."""
```

Create `bakeoff/session.py`:

```python
"""The session behind `bakeoff live`: what the page is allowed to start, and what it costs.

One session per command. It holds the ceiling the command set (one `RequestBudget` per paid player
for the whole session, never raised by anything the page sends), and it runs at most one `LiveRun`
at a time. The page asks it what can be run (`state`), starts a run (`start`) and stops it
(`cancel`); every refusal names its reason.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from bakeoff.clients.core import DiskCache, RequestBudget, SharedBudget
from bakeoff.game.rules import Rules
from bakeoff.live import LiveRun
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.replay import CONTESTANTS

# tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
FIRST_PRACTICE_SEED = 1000

# USD per live request, measured in docs/COSTS.md. An estimate for what a run may cost at worst, never
# a bill: the page shows it, the budget enforces the ceiling. GLM Flash is free while its free tier lasts.
PRICE_USD = {"llm": 0.0006, "llm_composed": 0.0006, "llm_choice": 0.0006, "llm_two_step": 0.0006,
             "llm_reader": 0.0006, "jev": 0.00003, "jev_composed": 0.00003, "jev_choice": 0.00003,
             "jev_two_step": 0.00003, "jev_reader": 0.00003,
             "glm_composed": 0.0, "glm_choice": 0.0, "glm_two_step": 0.0, "glm_reader": 0.0}

# every player here asks its provider once a row, so a track of N rows costs at worst N requests
REQUESTS_PER_ROW = 1


def _order(names) -> list[str]:
    """The contestants first, in the page's own order, then the free yardsticks."""
    rest = sorted(set(names) - set(CONTESTANTS))
    return [name for name in CONTESTANTS if name in names] + rest


class LobbyError(Exception):
    """The page asked for something the session will not do. The message is shown to the user."""


@dataclass
class Started:
    """What `start` gives back: the run and the empty replay the page resets itself from."""

    run: LiveRun
    replay: dict


def played_before(out_root: Path | str, game_version: str) -> dict[str, list[int]]:
    """(player, seed) pairs already recorded under this game version, from the run directories'
    `meta.json`. Their answers are in the response cache, so replaying them spends nothing. Coarse:
    a player that died on row 3 of a track is listed for it, and only the rows it reached are cached."""
    played: dict[str, set[int]] = {}
    for meta_path in sorted(Path(out_root).glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue  # a half-written or unreadable directory tells us nothing
        if (meta.get("game") or {}).get("version") != game_version:
            continue  # another game is another set of questions, so another set of cached answers
        for player in meta.get("players") or []:
            played.setdefault(player, set()).update(meta.get("seeds") or [])
    return {player: sorted(seeds) for player, seeds in played.items()}


class LiveSession:
    """The command's ceiling and the page's lobby. Thread-safe: the run loop is a thread of its own."""

    def __init__(self, rules: Rules, out_root: Path | str = "runs", cache_dir: Path | str = ".cache/responses",
                 max_requests: int = 0, tournament: bool = False, args: dict | None = None,
                 token: str | None = None, paid_blocked: str | None = None,
                 ready: tuple[int, list[str]] | None = None):
        self.rules, self.out_root, self.cache = rules, Path(out_root), DiskCache(cache_dir)
        self.max_requests, self.tournament = max_requests, tournament
        # why no paid player may play at all this session, if any (a vision the briefing does not match)
        self.paid_blocked = paid_blocked
        # what the command line offered: the lobby opens with this track and these players ticked
        self.ready_seed, self.ready_players = ready or (FIRST_PRACTICE_SEED + 1, [])
        self.args = args or {}
        self.token = token or secrets.token_urlsafe(16)
        # one budget per paid player for the whole session: the command's cap is per player per session,
        # so a second run from the page spends what the first one left
        self.budgets: dict[str, RequestBudget] = {name: RequestBudget(max_requests) for name in PAID}
        self.run: LiveRun | None = None
        self.finished: list[LiveRun] = []
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ---- what can be run ---------------------------------------------------------------------
    @property
    def status(self) -> str:
        if self.run is None:
            return "lobby"
        return "running" if self.run.status == "running" else "finished"

    def state(self, seed: int | None = None) -> dict:
        """Everything the lobby needs: the players with their price and their budget, the seed rule,
        the game, and what is happening now."""
        played = played_before(self.out_root, self.rules.version)
        players = []
        for name in _order(REGISTRY):
            paid = name in PAID
            players.append({
                "name": name, "paid": paid,
                "price_usd": PRICE_USD.get(name) if paid else 0.0,
                "requests_left": self.budgets[name].remaining if paid else None,
                "played_before": seed is not None and seed in played.get(name, []),
                # why this player cannot play this track, so the page can say so before anything is asked
                "why_not": None if seed is None else self.why_not(name, seed),
            })
        run = self.run
        return {
            "status": self.status,
            "game": self.rules.to_json(), "max_rows": self.rules.max_rows,
            "requests_per_row": REQUESTS_PER_ROW,
            "max_requests": self.max_requests, "tournament": self.tournament,
            "first_practice_seed": FIRST_PRACTICE_SEED,
            "seed": seed,
            "ready": {"seed": self.ready_seed, "players": list(self.ready_players)},
            "players": players,
            # `replay` is the empty replay of this run: the page resets itself to it and fills it from
            # the event stream, whether the page started the run or the command line did (--start)
            "run": None if run is None else {"run_id": run.run_id, "run_dir": str(run.run_dir),
                                             "seed": run.seed, "players": [p.name for p in run.players],
                                             "status": run.status, "error": run.error, "replay": run.replay},
        }

    # ---- starting and stopping ---------------------------------------------------------------
    def why_not(self, name: str, seed: int) -> str | None:
        """Why this player may not play this track, or None. The one place that rule lives: `check`
        refuses with it and `state` shows it."""
        if name not in PAID:
            return None
        if self.paid_blocked:
            return self.paid_blocked
        if seed < FIRST_PRACTICE_SEED and not self.tournament:
            return (f"paid players may not play seeds below {FIRST_PRACTICE_SEED} (tournament seeds); "
                    "this command was not started with --tournament")
        if self.max_requests > 0 and self.budgets[name].remaining == 0:
            return f"{name} has no requests left of this session's cap of {self.max_requests}"
        return None

    def check(self, seed: int, names: list[str]) -> None:
        """Raises `LobbyError` naming the first reason this run will not be started."""
        if self.status == "running":
            raise LobbyError("a run is already going; cancel it first")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise LobbyError("the track must be a whole number")
        if seed < 0:
            raise LobbyError("the track must not be negative")
        if not names:
            raise LobbyError("choose at least one player")
        unknown = [n for n in names if n not in REGISTRY]
        if unknown:
            raise LobbyError(f"unknown player {unknown[0]!r}; choose from {sorted(REGISTRY)}")
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise LobbyError(f"duplicate player names: {duplicates}")
        refused = [self.why_not(name, seed) for name in names]
        if any(refused):
            raise LobbyError(next(reason for reason in refused if reason))
        for name in names:  # a question set that cannot be asked on this vision, before anyone plays
            question_set = getattr(REGISTRY[name], "question_set", None)
            if question_set is not None:
                try:
                    question_set.build(self.rules)
                except ValueError as e:
                    raise LobbyError(f"{name}: {e}") from e

    def start(self, seed: int, names: list[str], wait_for_page: bool = False) -> Started:
        """Validates, builds the players on the session's budgets, prepares the run directory and
        plays it in a thread. Returns the run and the empty replay the page starts from.
        `wait_for_page`: hold the first decision until a browser is listening (`bakeoff live --start`;
        a run the page itself started needs no wait, since the stream carries its history)."""
        with self._lock:
            self.check(seed, names)
            players = self._players(names)
            run = LiveRun(players, seed, out_root=self.out_root, rules=self.rules, run_id=self._run_id(),
                          args={**self.args, "seed": seed, "players": ",".join(names)})
            replay = run.prepare()  # the directory and meta.json: a failure here starts nothing
            self.run = run
            self._thread = threading.Thread(target=self._play, args=(run, wait_for_page), daemon=True)
            self._thread.start()
            return Started(run, replay)

    def _run_id(self) -> str:
        """The usual timestamp, with a counter when a session plays two runs in the same second."""
        stamp = run_id = time.strftime("%Y%m%d-%H%M%S")
        nth = 1
        while (self.out_root / run_id).exists():
            nth += 1
            run_id = f"{stamp}-{nth}"
        return run_id

    def _play(self, run: LiveRun, wait_for_page: bool = False) -> None:
        try:
            if wait_for_page:
                run.broadcast.wait_for_listener()
            if run.stopped:  # cancelled while it waited: the directory closes without a decision
                run.cancel()
            else:
                run.run()
        finally:
            self.finished.append(run)

    def _players(self, names: list[str]) -> list:
        players = []
        for name in names:
            if name in PAID:
                # a view of the session's budget: it spends from the session's cap but a run's meta.json
                # records only what that run spent, against what it could have spent
                players.append(make_player(name, cache=self.cache, budget=SharedBudget(self.budgets[name])))
            else:
                players.append(make_player(name))
        return players

    def find(self, run_id: str | None) -> LiveRun | None:
        """The run with this id, whether it is still going or already closed; without an id, the
        run going now (or the last one). The page opens one event stream per run and names it."""
        if not run_id:
            return self.run
        return next((run for run in [*self.finished, self.run] if run is not None and run.run_id == run_id), None)

    def cancel(self) -> None:
        """Stop the run that is going. It closes as a normal run directory with status `interrupted`."""
        run = self.run
        if run is None or run.status != "running":
            raise LobbyError("no run is going")
        run.stop()

    def wait(self, timeout: float | None = None) -> None:
        """Waits for the run that is going, if any (the command's own thread does this)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_session.py`
Expected: `17 passed in 0.34s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `406 passed, 9 deselected in 22.77s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/clients/core.py bakeoff/live.py bakeoff/replay.py bakeoff/session.py tests/fakes.py tests/test_session.py
git commit -F <message file>   # feat: a live session holds the ceiling and the lobby's rules, and runs one track at a time
```

---

### Task 2: The control routes, behind the session's token

**Files:**
- Modify: `bakeoff/live_server.py`
- Modify: `bakeoff/view.py`
- Test: `tests/test_live_server.py`

**Interfaces:**
- `serve(page, session, port)` now takes the `LiveSession` (it took a `Broadcast`).
- `GET /` the page (no token: it is what carries the token). `GET /state[?seed=N]`, `POST /run` `{seed, players}`, `POST /cancel`, `GET /events?run=<run_id>[&token=...]`.
- `TOKEN_HEADER = "X-Bakeoff-Token"`; the stream also accepts `?token=` because an `EventSource` sends no headers. A wrong or missing token is 403, as is a request whose `Host` is not ours.
- A refusal is `409` with `{ok: false, error}`; a malformed request is `400`; a run that could not be created is `500`. A successful `/run` is `{ok: true, run_id, state}`, and the state's `run` block carries that run's empty `replay`.
- `render_html(..., token=...)` writes `data-token` next to `data-live`; a token that is not url-safe text is a `ValueError`.

- [ ] **Step 1: Write the failing tests**

Replace the whole of `tests/test_live_server.py` with:

```python
"""The loopback server of `bakeoff live`, on an ephemeral port with a session of free players.
The only connections are to 127.0.0.1, to the server under test."""

import http.client
import json
import re

import pytest

from bakeoff.game.rules import rules_for
from bakeoff.live import Broadcast, LiveRun
from bakeoff.live_server import EVENTS_PATH, TOKEN_HEADER, serve
from bakeoff.session import LiveSession
from bakeoff.view import render_html
from tests.fakes import slow_player

REPLAY = {"replay_version": 1, "runs": [{"run_id": "live"}], "players": [], "seeds": [1001], "tracks": {}, "episodes": []}
RULES = rules_for("v2").variant(max_rows=12)


@pytest.fixture
def server(tmp_path):
    session = LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", token="tok-123")
    httpd = serve(render_html(REPLAY, live=EVENTS_PATH, token=session.token), session, port=0)
    yield httpd, session
    if session.run is not None:
        session.run.stop()
    session.wait(30)
    httpd.shutdown()
    httpd.server_close()


def call(httpd, method, path, body=None, host=None, token="tok-123"):
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    headers = {}
    if host:
        headers["Host"] = host
    if token is not None:
        headers[TOKEN_HEADER] = token
    connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    response = connection.getresponse()
    text = response.read().decode()
    connection.close()
    return response, text


def get(httpd, path, host=None, token="tok-123"):
    return call(httpd, "GET", path, host=host, token=token)


def payload(httpd, method, path, body=None, token="tok-123"):
    response, text = call(httpd, method, path, body, token=token)
    return response.status, json.loads(text)


def test_the_live_page_is_the_player_with_an_empty_replay_the_stream_address_and_the_token():
    page = render_html(REPLAY, live=EVENTS_PATH, token="tok-123")
    assert '<body data-live="/events" data-token="tok-123">' in page
    assert "data-live" not in render_html(REPLAY)  # a replay file never looks for a server
    (data,) = re.findall(r'<script type="application/json" id="replay-data">(.*?)</script>', page, re.S)
    assert json.loads(data) == REPLAY
    with pytest.raises(ValueError, match="live must be a path"):
        render_html(REPLAY, live='"><script>')
    with pytest.raises(ValueError, match="token must be url-safe"):
        render_html(REPLAY, live=EVENTS_PATH, token='"><script>')


def test_it_binds_to_loopback_only_and_serves_the_page(server):
    httpd, _ = server
    assert httpd.server_address[0] == "127.0.0.1"
    response, body = get(httpd, "/")
    assert response.status == 200 and response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert '<body data-live="/events"' in body and response.getheader("Cache-Control") == "no-store"


def test_the_control_routes_need_the_token_but_the_page_itself_does_not(server):
    httpd, _ = server
    assert get(httpd, "/", token=None)[0].status == 200  # the page carries the token to the page
    assert get(httpd, "/state", token=None)[0].status == 403
    assert get(httpd, "/state", token="guessed")[0].status == 403
    assert call(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]}, token=None)[0].status == 403
    assert call(httpd, "POST", "/cancel", {}, token="guessed")[0].status == 403
    assert get(httpd, EVENTS_PATH, token=None)[0].status == 403
    assert get(httpd, "/state")[0].status == 200


def test_state_says_what_can_be_run(server):
    httpd, _ = server
    status, state = payload(httpd, "GET", "/state?seed=1001")
    assert status == 200 and state["status"] == "lobby" and state["seed"] == 1001
    assert state["game"]["version"] == "v2" and state["max_rows"] == 12
    assert {p["name"] for p in state["players"]} >= {"solver", "fly", "llm", "jev_composed"}
    assert [p["requests_left"] for p in state["players"] if p["name"] == "llm"] == [0]


def test_a_run_started_from_the_page_streams_its_frames_and_ends_in_the_lobby(server):
    httpd, session = server
    status, started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})
    assert status == 200 and started["ok"] is True and started["state"]["status"] == "running"
    assert started["state"]["run"]["replay"]["seeds"] == [1001]  # what the page resets itself to
    assert started["state"]["run"]["replay"]["runs"][0]["run_id"] == started["run_id"]
    session.wait(30)  # the whole run, so the history the stream replays is settled and the read cannot race
    response, body = get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")
    assert response.status == 200 and response.getheader("Content-Type") == "text/event-stream"
    assert response.getheader("Access-Control-Allow-Origin") is None  # other origins cannot read the stream
    kinds = [line[7:] for line in body.split("\n") if line.startswith("event: ")]
    assert kinds[0] == "episode" and kinds[-1] == "end" and "frame" in kinds
    assert payload(httpd, "GET", "/state")[1]["run"]["status"] == "completed"
    # and the stream of a finished run can still be replayed from its history, by name
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")[0].status == 200
    assert get(httpd, f"{EVENTS_PATH}?run=20200101-000000")[0].status == 404


def test_a_refusal_names_its_reason_and_starts_nothing(server):
    httpd, session = server
    status, refused = payload(httpd, "POST", "/run", {"seed": 7, "players": ["solver", "llm"]})
    assert status == 409 and refused["ok"] is False
    assert "seeds below 1000" in refused["error"] and session.run is None
    status, refused = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["nobody"]})
    assert status == 409 and "unknown player 'nobody'" in refused["error"]
    status, refused = payload(httpd, "POST", "/cancel", {})
    assert status == 409 and refused["error"] == "no run is going"
    assert not (session.out_root.exists() and any(session.out_root.iterdir()))


def test_cancel_stops_the_run_that_is_going(server, monkeypatch):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": [slow_player(monkeypatch)]})[1]
    status, stopped = payload(httpd, "POST", "/cancel", {})
    assert status == 200 and stopped["ok"] is True
    session.wait(30)
    meta = json.loads((session.out_root / started["run_id"] / "meta.json").read_text())
    assert meta["status"] == "interrupted"


def test_the_port_can_be_bound_before_the_page_exists(tmp_path):
    session = LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", token="tok-123")
    httpd = serve(None, session, port=0)
    try:
        assert get(httpd, "/")[0].status == 503
        httpd.page = "<p>ready</p>"
        assert get(httpd, "/")[1] == "<p>ready</p>"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_stream_sends_the_history_as_server_sent_events_and_ends_with_the_run(server):
    httpd, session = server
    run = LiveRun([], 1001, out_root=session.out_root, rules=RULES, run_id="handmade", broadcast=Broadcast())
    session.finished.append(run)
    run.broadcast.emit("episode", {"episode": {"player": "fly"}, "track": {"seed": 1001}})
    run.broadcast.emit("frame", {"player": "fly", "seed": 1001, "frame": {"row": 0, "answers": {"text": "line\nbreak </script>"}}})
    run.broadcast.emit("end", {"status": "completed"})
    run.broadcast.close()
    response, body = get(httpd, f"{EVENTS_PATH}?run=handmade")
    assert response.status == 200
    events = [block.split("\n") for block in body.strip().split("\n\n")]
    assert [lines[0] for lines in events] == ["event: episode", "event: frame", "event: end"]
    assert all(len(lines) == 2 and lines[1].startswith("data: ") for lines in events)  # one line each, whatever the log says
    assert json.loads(events[1][1][6:])["frame"]["answers"]["text"] == "line\nbreak </script>"


def test_the_stream_takes_the_token_in_the_query_because_an_event_source_sends_no_headers(server):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]})[1]
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}&token=tok-123", token=None)[0].status == 200
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}&token=wrong", token=None)[0].status == 403


def test_nothing_else_is_served(server):
    httpd, _ = server
    assert get(httpd, "/runs/")[0].status == 404
    assert get(httpd, "/../pyproject.toml")[0].status == 404
    assert call(httpd, "POST", "/anything", {})[0].status == 404
    assert get(httpd, "/", host="evil.example")[0].status == 403  # a rebound DNS name is not us
    assert get(httpd, "/", host=f"localhost:{httpd.server_address[1]}")[0].status == 200
    assert call(httpd, "POST", "/run", host="evil.example", body={"seed": 1001, "players": ["solver"]})[0].status == 403
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("PUT", "/state", body="x")
    assert connection.getresponse().status == 501
    connection.close()


def test_a_request_that_is_not_json_is_a_refusal_not_a_crash(server):
    httpd, _ = server
    response, text = call(httpd, "POST", "/run", None)  # no body at all: a refusal naming what is missing
    assert response.status == 409 and "the track must be a whole number" in json.loads(text)["error"]
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("POST", "/run", body="not json", headers={TOKEN_HEADER: "tok-123"})
    response = connection.getresponse()
    assert response.status == 400 and "not JSON" in json.loads(response.read())["error"]
    connection.close()
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_live_server.py`
Expected:

```text
ERROR tests/test_live_server.py
1 error in 0.11s
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `bakeoff/live_server.py` with:

```python
"""The server of `bakeoff live`: loopback only, standard library only. It serves the player page, the
control channel the page drives the session with, and the event stream (Server-Sent Events), and
nothing else: no files, no other method, no other host.

Every request but the page itself carries the session's token, minted at startup and embedded in the
page, so another program on this machine cannot drive the run.

| route | what it does |
| --- | --- |
| `GET /`            | the page |
| `GET /state`       | what can be run: players, prices, budgets, the seed rule, and what is happening now |
| `POST /run`        | `{seed, players}`: start a run, or refuse and name the reason |
| `POST /cancel`     | stop the run that is going |
| `GET /events`      | the frames of a run, Server-Sent Events (`?run=<run_id>`) |
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bakeoff.session import LiveSession, LobbyError

EVENTS_PATH = "/events"
HOST = "127.0.0.1"
TOKEN_HEADER = "X-Bakeoff-Token"
MAX_BODY = 64 * 1024  # a lobby request is a few hundred bytes; anything larger is not ours


def serve(page: str | None, session: LiveSession, port: int = 8000) -> ThreadingHTTPServer:
    """Starts serving in a daemon thread and returns the server (`shutdown()` stops it). Port 0 picks a
    free one. The port is bound before anything is written to disk, so the page may come later: set
    `server.page`; until then `/` answers 503."""

    class Handler(BaseHTTPRequestHandler):
        # ---- the checks every request goes through ------------------------------------------
        def _ours(self) -> bool:
            names = {f"{HOST}:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}"}
            if self.headers.get("Host") in names:
                return True
            self.send_error(403)  # a page elsewhere that points a DNS name at us gets nothing
            return False

        def _token(self) -> bool:
            """The token is in the header, or in `token=` for the event stream (an EventSource sends
            no headers). A wrong one is 403: another program on this machine is not the page."""
            sent = self.headers.get(TOKEN_HEADER) or self._query().get("token")
            if sent == self.server.session.token:
                return True
            self.send_error(403)
            return False

        def _query(self) -> dict:
            _, _, query = self.path.partition("?")
            out = {}
            for part in query.split("&"):
                key, _, value = part.partition("=")
                if key:
                    out[key] = value
            return out

        @property
        def _route(self) -> str:
            return self.path.partition("?")[0]

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("the request is too large")
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except ValueError as e:
                raise ValueError(f"the request is not JSON: {e}") from e

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        # ---- the routes ----------------------------------------------------------------------
        def do_GET(self):  # noqa: N802 (the base class names it)
            if not self._ours():
                return
            if self._route == "/":
                self._page()
            elif self._route == "/state":
                if self._token():
                    seed = self._query().get("seed")
                    self._json(self.server.session.state(int(seed) if (seed or "").isdigit() else None))
            elif self._route == EVENTS_PATH:
                if self._token():
                    self._events()
            else:
                self.send_error(404)

        def do_POST(self):  # noqa: N802
            if not self._ours():
                return
            if self._route not in ("/run", "/cancel"):
                return self.send_error(404)
            if not self._token():
                return
            try:
                body = self._body()
                if self._route == "/cancel":
                    self.server.session.cancel()
                    return self._json({"ok": True, "state": self.server.session.state()})
                started = self.server.session.start(body.get("seed"), list(body.get("players") or []))
                # the state carries the run's empty replay, so the page has one way in whoever started it
                self._json({"ok": True, "run_id": started.run.run_id,
                            "state": self.server.session.state(started.run.seed)})
            except LobbyError as e:
                self._json({"ok": False, "error": str(e)}, status=409)  # a refusal, not a crash
            except (ValueError, TypeError) as e:
                self._json({"ok": False, "error": str(e)}, status=400)
            except OSError as e:  # the run directory could not be made: nothing was started
                self._json({"ok": False, "error": f"cannot start the run: {e}"}, status=500)

        def _page(self) -> None:
            if self.server.page is None:
                return self.send_error(503)
            body = self.server.page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _events(self) -> None:
            """The frames of one run. `?run=<run_id>` picks it: the page opens a stream per run, so a
            stream never runs on into the next one. Without it, the run going now (or the last one)."""
            wanted = self._query().get("run")
            run = self.server.session.find(wanted)
            if run is None:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for event in run.broadcast.listen():
                    if event is None:
                        self.wfile.write(b": keep-alive\n\n")
                    else:
                        name, data = event  # json.dumps escapes every newline, so an event is always two lines
                        self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the page was closed

        def log_message(self, format, *args):  # noqa: A002
            pass  # the terminal belongs to the run's own output

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    httpd.page = page
    httpd.session = session
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
```

Apply to `bakeoff/view.py`:

```diff
@@ -41,10 +41,12 @@ def _stylesheet(path: Path) -> str:
 
 
 def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | None = None,
-                page_name: str = "index.html") -> str:
-    """`live`: the path of the event stream of `bakeoff live`. The page then also listens there; a
-    replay file has no such attribute and never looks for a server. `page_name`: the viewer page to
-    fill, `index.html` (the replay) or `bench.html` (the benchmark); both carry the same data slot."""
+                page_name: str = "index.html", token: str | None = None) -> str:
+    """`live`: the path of the event stream of `bakeoff live`. The page then also listens there, and
+    drives the session through the control routes; a replay file has no such attribute and never looks
+    for a server. `token`: the session's token, which every request of the page carries. `page_name`:
+    the viewer page to fill, `index.html` (the replay) or `bench.html` (the benchmark); both carry the
+    same data slot."""
     viewer_dir = Path(viewer_dir)
     page = (viewer_dir / page_name).read_text(encoding="utf-8")
     if page.count(DATA_SLOT) != 1:
@@ -54,7 +56,12 @@ def render_html(replay: dict, viewer_dir: Path | str = VIEWER_DIR, live: str | N
             raise ValueError(f"live must be a path like /events, not {live!r}")
         if page.count("<body>") != 1:
             raise ValueError(f"{viewer_dir / page_name} must contain <body> exactly once")
-        page = page.replace("<body>", f'<body data-live="{live}">')
+        attributes = f'data-live="{live}"'
+        if token is not None:
+            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
+                raise ValueError("the token must be url-safe text")
+            attributes += f' data-token="{token}"'
+        page = page.replace("<body>", f"<body {attributes}>")
     # lambdas, so that a backslash in a file is never read as a regex group reference
     page = _STYLESHEET.sub(lambda m: "<style>\n" + _stylesheet(viewer_dir / m.group(1)) + "</style>", page)
     page = _SCRIPT.sub(lambda m: "<script>\n" + (viewer_dir / m.group(1)).read_text(encoding="utf-8") + "</script>", page)
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_live_server.py`
Expected: `12 passed in 5.84s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `413 passed, 9 deselected in 25.67s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/live_server.py bakeoff/view.py tests/test_live_server.py
git commit -F <message file>   # feat: the page drives the run over /state, /run and /cancel, behind a token, on loopback only
```

---

### Task 3: The command hands the show to the page

**Files:**
- Modify: `bakeoff/__main__.py`
- Test: `tests/test_cli_live.py`

**Interfaces:**
- `bakeoff live` with no `--seed` and no `--players` opens the lobby with `DEMO_PLAYERS` (`fly,jev_composed,llm`) on `DEMO_SEED` (1001) ready, and starts nothing.
- `--start` plays that run at once and then keeps serving, so another track can be played from the page; `--no-wait` is only allowed with `--start`.
- Every run the page finishes is reported to the terminal (`run directory:`, the report table, `replay it later:`) until Ctrl-C.
- `--max-rows` now shapes the session's rules, so every run of the command plays the same prefix.
- The seed rule is stricter here than in `run`: a paid player may not play a seed below 1000 without `--tournament`, cap or no cap, because the page may start a run at any moment.

- [ ] **Step 1: Write the failing tests**

Replace the whole of `tests/test_cli_live.py` with:

```python
"""`bakeoff live` from the command line, with free players only. `--start` plays the command line's own
run; `--no-wait` neither waits for a browser before it nor keeps serving after it. Without `--start` the
command opens the lobby and serves until Ctrl-C, which is covered in tests/test_session.py and
tests/test_live_server.py rather than by blocking here."""

import json
import socket

from bakeoff.__main__ import DEMO_PLAYERS, DEMO_SEED, _parser, main


def live_args(tmp_path, *extra, players="solver,random"):
    return ["live", "--players", players, "--max-rows", "30", "--port", "0", "--no-wait", "--start",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]


def test_by_default_the_page_runs_the_show_with_the_demos_three_ready_and_no_budget():
    args = _parser().parse_args(["live"])
    assert (args.players, args.seed, args.start) == (None, None, False)  # the lobby chooses
    assert (args.max_requests, args.port, args.tournament) == (0, 8000, False)
    assert (DEMO_PLAYERS, DEMO_SEED) == ("fly,jev_composed,llm", 1001)  # what it offers first


def test_the_lobby_serves_until_it_is_interrupted_and_reports_the_runs_the_page_played(tmp_path, capsys, monkeypatch):
    """No --start: the command binds the port, says where to watch and hands over to the page."""
    lobby = []
    monkeypatch.setattr("bakeoff.__main__._serve_until_interrupted",
                        lambda session, printed=None: lobby.append(session) or 0)
    assert main(["live", "--port", "0", "--max-rows", "12", "--out", str(tmp_path / "runs"),
                 "--cache", str(tmp_path / "cache")]) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "the page runs the show" in out
    assert "fly,jev_composed,llm on track 1001" in out
    assert lobby and lobby[0].status == "lobby" and not (tmp_path / "runs").exists()


def test_no_wait_without_start_is_a_usage_error(tmp_path, capsys):
    assert main(["live", "--port", "0", "--no-wait", "--out", str(tmp_path / "runs")]) == 2
    assert "--no-wait needs --start" in capsys.readouterr().err


def test_a_live_run_leaves_a_normal_run_directory_and_prints_where_to_watch(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001")) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "status: completed" in out and "| solver |" in out
    assert "replay it later: python -m bakeoff view " in out
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["command"] == "live" and meta["args"]["max_requests"] == 0
    assert main(["view", str(run_dir), "--output", str(tmp_path / "replay.html")]) == 0  # and it replays afterwards


def test_a_paid_player_on_a_tournament_seed_is_refused_before_anything_exists(tmp_path, capsys):
    """Live, the rule is stricter than `run`'s: a paid player may not play a seed below 1000 at all
    without --tournament, cap or no cap. The page may start a run at any moment, so the seed is settled
    once, when the session is built, not per request."""
    assert main(live_args(tmp_path, "--seed", "7", "--max-requests", "5", players="solver,jev_composed")) == 2
    assert "paid players may not play seeds below 1000" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--seed", "7", players="solver,jev_composed")) == 2
    assert "paid players may not play seeds below 1000" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--seed", "7", players="solver,random")) == 0  # free players, nothing at stake
    assert not any((tmp_path / "runs").glob("*/jev_composed.jsonl"))


def test_without_a_cap_a_paid_player_can_only_replay_the_cache(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", players="solver,jev_composed")) == 1
    captured = capsys.readouterr()
    assert "run budget_exhausted: request cap of 0 reached" in captured.err
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert json.loads((run_dir / "meta.json").read_text())["requests"] == {"jev_composed": {"max": 0, "used": 0}}


def test_a_live_run_plays_the_chosen_game_for_the_chosen_length(tmp_path):
    assert main(live_args(tmp_path, "--game", "v1", "--window", "2")) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["game"]["version"] == "v1+win2" and meta["args"]["game"] == "v1" and meta["args"]["window"] == 2
    assert meta["game"]["max_rows"] == 30  # --max-rows belongs to the session's rules, so every run is a prefix
    assert max(json.loads(line)["row"] for line in (run_dir / "solver.jsonl").read_text().splitlines()) < 30


def test_a_paid_player_with_a_different_window_is_refused_before_anything_exists(tmp_path, capsys):
    assert main(live_args(tmp_path, "--window", "2", players="solver,jev_composed")) == 2
    assert ("paid players are told they see 3 lanes either side; --window 2 is for free players only"
            in capsys.readouterr().err)
    assert not (tmp_path / "runs").exists()


def test_a_paid_player_with_the_same_window_explicit_is_not_refused_by_this_check(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", "--window", "3", players="solver,jev_composed")) == 1
    assert "run budget_exhausted: request cap of 0 reached" in capsys.readouterr().err


def test_usage_errors(tmp_path, capsys):
    assert main(live_args(tmp_path, players="solver,nobody")) == 2
    assert "unknown player 'nobody'" in capsys.readouterr().err
    assert main(live_args(tmp_path, players="solver,solver")) == 2
    assert "duplicate player names" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--window", "9")) == 2
    assert "window must be 1 to 5 lanes" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--lookahead", "3", players="solver,jev_two_step")) == 2
    assert "the two-step questions need 4 rows" in capsys.readouterr().err
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
ERROR tests/test_cli_live.py
1 error in 0.12s
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `bakeoff/__main__.py` with:

```python
"""uv run python -m bakeoff run|report|view|live|bench"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
from bakeoff.game.rules import DEFAULT, RULES, Rules, resolve, rules_for
from bakeoff.live_server import EVENTS_PATH, HOST, serve
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.report import format_table, load_meta, load_steps, summarize
from bakeoff.replay import build_replay, empty_replay
from bakeoff.runner import RunAborted, Runner
from bakeoff.session import FIRST_PRACTICE_SEED, LiveSession, LobbyError
from bakeoff.view import render_html

DEMO_PLAYERS = "fly,jev_composed,llm"  # the demo's three: what the lobby offers first
DEMO_SEED = 1001


def _add_game_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game", choices=sorted(RULES), default=DEFAULT,
                        help=f"the game version (default {DEFAULT}); different versions never share a scoreboard")
    parser.add_argument("--lookahead", type=int,
                        help="rows a player is shown (default: the version's); renames the game")
    parser.add_argument("--window", type=int,
                        help="lanes a player is shown either side (default: the version's); renames the game")


def _rules(args) -> Rules:
    return rules_for(args.game).variant(lookahead=args.lookahead, window=args.window)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakeoff")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run players over seeded tracks")
    run.add_argument("--players", default="random,solver", help=f"comma-separated; available: {sorted(REGISTRY)}")
    run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
    run.add_argument("--seed-start", type=int, default=0,
                     help="first seed; practice seeds must not overlap tournament seeds")
    _add_game_arguments(run)
    run.add_argument("--max-rows", type=int, help="play a prefix of each track (default: the whole track)")
    run.add_argument("--out", default="runs")
    run.add_argument("--max-requests", type=int, default=0,
                     help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only replays "
                          "the cache. Worst case a run spends this many requests per paid player")
    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    run.add_argument("--tournament", action="store_true",
                     help="allows live paid requests on seeds below 1000; for the phase 6 tournament only")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
    bench = sub.add_parser("bench", help="score recorded runs: who is better and how sure, time and cost per row; "
                                         "spends nothing")
    bench.add_argument("sources", nargs="+", metavar="RUN_DIR[:PLAYER,...]",
                       help="run directories, each optionally with the players to take from it")
    bench.add_argument("--output", default="bench.html",
                       help="the page to write (default bench.html); the numbers go next to it as .json")
    bench.add_argument("--pair", action="append", default=[], metavar="A,B",
                       help="show only these pairs in the terminal (repeatable); the page shows every pair")
    live = sub.add_parser("live", help="play one track in real time and watch it in the browser (loopback only); "
                                       "the run is recorded like any other")
    live.add_argument("--players", help=f"comma-separated; available: {sorted(REGISTRY)}. Without it the page "
                                        f"opens in the lobby with the demo's three ready ({DEMO_PLAYERS})")
    live.add_argument("--seed", type=int, help=f"the track; practice seeds are 1000 and up (default {DEMO_SEED} in "
                                               "the lobby, where the page may choose another)")
    _add_game_arguments(live)
    live.add_argument("--max-rows", type=int, help="play a prefix of the track (default: the whole track)")
    live.add_argument("--out", default="runs")
    live.add_argument("--max-requests", type=int, default=0,
                      help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only "
                           "replays the cache, which makes a free live run of a track that was already played")
    live.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    live.add_argument("--tournament", action="store_true", help="allows live paid requests on seeds below 1000")
    live.add_argument("--start", action="store_true",
                      help="play at once with --players on --seed, as before; without it the page opens in the "
                           "lobby and starts the run when you say so")
    live.add_argument("--port", type=int, default=8000, help="the page is served on 127.0.0.1 only (default port 8000)")
    live.add_argument("--no-wait", action="store_true",
                      help="do not wait for a browser before the run, and do not keep serving after it")
    return parser


def _players(names: str, cache: DiskCache, max_requests: int, rules: Rules) -> list:
    # one budget per paid player: the providers bill separately, and one must not starve the other
    players = [make_player(name, cache=cache, budget=RequestBudget(max_requests)) if name in PAID
               else make_player(name) for name in (n.strip() for n in names.split(","))]
    for p in players:  # a question set that cannot be asked on this vision is a usage error, before anyone plays
        if hasattr(p, "question_set"):
            p.question_set.build(rules)
    return players


def _spends_on_tournament_seeds(players: list, max_requests: int, first_seed: int, tournament: bool) -> bool:
    return (max_requests > 0 and any(p.name in PAID for p in players)
            and first_seed < FIRST_PRACTICE_SEED and not tournament)


SEED_RULE = ("paid players may not spend requests on seeds below 1000 (tournament seeds); "
             "use {flag} 1000 or higher, or pass --tournament")

# the paid players' briefing (bakeoff/players/briefing.py) tells them they see 3 lanes either side; until
# that text follows the window, a different window would be a lie to a paid player, cache or not
WINDOW_RULE = ("paid players are told they see {chosen} lanes either side; --window {requested} is for "
               "free players only")


def _paid_window_mismatch(players: list, chosen_window: int, requested_window: int | None) -> bool:
    return requested_window is not None and requested_window != chosen_window and any(p.name in PAID for p in players)


def _live(args) -> int:
    """The page runs the show: the command sets the ceiling, binds the loopback port and keeps serving;
    the lobby in the browser picks the track and the players. `--start` plays at once, as before."""
    try:  # the session plays every run of this command, so --max-rows belongs to its rules
        rules = resolve(_rules(args), args.max_rows)
    except (KeyError, ValueError) as e:
        print(e.args[0] if isinstance(e, KeyError) else e, file=sys.stderr)
        return 2
    if args.no_wait and not args.start:
        print("--no-wait needs --start: without it the page starts the run and there is nothing to wait for",
              file=sys.stderr)
        return 2
    seed = DEMO_SEED if args.seed is None else args.seed
    names = [n.strip() for n in (args.players or DEMO_PLAYERS).split(",")]
    run_args = {"command": "live", "game": args.game, "lookahead": args.lookahead, "window": args.window,
                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
                "tournament": args.tournament, "port": args.port}
    # a vision the paid players' briefing does not match: they may not play this session at all
    blocked = (WINDOW_RULE.format(chosen=RULES[args.game].window, requested=args.window)
               if args.window is not None and args.window != RULES[args.game].window else None)
    session = LiveSession(rules, out_root=args.out, cache_dir=args.cache, max_requests=args.max_requests,
                          tournament=args.tournament, args=run_args, paid_blocked=blocked, ready=(seed, names))
    try:
        session.check(seed, names)  # what the command line asks for, refused before anything is bound
    except LobbyError as e:
        print(e, file=sys.stderr)
        return 2
    try:
        server = serve(None, session, args.port)  # before anything is on disk: a busy port leaves nothing behind
    except OSError as e:
        print(f"cannot listen on {HOST}:{args.port}: {e}", file=sys.stderr)
        return 2
    try:
        try:
            server.page = render_html(empty_replay(rules), live=EVENTS_PATH, token=session.token)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        print(f"watch: http://{HOST}:{server.server_address[1]}/", flush=True)
        if args.start:
            return _play_now(session, seed, names, args)
        print(f"the page runs the show: pick a track and the players there (Ctrl-C to stop). "
              f"Ready: {','.join(names)} on track {seed}", flush=True)
        return _serve_until_interrupted(session)
    finally:
        _shutdown(server, session)


def _play_now(session, seed: int, names: list[str], args) -> int:
    """`--start`: the command line's own run, played at once. Today's behaviour."""
    try:
        started = session.start(seed, names, wait_for_page=not args.no_wait)
    except LobbyError as e:
        print(e, file=sys.stderr)
        return 2
    except FileExistsError:
        print(f"run directory already exists: {session.out_root}", file=sys.stderr)
        return 2
    if not args.no_wait:
        print("waiting for a browser to open the page (Ctrl-C to give up)", flush=True)
    try:  # the run itself holds its first decision until the page is listening
        session.wait()
    except KeyboardInterrupt:
        started.run.stop()
        session.wait(30)
    run = started.run
    if run.status != "completed":
        print(f"run {run.status}" + (f": {run.error}" if run.error else ""), file=sys.stderr)
    _report_run(run)
    if not args.no_wait and run.status != "interrupted":
        print("still serving the page; pick another track there, or Ctrl-C to stop.", flush=True)
        _serve_until_interrupted(session, printed={run.run_id})
    return 0 if run.status == "completed" else 1


def _serve_until_interrupted(session, printed: set | None = None) -> int:
    """Keeps serving while the page starts runs, reporting each one as it closes, until Ctrl-C."""
    printed = set() if printed is None else printed
    try:
        while True:
            for run in list(session.finished):
                if run.run_id not in printed:
                    printed.add(run.run_id)
                    if run.status != "completed":
                        print(f"run {run.status}" + (f": {run.error}" if run.error else ""), file=sys.stderr)
                    _report_run(run)
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0


def _report_run(run) -> None:
    print(f"run directory: {run.run_dir}")
    _print_report(run.run_dir)
    print(f"replay it later: python -m bakeoff view {run.run_dir}", flush=True)


def _shutdown(server, session) -> None:
    if session.run is not None and session.run.status == "running":
        session.run.stop()
        session.wait(30)
    server.shutdown()
    server.server_close()


def _print_report(run_dir) -> None:
    meta = load_meta(run_dir)
    print(f"status: {meta.get('status', 'unknown') if meta else 'unknown'}")
    if meta and meta.get("game"):
        print(f"game: {Rules.from_json(meta['game']).version}")
    print(format_table(summarize(load_steps(run_dir), meta)))


def _bench(args) -> int:
    from bakeoff.bench import benchmark, format_tables, load as load_runs, parse_source  # numpy: only for bench

    try:
        pairs = [tuple(n.strip() for n in pair.split(",")) for pair in args.pair]
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("--pair takes two players: A,B")
        if any(pair[0] == pair[1] for pair in pairs):
            raise ValueError("--pair takes two different players: A,B")
        if Path(args.output).suffix != ".html":
            raise ValueError("--output must end in .html (the numbers go next to it as .json)")
        loaded = load_runs([parse_source(s) for s in args.sources])
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    if not loaded.episodes:
        print("no complete episode in " + ", ".join(args.sources), file=sys.stderr)
        return 2
    out = benchmark(loaded)
    names = {p["player"] for p in out["players"]}
    unknown = sorted({n for pair in pairs for n in pair} - names)
    if unknown:
        print(f"--pair names players that are not in the runs: {', '.join(unknown)}", file=sys.stderr)
        return 2
    page, numbers = Path(args.output), Path(args.output).with_suffix(".json")
    try:
        numbers.write_text(json.dumps(out, indent=1), encoding="utf-8")
        page.write_text(render_html(out, page_name="bench.html"), encoding="utf-8")
    except OSError as e:
        print(f"cannot write {e.filename}: {e.strerror}", file=sys.stderr)
        return 2
    print(format_tables(out, pairs or None))
    print(f"\nbench: {page} and {numbers}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "bench":
        return _bench(args)
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
        rules = _rules(args)
        players = _players(args.players, DiskCache(args.cache), args.max_requests, rules)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_tournament_seeds(players, args.max_requests, args.seed_start, args.tournament):
        print(SEED_RULE.format(flag="--seed-start"), file=sys.stderr)
        return 2
    if _paid_window_mismatch(players, RULES[args.game].window, args.window):
        print(WINDOW_RULE.format(chosen=RULES[args.game].window, requested=args.window), file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start, "game": args.game,
                "lookahead": args.lookahead, "window": args.window, "max_rows": args.max_rows,
                "max_requests": args.max_requests, "cache": args.cache, "tournament": args.tournament}
    status = 0
    try:
        runner.run(players, seeds, rules, max_rows=args.max_rows, run_id=run_id, args=run_args)
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
Expected: `10 passed in 3.19s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `415 passed, 9 deselected in 26.54s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/__main__.py tests/test_cli_live.py
git commit -F <message file>   # feat: bakeoff live opens the lobby and keeps serving; --start plays the command line's own run
```

---

### Task 4: The lobby in the page

**Files:**
- Modify: `viewer/app.js`
- Modify: `viewer/index.html`
- Create: `viewer/lobby.js`
- Modify: `viewer/viewer.css`
- Test: `tests/test_view.py`
- Test: `viewer/tests/lobby.test.js`

**Interfaces:**
- `viewer/lobby.js` (pure, `node --test`): `usd(amount)`, `estimate(state, chosen) -> {rows, lines, total_usd}`, `estimateText(state, chosen)`, `whyNot(state, chosen, seed)`, `playerList(state, chosen)` (HTML, everything escaped), `ceilingText(state)`.
- `viewer/app.js`: `control(path, options)` (adds the token), `refreshState()`, `applyState(state)`, `watch(run)` (one `EventSource` per run), `resetTo(replay)` (the page starts again from a run's empty replay), `renderLobby()`, `pressedStart()` (arms once when a paid player is in the run), `startRun()`.
- `viewer/index.html`: a `#lobby` section, hidden unless the page has a server; `lobby.js` is loaded before `app.js`.

The estimate, the refusals and the ceiling are the page's own words for what `bakeoff/session.py` decides; the server decides again on `/run`. A replay file has no `data-live`, so the section stays hidden and nothing is fetched.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_view.py`:

```diff
@@ -59,7 +59,7 @@ def test_the_page_keeps_every_caveat_about_the_fly_and_about_jevs_questions():
 
 def test_every_script_the_page_names_exists_and_app_comes_last():
     names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
-    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "app.js"]
+    assert names == ["timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "lobby.js", "app.js"]
     assert all((VIEWER_DIR / name).is_file() for name in names)
 
 
```

Create `viewer/tests/lobby.test.js`:

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
            player("llm", { paid: true, price_usd: 0.0006, requests_left: 200 }),
            player("jev_composed", { paid: true, price_usd: 0.00003, requests_left: 200 }),
            player("glm_composed", { paid: true, price_usd: 0, requests_left: 200 })],
  ...extra,
});

test("the estimate is the worst case: every row a request, until the budget runs out", () => {
  const { rows, lines, total_usd } = Lobby.estimate(state(), ["fly", "llm", "jev_composed"]);
  assert.equal(rows, 150);
  assert.deepEqual(lines.map((l) => [l.player, l.requests]), [["llm", 150], ["jev_composed", 150]]);
  assert.equal(total_usd.toFixed(4), (150 * 0.0006 + 150 * 0.00003).toFixed(4));
  // a budget smaller than the track caps the estimate: the run stops when the cap is reached
  const short = Lobby.estimate(state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 20 })] }), ["llm"]);
  assert.deepEqual(short.lines.map((l) => l.requests), [20]);
  assert.equal(short.total_usd.toFixed(4), "0.0120");
});

test("a run of free players says it spends nothing, and the free tier says so too", () => {
  assert.match(Lobby.estimateText(state(), ["fly", "solver"]), /spends nothing/);
  const text = Lobby.estimateText(state(), ["glm_composed"]);
  assert.match(text, /0 USD \(free tier\)/);
  assert.match(text, /GLM COMPOSED 150 requests at worst/);
});

test("the estimate names each paid player, its worst case and whether the track was played before", () => {
  const played = state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 150, played_before: true })] });
  const text = Lobby.estimateText(played, ["llm"]);
  assert.match(text, /At worst this run of 150 rows spends 0.09 USD/);
  assert.match(text, /LLM 150 requests at worst, 0.09 USD, played before \(cached answers cost nothing\)/);
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
  const refused = state({ players: [player("llm", { paid: true, why_not: "no requests left" })] });
  assert.equal(Lobby.whyNot(refused, ["llm"], 7), "no requests left");
});

test("the player list marks the paid ones, their price and what is left of the cap", () => {
  const html = Lobby.playerList(state(), ["fly"]);
  assert.match(html, /value="fly" checked/);
  assert.match(html, /value="solver"(?! checked)/);
  assert.match(html, /0\.0006 USD a request · 200 left of the cap/);
  assert.match(html, /free tier · 200 left of the cap/); // GLM Flash
  assert.match(html, />free</);
});

test("a player that may not run is disabled and says why", () => {
  const blocked = state({ players: [player("llm", { paid: true, price_usd: 0.0006, requests_left: 0,
                                                    why_not: "llm has no requests left of this session's cap of 5" })] });
  const html = Lobby.playerList(blocked, []);
  assert.match(html, /disabled/);
  assert.match(html, /class="pick blocked"/);
  assert.match(html, /no requests left of this session&#39;s cap of 5/);
});

test("a name or a reason from the server is text, never markup", () => {
  const evil = "</label><script>alert(1)</script>";
  const html = Lobby.playerList(state({ players: [player(evil, { why_not: evil })] }), []);
  assert.equal(html.includes("<script>"), false);
  assert.match(html, /&#60;script&#62;/);
  assert.equal(Lobby.estimateText(state({ players: [player(evil, { paid: true, price_usd: 1, requests_left: 2 })] }),
                                  [evil]).includes("<script>"), false);
});

test("the ceiling is written out, cap or no cap", () => {
  assert.match(Lobby.ceilingText(state()), /without a cap, so paid players only replay answers that are already cached/);
  assert.match(Lobby.ceilingText(state()), /may only play seeds 1000 and up/);
  assert.match(Lobby.ceilingText(state({ max_requests: 700 })), /cap is 700 requests for each paid player/);
  assert.match(Lobby.ceilingText(state({ tournament: true })), /Seeds below 1000 are allowed here/);
  assert.match(Lobby.ceilingText(state()), /Nothing on this page can raise either\./);
});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_view.py::test_every_script_the_page_names_exists_and_app_comes_last
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ es...
2 failed, 13 passed in 0.65s
```

- [ ] **Step 3: Write the implementation**

Apply to `viewer/app.js`:

```diff
@@ -8,6 +8,7 @@
   const embedded = JSON.parse(document.getElementById("replay-data").textContent);
   if (!embedded) return;
   const liveUrl = document.body.dataset.live || null;
+  const token = document.body.dataset.token || null; // every control request carries it; a replay has none
 
   const $ = (id) => document.getElementById(id);
   const esc = Minds.esc;
@@ -82,6 +83,7 @@
       if (end.scoreboard) store.scoreboard = end.scoreboard;
       notice(end.status === "completed" ? null : "The run ended: " + end.status, false);
       renderAll();
+      if (liveUrl) refreshState(); // the run is over: the lobby comes back, with the run still on screen
     },
     onError(message) {
       if (store.ended) return;
@@ -397,6 +399,118 @@
     if (nth) focusOn(nth.episode.player, true);
   });
 
+  // ---- the lobby: the page starts the runs ----------------------------------------------------
+  const lobby = { state: null, chosen: [], armed: false, refusal: null, watching: null, source: null, timer: null };
+
+  async function control(path, options) {
+    const settings = options || {};
+    try {
+      const response = await fetch(path, { ...settings, headers: { "X-Bakeoff-Token": token, ...(settings.headers || {}) } });
+      const body = await response.json().catch(() => ({ error: "the server answered something that is not JSON" }));
+      return { ok: response.ok, body };
+    } catch (e) { // the command was stopped, or the machine went to sleep
+      return { ok: false, body: { error: "no answer from the run: is `bakeoff live` still going?" } };
+    }
+  }
+
+  const chosenSeed = () => Math.round(Number($("seed").value));
+
+  async function refreshState() {
+    const { ok, body } = await control("/state?seed=" + encodeURIComponent(chosenSeed()));
+    if (ok) applyState(body);
+    else { lobby.refusal = body.error; renderLobby(); }
+  }
+
+  function applyState(state) {
+    if (lobby.state == null) { // the first answer: the lobby opens with what the command line offered
+      lobby.chosen = (state.ready || {}).players || [];
+      if ((state.ready || {}).seed != null) $("seed").value = state.ready.seed;
+    }
+    lobby.state = state;
+    const run = state.run;
+    if (run && run.replay && lobby.watching !== run.run_id) watch(run);
+    renderLobby();
+  }
+
+  function watch(run) { // one stream per run, so a stream never runs on into the next one
+    lobby.watching = run.run_id;
+    if (lobby.source) lobby.source.close();
+    resetTo(run.replay);
+    notice("Waiting for the first decision…", false);
+    lobby.source = Feed.fromStream(liveUrl + "?run=" + encodeURIComponent(run.run_id) +
+                                   "&token=" + encodeURIComponent(token), handlers);
+  }
+
+  function resetTo(replay) { // a new run: the page starts again from that run's empty replay
+    Object.assign(store, { game: null, runs: [], players: [], seeds: [], tracks: {}, episodes: [],
+                           scoreboard: null, ended: false, error: null });
+    Object.assign(view, { seed: null, shown: new Set(), focus: null, auto: true, heldSince: 0, t: 0,
+                          playing: false, following: true, runners: [], panels: {} });
+    Feed.fromEmbedded(replay, handlers);
+    renderAll();
+  }
+
+  function renderLobby() {
+    const state = lobby.state;
+    if (!state) return;
+    const running = state.status === "running";
+    $("picks").innerHTML = Lobby.playerList(state, lobby.chosen);
+    $("estimate").textContent = Lobby.estimateText(state, lobby.chosen);
+    $("ceiling").textContent = Lobby.ceilingText(state);
+    const why = lobby.refusal || Lobby.whyNot(state, lobby.chosen, chosenSeed());
+    $("lobby-why").hidden = !why;
+    $("lobby-why").textContent = why || "";
+    const cost = Lobby.estimate(state, lobby.chosen);
+    $("start").disabled = !!why;
+    $("start").textContent = !lobby.armed ? "Start"
+      : "Confirm: start and spend at most " + Lobby.usd(cost.total_usd);
+    $("start").dataset.armed = String(lobby.armed);
+    $("cancel").hidden = !running;
+    $("seed").disabled = running;
+  }
+
+  function pressedStart() {
+    const state = lobby.state;
+    if (!state || Lobby.whyNot(state, lobby.chosen, chosenSeed())) return;
+    // a run with a paid player in it is confirmed once, with its worst case on the button
+    if (Lobby.estimate(state, lobby.chosen).lines.length && !lobby.armed) {
+      lobby.armed = true;
+      return renderLobby();
+    }
+    startRun();
+  }
+
+  async function startRun() {
+    lobby.armed = false;
+    lobby.refusal = null;
+    const { ok, body } = await control("/run", { method: "POST", headers: { "Content-Type": "application/json" },
+                                                 body: JSON.stringify({ seed: chosenSeed(), players: lobby.chosen }) });
+    if (!ok) lobby.refusal = body.error || "the run was refused";
+    if (ok && body.state) applyState(body.state);
+    else renderLobby();
+  }
+
+  $("lobby-form").addEventListener("submit", (event) => { event.preventDefault(); pressedStart(); });
+  $("picks").addEventListener("change", () => {
+    lobby.chosen = [...$("picks").querySelectorAll("input[name=player]:checked")].map((input) => input.value);
+    lobby.armed = false;
+    lobby.refusal = null;
+    renderLobby();
+  });
+  $("seed").addEventListener("input", () => { // another track: another set of prices and refusals
+    lobby.armed = false;
+    lobby.refusal = null;
+    renderLobby();
+    clearTimeout(lobby.timer);
+    lobby.timer = setTimeout(refreshState, 300);
+  });
+  $("cancel").addEventListener("click", async () => {
+    const { ok, body } = await control("/cancel", { method: "POST" });
+    if (!ok) lobby.refusal = body.error || "the run could not be stopped";
+    if (ok && body.state) applyState(body.state);
+    else renderLobby();
+  });
+
   // ---- the sections underneath --------------------------------------------------------------
   function renderBelow() {
     const board = store.scoreboard || { columns: [], rows: [], same_seeds: true };
@@ -441,10 +555,10 @@
   window.addEventListener("resize", () => { resize(); draw(); });
   if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw); // the canvas tags use the embedded mono
   if (liveUrl) {
-    notice("Waiting for the first decision…", false);
     const clear = handlers.onFrame;
     // a frame means the stream is alive: the waiting or the lost-connection notice goes, a real error stays
     handlers.onFrame = (...args) => { if (store.error == null) notice(null); clear(...args); };
-    Feed.fromStream(liveUrl, handlers);
+    $("lobby").hidden = false; // the page runs the show; a replay file has no server and no controls
+    refreshState();
   }
 })();
```

Apply to `viewer/index.html`:

```diff
@@ -25,6 +25,22 @@
       Everyone is on the same row at the same time: a jump covers two rows, so it takes two ticks.</p>
   </section>
 
+  <section id="lobby" aria-label="Start a run" hidden>
+    <h2 class="label">Start a run</h2>
+    <form id="lobby-form">
+      <div class="lobby-top">
+        <label class="label" for="seed">Track</label>
+        <input id="seed" type="number" min="0" step="1" value="1001" inputmode="numeric">
+        <button id="start" type="submit" class="label">Start</button>
+        <button id="cancel" type="button" class="label" hidden>Cancel the run</button>
+      </div>
+      <div id="picks" role="group" aria-label="Who runs"></div>
+      <p class="note" id="estimate"></p>
+      <p class="note warn" id="lobby-why" hidden></p>
+      <p class="note" id="ceiling"></p>
+    </form>
+  </section>
+
   <section aria-label="Levels">
     <h2 class="label">Levels</h2>
     <div class="scroll"><table id="matrix"></table></div>
@@ -115,6 +131,7 @@
 <script src="stage.js"></script>
 <script src="minds.js"></script>
 <script src="feed.js"></script>
+<script src="lobby.js"></script>
 <script src="app.js"></script>
 </body>
 </html>
```

Create `viewer/lobby.js`:

```javascript
// The lobby: who may run, what a run would cost at worst, and the list the page shows. Pure and
// tested under node; app.js does the fetching and the DOM. Everything that comes from the server
// goes through esc(): a player name or a refusal is text, never markup.
//
// `state` is what GET /state answers (bakeoff/session.py): {status, game, max_rows, requests_per_row,
// max_requests, tournament, first_practice_seed, seed, players: [{name, paid, price_usd,
// requests_left, played_before, why_not}], run}.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const esc = Minds_.esc;
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
      (line.played_before ? ", played before (cached answers cost nothing)" : ""));
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

  // One row per player: a checkbox, what it is, and what it would cost.
  function playerList(state, chosen) {
    return (state.players || []).map((player) => {
      const on = chosen.includes(player.name);
      const notes = [];
      if (player.paid) {
        notes.push(player.price_usd > 0 ? usd(player.price_usd) + " a request" : "free tier");
        notes.push((player.requests_left || 0) + " left of the cap");
      } else {
        notes.push("free");
      }
      if (player.played_before) notes.push("played before");
      return '<label class="pick' + (player.why_not ? " blocked" : "") + '">' +
        '<input type="checkbox" name="player" value="' + esc(player.name) + '"' + (on ? " checked" : "") +
        (player.why_not ? " disabled" : "") + ">" +
        '<span class="label tag">' + esc(tagOf(player.name)) + "</span>" +
        '<span class="about">' + esc(player.name) + "</span>" +
        '<span class="note">' + esc(notes.join(" · ")) + "</span>" +
        (player.why_not ? '<span class="note warn">' + esc(player.why_not) + "</span>" : "") +
        "</label>";
    }).join("");
  }

  // The line under the lobby: the ceiling the command set, and the seed rule.
  function ceilingText(state) {
    const cap = state.max_requests === 0
      ? "This command was started without a cap, so paid players only replay answers that are already cached."
      : "This command's cap is " + state.max_requests + " requests for each paid player, for the whole session.";
    const seeds = state.tournament
      ? "Seeds below " + state.first_practice_seed + " are allowed here (--tournament)."
      : "Paid players may only play seeds " + state.first_practice_seed + " and up; the tournament seeds are kept unseen.";
    return cap + " " + seeds + " Nothing on this page can raise either.";
  }

  const api = { usd, estimate, estimateText, whyNot, playerList, ceilingText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lobby = api;
})(typeof window !== "undefined" ? window : globalThis);
```

Apply to `viewer/viewer.css`:

```diff
@@ -153,3 +153,22 @@ table { border-collapse: collapse; font-size: var(--size-small); font-variant-nu
   #speeds button[data-speed="1"], #speeds button[data-speed="20"] { display: none; }
   #auto { margin-left: auto; }
 }
+
+/* ---- the lobby: the page starts the runs ------------------------------------------------------ */
+#lobby form { max-width: 900px; }
+.lobby-top { display: flex; align-items: center; gap: 12px; margin-bottom: var(--gutter); }
+.lobby-top input { width: 9ch; padding: 6px 8px; background: var(--panel); color: var(--bright);
+  border: 1px solid var(--line-strong); font: inherit; }
+#lobby button { padding: 8px 14px; background: var(--panel); color: var(--bright);
+  border: 1px solid var(--line-strong); cursor: pointer; }
+#lobby button[disabled] { color: var(--muted); cursor: not-allowed; }
+#lobby button[data-armed="true"] { border-color: var(--warn); color: var(--warn); }
+#cancel { border-color: var(--bad); color: var(--bad); }
+#picks { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1px;
+  background: var(--hairline); border: 1px solid var(--hairline); }
+.pick { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; align-items: baseline;
+  padding: 10px 12px; background: var(--panel); cursor: pointer; }
+.pick input { grid-row: span 3; align-self: center; accent-color: var(--accent); }
+.pick .about { color: var(--muted); font-size: var(--size-small); }
+.pick .note { grid-column: 2; margin-top: 0; font-size: var(--size-label-sm); }
+.pick.blocked { opacity: 0.55; cursor: not-allowed; }
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_view.py tests/test_viewer_js.py`
Expected: `15 passed in 0.40s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `415 passed, 9 deselected in 26.79s`

- [ ] **Step 6: Commit**

```bash
git add tests/test_view.py viewer/app.js viewer/index.html viewer/lobby.js viewer/tests/lobby.test.js viewer/viewer.css
git commit -F <message file>   # feat: the page picks the track and the players, shows the worst case and starts and cancels the run
```

---

### Task 5: The docs say what the command and the page now do

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/UPDATES.md`

**Interfaces:**
`CLAUDE.md` gains the update 3a bullet (the routes, the token, the session's budgets, `--start`); `docs/UPDATES.md` records items 4, 5, 8, 9 as update 3a built and 3b next.

- [ ] **Step 1: Write the implementation**

Apply to `CLAUDE.md`:

```diff
@@ -75,11 +75,18 @@ gets its own plan.
   `viewer/fonts/` are embedded as base64 by `bakeoff/view.py`). The page is the user's brand: tokens from
   `~/Documents/PROJECTS/BRAND/brand.css`, blue only for the cursor (the mind in focus and its tiles), mono for short
   labels only, deaths and errors `--bad`, warnings `--warn`. Frames reach `app.js` through `Feed` alone.
-- `bakeoff live` (`bakeoff/live.py`, `bakeoff/live_server.py`) plays one track in lockstep by row, records a
-  normal run directory and streams it to the page over Server-Sent Events on `127.0.0.1` only (standard
-  library, no dependency). It builds one fly brain in its own process: never start it next to another fly run.
-  Its records come from `runner.play_row` and its frames from `replay.frame_of`, the same functions `run` and
+- `bakeoff live` (`bakeoff/live.py`, `bakeoff/live_server.py`, `bakeoff/session.py`) plays one track in lockstep by
+  row, records a normal run directory and streams it to the page over Server-Sent Events on `127.0.0.1` only
+  (standard library, no dependency). It builds one fly brain in its own process: never start it next to another fly
+  run. Its records come from `runner.play_row` and its frames from `replay.frame_of`, the same functions `run` and
   `view` use; keep it that way.
+- The page runs the show (update 3a, design `docs/superpowers/specs/2026-09-22-page-control-design.md`): the command
+  binds the port and sets the ceiling, the lobby in the browser picks the track and the players and starts and
+  cancels the run (`GET /state`, `POST /run`, `POST /cancel`, `GET /events?run=`). Every request but the page itself
+  carries a token minted at startup and embedded in the page. One `LiveSession` per command holds one budget per
+  paid player for the whole session (`SharedBudget` gives each run its own record of what it spent), runs one
+  `LiveRun` at a time and keeps serving so another track can be played without restarting. `--start` plays the
+  command line's own run at once, as before, and holds its first decision until a browser is listening.
 - Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
   raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
   request on a seed below 1000 before the tournament; the CLI refuses a live paid run on seeds
```

Apply to `docs/UPDATES.md`:

```diff
@@ -37,7 +37,10 @@ Branch: `phase6-updates`.
   `glm-4.5-flash`, the same questions and rules as their Jev and Haiku twins. Built; track 1000 recorded, the rest
   parked while the free tier throttles (`docs/COSTS.md`).
 - Items 4, 5, 8, 9, the page: approved design (decision 35,
-  `docs/superpowers/specs/2026-09-22-page-control-design.md`), to be built as updates 3a and 3b. Not built.
+  `docs/superpowers/specs/2026-09-22-page-control-design.md`), built as updates 3a and 3b. **Update 3a is built**
+  (plan `docs/superpowers/plans/2026-09-22-update3a-page-control.md`): the control channel, the money ceiling for a
+  whole session and the lobby, so the page picks the track and the players and starts and cancels the run. Update 3b
+  (the logs in the mind panels, the Run and Analysis tabs, the player picker in a replay) is next.
 - Item 7, the benchmark (decision 31, `docs/superpowers/specs/2026-09-22-benchmark-design.md`): built; `python -m
   bakeoff bench` scores recorded runs with intervals, pairs, time and cost per row, and writes its own page.
 
```

- [ ] **Step 2: Run all tests**

Run: `uv run pytest -q`
Expected: `415 passed, 9 deselected in 29.24s`

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/UPDATES.md
git commit -F <message file>   # docs: the page runs the show (update 3a): the control channel, the session ceiling and the lobby
```

---

### Task 6: Look at it (controller only)

Nothing here is dispatched to an implementer. Free players only; no paid player, no fly.

- [ ] `uv run python -m bakeoff live --port 8765 --out /tmp/lobby-check --players solver,random,always_jump`, then open `http://127.0.0.1:8765/` and start a run from the page. Watch: the tunnel fills, the lobby comes back when the run ends with the run still on screen, and a second track can be started without restarting the command.
- [ ] While a run is going: the Cancel button appears and the track box is disabled; cancelling leaves a run directory with status `interrupted` that `python -m bakeoff view` still replays.
- [ ] Tick a paid player with the default cap of 0: the estimate names it and its worst case, the Start button arms once with the amount, and changing the track disarms it. Type a track below 1000: the paid player is greyed out and says why, and Start is refused. **Do not start a paid run.**
- [ ] `--start` still behaves as before: `uv run python -m bakeoff live --port 8765 --out /tmp/lobby-check --start --seed 1010 --players solver,random`; the terminal waits for a browser, the run holds its first decision until the page is open, and the report is printed when it ends.
- [ ] A replay file has no controls: `uv run python -m bakeoff view <a run directory> --output /tmp/replay.html` and check the lobby section stays hidden and nothing is fetched.
- [ ] Delete `.playwright-mcp/` if a browser check wrote screenshots into the repo, and remove `/tmp/lobby-check`.

### Task 7: Review (controller only)

- [ ] A task review after each task (the diff against the prototype, then a reviewer on the diff).
- [ ] A whole-update review aimed at the design, not at transcription: money safety (the ceiling cannot be raised from the page; the seed rule holds on every path; each run's `meta.json` records what that run spent), key safety (the token, loopback only, nothing else served), honest records (a cancelled run is `interrupted`, a run directory is a normal one), and the page's wording (the estimate is a worst case and says so; "played before" is not a promise of a free run).
- [ ] Then `docs/NEXT.md` is rewritten for update 3b.
