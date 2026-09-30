# Phase 5a: The Composed Jev (`jev_composed`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a second Jev player, `jev_composed`, that asks Jev four pointed yes/no questions per row ("would this action land on a gap?") and lets code pick the action least likely to land on a gap; the report scores the four answers; one recorded run on practice track 1000 for the demo.

**Architecture:** `bakeoff/senses.py` gains the one table that says where each action lands (`LANDS`) and `lands_on_gap(senses, action)`, read from the senses alone. `bakeoff/players/jev_composed.py` builds its four questions from that table, reuses `PaidPlayer` and `JevClient` unchanged (same cache, cap, error and fallback rules as `jev`) and adds only `read()` (four Nouls to a move) and the two extra `info` keys. The report scores the four Nouls against what the record's senses show, so the step record and `ground_truth` do not change.

**Tech Stack:** Python 3.13, `uv`, `pytest`. No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-20-demo-player-design.md`, section "Phase 5a" (binding). Background: `docs/DECISIONS.md` decisions 14, 15 and 19; `spikes/02-jev-questions/REPORT.md` on branch `spike/jev-questions`.

**Branch:** `phase5-demo-player` (already created, rebased onto `main` after PR #3 was merged; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add` in this phase.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network**: the TypeSafe SDK is replaced by the fakes in `tests/fakes.py`.
- **Tasks 1 to 3 spend no money.** No `--max-requests`, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run` with a paid player. Task 4 is the only paid step and belongs to the controller alone, inside decision 19's ceiling.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command. Nothing in tasks 1 to 3 needs it.
- **Frozen:** the fly and its constants, `bakeoff/game/`, `bakeoff/fly/`, `bakeoff/clients/`, `bakeoff/players/paid.py`, `bakeoff/players/jev.py`, `bakeoff/players/llm.py`, `bakeoff/players/briefing.py`, `bakeoff/runner.py`, `calibration/`. `bakeoff/senses.py` only gains `LANDS` and `lands_on_gap`; nothing existing in it changes. The step record does not change; `schema_version` stays 1.
- **Seed hygiene:** the question wording is the spike's, fixed before this plan; it is verified on practice seeds 1000 and up only and frozen before any tournament seed is touched.
- **Honesty:** the wording of the four questions and the pick-the-safest rule are ours, not TypeSafe's, and every document that describes the player says so. It looks one step ahead only.
- Every code block below was run in a prototype and passes as written (final state: 262 fast tests, 9 deselected). If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **The truth of the four Nouls is read from the record's senses, not added to `ground_truth`.** The questions literally ask what the senses show ("does `ahead[0].gaps_relative` contain -1?"), every record carries its senses, and the spec forbids a change to the step record. `bakeoff.senses.lands_on_gap` is that truth; `ground_truth` keeps its two keys for the one-shot `jev`.
2. **`lands_on_gap` and the engine differ in one place, by design:** past the finish line a gap no longer kills, but the senses still show it. On the last row a jump can therefore read "lands on a gap" and be safe. The composed Jev may avoid that jump; any other safe move finishes the track just the same. The test pins the agreement up to the finish line.
3. **One table for where actions land** (`LANDS` in `bakeoff/senses.py`): the questions are generated from it and the report reads it, so the wording and the scoring cannot drift apart. The generated wording is asserted literally against the spike's text.
4. **Invalid means all or nothing:** any of the four Nouls missing, not a number, a bool, or not finite makes the decision invalid (`chosen_action` null, the runner executes `stay`). The answers that did arrive are still logged.
5. **`info` is extended by overriding `act()`** (`{model, rule, order}`), leaving `PaidPlayer` untouched. After a provider error `info` stays null, as for the other paid players.
6. **The report's four new columns go last** (`brier_gap_left`, `brier_gap_stay`, `brier_gap_right`, `brier_gap_jump`), so existing columns keep their place; they are `-` for every other player.
7. **The CLI's help names the paid players from `PAID`,** so the next paid player cannot be forgotten there. The seed rule and the cap already key on `PAID`.
8. **What the rule can and cannot do, measured for free before any request:** with perfect answers the rule survives 246 rows of practice track 1000 (it dies where all four landing tiles are gaps one step ahead), finishes 1001, and reaches 162, 237, 123 and 197 rows on 1002 to 1005. That is the ceiling of "one step ahead", not of Jev.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/senses.py` | `LANDS`, `lands_on_gap(senses, action)` | 1 |
| `bakeoff/players/jev_composed.py` | `QUESTIONS`, `ORDER`, `RULE`, `pick()`, `JevComposedPlayer` | 1 |
| `bakeoff/players/__init__.py` | registry entry and `PAID` | 1 |
| `tests/fakes.py` | `jev_composed_reply` | 1 |
| `tests/test_jev_composed.py`, `tests/test_senses.py`, `tests/test_players.py` | tests | 1 |
| `bakeoff/report.py`, `tests/test_report.py` | four Brier columns scored against the senses | 2 |
| `bakeoff/__main__.py`, `tests/test_cli.py` | help text from `PAID`; the seed rule covers the new player | 3 |
| `README.md`, `docs/STEP_RECORD.md` | the player, what is ours, how its Nouls are scored | 3 |
| `docs/COSTS.md`, `docs/DECISIONS.md`, `CLAUDE.md` | the recorded run (controller) | 4 |

