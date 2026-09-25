"""Question sets: what a paid player asks each row, and the rule that turns the answers into a move. Each set
is played twice, by Jev (`jev_<set>`) and by Claude Haiku (`haiku_<set>`), with the same questions and the same rule
(docs/superpowers/specs/2026-09-21-jev-family-design.md; what still differs is in docs/COSTS.md, "Update 2a"). OURS, not TypeSafe's or Anthropic's: every wording and
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
