"""Jev: one request per row. A Choice over the four actions decides; two speculative Nouls are
logged for calibration only (the engine knows the truth for free) and never influence the move."""

from __future__ import annotations

from bakeoff.clients.jev import JevClient
from bakeoff.game.engine import ACTIONS
from bakeoff.players.briefing import RULES
from bakeoff.players.paid import PaidPlayer
from bakeoff.senses import ACTION_DESCRIPTIONS

# The Noul ids are the keys of the record's `ground_truth`, so the report can score them.
QUESTIONS = {
    "action": {"type": "choice", "instructions": RULES + " Which action should the runner take now?",
               "criteria": dict(ACTION_DESCRIPTIONS)},
    "gap_ahead": {"type": "noul", "instructions": "Is there a gap directly ahead of the runner in the next row, "
                                                  "that is, does `ahead[0].gaps_relative` contain 0?"},
    "left_safe": {"type": "noul", "instructions": "Is the lane to the runner's left safe in the next row, "
                                                  "that is, is -1 absent from `ahead[0].gaps_relative`?"},
}


class JevPlayer(PaidPlayer):
    name = "jev_plain"
    client_class = JevClient
    questions = QUESTIONS

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers = payload.get("answers") or {}
        action = (answers.get("action") or {}).get("choice")
        return action, action not in ACTIONS, answers