---

### Task 1: Where actions land, and the `jev_composed` player

**Files:**
- Modify: `bakeoff/players/__init__.py`
- Create: `bakeoff/players/jev_composed.py`
- Modify: `bakeoff/senses.py`
- Modify: `tests/fakes.py`
- Test: `tests/test_jev_composed.py`
- Test: `tests/test_players.py`
- Test: `tests/test_senses.py`

**Interfaces:**
- Consumes: `PaidPlayer` (`read(payload) -> (action, invalid, answers)`, `act`), `JevClient`, `FakeTypeSafe`, `Runner.run_seed`.
- Produces: `bakeoff.senses.LANDS: dict[str, tuple[int, int]]` (action -> index into `ahead`, lane offset) and `lands_on_gap(senses, action) -> bool`; `bakeoff.players.jev_composed`: `QUESTIONS`, `ORDER`, `RULE`, `pick(nouls) -> str`, `JevComposedPlayer`; registry name `jev_composed`, in `PAID`; `tests.fakes.jev_composed_reply(left, stay, right, jump)`.

`tests/fakes.py` is test support, not a test: it is written in Step 3 with the implementation, so Step 2 fails at import.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_jev_composed.py`:

```python
import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import Game
from bakeoff.game.track import generate_track
from bakeoff.players import PAID, make_player
from bakeoff.players.jev_composed import ORDER, QUESTIONS, JevComposedPlayer, pick
from bakeoff.runner import Runner
from bakeoff.senses import LANDS, compute_senses, lands_on_gap
from tests.fakes import FakeTypeSafe, jev_composed_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return JevComposedPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_four_pointed_nouls_one_per_action_worded_as_in_the_spike():
    assert list(QUESTIONS) == ["gap_left", "gap_stay", "gap_right", "gap_jump"]
    assert all(q["type"] == "noul" for q in QUESTIONS.values())
    assert QUESTIONS["gap_left"]["instructions"] == (
        "Would the action `left` land the runner on a gap, that is, does `ahead[0].gaps_relative` contain -1?")
    assert QUESTIONS["gap_stay"]["instructions"].endswith("does `ahead[0].gaps_relative` contain 0?")
    assert QUESTIONS["gap_right"]["instructions"].endswith("does `ahead[0].gaps_relative` contain 1?")
    assert QUESTIONS["gap_jump"]["instructions"] == (
        "Would the action `jump` land the runner on a gap, that is, does `ahead[1].gaps_relative` contain 0?")


def test_it_is_a_paid_player_in_the_registry(tmp_path):
    assert "jev_composed" in PAID
    made = make_player("jev_composed", cache=DiskCache(tmp_path), budget=RequestBudget(0))
    assert isinstance(made, JevComposedPlayer) and made.name == "jev_composed" and made.model == "jev-latest"


def test_the_sdk_gets_the_senses_and_four_typed_nouls_in_one_request(tmp_path):
    from typesafe_sdk import Noul

    jev, sdk = player(tmp_path, jev_composed_reply())
    senses = senses_for()
    jev.act(senses)
    (call,) = sdk.calls
    assert call["state"] == senses and call["model"] == "jev-latest"
    assert set(call["questions"]) == set(QUESTIONS)
    assert all(isinstance(q, Noul) for q in call["questions"].values())
    assert call["questions"]["gap_jump"].instructions == QUESTIONS["gap_jump"]["instructions"]


def test_the_move_is_the_action_least_likely_to_land_on_a_gap(tmp_path):
    jev, _ = player(tmp_path, jev_composed_reply(left=0.9, stay=0.8, right=0.03, jump=0.4))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "right" and not decision.needs_fallback and not decision.gated
    assert decision.questions == QUESTIONS
    assert {k: v["noul"] for k, v in decision.answers.items()} == {
        "gap_left": 0.9, "gap_stay": 0.8, "gap_right": 0.03, "gap_jump": 0.4}
    assert decision.usage == {"input_tokens": 300, "output_tokens": 4}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "jev-latest", "rule": "lowest_gap_probability",
                             "order": ["stay", "left", "right", "jump"]}


