"""jev_step1 (Jev asked the step1 set; `jev_composed` until decision 44): one request per row with
four pointed yes/no questions, one per action ("would this action land on a gap?", naming the value
to look up), and code that picks the action Jev thinks is least likely to land on a gap. OURS, not TypeSafe's: the wording of the questions and the rule that
turns four answers into a move (docs/DECISIONS.md, decisions 14 and 15). It looks one step ahead only;
it does not plan. `jev_plain`, the one broad question, stays as it was, for comparison."""

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


class JevStep1Player(PaidPlayer):
    name = "jev_step1"
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
