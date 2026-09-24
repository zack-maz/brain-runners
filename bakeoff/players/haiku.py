"""The LLM: Claude Haiku 4.5 gets the same JSON senses and must answer with one action as
structured output. Anything else (cut off, refused, not JSON, no action) is logged as invalid."""

from __future__ import annotations

import json

from bakeoff.clients.llm import LlmClient
from bakeoff.game.engine import ACTIONS
from bakeoff.players.briefing import RULES
from bakeoff.players.paid import PaidPlayer

QUESTIONS = {
    "system": RULES + " The user message is the runner's current view as JSON. Answer with the action to take now.",
    "schema": {"type": "object", "properties": {"action": {"type": "string", "enum": list(ACTIONS)}},
               "required": ["action"], "additionalProperties": False},
    "max_tokens": 256,
}


class HaikuPlayer(PaidPlayer):
    name = "haiku"
    client_class = LlmClient
    questions = QUESTIONS

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers = {"text": payload.get("text"), "stop_reason": payload.get("stop_reason")}
        try:
            action = json.loads(payload.get("text") or "")["action"]
        except (ValueError, KeyError, TypeError):
            return None, True, answers
        if not isinstance(action, str):
            return None, True, answers
        return action, payload.get("stop_reason") != "end_turn" or action not in ACTIONS, answers