def test_ties_after_rounding_to_two_decimals_go_in_the_solvers_order():
    assert ORDER == ("stay", "left", "right", "jump")
    assert pick({"left": 0.1, "stay": 0.1, "right": 0.1, "jump": 0.1}) == "stay"
    assert pick({"left": 0.012, "stay": 0.5, "right": 0.008, "jump": 0.014}) == "left"  # all three round to 0.01
    assert pick({"left": 0.5, "stay": 0.5, "right": 0.021, "jump": 0.019}) == "right"  # both round to 0.02
    assert pick({"left": 0.5, "stay": 0.5, "right": 0.03, "jump": 0.02}) == "jump"


def test_it_is_never_gated_even_when_every_action_looks_fatal(tmp_path):
    jev, _ = player(tmp_path, jev_composed_reply(left=0.99, stay=0.98, right=0.99, jump=0.99))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "stay" and not decision.gated and not decision.needs_fallback


@pytest.mark.parametrize("broken", [None, "0.2", True, float("nan"), {"type": "noul"}])
def test_a_missing_or_non_numeric_noul_is_invalid_never_half_a_judgment(tmp_path, broken):
    jev, _ = player(tmp_path, jev_composed_reply())
    answers = jev_composed_reply(right=0.0)["answers"]
    answers["gap_jump"] = broken if isinstance(broken, dict) else {"type": "noul", "noul": broken}
    action, invalid, logged = jev.read({"answers": answers})
    assert action is None and invalid and logged == answers
    assert jev.read({}) == (None, True, {})


def test_an_invalid_answer_is_logged_and_left_to_the_runners_fallback(tmp_path):
    reply = jev_composed_reply(right=0.0)
    del reply["answers"]["gap_jump"]
    jev, _ = player(tmp_path, reply)
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.invalid and decision.needs_fallback
    assert set(decision.answers) == {"gap_left", "gap_stay", "gap_right"}
    assert decision.info["rule"] == "lowest_gap_probability"


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    jev, sdk = player(tmp_path, jev_composed_reply(left=0.0))
    senses = senses_for()
    jev.act(senses)
    again = jev.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and jev.budget.used == 1


def test_the_one_shot_jev_never_answers_from_the_composed_jevs_cache(tmp_path):
    from bakeoff.players.jev import JevPlayer
    from tests.fakes import jev_reply

    composed, _ = player(tmp_path, jev_composed_reply())
    senses = senses_for()
    composed.act(senses)
    one_shot = JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(0), sdk=FakeTypeSafe(jev_reply()))
    with pytest.raises(BudgetExhausted):  # same provider, model and senses, other questions: another key
        one_shot.act(senses)


def test_a_provider_error_becomes_a_logged_error_and_the_cap_ends_the_run(tmp_path):
    from typesafe_sdk import TypeSafeAPIConnectionError

    jev, _ = player(tmp_path, TypeSafeAPIConnectionError("connection refused"))
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.error == "TypeSafeAPIConnectionError: connection refused"
    assert decision.info is None and decision.questions == QUESTIONS
    capped, sdk = player(tmp_path / "other", jev_composed_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        capped.act(senses_for())
    assert sdk.calls == []


class TruthfulTypeSafe(FakeTypeSafe):
    """Answers the four questions from the state it is sent, as a Jev that reads the track perfectly would."""

    def system_one(self, state, questions, model=None):
        self.reply = jev_composed_reply(**{action: float(lands_on_gap(state, action)) for action in LANDS})
        return super().system_one(state, questions, model)


def test_with_perfect_answers_it_runs_a_practice_track_through_the_runner(tmp_path):
    sdk = TruthfulTypeSafe(None)
    jev = JevComposedPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(100), sdk=sdk)
    records = Runner(tmp_path / "runs").run_seed(jev, 1001, "r", max_rows=60)
    assert records[-1]["finished"] and records[-1]["rows_survived"] == 60
    assert all(r["executed_action"] == r["chosen_action"] and not r["invalid"] for r in records)
    assert {r["executed_action"] for r in records} > {"stay"}  # it had to dodge or jump on the way
    assert jev.budget.used == len(records) == len(sdk.calls)
    assert set(records[0]["answers"]) == set(QUESTIONS) and records[0]["info"]["rule"] == "lowest_gap_probability"
```

Apply to `tests/test_players.py`:

```diff
@@ -29,8 +29,8 @@ def test_decision_defaults_and_fallback_rule():
 
 
 def test_factory_knows_the_baselines_and_rejects_unknown_names():
-    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "llm"}
-    assert set(PAID) == {"jev", "llm"}
+    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "jev_composed", "llm"}
+    assert set(PAID) == {"jev", "jev_composed", "llm"}
     assert all(make_player(name).name == name for name in REGISTRY)  # a paid player without a budget only replays
     with pytest.raises(KeyError, match="unknown player 'nope'"):
         make_player("nope")
