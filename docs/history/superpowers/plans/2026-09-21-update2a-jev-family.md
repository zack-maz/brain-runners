# Update 2a: the Jev family and its LLM twins — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** three new ways to ask Jev (`jev_choice`, `jev_two_step`, `jev_reader`) and an LLM twin for every question set (`llm_composed`, `llm_choice`, `llm_two_step`, `llm_reader`) that asks Claude Haiku the same questions and uses the same rule; the report scores every Noul; the page shows what each set player was told.

**Architecture:** `bakeoff/players/question_sets.py` (new) defines a `QuestionSet` (questions built from the game's `Rules`, and a pure rule from answer values to a move) for `composed`, `choice`, `two_step`, `reader`, plus `values_of`. `bakeoff/senses.py` gains `trapped`, `tile_id`, `parse_tile_id` and `truth_of`, so any Noul's truth is read from a record's senses. `bakeoff/players/set_players.py` (new) has `SetPlayer(PaidPlayer)` with a Jev and an LLM subclass and seven named players; the registry and `PAID` gain them. The report adds `brier_all`; the viewer adds tags, one-line descriptions and a generic `setMind` panel.

**Tech Stack:** Python 3.13, `uv`, `pytest`; plain JavaScript with `node --test` (run by `uv run pytest`). No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-21-jev-family-design.md` (binding). Background: `docs/DECISIONS.md` decisions 14, 15, 25 and 26; `docs/UPDATES.md` item 2.

**Branch:** `phase6-updates` (already checked out; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`. No `uv add`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network**: the SDKs are replaced by the fakes in `tests/fakes.py`.
- **Tasks 1 to 3 spend no money.** No `--max-requests`, no `pytest -m live`, no `pytest -m slow`, no `bakeoff run`/`live` with a paid player or the fly. Task 4 (the paid runs) belongs to the controller alone, within decision 26: Claude Haiku at most 5.00 USD in total, v2 practice seeds 1000 and up only.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command.
- **Frozen:** `bakeoff/players/jev.py`, `jev_composed.py`, `llm.py`, `briefing.py` (its text is part of the cache key), `bakeoff/clients/`, the fly, the game, the shape of the senses and of the step record (`schema_version` stays 1). The `composed` set must build exactly `jev_composed.QUESTIONS` so its cache keeps replaying.
- **Honesty:** every question wording and every rule is ours, not TypeSafe's or Anthropic's, and the page and docs say so. The LLM twins' numbers are the model's stated probabilities, not calibrated ones.
- **Viewer rules:** plain JavaScript, no build step, no npm packages; text from a log is always escaped (`esc`).
- Every code block below was run in a prototype and passes as written (final state: 353 fast tests, 9 deselected). If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **Rule details.** Two-step: minimise (round(P(gap) + (1 − P(gap))·P(trapped), 2), round(P(gap), 2)), ties in the order stay, left, right, jump. Reader: tiles with P > 0.5 become gaps and `solve(picture, window)` picks, with the window and the rows taken from the tile ids. Choice: the chosen move.
2. **`truth_of` returns None for a follow-up beyond the view** (`trapped` raises IndexError there, never reads a missing row as floor), and for ids it does not know, so the report skips them.
3. **Two-step needs 4 rows and 2 lanes either side in view**; building it for a smaller vision raises ValueError (at `reset`, so an impossible experiment stops at once).
4. **A set player builds its questions for the default game at construction and again at `reset`** from the track's rules (the reader's questions depend on the vision).
5. **LLM twins.** System prompt = `briefing.RULES` + one line on how to answer + a list `- \`id\` (yes/no|choice): wording` (the Choice's options listed once, the briefing never twice); a JSON schema with one property per id (`number`, or the four moves as an enum), all required, no extras; `max_tokens` = 256 + 12 per question. The logged `questions` add the set itself, so the cache key covers it. Answers are logged in Jev's form plus `text` and `stop_reason`; a stop other than `end_turn` is invalid.
6. **`brier_all`** is added as the last report column; the one-shot Jev's two Nouls count through `ground_truth`, set Nouls through `truth_of`; booleans and non-numbers are skipped.
7. **The page:** `isSetPlayer` matches `(jev|llm)_(composed|choice|two_step|reader)` except `jev_composed`, which keeps its own panel; the default demo view is unchanged.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/senses.py` | `trapped`, `tile_id`, `parse_tile_id`, `truth_of` | 1 |
| `bakeoff/players/question_sets.py` | `QuestionSet`, `values_of`, `COMPOSED`, `CHOICE`, `TWO_STEP`, `READER`, `SETS` | 1 |
| `bakeoff/players/set_players.py` | `SetPlayer`, `JevSetPlayer`, `LlmSetPlayer`, seven players, `SET_PLAYERS`, `LLM_SYSTEM` | 2 |
| `bakeoff/players/__init__.py` | registry and `PAID` | 2 |
| `tests/fakes.py` | `jev_set_reply` | 2 |
| `bakeoff/report.py` | `truth_of` for set Nouls, `brier_all` | 3 |
| `bakeoff/replay.py` | the new players' order | 3 |
| `viewer/minds.js`, `viewer/app.js` | tags, descriptions, `setMind`, `readGrid` | 3 |
| `docs/STEP_RECORD.md`, `README.md` | the new players and their records | 3 |
| `docs/COSTS.md`, `docs/DECISIONS.md`, `docs/UPDATES.md`, `CLAUDE.md` | the paid runs (controller) | 4 |

---

### Task 1: Question sets and the truth of their questions

**Files:**
- Create: `bakeoff/players/question_sets.py`
- Modify: `bakeoff/senses.py`
- Test: `tests/test_question_sets.py`
- Test: `tests/test_senses.py`

**Interfaces:**
- Consumes: `Rules` (bakeoff/game/rules.py), `solve(senses, window)`, `jev_composed.QUESTIONS/ORDER/pick`, `briefing.RULES`, `LANDS`, `ACTION_DESCRIPTIONS`.
- Produces: `bakeoff.senses.trapped(senses, action) -> bool` (IndexError beyond the view), `tile_id(row, offset) -> str`, `parse_tile_id(id) -> (row, offset) | None`, `truth_of(senses, noul_id) -> bool | None`; `bakeoff.players.question_sets`: `QuestionSet(name, rule, about, build(rules) -> dict, pick(values) -> str)`, `values_of(questions, answers) -> dict | None`, `COMPOSED`, `CHOICE`, `TWO_STEP`, `READER`, `SETS`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_question_sets.py`:

```python
import pytest

from bakeoff.game.engine import Game
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players.jev_composed import QUESTIONS as COMPOSED_QUESTIONS
from bakeoff.players.question_sets import CHOICE, COMPOSED, READER, SETS, TWO_STEP, values_of
from bakeoff.senses import compute_senses, truth_of


def noul(p):
    return {"type": "noul", "noul": p}


def test_the_four_sets():
    assert list(SETS) == ["composed", "choice", "two_step", "reader"]
    assert all(SETS[name].name == name for name in SETS)


def test_composed_asks_exactly_what_jev_composed_asks_so_its_cache_replays():
    assert COMPOSED.build(V2) == COMPOSED_QUESTIONS


def test_choice_is_one_choice_that_names_each_landing_tile():
    questions = CHOICE.build(V2)
    assert list(questions) == ["action"] and questions["action"]["type"] == "choice"
    criteria = questions["action"]["criteria"]
    assert list(criteria) == ["stay", "left", "right", "jump"]
    assert criteria["left"] == ("move one lane left; lands on offset -1 of `ahead[0]`, a gap if "
                                "`ahead[0].gaps_relative` contains -1")
    assert criteria["jump"].endswith("lands on offset 0 of `ahead[1]`, a gap if `ahead[1].gaps_relative` contains 0")
    assert questions["action"]["instructions"].endswith("Choose one whose landing tile is not a gap.")


def test_two_step_adds_a_trapped_question_per_move():
    questions = TWO_STEP.build(V2)
    assert list(questions) == [*COMPOSED_QUESTIONS, "trapped_stay", "trapped_left", "trapped_right", "trapped_jump"]
    assert questions["trapped_jump"]["instructions"] == (
        "After the action `jump` (landing on offset 0 of `ahead[1]`), would every next move land on a gap, that is, "
        "does `ahead[2].gaps_relative` contain all of -1, 0 and 1, and does `ahead[3].gaps_relative` contain 0?")
    with pytest.raises(ValueError, match="need 4 rows and 2 lanes"):
        TWO_STEP.build(V2.variant(lookahead=3))


def test_reader_asks_one_question_per_visible_tile():
    questions = READER.build(V2)
    assert len(questions) == 6 * 7 and all(q["type"] == "noul" for q in questions.values())
    assert questions["tile_r2_l3"]["instructions"] == (
        "Is offset -3 of `ahead[1]` a gap, that is, does `ahead[1].gaps_relative` contain -3?")
    assert len(READER.build(V2.variant(lookahead=3, window=2))) == 3 * 5


def test_values_of_wants_every_answer_usable():
    questions = TWO_STEP.build(V2)
    good = {q: noul(0.25) for q in questions}
    assert values_of(questions, good) == {q: 0.25 for q in questions}
    for bad in (None, 1.5, -0.1, float("nan"), True, "0.2"):
        assert values_of(questions, {**good, "trapped_jump": noul(bad)}) is None
    assert values_of(questions, {q: a for q, a in good.items() if q != "gap_left"}) is None
    assert values_of(CHOICE.build(V2), {"action": {"choice": "jump"}}) == {"action": "jump"}
    assert values_of(CHOICE.build(V2), {"action": {"choice": "fly"}}) is None


def test_the_rules_on_hand_made_answers():
    assert COMPOSED.pick({"gap_stay": 0.4, "gap_left": 0.1, "gap_right": 0.1, "gap_jump": 0.3}) == "left"
    assert CHOICE.pick({"action": "right"}) == "right"
    safe_but_trapped = {"gap_stay": 0.0, "trapped_stay": 0.9, "gap_left": 0.2, "trapped_left": 0.0,
                        "gap_right": 0.6, "trapped_right": 0.0, "gap_jump": 0.9, "trapped_jump": 0.0}
    assert TWO_STEP.pick(safe_but_trapped) == "left"  # stay's landing is floor, but a dead end
    tied = {f"{kind}_{a}": 0.0 for kind in ("gap", "trapped") for a in ("stay", "left", "right", "jump")}
    assert TWO_STEP.pick(tied) == "stay"
    tiles = {q: 0.0 for q in READER.build(V2)}
    assert READER.pick(tiles) == "stay"
    assert READER.pick({**tiles, "tile_r1_c": 0.9}) == "left"
    assert READER.pick({**tiles, "tile_r1_c": 0.4}) == "stay"  # read as floor: 0.5 or less


@pytest.mark.parametrize("name, floor", [("composed", 60), ("two_step", 100), ("reader", 140)])
def test_perfect_answers_reach_each_rules_ceiling(name, floor):
    # free and exact: the answers are the truth; a real model can only do worse
    question_set = SETS[name]
    questions, rows = question_set.build(V2), []
    for seed in range(1000, 1010):
        game = Game(generate_track(seed))
        while not game.over:
            senses = compute_senses(game)
            game.step(question_set.pick({q: float(truth_of(senses, q)) for q in questions}))
        rows.append(game.rows_survived)
    assert sum(rows) / len(rows) >= floor
```

Apply to `tests/test_senses.py`:

```diff
@@ -118,3 +118,27 @@ def test_the_senses_follow_the_games_vision(make_track):
     senses = compute_senses(Game(make_track({1: [3, 4], 2: [9]}, lookahead=3, window=2)))
     assert [e["row"] for e in senses["ahead"]] == [1, 2, 3]
     assert senses["ahead"][0]["gaps_relative"] == [-2] and senses["ahead"][1]["gaps_relative"] == []
+
+
+def test_truth_of_reads_every_question_set_noul_from_the_senses(make_track):
+    from bakeoff.senses import parse_tile_id, tile_id, trapped, truth_of
+
+    # runner in lane 6: a gap ahead; a dead end after stepping left (row 2 lanes 4, 5, 6 and row 3 lane 5)
+    senses = compute_senses(Game(make_track({1: [6], 2: [4, 5, 6], 3: [5]})))
+    assert truth_of(senses, "gap_stay") is True and truth_of(senses, "gap_left") is False
+    assert trapped(senses, "left") and truth_of(senses, "trapped_left") is True
+    assert truth_of(senses, "trapped_right") is False
+    assert truth_of(senses, "tile_r1_c") is True and truth_of(senses, "tile_r2_l2") is True
+    assert truth_of(senses, "tile_r2_r1") is False
+    assert truth_of(senses, "tile_r9_c") is None and truth_of(senses, "gap_ahead") is None
+    assert truth_of(senses, "tile_r1_l0") is None and truth_of(senses, "nonsense") is None
+    assert [tile_id(2, o) for o in (-3, 0, 1)] == ["tile_r2_l3", "tile_r2_c", "tile_r2_r1"]
+    assert parse_tile_id("tile_r2_l3") == (2, -3) and parse_tile_id("tile_r4_r1") == (4, 1)
+
+
+def test_truth_of_a_follow_up_beyond_the_view_is_unknown(make_track):
+    from bakeoff.senses import truth_of
+
+    senses = compute_senses(Game(make_track({}, lookahead=3)))
+    assert truth_of(senses, "trapped_stay") is False  # rows 2 and 3 are in view
+    assert truth_of(senses, "trapped_jump") is None  # would need row 4
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_question_sets.py tests/test_senses.py`
Expected:

```text
ERROR tests/test_question_sets.py
1 error in 0.13s
```

- [ ] **Step 3: Write the implementation**

Create `bakeoff/players/question_sets.py`:

```python
"""Question sets: what a paid player asks each row, and the rule that turns the answers into a move. Each set
is played twice, by Jev (`jev_<set>`) and by Claude Haiku (`llm_<set>`), so the model is the only difference
(docs/superpowers/specs/2026-09-21-jev-family-design.md). OURS, not TypeSafe's or Anthropic's: every wording and
every rule here. Pure: no I/O."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from bakeoff.game.engine import ACTIONS
from bakeoff.game.rules import Rules
from bakeoff.players.briefing import RULES as BRIEFING
from bakeoff.players.jev_composed import ORDER
from bakeoff.players.jev_composed import QUESTIONS as COMPOSED_QUESTIONS
from bakeoff.players.jev_composed import pick as pick_composed
from bakeoff.players.solver import solve
from bakeoff.senses import ACTION_DESCRIPTIONS, LANDS, parse_tile_id, tile_id


@dataclass(frozen=True)
class QuestionSet:
    name: str
    rule: str  # the rule's name, logged in each decision's `info`
    about: str  # one line for the page
    build: Callable[[Rules], dict]  # the questions for a game's vision: {id: {"type": "noul" | "choice", ...}}
    pick: Callable[[dict], str]  # the answers' values ({id: P(yes) or a move}) -> the move


def values_of(questions: dict, answers: dict) -> dict | None:
    """Each question's value from the answers (`{"noul": p}` or `{"choice": move}`), or None unless every
    question has a usable one: a finite probability from 0 to 1, or one of the four moves."""
    values = {}
    for qid, question in questions.items():
        answer = answers.get(qid) if isinstance(answers, dict) else None
        if not isinstance(answer, dict):
            return None
        if question["type"] == "noul":
            p = answer.get("noul")
            if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
                return None
            values[qid] = float(p)
        else:
            move = answer.get("choice")
            if move not in ACTIONS:
                return None
            values[qid] = move
    return values


# composed: the composed Jev's four Nouls, byte for byte, and its rule
def _pick_composed(values: dict) -> str:
    return pick_composed({action: values[f"gap_{action}"] for action in ORDER})


COMPOSED = QuestionSet("composed", "lowest_gap_probability", "four yes/no questions a row, one per move",
                       lambda rules: dict(COMPOSED_QUESTIONS), _pick_composed)


# choice: one Choice whose options name the tile each move lands on
def _landing(action: str) -> str:
    ahead, offset = LANDS[action]
    return f"lands on offset {offset} of `ahead[{ahead}]`, a gap if `ahead[{ahead}].gaps_relative` contains {offset}"


CHOICE_QUESTIONS = {
    "action": {"type": "choice",
               "instructions": BRIEFING + " Which action should the runner take now? Choose one whose landing tile "
                                          "is not a gap.",
               "criteria": {action: f"{ACTION_DESCRIPTIONS[action]}; {_landing(action)}" for action in ORDER}},
}
CHOICE = QuestionSet("choice", "the_choice", "one question a row: which move, each move's landing tile named",
                     lambda rules: dict(CHOICE_QUESTIONS), lambda values: values["action"])


# two_step: the four landing Nouls, and for each move whether every next move from its landing is a gap
def _trapped_question(action: str) -> dict:
    ahead, o = LANDS[action]
    return {"type": "noul",
            "instructions": f"After the action `{action}` (landing on offset {o} of `ahead[{ahead}]`), would every "
                            f"next move land on a gap, that is, does `ahead[{ahead + 1}].gaps_relative` contain all of "
                            f"{o - 1}, {o} and {o + 1}, and does `ahead[{ahead + 2}].gaps_relative` contain {o}?"}


def _build_two_step(rules: Rules) -> dict:
    if rules.lookahead < 4 or rules.window < 2:
        raise ValueError("the two-step questions need 4 rows and 2 lanes either side in view")
    return {**COMPOSED_QUESTIONS, **{f"trapped_{action}": _trapped_question(action) for action in ORDER}}


def _pick_two_step(values: dict) -> str:
    """Lowest risk that the move or the move after it lands on a gap, then lowest P(gap); ties in ORDER."""
    def risk(action: str) -> tuple[float, float]:
        gap, trapped = values[f"gap_{action}"], values[f"trapped_{action}"]
        return round(gap + (1 - gap) * trapped, 2), round(gap, 2)

    return min(ORDER, key=risk)


TWO_STEP = QuestionSet("two_step", "lowest_two_step_risk",
                       "eight yes/no questions a row: each move's landing, and whether it leaves a way on",
                       _build_two_step, _pick_two_step)


# reader: one Noul per visible tile; the reference solver plans over the tiles read as gaps
def _build_reader(rules: Rules) -> dict:
    return {tile_id(row, offset): {"type": "noul",
                                   "instructions": f"Is offset {offset} of `ahead[{row - 1}]` a gap, that is, does "
                                                   f"`ahead[{row - 1}].gaps_relative` contain {offset}?"}
            for row in range(1, rules.lookahead + 1) for offset in range(-rules.window, rules.window + 1)}


def _pick_reader(values: dict) -> str:
    """The tiles read as more likely gap than floor become the picture the solver plans over."""
    tiles = {parse_tile_id(qid): p for qid, p in values.items()}
    rows = max(row for row, _ in tiles)
    window = max(abs(offset) for _, offset in tiles)
    senses = {"ahead": [{"row": row, "gaps_relative": sorted(o for (r, o), p in tiles.items() if r == row and p > 0.5)}
                        for row in range(1, rows + 1)]}
    return solve(senses, window)


READER = QuestionSet("reader", "solver_over_read_tiles",
                     "reads every visible tile (a yes/no question each), then plans like the solver",
                     _build_reader, _pick_reader)

SETS = {s.name: s for s in (COMPOSED, CHOICE, TWO_STEP, READER)}
```

Apply to `bakeoff/senses.py`:

```diff
@@ -62,3 +62,49 @@ def lands_on_gap(senses: dict, action: str) -> bool:
     the engine differs only past the finish line, where a gap no longer kills."""
     ahead, offset = LANDS[action]
     return offset in senses["ahead"][ahead]["gaps_relative"]
+
+
+def trapped(senses: dict, action: str) -> bool:
+    """After `action`, would every next move land on a gap the senses show? (The two-step question sets
+    ask this; it needs two more rows in view beyond the landing row.)"""
+    ahead, offset = LANDS[action]
+    if ahead + 2 >= len(senses["ahead"]):
+        raise IndexError(f"the view ends before the move after `{action}`")
+    return all(offset + shift in senses["ahead"][ahead + step]["gaps_relative"]
+               for step, shift in ((1, -1), (1, 0), (1, 1), (2, 0)))
+
+
+def tile_id(row: int, offset: int) -> str:
+    """The question id of one visible tile: `tile_r2_c` is the runner's lane two rows ahead, `tile_r1_l3`
+    three lanes to its left one row ahead, `tile_r4_r1` one lane to its right four rows ahead."""
+    side = "c" if offset == 0 else ("l" if offset < 0 else "r") + str(abs(offset))
+    return f"tile_r{row}_{side}"
+
+
+def parse_tile_id(noul_id: str) -> tuple[int, int] | None:
+    """(row, offset) of a `tile_id`, or None if `noul_id` is not one."""
+    parts = noul_id.split("_")
+    if len(parts) != 3 or parts[0] != "tile" or not parts[1].startswith("r") or not parts[1][1:].isdigit():
+        return None
+    side = parts[2]
+    if side == "c":
+        return int(parts[1][1:]), 0
+    if side[:1] in ("l", "r") and side[1:].isdigit() and side[1:] != "0":
+        return int(parts[1][1:]), int(side[1:]) * (-1 if side[0] == "l" else 1)
+    return None
+
+
+def truth_of(senses: dict, noul_id: str) -> bool | None:
+    """The truth of a question-set Noul, read from the senses alone (so the report can score any record):
+    `gap_<action>`, `trapped_<action>` and `tile_r<row>_<side>`. None for any other id, or for a tile or a
+    follow-up the senses do not reach."""
+    kind, _, rest = noul_id.partition("_")
+    if kind in ("gap", "trapped") and rest in LANDS:
+        try:
+            return lands_on_gap(senses, rest) if kind == "gap" else trapped(senses, rest)
+        except IndexError:
+            return None
+    tile = parse_tile_id(noul_id)
+    if tile is not None and 1 <= tile[0] <= len(senses["ahead"]):
+        return tile[1] in senses["ahead"][tile[0] - 1]["gaps_relative"]
+    return None
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_question_sets.py tests/test_senses.py`
Expected: `28 passed in 0.19s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `338 passed, 9 deselected in 31.39s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/players/question_sets.py bakeoff/senses.py tests/test_question_sets.py tests/test_senses.py
git commit -F <message file>   # feat: question sets (composed, choice, two-step, reader) and the truth of their questions
```

---

### Task 2: jev_choice, jev_two_step, jev_reader and an LLM twin for every question set

**Files:**
- Modify: `bakeoff/players/__init__.py`
- Create: `bakeoff/players/set_players.py`
- Test: `tests/fakes.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_players.py`
- Test: `tests/test_set_players.py`

**Interfaces:**
- Consumes: task 1's `QuestionSet`, `values_of`, the four sets; `PaidPlayer` (bakeoff/players/paid.py), `JevClient`, `LlmClient`.
- Produces: `bakeoff.players.set_players`: `SetPlayer`, `JevSetPlayer`, `LlmSetPlayer`, `LLM_SYSTEM`, the seven player classes (names `jev_choice`, `jev_two_step`, `jev_reader`, `llm_composed`, `llm_choice`, `llm_two_step`, `llm_reader`), `SET_PLAYERS`; registry entries and `PAID`; `tests.fakes.jev_set_reply(values)`. Decisions' `info` gains `set`, `rule`, `order`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/fakes.py`:

```diff
@@ -60,3 +60,10 @@ def llm_reply(text='{"action": "stay"}', stop_reason="end_turn"):
     return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-4-5-20251001",
             "content": [{"type": "text", "text": text}], "stop_reason": stop_reason, "stop_sequence": None,
             "usage": {"input_tokens": 520, "output_tokens": 9}}
+
+
+def jev_set_reply(values: dict):
+    """A Jev reply to a question set: {id: P(yes)} for Nouls, {id: move} for a Choice."""
+    answers = {qid: {"type": "choice", "choice": v, "confidence": 0.7} if isinstance(v, str)
+               else {"type": "noul", "noul": v} for qid, v in values.items()}
+    return {"model": "jev-latest", "usage": {"input_tokens": 300, "output_tokens": 4 * len(values)}, "answers": answers}
```

Apply to `tests/test_cli.py`:

```diff
@@ -215,7 +215,8 @@ def test_the_composed_jev_is_a_paid_player_for_the_seed_rule_and_the_help(tmp_pa
     assert not (tmp_path / "runs").exists()
     with pytest.raises(SystemExit):
         main(["run", "--help"])
-    assert "EACH paid player (jev, jev_composed, llm)" in " ".join(capsys.readouterr().out.split())
+    assert ("EACH paid player (jev, jev_composed, llm, jev_choice, jev_two_step, jev_reader, llm_composed, "
+            "llm_choice, llm_two_step, llm_reader)") in " ".join(capsys.readouterr().out.split())
 
 
 def test_max_requests_0_on_low_seeds_is_not_refused_by_the_guard(tmp_path, capsys, monkeypatch):
```

Apply to `tests/test_players.py`:

```diff
@@ -30,8 +30,9 @@ def test_decision_defaults_and_fallback_rule():
 
 
 def test_factory_knows_the_baselines_and_rejects_unknown_names():
-    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "jev_composed", "llm"}
-    assert set(PAID) == {"jev", "jev_composed", "llm"}
+    sets = {"jev_choice", "jev_two_step", "jev_reader", "llm_composed", "llm_choice", "llm_two_step", "llm_reader"}
+    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "jev_composed", "llm", *sets}
+    assert set(PAID) == {"jev", "jev_composed", "llm", *sets}
     assert all(make_player(name).name == name for name in REGISTRY)  # a paid player without a budget only replays
     with pytest.raises(KeyError, match="unknown player 'nope'"):
         make_player("nope")
```

Create `tests/test_set_players.py`:

```python
import json

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import Game
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players import PAID, make_player
from bakeoff.players.briefing import RULES as BRIEFING
from bakeoff.players.question_sets import CHOICE, READER, TWO_STEP
from bakeoff.players.set_players import (LLM_SYSTEM, JevReaderPlayer, JevTwoStepPlayer, LlmChoicePlayer,
                                         LlmComposedPlayer, LlmReaderPlayer, SET_PLAYERS)
from bakeoff.runner import Runner
from bakeoff.senses import compute_senses, truth_of
from tests.fakes import FakeAnthropic, FakeTypeSafe, jev_set_reply, llm_reply

SENSES = compute_senses(Game(generate_track(1000)))


def jev(tmp_path, cls, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return cls(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def llm(tmp_path, cls, text, stop_reason="end_turn", cap=10):
    sdk = FakeAnthropic(llm_reply(text, stop_reason))
    return cls(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def safe(questions, value=0.1):
    return {qid: value for qid in questions}


def test_seven_paid_players_one_per_model_and_set():
    names = [p.name for p in SET_PLAYERS]
    assert names == ["jev_choice", "jev_two_step", "jev_reader", "llm_composed", "llm_choice", "llm_two_step",
                     "llm_reader"]
    assert all(name in PAID for name in names)


def test_a_jev_set_player_asks_its_questions_and_its_rule_picks(tmp_path):
    from typesafe_sdk import Noul

    values = {**safe(TWO_STEP.build(V2)), "gap_stay": 0.9}
    player, sdk = jev(tmp_path, JevTwoStepPlayer, jev_set_reply(values))
    decision = player.act(SENSES)
    (call,) = sdk.calls
    assert set(call["questions"]) == set(TWO_STEP.build(V2)) and all(isinstance(q, Noul) for q in call["questions"].values())
    assert decision.chosen_action == "left" and not decision.invalid
    assert decision.info == {"model": "jev-latest", "set": "two_step", "rule": "lowest_two_step_risk",
                             "order": ["stay", "left", "right", "jump"]}
    assert decision.questions == TWO_STEP.build(V2) and decision.answers["gap_stay"]["noul"] == 0.9


def test_a_missing_or_impossible_answer_is_invalid_and_logged(tmp_path):
    values = safe(TWO_STEP.build(V2))
    del values["trapped_jump"]
    player, _ = jev(tmp_path, JevTwoStepPlayer, jev_set_reply(values))
    decision = player.act(SENSES)
    assert decision.invalid and decision.chosen_action is None and "gap_left" in decision.answers


def test_the_reader_asks_about_every_tile_of_the_games_view(tmp_path):
    player, sdk = jev(tmp_path, JevReaderPlayer, jev_set_reply(safe(READER.build(V2.variant(lookahead=3)), 0.0)))
    player.reset(Game(generate_track(1000, V2.variant(lookahead=3))), 1000)
    assert len(player.questions) == 3 * 7
    assert player.act(compute_senses(Game(generate_track(1000, V2.variant(lookahead=3))))).chosen_action == "stay"


def test_a_jev_set_player_with_perfect_answers_plays_its_rules_ceiling(tmp_path):
    class Oracle(FakeTypeSafe):  # answers the truth, read from the senses it is sent
        def system_one(self, state, questions, model=None):
            self.reply = jev_set_reply({qid: float(truth_of(state, qid)) for qid in questions})
            return super().system_one(state, questions, model)

    player = JevReaderPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(1000), sdk=Oracle(None))
    records = Runner(tmp_path / "runs").run_seed(player, 1000, "r")
    assert records[-1]["finished"] and records[-1]["rows_survived"] == 150


def test_the_llm_twin_gets_the_same_questions_in_one_structured_request(tmp_path):
    values = {**safe(TWO_STEP.build(V2)), "gap_stay": 0.9}
    player, sdk = llm(tmp_path, LlmComposedPlayer, json.dumps({k: v for k, v in values.items() if k.startswith("gap_")}))
    decision = player.act(SENSES)
    (call,) = sdk.calls
    assert call["system"].startswith(LLM_SYSTEM) and call["system"].startswith(BRIEFING)
    assert "- `gap_left` (yes/no): Would the action `left` land the runner on a gap" in call["system"]
    schema = call["output_config"]["format"]["schema"]
    assert schema["required"] == ["gap_left", "gap_stay", "gap_right", "gap_jump"]
    assert schema["properties"]["gap_left"] == {"type": "number"} and schema["additionalProperties"] is False
    assert json.loads(call["messages"][0]["content"]) == SENSES
    assert decision.chosen_action == "left" and not decision.invalid
    assert decision.answers["gap_stay"] == {"noul": 0.9} and decision.answers["stop_reason"] == "end_turn"
    assert decision.questions["questions"] == {k: v for k, v in TWO_STEP.build(V2).items() if k.startswith("gap_")}


def test_the_llm_choice_twin_names_the_options_once_and_not_the_briefing_twice(tmp_path):
    player, sdk = llm(tmp_path, LlmChoicePlayer, '{"action": "jump"}')
    assert player.act(SENSES).chosen_action == "jump"
    system = sdk.calls[0]["system"]
    assert system.count(BRIEFING) == 1
    assert "Options: `stay`: run straight; lands on offset 0 of `ahead[0]`" in system
    assert sdk.calls[0]["output_config"]["format"]["schema"]["properties"]["action"] == {
        "type": "string", "enum": ["stay", "left", "right", "jump"]}


@pytest.mark.parametrize("text, stop_reason", [
    ("not json", "end_turn"), ('["a list"]', "end_turn"), ('{"gap_left": 0.1}', "end_turn"),
    ('{"gap_left": 2, "gap_stay": 0, "gap_right": 0, "gap_jump": 0}', "end_turn"),
    ('{"gap_left": 0.1, "gap_stay": 0, "gap_right": 0, "gap_jump": 0}', "max_tokens")])
def test_an_llm_answer_that_is_not_every_usable_number_is_invalid(tmp_path, text, stop_reason):
    player, _ = llm(tmp_path, LlmComposedPlayer, text, stop_reason)
    decision = player.act(SENSES)
    assert decision.invalid and decision.chosen_action is None and decision.answers["text"] == text


def test_the_reader_twin_leaves_room_for_42_answers(tmp_path):
    player, sdk = llm(tmp_path, LlmReaderPlayer, json.dumps(safe(READER.build(V2), 0.0)))
    assert player.act(SENSES).chosen_action == "stay"
    assert sdk.calls[0]["max_tokens"] == 256 + 12 * 42


def test_set_players_spend_nothing_without_a_budget_and_stop_at_the_cap(tmp_path):
    player = make_player("llm_choice", cache=DiskCache(tmp_path))
    with pytest.raises(BudgetExhausted):
        player.act(SENSES)
    capped, _ = jev(tmp_path, JevReaderPlayer, jev_set_reply(safe(READER.build(V2))), cap=1)
    capped.act(SENSES)
    game = Game(generate_track(1000))
    for _ in range(12):  # past the empty runway, so the senses differ and the cache cannot answer
        game.step("jump")
    with pytest.raises(BudgetExhausted):
        capped.act(compute_senses(game))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_set_players.py tests/test_players.py tests/test_cli.py`
Expected:

```text
ERROR tests/test_set_players.py
1 error in 0.19s
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
from bakeoff.players.set_players import SET_PLAYERS
from bakeoff.players.solver import SolverPlayer

REGISTRY: dict[str, Callable[..., Player]] = {
    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
    "jev": JevPlayer, "jev_composed": JevComposedPlayer, "llm": LlmPlayer,
    **{player.name: player for player in SET_PLAYERS}}
# these take cache= and budget=; without a budget they can only replay the cache
PAID = ("jev", "jev_composed", "llm", *(player.name for player in SET_PLAYERS))


def make_player(name: str, **options) -> Player:
    """Options are passed to the player's constructor (paid players need a client and a cap)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown player {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**options)
```

Create `bakeoff/players/set_players.py`:

```python
"""Players that ask a question set (bakeoff/players/question_sets.py): `jev_<set>` asks Jev, `llm_<set>` asks
Claude Haiku the same questions, and the set's rule picks the move from either one's answers. The same cache, cap,
error and fallback rules as every paid player (PaidPlayer). The composed set's Jev is `jev_composed`, which stays
its own class."""

from __future__ import annotations

import json

from bakeoff.clients.jev import JevClient
from bakeoff.clients.llm import LlmClient
from bakeoff.game.engine import Game
from bakeoff.game.rules import DEFAULT, RULES
from bakeoff.players.base import Decision
from bakeoff.players.briefing import RULES as BRIEFING
from bakeoff.players.jev_composed import ORDER
from bakeoff.players.paid import PaidPlayer
from bakeoff.players.question_sets import CHOICE, COMPOSED, READER, TWO_STEP, QuestionSet, values_of

LLM_SYSTEM = (BRIEFING + " The user message is the runner's current view as JSON. Answer every question below, "
              "each under its id, in the JSON format given: for a yes/no question, your probability from 0 to 1 that "
              "the answer is yes; for a choice, one of its options.")


class SetPlayer(PaidPlayer):
    question_set: QuestionSet

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._use(self.question_set.build(RULES[DEFAULT]))

    def _use(self, set_questions: dict) -> None:
        self.set_questions = set_questions
        self.questions = self.request(set_questions)  # logged in every record and part of the cache key

    def reset(self, game: Game, seed: int) -> None:
        self._use(self.question_set.build(game.track.rules))  # the reader asks about every tile in view

    def request(self, set_questions: dict) -> dict:
        """What the provider is sent besides the senses."""
        raise NotImplementedError

    def answers_of(self, payload: dict) -> tuple[dict | None, dict]:
        """The provider's payload -> (answers in Jev's shape, or None if unreadable; answers to log)."""
        raise NotImplementedError

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers, logged = self.answers_of(payload)
        values = values_of(self.set_questions, answers) if answers is not None else None
        if values is None:
            return None, True, logged  # never half a judgment: every answer usable, or the runner's fallback
        return self.question_set.pick(values), False, logged

    def act(self, senses: dict) -> Decision:
        decision = super().act(senses)
        if decision.info is not None:
            decision.info = {**decision.info, "set": self.question_set.name, "rule": self.question_set.rule,
                             "order": list(ORDER)}
        return decision


class JevSetPlayer(SetPlayer):
    client_class = JevClient

    def request(self, set_questions: dict) -> dict:
        return set_questions

    def answers_of(self, payload: dict) -> tuple[dict | None, dict]:
        answers = payload.get("answers") or {}
        return answers, answers


class LlmSetPlayer(SetPlayer):
    client_class = LlmClient

    def request(self, set_questions: dict) -> dict:
        lines = []
        for qid, q in set_questions.items():
            text = q["instructions"].removeprefix(BRIEFING).strip()
            if q["type"] == "choice":
                text += " Options: " + "; ".join(f"`{option}`: {what}" for option, what in q["criteria"].items()) + "."
            lines.append(f"- `{qid}` ({'yes/no' if q['type'] == 'noul' else 'choice'}): {text}")
        properties = {qid: {"type": "number"} if q["type"] == "noul" else {"type": "string", "enum": list(q["criteria"])}
                      for qid, q in set_questions.items()}
        return {"system": LLM_SYSTEM + "\n\nQuestions:\n" + "\n".join(lines),
                "schema": {"type": "object", "properties": properties, "required": list(set_questions),
                           "additionalProperties": False},
                "max_tokens": 256 + 12 * len(set_questions), "questions": set_questions}

    def answers_of(self, payload: dict) -> tuple[dict | None, dict]:
        logged = {"text": payload.get("text"), "stop_reason": payload.get("stop_reason")}
        try:
            data = json.loads(payload.get("text") or "")
        except ValueError:
            return None, logged
        if not isinstance(data, dict) or payload.get("stop_reason") != "end_turn":
            return None, logged
        answers = {qid: {"noul": data.get(qid)} if q["type"] == "noul" else {"choice": data.get(qid)}
                   for qid, q in self.set_questions.items()}
        return answers, {**answers, **logged}


class JevChoicePlayer(JevSetPlayer):
    name, question_set = "jev_choice", CHOICE


class JevTwoStepPlayer(JevSetPlayer):
    name, question_set = "jev_two_step", TWO_STEP


class JevReaderPlayer(JevSetPlayer):
    name, question_set = "jev_reader", READER


class LlmComposedPlayer(LlmSetPlayer):
    name, question_set = "llm_composed", COMPOSED


class LlmChoicePlayer(LlmSetPlayer):
    name, question_set = "llm_choice", CHOICE


class LlmTwoStepPlayer(LlmSetPlayer):
    name, question_set = "llm_two_step", TWO_STEP


class LlmReaderPlayer(LlmSetPlayer):
    name, question_set = "llm_reader", READER


SET_PLAYERS = (JevChoicePlayer, JevTwoStepPlayer, JevReaderPlayer,
               LlmComposedPlayer, LlmChoicePlayer, LlmTwoStepPlayer, LlmReaderPlayer)
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_set_players.py tests/test_players.py tests/test_cli.py`
Expected: `58 passed in 5.88s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `352 passed, 9 deselected in 29.65s`

- [ ] **Step 6: Commit**

```bash
git add bakeoff/players/__init__.py bakeoff/players/set_players.py tests/fakes.py tests/test_cli.py tests/test_players.py tests/test_set_players.py
git commit -F <message file>   # feat: jev_choice, jev_two_step, jev_reader and an LLM twin for every question set
```

---

### Task 3: The report scores every question-set Noul, and the page shows what set players were told

**Files:**
- Modify: `README.md`
- Modify: `bakeoff/replay.py`
- Modify: `bakeoff/report.py`
- Modify: `docs/STEP_RECORD.md`
- Modify: `viewer/app.js`
- Modify: `viewer/minds.js`
- Test: `tests/test_report.py`
- Test: `viewer/tests/minds.test.js`

**Interfaces:**
- Consumes: `truth_of` (task 1); the answers and `info.rule` the set players log (task 2).
- Produces: report column `brier_all` (last); `Minds.isSetPlayer`, `Minds.readGrid`, `Minds.setMind`; tags and descriptions for the seven players; their order in `bakeoff.replay.CONTESTANTS`.

- [ ] **Step 1: Write the failing tests**

Apply to `tests/test_report.py`:

```diff
@@ -221,12 +221,22 @@ def test_brier_scores_the_composed_jevs_four_nouls_against_what_the_senses_show(
     assert row["brier_gap_right"] == 0.0
     assert row["brier_gap_jump"] == pytest.approx(0.5 ** 2 / 2)
     assert row["brier_gap_ahead"] is None and row["brier_left_safe"] is None  # it is not asked those
+    assert row["brier_all"] == pytest.approx((0.1 ** 2 + 0.3 ** 2 + 0 + 0.5 ** 2 + 0.2 ** 2 + 0.1 ** 2 + 0 + 0) / 8)
 
 
-def test_the_four_composed_columns_close_the_table_and_are_empty_for_everyone_else():
-    assert COLUMNS[-4:] == ("brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump")
+def test_brier_all_scores_every_question_set_noul_it_can_check():
+    senses = {"ahead": [{"row": r, "gaps_relative": [0] if r == 1 else []} for r in range(1, 7)]}
+    answers = {"tile_r1_c": {"noul": 0.8}, "tile_r2_l1": {"noul": 0.4}, "trapped_stay": {"noul": 0.5},
+               "tile_r9_c": {"noul": 1.0}, "text": "{}", "stop_reason": "end_turn", "flag": {"noul": True}}
+    (row,) = summarize([step(player="llm_reader", senses=senses, ground_truth={}, answers=answers)])
+    assert row["brier_all"] == pytest.approx((0.2 ** 2 + 0.4 ** 2 + 0.5 ** 2) / 3)  # row 9 is out of view
+    assert row["brier_gap_left"] is None
+
+
+def test_the_four_composed_columns_then_brier_all_close_the_table():
+    assert COLUMNS[-5:] == ("brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump", "brier_all")
     (row,) = summarize([step(answers={"gap_ahead": {"type": "noul", "noul": 0.5}}, ground_truth={"gap_ahead": True})])
-    assert [row[c] for c in COLUMNS[-4:]] == [None] * 4 and row["brier_gap_ahead"] == 0.25
+    assert [row[c] for c in COLUMNS[-5:-1]] == [None] * 4 and row["brier_gap_ahead"] == row["brier_all"] == 0.25
 
 
 def test_small_amounts_keep_four_decimals_in_the_table():
```

Apply to `viewer/tests/minds.test.js`:

```diff
@@ -223,3 +223,34 @@ test("the status line says how an episode ended", () => {
   const hostile = { ...episode, rows_survived: "<script>" };
   for (const status of ["dead", "cut", "finished"]) assert.doesNotMatch(Minds.statusLine(hostile, { status }, 12), /<script>/);
 });
+
+test("question-set players get the set panel; the composed Jev and the one-shots keep theirs", () => {
+  assert.deepEqual(["jev_choice", "jev_two_step", "jev_reader", "llm_composed", "llm_choice", "llm_two_step", "llm_reader"]
+    .map(Minds.isSetPlayer), [true, true, true, true, true, true, true]);
+  assert.deepEqual(["jev_composed", "jev", "llm", "fly", "jev_other"].map(Minds.isSetPlayer), [false, false, false, false, false]);
+  assert.equal(Minds.tagOf("jev_two_step"), "JEV 2-STEP");
+  assert.equal(Minds.tagOf("llm_reader"), "LLM READER");
+});
+
+test("the two-step panel shows both answers per move, marks the move made and names the rule as ours", () => {
+  const answers = {};
+  for (const a of ["left", "stay", "right", "jump"]) { answers["gap_" + a] = { noul: 0.1 }; answers["trapped_" + a] = { noul: 0.2 }; }
+  const html = Minds.setMind(frame({ answers, chosen_action: "left", info: { rule: "lowest_two_step_risk" } }));
+  assert.match(html, /lands on a gap<\/th><th>dead end after/);
+  assert.match(html, /<tr class="picked"><th>left<\/th>/);
+  assert.equal(count(html, "10%"), 4);
+  assert.match(html, /by lowest_two_step_risk\. The questions and that rule are ours\./);
+});
+
+test("the reader panel draws what it read, darker for surer gaps, and escapes a choice and a stop reason", () => {
+  const answers = { tile_r1_c: { noul: 0.9 }, tile_r1_l1: { noul: 0 }, tile_r1_r1: { noul: 0.25 }, tile_r2_c: { noul: 1 },
+                    tile_r2_l1: { noul: 0 }, tile_r2_r1: { noul: 0 } };
+  const html = Minds.setMind(frame({ answers, info: null }));
+  assert.match(html, /aria-label="the 6 tiles it read"/);
+  assert.match(html, /fill-opacity="0\.90"/);
+  assert.match(html, /by its rule\./);
+  const odd = Minds.setMind(frame({ answers: { action: { choice: "<b>" }, stop_reason: "<i>" } }));
+  assert.match(odd, /Chose &#60;b&#62;/);
+  assert.match(odd, /stopped: &#60;i&#62;/);
+  assert.equal(Minds.readGrid({ gap_left: { noul: 0.1 } }), "");
+});
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest -q tests/test_report.py tests/test_viewer_js.py`
Expected:

```text
FAILED tests/test_report.py::test_brier_scores_the_composed_jevs_four_nouls_against_what_the_senses_show
FAILED tests/test_report.py::test_brier_all_scores_every_question_set_noul_it_can_check
FAILED tests/test_report.py::test_the_four_composed_columns_then_brier_all_close_the_table
FAILED tests/test_viewer_js.py::test_viewer_javascript - AssertionError: ✔ an...
4 failed, 24 passed in 0.54s
```

- [ ] **Step 3: Write the implementation**

Apply to `README.md`:

```diff
@@ -40,7 +40,7 @@ neither). The cap works as in `run`: per paid player, default 0, which makes a f
 answers are already cached; a live paid run on a seed below 1000 is refused without `--tournament`. `live`
 builds one fly brain; do not start a second fly process next to it. Afterwards `view` replays the directory.
 
-Paid players (`jev`, `jev_composed`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
+Paid players (`jev`, `jev_composed`, `llm` and the question-set players below) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
 file at the repo root (template: `.env.example`). They spend nothing unless told to:
 
     uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300 --game v1
@@ -52,6 +52,13 @@ jump. The wording and that rule are ours, not TypeSafe's, and it looks one step
 one-shot `jev` stays for comparison: on the dangerous states of practice track 1000 its single Choice
 landed on a gap about as often as always staying (`docs/DECISIONS.md`, decisions 14 and 15).
 
+Three more ways to ask Jev, and an LLM twin for each way (decisions 25 and 26): `jev_choice` asks one Choice whose
+options name each move's landing tile, `jev_two_step` asks eight yes/no questions (each move's landing, and whether it
+leaves a way on), `jev_reader` asks about every visible tile and code plans over its answers like the solver.
+`llm_composed`, `llm_choice`, `llm_two_step` and `llm_reader` ask Claude Haiku exactly the same questions and use the
+same rule, so the model is the only difference. The questions and the rules are ours
+(`bakeoff/players/question_sets.py`).
+
 `--max-requests` is a hard cap on live requests for **each** paid player in the run; the default 0
 only replays `.cache/responses`. Every answer is cached, so a repeated run of the same game and track
 is free, and a run stopped by the cap (`status: budget_exhausted`) continues from the cache next time.
```

Apply to `bakeoff/replay.py`:

```diff
@@ -15,7 +15,8 @@ REPLAY_VERSION = 1
 SCHEMA_VERSION = 1  # the step record this module reads; the runner writes it (a test keeps the two equal)
 # shown first, in this order: the demo's three (the composed Jev is its Jev), then the one-shot Jev;
 # everyone else in order of appearance
-CONTESTANTS = ("fly", "jev_composed", "llm", "jev")
+CONTESTANTS = ("fly", "jev_composed", "llm", "jev", "jev_choice", "llm_choice", "llm_composed", "jev_two_step",
+               "llm_two_step", "jev_reader", "llm_reader")
 # what a frame leaves out of its step record: the first three name the episode, the others are
 # replaced by `ahead`, `q` and the replay's `tracks`
 DROPPED = ("run_id", "player", "seed", "senses", "questions", "track")
```

Apply to `bakeoff/report.py`:

```diff
@@ -7,14 +7,14 @@ import statistics
 from collections import defaultdict
 from pathlib import Path
 
-from bakeoff.senses import LANDS, lands_on_gap
+from bakeoff.senses import truth_of
 
 COLUMNS = ("player", "runs", "incomplete", "missing", "mean_rows", "median_rows", "finished",
            "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
            "fallback_rate", "invalid_rate", "error_rate",
            "requests", "spent", "cache_hits", "mean_latency_ms", "input_tokens", "output_tokens", "cost_usd",
            "brier_gap_ahead", "brier_left_safe",
-           "brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump")
+           "brier_gap_left", "brier_gap_stay", "brier_gap_right", "brier_gap_jump", "brier_all")
 
 # USD per million tokens (input, output), by the model id in meta.json. Jev is absent: only a blended
 # figure from its console is known (docs/COSTS.md), not an input and an output price, so its cost
@@ -75,23 +75,30 @@ def _cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float
 
 
 def _truth(step: dict, noul: str) -> bool | None:
-    """The logged `ground_truth` for the one-shot Jev's two Nouls. The composed Jev's `gap_<action>`
-    Nouls ask what the senses show, so their truth is read from the record's senses."""
+    """The logged `ground_truth` for the one-shot Jev's two Nouls. The question sets' Nouls (`gap_<action>`,
+    `trapped_<action>`, `tile_r<row>_<side>`) ask what the senses show, so their truth is read from the
+    record's senses (bakeoff.senses.truth_of)."""
     truth = (step.get("ground_truth") or {}).get(noul)
-    if truth is None and noul.removeprefix("gap_") in LANDS and step.get("senses"):
-        truth = lands_on_gap(step["senses"], noul.removeprefix("gap_"))
+    if truth is None and step.get("senses"):
+        truth = truth_of(step["senses"], noul)
     return truth
 
 
-def _brier(steps: list[dict], noul: str) -> float | None:
+def _brier(steps: list[dict], noul: str | None) -> float | None:
     """Mean squared gap between a logged Noul probability and the truth (0 is perfect, 0.25 is what
-    always answering 0.5 scores). Cached answers count: a judgment is a judgment."""
+    always answering 0.5 scores), for one Noul id, or for every Noul whose truth is known when `noul` is
+    None. Cached answers count: a judgment is a judgment."""
     errors = []
     for s in steps:
-        answer = (s.get("answers") or {}).get(noul)
-        truth = _truth(s, noul)
-        if isinstance(answer, dict) and isinstance(answer.get("noul"), (int, float)) and truth is not None:
-            errors.append((answer["noul"] - float(truth)) ** 2)
+        answers = s.get("answers") or {}
+        for qid in (answers if noul is None else (noul,)):
+            answer = answers.get(qid)
+            if not isinstance(answer, dict) or isinstance(answer.get("noul"), bool) \
+                    or not isinstance(answer.get("noul"), (int, float)):
+                continue
+            truth = _truth(s, qid)
+            if truth is not None:
+                errors.append((answer["noul"] - float(truth)) ** 2)
     return _mean(errors)
 
 
@@ -129,6 +136,7 @@ def _summarize_player(player: str, steps: list[dict], model: str | None = None)
         "cost_usd": _cost_usd(model, input_tokens, output_tokens),
         "brier_gap_ahead": _brier(steps, "gap_ahead"), "brier_left_safe": _brier(steps, "left_safe"),
         **{f"brier_gap_{action}": _brier(steps, f"gap_{action}") for action in ("left", "stay", "right", "jump")},
+        "brier_all": _brier(steps, None),
     }
 
 
```

Apply to `docs/STEP_RECORD.md`:

```diff
@@ -38,8 +38,8 @@ use the next record's `row`/`lane`, or derive the landing tile as below.
 | `lane` | int | lane at decision time, `0 .. lanes-1` (starts at `lanes // 2`, i.e. 6) |
 | `senses` | object | exactly what the player was shown, see below |
 | `looming` | `{left_hz, right_hz}` | floats, the fly's eye rates for these senses: each visible gap adds `gain_hz / row ** falloff` to its eye (own lane: both eyes), the sum is capped at `max_hz` and rounded to the nearest `step_hz` (so 11 levels, 0 to 250). Ours, not the fly's biology |
-| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. Composed Jev: `{gap_left, gap_stay, gap_right, gap_jump}`, four Nouls. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON |
-| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. Composed Jev: `{gap_left: {type, noul}, gap_stay, gap_right, gap_jump}`, each the probability that the action lands on a gap. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Null after an `error` |
+| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. Composed Jev: `{gap_left, gap_stay, gap_right, gap_jump}`, four Nouls. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON. Question-set players (`jev_choice`, `jev_two_step`, `jev_reader`): the set's questions, in Jev's form. Their LLM twins (`llm_<set>`): `{system, schema, max_tokens, questions}`, `questions` being the same set |
+| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. Composed Jev: `{gap_left: {type, noul}, gap_stay, gap_right, gap_jump}`, each the probability that the action lands on a gap. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Question-set players: one entry per question id in Jev's form (`{noul}` or `{choice}`); an LLM twin's entries are read from its JSON, plus `text` and `stop_reason`. Null after an `error` |
 | `chosen_action` | string or null | what the player asked for. May be an invalid string, or null if it gave none |
 | `executed_action` | string | what the game ran: `left`, `right`, `jump` or `stay`. Equals `chosen_action` unless a fallback applied |
 | `solver_action` | string | the reference solver's move on the same senses: the first action, in the order `stay, left, right, jump`, with the maximum depth |
@@ -103,6 +103,16 @@ finite number, and never `gated`. The report scores its Nouls (`brier_gap_left`
 the record's `senses` show (`bakeoff.senses.lands_on_gap`), since that is what the questions ask;
 `ground_truth` keeps its two keys.
 
+The question-set players (`bakeoff/players/question_sets.py`, `set_players.py`) ask one set each: `composed` (the
+composed Jev's four Nouls; Jev's own player is `jev_composed`), `choice` (one Choice whose options name each move's
+landing tile), `two_step` (the four landing Nouls plus `trapped_<action>`: would every move after this one land on a
+gap?) and `reader` (`tile_r<row>_<side>`, one Noul per visible tile, e.g. `tile_r2_l3`). `jev_<set>` asks Jev,
+`llm_<set>` asks Claude Haiku the same questions in one structured request. The set's rule picks the move from the
+answers and is named in `info.rule` (with `info.set` and `info.order`); every wording and every rule is ours. A
+decision is `invalid` unless every answer is usable (a Noul a finite number from 0 to 1, the Choice one of the four
+moves; for an LLM twin also JSON with `stop_reason` `end_turn`). The report's `brier_all` scores every Noul whose
+truth the senses show (`bakeoff.senses.truth_of`).
+
 ## The landing tile
 
 Given `row`, `lane` and `executed_action` (`lanes` from `track.lanes`):
```

Apply to `viewer/app.js`:

```diff
@@ -19,6 +19,13 @@
     jev_composed: "Jev, four yes/no questions a row",
     jev: "Jev, one broad question a row",
     llm: "Large language model",
+    jev_choice: "Jev, one question a row, landings named",
+    jev_two_step: "Jev, eight yes/no questions a row, looks two moves on",
+    jev_reader: "Jev reads every visible tile, code plans",
+    llm_composed: "The LLM, asked the composed Jev's four questions",
+    llm_choice: "The LLM, asked jev_choice's question",
+    llm_two_step: "The LLM, asked jev_two_step's eight questions",
+    llm_reader: "The LLM reads every visible tile, code plans",
     random: "Random moves, the floor",
     always_jump: "Always jumps, the second floor",
     solver: "Scripted solver, the reference (not a contestant)",
```

Apply to `viewer/minds.js`:

```diff
@@ -8,7 +8,12 @@
     ["DNa01", "steering"], ["DNb01", "steering"], ["DNp01", "Giant Fiber, escape jump"], ["DNa02", "logged only"],
   ];
   // the short uppercase tag a runner carries in the tunnel and on its panel
-  const TAGS = { fly: "FLY", jev_composed: "JEV", llm: "LLM", jev: "JEV ONE-SHOT", solver: "SOLVER", random: "RANDOM", always_jump: "JUMPER" };
+  const TAGS = { fly: "FLY", jev_composed: "JEV", llm: "LLM", jev: "JEV ONE-SHOT", solver: "SOLVER", random: "RANDOM", always_jump: "JUMPER",
+    jev_choice: "JEV CHOICE", jev_two_step: "JEV 2-STEP", jev_reader: "JEV READER", llm_composed: "LLM COMPOSED",
+    llm_choice: "LLM CHOICE", llm_two_step: "LLM 2-STEP", llm_reader: "LLM READER" };
+  // players that ask a question set (bakeoff/players/question_sets.py): Jev or the LLM, and the set's name
+  const SET_PLAYER = /^(jev|llm)_(composed|choice|two_step|reader)$/;
+  const isSetPlayer = (player) => SET_PLAYER.test(player) && player !== "jev_composed";
   const tagOf = (player) => TAGS[player] || String(player).toUpperCase();
   const DEATHS = {
     ran_into_gap: "ran straight into a gap",
@@ -159,6 +164,38 @@
       ". The wording and that rule are ours. It looks one step ahead only.</p>";
   }
 
+  // What a question-set player was told (docs/superpowers/specs/2026-09-21-jev-family-design.md): the read tiles as a
+  // grid (darker = more sure it is a gap), each move's yes/no answers as bars, or the Choice it made.
+  function readGrid(answers) {
+    const tiles = Object.keys(answers).map((id) => /^tile_r(\d+)_(c|l\d+|r\d+)$/.exec(id)).filter(Boolean).map((m) => ({
+      row: Number(m[1]), offset: m[2] === "c" ? 0 : (m[2][0] === "l" ? -1 : 1) * Number(m[2].slice(1)), p: answers[m[0]].noul }));
+    if (!tiles.length) return "";
+    const rows = Math.max(...tiles.map((t) => t.row)), window_ = Math.max(...tiles.map((t) => Math.abs(t.offset)));
+    const cells = tiles.map((t) => '<rect x="' + (t.offset + window_) * 12 + '" y="' + (rows - t.row) * 8 +
+      '" width="11" height="7" class="tile"/>' + (typeof t.p === "number" ? '<rect x="' + (t.offset + window_) * 12 + '" y="' +
+      (rows - t.row) * 8 + '" width="11" height="7" class="gap" fill-opacity="' + Math.max(0, Math.min(1, t.p)).toFixed(2) + '"/>' : "")).join("");
+    return '<p class="label">What it read (darker = more sure it is a gap)</p><svg class="senses" viewBox="0 0 ' +
+      (2 * window_ + 1) * 12 + " " + rows * 8 + '" role="img" aria-label="the ' + tiles.length + ' tiles it read">' + cells + "</svg>";
+  }
+
+  function setMind(frame) {
+    const answers = frame.answers;
+    if (!answers) return "";
+    const noul = (id) => (answers[id] && typeof answers[id].noul === "number" ? answers[id].noul : null);
+    const kinds = [["gap_", "lands on a gap"], ["trapped_", "dead end after"]].filter(([prefix]) => ACTIONS.some((a) => answers[prefix + a]));
+    let html = readGrid(answers);
+    if (kinds.length) {
+      html += '<table class="probs"><tr><th></th>' + kinds.map(([, label]) => "<th>" + label + "</th>").join("") + "</tr>" +
+        ACTIONS.map((a) => "<tr" + (a === frame.chosen_action ? ' class="picked"' : "") + "><th>" + a + "</th>" +
+          kinds.map(([prefix]) => { const p = noul(prefix + a); return "<td>" + (p == null ? "–" : bar(p) + " " + percent(p)) + "</td>"; }).join("") +
+          "</tr>").join("") + "</table>";
+    }
+    if (answers.action && answers.action.choice != null) html += '<p class="label">Chose ' + esc(answers.action.choice) + "</p>";
+    if (answers.stop_reason != null && answers.stop_reason !== "end_turn") html += '<p class="warn">stopped: ' + esc(answers.stop_reason) + "</p>";
+    const rule = frame.info && frame.info.rule ? esc(frame.info.rule) : "its rule";
+    return html + '<p class="muted">Code picks the move from these answers by ' + rule + ". The questions and that rule are ours.</p>";
+  }
+
   // How sure the composed Jev was that the move it chose does not land on a gap (the visor's slit), or null
   function visorP(frame) {
     const answer = (frame.answers || {})["gap_" + frame.chosen_action];
@@ -215,7 +252,8 @@
     const body = episode.player === "fly" ? flyMind(frame, context)
       : episode.player === "jev" ? jevMind(frame)
       : episode.player === "jev_composed" ? jevComposedMind(frame)
-      : episode.player === "llm" ? llmMind(frame) : "";
+      : episode.player === "llm" ? llmMind(frame)
+      : isSetPlayer(episode.player) ? setMind(frame) : "";
     return '<div class="saw">' + sensesGrid(frame, context.window) + verdict(frame) + "</div>" + body + cost(frame) + asked(episode, frame);
   }
 
@@ -229,7 +267,7 @@
   }
 
   const api = { esc, cell, bar, tagOf, sensesGrid, verdict, spikeRaster, flyMind, jevMind, jevComposedMind, visorP, llmMind, cost, asked,
-                ours, mind, statusLine };
+                ours, mind, statusLine, isSetPlayer, readGrid, setMind };
   if (typeof module !== "undefined" && module.exports) module.exports = api;
   else root.Minds = api;
 })(typeof window !== "undefined" ? window : globalThis);
```

- [ ] **Step 4: Run the task's tests**

Run: `uv run pytest -q tests/test_report.py tests/test_viewer_js.py`
Expected: `28 passed in 0.41s`

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `353 passed, 9 deselected in 31.13s`

- [ ] **Step 6: Commit**

```bash
git add README.md bakeoff/replay.py bakeoff/report.py docs/STEP_RECORD.md tests/test_report.py viewer/app.js viewer/minds.js viewer/tests/minds.test.js
git commit -F <message file>   # feat: the report scores every question-set Noul, and the page shows what set players were told
```

---

### Task 4: The paid runs (controller only)

Nothing here is dispatched to an implementer. One command at a time, every paid command capped, v2 practice seeds only.

- [ ] One capped track: `uv run python -m bakeoff run --players jev_composed,jev_choice,jev_two_step,jev_reader,llm,llm_composed,llm_choice,llm_two_step,llm_reader --seeds 1 --seed-start 1000 --max-requests 150`. Read the report: requests, tokens, `cost_usd`, latency, rows, `brier_all` per player.
- [ ] From the measured Haiku cost per request, size the cap for seeds 1001–1004 so the Haiku total for update 2 stays at or under 5.00 USD (decision 26), then run them.
- [ ] The fly on seeds 1000–1004 (free; one process, nothing else using the fly at the same time).
- [ ] `docs/COSTS.md` (a table per player: rows, requests, tokens, USD, latency, Brier), `docs/DECISIONS.md` (the result and what the write-up must carry), `docs/UPDATES.md` (item 2 built), `CLAUDE.md` status. Five tracks are an impression, not a result.
- [ ] Final whole-branch review of update 2a aimed at the design: money safety, same signals for both models, honest labels, the cache of `jev_composed` still replaying.