```

Apply to `tests/test_senses.py`:

```diff
@@ -1,7 +1,8 @@
 import json
 
 from bakeoff.game.engine import Game
-from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ, compute_senses, ground_truth, looming_rates
+from bakeoff.senses import (LANDS, LOOMING_STEP_HZ, MAX_HZ, compute_senses, ground_truth, lands_on_gap,
+                            looming_rates)
 
 
 def test_senses_shape_matches_the_spec(make_track):
@@ -88,3 +89,26 @@ def test_rates_are_capped_at_250_hz(make_track):
 def test_ground_truth(make_track):
     assert ground_truth(Game(make_track({1: [6]}))) == {"gap_ahead": True, "left_safe": True}
     assert ground_truth(Game(make_track({1: [5]}))) == {"gap_ahead": False, "left_safe": False}
+
+
+def test_lands_on_gap_reads_each_actions_landing_tile_from_the_senses(make_track):
+    senses = compute_senses(Game(make_track({1: [5], 2: [6]})))  # row 1: a gap to the left; row 2: a gap ahead
+    assert {a: lands_on_gap(senses, a) for a in LANDS} == {"left": True, "stay": False, "right": False, "jump": True}
+
+
+def test_lands_on_gap_agrees_with_the_engine_up_to_the_finish_line():
+    from bakeoff.game.track import generate_track
+
+    checked = 0
+    for action, (ahead, _) in LANDS.items():
+        game = Game(generate_track(1000, max_rows=60))
+        while not game.over:
+            senses = compute_senses(game)
+            if game.row + ahead + 1 <= game.track.max_rows:  # past the finish line a gap no longer kills
+                probe = Game(game.track)
+                probe.row, probe.lane = game.row, game.lane
+                probe.step(action)
+                assert (not probe.alive) == lands_on_gap(senses, action)
+                checked += 1
+            game.step(next(a for a in ("stay", "left", "right", "jump") if not lands_on_gap(senses, a)))
+    assert checked > 200
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_jev_composed.py tests/test_senses.py tests/test_players.py`
Expected:

```text
ERROR tests/test_jev_composed.py
ERROR tests/test_senses.py
2 errors in 0.20s
```

- [ ] **Step 3: Write the implementation**

Replace the whole of `bakeoff/players/__init__.py` with:

```python
from __future__ import annotations

from typing import Callable

from bakeoff.players.always_jump import AlwaysJumpPlayer
from bakeoff.players.base import Player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.jev import JevPlayer
from bakeoff.players.jev_composed import JevComposedPlayer
from bakeoff.players.llm import LlmPlayer
from bakeoff.players.random_player import RandomPlayer
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
    "jev": JevPlayer, "jev_composed": JevComposedPlayer, "llm": LlmPlayer}
PAID = ("jev", "jev_composed", "llm")  # these take cache= and budget=; without a budget they can only replay the cache


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
```

Create `bakeoff/players/jev_composed.py`:

```python
"""Composed Jev: one request per row with four pointed yes/no questions, one per action ("would this
action land on a gap?", naming the value to look up), and code that picks the action Jev thinks is
least likely to land on a gap. OURS, not TypeSafe's: the wording of the questions and the rule that
turns four answers into a move (docs/DECISIONS.md, decisions 14 and 15). It looks one step ahead only;
it does not plan. The one-shot `jev` stays as it was, for comparison."""

from __future__ import annotations

import math

from bakeoff.clients.jev import JevClient
from bakeoff.players.base import Decision
from bakeoff.players.paid import PaidPlayer
from bakeoff.senses import LANDS

RULE = "lowest_gap_probability"
ORDER = ("stay", "left", "right", "jump")  # ties go to the first of these: the reference solver's order

# The Noul ids are `gap_<action>`; the report scores them against the senses (bakeoff.senses.lands_on_gap).
QUESTIONS = {
    f"gap_{action}": {"type": "noul",
                      "instructions": f"Would the action `{action}` land the runner on a gap, that is, does "
                                      f"`ahead[{ahead}].gaps_relative` contain {offset}?"}
    for action, (ahead, offset) in LANDS.items()}


def pick(nouls: dict[str, float]) -> str:
    """The action with the lowest P(lands on a gap) after rounding to two decimals; ties in ORDER."""
    return min(ORDER, key=lambda action: round(nouls[action], 2))


class JevComposedPlayer(PaidPlayer):
    name = "jev_composed"
    client_class = JevClient
    questions = QUESTIONS

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers = payload.get("answers") or {}
        nouls = {action: (answers.get(f"gap_{action}") or {}).get("noul") for action in ORDER}
        if not all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)
                   for n in nouls.values()):
            return None, True, answers  # never half a judgment: all four, or the runner's fallback
        return pick(nouls), False, answers

    def act(self, senses: dict) -> Decision:
        decision = super().act(senses)
        if decision.info is not None:
            decision.info = {**decision.info, "rule": RULE, "order": list(ORDER)}
        return decision
```

Apply to `bakeoff/senses.py`:

```diff
@@ -20,6 +20,9 @@ ACTION_DESCRIPTIONS = {
     "left": "move one lane left", "right": "move one lane right",
     "jump": "clear the next row, land on the one after", "stay": "run straight",
 }
+# Where each action lands, as (index into `ahead`, lane offset): the rule of the game, written once for
+# everything that reads senses (the composed Jev's questions, the report's truth for them).
+LANDS = {"left": (0, -1), "stay": (0, 0), "right": (0, 1), "jump": (1, 0)}
 
 
 def compute_senses(game: Game) -> dict:
@@ -51,3 +54,11 @@ def looming_rates(senses: dict, gain_hz: float = LOOMING_GAIN_HZ,
 def ground_truth(game: Game) -> dict:
     return {"gap_ahead": game.track.is_gap(game.row + 1, game.lane),
             "left_safe": not game.track.is_gap(game.row + 1, game.lane - 1)}
+
+
+def lands_on_gap(senses: dict, action: str) -> bool:
+    """Does `action` land on a tile the senses show as a gap? Read from the senses alone, so it can be
+    asked of a logged record. It is the truth of the composed Jev's questions, which ask about the senses;
+    the engine differs only past the finish line, where a gap no longer kills."""
+    ahead, offset = LANDS[action]
+    return offset in senses["ahead"][ahead]["gaps_relative"]
```

Apply to `tests/fakes.py`:

```diff
@@ -30,6 +30,13 @@ def jev_reply(action="stay", gap_ahead=0.1, left_safe=0.9):
                         "left_safe": {"type": "noul", "noul": left_safe}}}
 
 
+def jev_composed_reply(left=0.1, stay=0.1, right=0.1, jump=0.1):
+    """P(lands on a gap) per action, as the four Nouls of the composed Jev."""
+    nouls = {"left": left, "stay": stay, "right": right, "jump": jump}
+    return {"model": "jev-latest", "usage": {"input_tokens": 300, "output_tokens": 4},
+            "answers": {f"gap_{action}": {"type": "noul", "noul": p} for action, p in nouls.items()}}
+
+
 class FakeAnthropic:
     """Looks like anthropic.Anthropic. `reply` is a Message-shaped dict, or an exception to raise."""
 
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_jev_composed.py tests/test_senses.py tests/test_players.py`
Expected: `47 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `259 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/players/__init__.py bakeoff/players/jev_composed.py bakeoff/senses.py tests/fakes.py tests/test_jev_composed.py tests/test_players.py tests/test_senses.py
git commit -F <message file>   # feat: jev_composed player: four pointed Nouls, code picks the action least likely to land on a gap
```

---

### Task 2: Report: the four Nouls scored against what the senses show

**Files:**
- Modify: `bakeoff/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `bakeoff.senses.LANDS`, `lands_on_gap` (Task 1); step records' `answers` and `senses`.
- Produces: `COLUMNS` ends with `brier_gap_left`, `brier_gap_stay`, `brier_gap_right`, `brier_gap_jump`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_report.py`:

```diff
@@ -206,6 +206,29 @@ def test_brier_is_none_for_a_player_that_answers_no_nouls():
     assert row["brier_gap_ahead"] is None and row["brier_left_safe"] is None
 
 
+def test_brier_scores_the_composed_jevs_four_nouls_against_what_the_senses_show():
+    def composed(row, gaps_row_1, gaps_row_2, **nouls):
+        senses = {"ahead": [{"row": 1, "gaps_relative": gaps_row_1}, {"row": 2, "gaps_relative": gaps_row_2}]}
+        return step(player="jev_composed", row=row, senses=senses,
+                    ground_truth={"gap_ahead": 0 in gaps_row_1, "left_safe": -1 not in gaps_row_1},
+                    answers={f"gap_{a}": {"type": "noul", "noul": p} for a, p in nouls.items()})
+
+    steps = [composed(0, [-1, 0], [], left=0.9, stay=0.7, right=0.0, jump=0.5),
+             composed(1, [], [0], left=0.2, stay=0.1, right=0.0, jump=1.0, cache_hit=True)]
+    (row,) = summarize(steps)
+    assert row["brier_gap_left"] == pytest.approx((0.1 ** 2 + 0.2 ** 2) / 2)
+    assert row["brier_gap_stay"] == pytest.approx((0.3 ** 2 + 0.1 ** 2) / 2)
+    assert row["brier_gap_right"] == 0.0
+    assert row["brier_gap_jump"] == pytest.approx(0.5 ** 2 / 2)
+    assert row["brier_gap_ahead"] is None and row["brier_left_safe"] is None  # it is not asked those
+
+
+def test_the_four_composed_columns_close_the_table_and_are_empty_for_everyone_else():
+    assert COLUMNS[-4:] == ("brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump")
+    (row,) = summarize([step(answers={"gap_ahead": {"type": "noul", "noul": 0.5}}, ground_truth={"gap_ahead": True})])
+    assert [row[c] for c in COLUMNS[-4:]] == [None] * 4 and row["brier_gap_ahead"] == 0.25
+
+
 def test_small_amounts_keep_four_decimals_in_the_table():
     steps = [step(player="llm", latency_ms=100.0, usage={"input_tokens": 5200, "output_tokens": 90}, alive=False)]
     table = format_table(summarize(steps, {"models": {"llm": "claude-haiku-4-5-20251001"}}))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_report.py`
Expected:

```text
FAILED tests/test_report.py::test_brier_scores_the_composed_jevs_four_nouls_against_what_the_senses_show
FAILED tests/test_report.py::test_the_four_composed_columns_close_the_table_and_are_empty_for_everyone_else
2 failed, 24 passed
```

- [ ] **Step 3: Write the implementation**

Apply to `bakeoff/report.py`:

```diff
@@ -7,11 +7,14 @@ import statistics
 from collections import defaultdict
 from pathlib import Path
 
+from bakeoff.senses import LANDS, lands_on_gap
+
 COLUMNS = ("player", "runs", "incomplete", "missing", "mean_rows", "median_rows", "finished",
            "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
            "fallback_rate", "invalid_rate", "error_rate",
            "requests", "spent", "cache_hits", "mean_latency_ms", "input_tokens", "output_tokens", "cost_usd",
-           "brier_gap_ahead", "brier_left_safe")
+           "brier_gap_ahead", "brier_left_safe",
+           "brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump")
 
 # USD per million tokens (input, output), by the model id in meta.json. Jev is absent: only a blended
 # figure from its console is known (docs/COSTS.md), not an input and an output price, so its cost
@@ -71,13 +74,22 @@ def _cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float
     return (input_tokens * per_input + output_tokens * per_output) / 1_000_000
 
 
+def _truth(step: dict, noul: str) -> bool | None:
+    """The logged `ground_truth` for the one-shot Jev's two Nouls. The composed Jev's `gap_<action>`
+    Nouls ask what the senses show, so their truth is read from the record's senses."""
+    truth = (step.get("ground_truth") or {}).get(noul)
+    if truth is None and noul.removeprefix("gap_") in LANDS and step.get("senses"):
+        truth = lands_on_gap(step["senses"], noul.removeprefix("gap_"))
+    return truth
+
+
 def _brier(steps: list[dict], noul: str) -> float | None:
-    """Mean squared gap between a logged Noul probability and the engine's truth (0 is perfect,
-    0.25 is what always answering 0.5 scores). Cached answers count: a judgment is a judgment."""
+    """Mean squared gap between a logged Noul probability and the truth (0 is perfect, 0.25 is what
+    always answering 0.5 scores). Cached answers count: a judgment is a judgment."""
     errors = []
     for s in steps:
         answer = (s.get("answers") or {}).get(noul)
-        truth = (s.get("ground_truth") or {}).get(noul)
+        truth = _truth(s, noul)
         if isinstance(answer, dict) and isinstance(answer.get("noul"), (int, float)) and truth is not None:
             errors.append((answer["noul"] - float(truth)) ** 2)
     return _mean(errors)
@@ -116,6 +128,7 @@ def _summarize_player(player: str, steps: list[dict], model: str | None = None)
         "input_tokens": input_tokens, "output_tokens": output_tokens,
         "cost_usd": _cost_usd(model, input_tokens, output_tokens),
         "brier_gap_ahead": _brier(steps, "gap_ahead"), "brier_left_safe": _brier(steps, "left_safe"),
+        **{f"brier_gap_{action}": _brier(steps, f"gap_{action}") for action in ("left", "stay", "right", "jump")},
     }
 
 
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_report.py`
Expected: `26 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `261 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/report.py tests/test_report.py
git commit -F <message file>   # feat: report scores the composed Jev's four Nouls against the senses
```

---

### Task 3: CLI help and documentation

**Files:**
- Modify: `README.md`
- Modify: `bakeoff/__main__.py`
- Modify: `docs/STEP_RECORD.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `PAID` (Task 1).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_cli.py`:

```diff
@@ -1,6 +1,8 @@
 import json
 import time
 
+import pytest
+
 from bakeoff.__main__ import main
 from bakeoff.players import REGISTRY
 from bakeoff.players.base import Decision
@@ -186,6 +188,17 @@ def test_the_tournament_flag_allows_a_paid_cap_on_seeds_below_1000(tmp_path, mon
     assert meta["args"]["tournament"] is True
 
 
+def test_the_composed_jev_is_a_paid_player_for_the_seed_rule_and_the_help(tmp_path, capsys):
+    args = ["run", "--players", "jev_composed", "--seeds", "1", "--max-rows", "12", "--max-requests", "5",
+            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache")]
+    assert main(args) == 2
+    assert "paid players may not spend requests on seeds below 1000" in capsys.readouterr().err
+    assert not (tmp_path / "runs").exists()
+    with pytest.raises(SystemExit):
+        main(["run", "--help"])
+    assert "EACH paid player (jev, jev_composed, llm)" in " ".join(capsys.readouterr().out.split())
+
+
 def test_max_requests_0_on_low_seeds_is_not_refused_by_the_guard(tmp_path, capsys, monkeypatch):
     fake_paid(monkeypatch)
     assert main(low_seed_paid_args(tmp_path)) == 1
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_cli.py`
Expected:

```text
FAILED tests/test_cli.py::test_the_composed_jev_is_a_paid_player_for_the_seed_rule_and_the_help
1 failed, 18 passed
```

- [ ] **Step 3: Write the implementation**

Apply to `README.md`:

```diff
@@ -23,11 +23,18 @@ are in `docs/COSTS.md`.
     uv run python -m bakeoff report runs/<run_id>
     uv run python -m bakeoff view runs/<run_id> [runs/<other_run_id> ...]   # writes replay.html
 
-Paid players (`jev`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
+Paid players (`jev`, `jev_composed`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
 file at the repo root (template: `.env.example`). They spend nothing unless told to:
 
     uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300
 
+`jev_composed` is the Jev of the demo: instead of one broad question it asks Jev four pointed yes/no
+questions in one request ("would `left` land on a gap, that is, does `ahead[0].gaps_relative` contain
+-1?") and code picks the action least likely to land on a gap, ties in the order stay, left, right,
+jump. The wording and that rule are ours, not TypeSafe's, and it looks one step ahead only. The
+one-shot `jev` stays for comparison: on the dangerous states of practice track 1000 its single Choice
+landed on a gap about as often as always staying (`docs/DECISIONS.md`, decisions 14 and 15).
+
 `--max-requests` is a hard cap on live requests for **each** paid player in the run; the default 0
 only replays `.cache/responses`. Every answer is cached, so a repeated run is free and a run stopped
 by the cap (`status: budget_exhausted`) continues from the cache next time. `uv run pytest -m live`
```

Apply to `bakeoff/__main__.py`:

```diff
@@ -30,7 +30,7 @@ def _parser() -> argparse.ArgumentParser:
     run.add_argument("--max-rows", type=int, default=MAX_ROWS)
     run.add_argument("--out", default="runs")
     run.add_argument("--max-requests", type=int, default=0,
-                     help="hard cap on live requests for EACH paid player (jev, llm); the default 0 only replays "
+                     help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only replays "
                           "the cache. Worst case a run spends this many requests per paid player")
     run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
     run.add_argument("--tournament", action="store_true",
```

Apply to `docs/STEP_RECORD.md`:

```diff
@@ -38,8 +38,8 @@ use the next record's `row`/`lane`, or derive the landing tile as below.
 | `lane` | int | lane at decision time, `0 .. lanes-1` (starts at `lanes // 2`, i.e. 6) |
 | `senses` | object | exactly what the player was shown, see below |
 | `looming` | `{left_hz, right_hz}` | floats, the fly's eye rates for these senses: each visible gap adds `gain_hz / row ** falloff` to its eye (own lane: both eyes), the sum is capped at `max_hz` and rounded to the nearest `step_hz` (so 11 levels, 0 to 250). Ours, not the fly's biology |
-| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON |
-| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Null after an `error` |
+| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. Composed Jev: `{gap_left, gap_stay, gap_right, gap_jump}`, four Nouls. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON |
+| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. Composed Jev: `{gap_left: {type, noul}, gap_stay, gap_right, gap_jump}`, each the probability that the action lands on a gap. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Null after an `error` |
 | `chosen_action` | string or null | what the player asked for. May be an invalid string, or null if it gave none |
 | `executed_action` | string | what the game ran: `left`, `right`, `jump` or `stay`. Equals `chosen_action` unless a fallback applied |
 | `solver_action` | string | the reference solver's move on the same senses: the first action, in the order `stay, left, right, jump`, with the maximum depth |
@@ -55,7 +55,7 @@ use the next record's `row`/`lane`, or derive the landing tile as below.
 | `latency_ms` | float or null | wall time of a live call; null for players with no call |
 | `usage` | object or null | `{input_tokens, output_tokens}` for paid players, as reported by the provider (also on a cache hit: what the original request used) |
 | `cache_hit` | bool | the answer came from the response cache (no request, no cost) |
-| `info` | object or null | player-specific extras: the fly's activity (below); `{model}` for paid players, the model id the provider reported |
+| `info` | object or null | player-specific extras: the fly's activity (below); `{model}` for paid players, the model id the provider reported; the composed Jev adds `rule` (`"lowest_gap_probability"`) and `order` (its tie-break, `["stay", "left", "right", "jump"]`) |
 | `track` | object or null | the full track, present only in the first record of each seed, else null |
 
 The fallback rule: when `gated`, `invalid`, `error` is set, or `chosen_action` is null, the
@@ -96,6 +96,13 @@ JSON with a string `action`, the action is unknown, or `stop_reason` is not `end
 `invalid` when its choice is missing or unknown. Jev is never `gated`. The two Nouls never influence
 the move: they are scored against `ground_truth` (same key names) in the report.
 
+The composed Jev (`jev_composed`) is asked four Nouls and no Choice; its move is the action with the
+lowest Noul after rounding to two decimals, ties in the order of `info.order`. That rule and the
+wording of the questions are ours. It is `invalid` when any of the four Nouls is missing or not a
+finite number, and never `gated`. The report scores its Nouls (`brier_gap_left` and so on) against what
+the record's `senses` show (`bakeoff.senses.lands_on_gap`), since that is what the questions ask;
+`ground_truth` keeps its two keys.
+
 ## The landing tile
 
 Given `row`, `lane` and `executed_action` (`lanes` from `track.lanes`):
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_cli.py`
Expected: `19 passed`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `262 passed, 9 deselected`

- [ ] **Step 6: Commit**

```bash
git add README.md bakeoff/__main__.py docs/STEP_RECORD.md tests/test_cli.py
git commit -F <message file>   # docs: the composed Jev in the CLI help, README and step record
```

---

### Task 4: The recorded run on practice track 1000 (spends money: controller only)

Not a subagent task. Inside decision 19's ceiling (1,000 Jev requests in total for phase 5); the rule's ceiling on this track is 246 rows, so the run needs at most 247 requests.

- [ ] **Step 1: One capped run**

```bash
uv run python -m bakeoff run --players jev_composed --seeds 1 --seed-start 1000 --max-requests 300
```

Expected: `status: completed`, one row for `jev_composed`, `spent` at most 247, `error_rate` 0.00. A provider failure or a `budget_exhausted` status is reported to the user, not retried.

- [ ] **Step 2: Read the result against the free ceiling**

`uv run python -m bakeoff report runs/<run_id>`: rows survived (ceiling 246), the four Brier columns (spike 02: 1 wrong answer in 800), `solver_agreement`. Every row on which the move differs from the perfect-answers move is a perception error; count them from the log.

- [ ] **Step 3: Record it**

`docs/COSTS.md` (requests, tokens, latency for four Nouls per request), `docs/DECISIONS.md` (the result under decision 15; "Next step"), `CLAUDE.md` (status). Commit: `docs: composed Jev's first recorded track`.

## Self-review against the spec

| Spec, phase 5a | Where |
| --- | --- |
| new `bakeoff/players/jev_composed.py`, registry name `jev_composed`, in `PAID`, same `PaidPlayer` base, cache, cap, error and fallback rules | Task 1 (`JevComposedPlayer(PaidPlayer)`, `client_class = JevClient`; cache, cap and error tests) |
| one request per row with four Nouls `gap_left`, `gap_stay`, `gap_right`, `gap_jump`, worded exactly as in the spike | Task 1, `test_four_pointed_nouls_one_per_action_worded_as_in_the_spike` (literal strings) |
| lowest Noul after rounding to two decimals; ties `stay, left, right, jump` | Task 1, `pick()` and its test |
| invalid when any Noul is missing or not a number; never gated | Task 1, two tests |
| `answers` logs the four Nouls; `info` logs `{model, rule, order}` | Task 1 |
| ours and labelled as ours; one step ahead only | module docstring, README, `docs/STEP_RECORD.md` (Task 3); on the page in phase 5b |
| the report scores the four Nouls (Brier); `meta.json` gains nothing | Task 2 |
| frozen before any tournament seed; practice seeds 1000 and up only | Task 3's CLI test (the seed rule covers it), Task 4 |
