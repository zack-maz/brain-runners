"""Players that ask a question set (bakeoff/players/question_sets.py): `jev_<set>` asks Jev, `haiku_<set>` asks
Claude Haiku and `glm_<set>` asks GLM Flash the same questions, and the set's rule picks the move from any of their
answers. The two chat models are sent the same request, built once in ChatSetPlayer, so only the model differs.
The same cache, cap, error and fallback rules as every paid player (PaidPlayer). The step1 set's Jev is
`jev_step1`, which stays its own class."""

from __future__ import annotations

import json

from bakeoff.clients.glm import GlmClient
from bakeoff.clients.jev import JevClient
from bakeoff.clients.llm import LlmClient
from bakeoff.game.engine import Game
from bakeoff.game.rules import DEFAULT, RULES
from bakeoff.players.base import Decision
from bakeoff.players.briefing import RULES as BRIEFING
from bakeoff.players.jev_step1 import ORDER
from bakeoff.players.paid import PaidPlayer, unfenced
from bakeoff.players.question_sets import GUIDED, STEP1, MAP, STEP2, QuestionSet, values_of


CHAT_SYSTEM = (BRIEFING + " The user message is the runner's current view as JSON. Answer every question below, "
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


class ChatSetPlayer(SetPlayer):
    """A chat model asked the set's questions in one request: the same system prompt, the same question lines and
    the same JSON shape for every such model, so the model is what differs."""

    def request(self, set_questions: dict) -> dict:
        lines = []
        for qid, q in set_questions.items():
            text = q["instructions"].removeprefix(BRIEFING).strip()
            if q["type"] == "choice":
                text += " Options: " + "; ".join(f"`{option}`: {what}" for option, what in q["criteria"].items()) + "."
            lines.append(f"- `{qid}` ({'yes/no' if q['type'] == 'noul' else 'choice'}): {text}")
        properties = {qid: {"type": "number"} if q["type"] == "noul" else {"type": "string", "enum": list(q["criteria"])}
                      for qid, q in set_questions.items()}
        return {"system": CHAT_SYSTEM + "\n\nQuestions:\n" + "\n".join(lines),
                "schema": {"type": "object", "properties": properties, "required": list(set_questions),
                           "additionalProperties": False},
                "max_tokens": 256 + 12 * len(set_questions), "questions": set_questions}

    def answers_of(self, payload: dict) -> tuple[dict | None, dict]:
        logged = {"text": payload.get("text"), "stop_reason": payload.get("stop_reason")}
        try:
            data = json.loads(unfenced(payload.get("text") or ""))
        except ValueError:
            return None, logged
        if not isinstance(data, dict) or payload.get("stop_reason") != "end_turn":
            return None, logged
        answers = {qid: {"noul": data.get(qid)} if q["type"] == "noul" else {"choice": data.get(qid)}
                   for qid, q in self.set_questions.items()}
        return answers, {**answers, **logged}


class HaikuSetPlayer(ChatSetPlayer):
    client_class = LlmClient


class GlmSetPlayer(ChatSetPlayer):
    client_class = GlmClient


class JevGuidedPlayer(JevSetPlayer):
    name, question_set = "jev_guided", GUIDED


class JevStep2Player(JevSetPlayer):
    name, question_set = "jev_step2", STEP2


class JevMapPlayer(JevSetPlayer):
    name, question_set = "jev_map", MAP


class HaikuStep1Player(HaikuSetPlayer):
    name, question_set = "haiku_step1", STEP1


class HaikuGuidedPlayer(HaikuSetPlayer):
    name, question_set = "haiku_guided", GUIDED


class HaikuStep2Player(HaikuSetPlayer):
    name, question_set = "haiku_step2", STEP2


class HaikuMapPlayer(HaikuSetPlayer):
    name, question_set = "haiku_map", MAP


class GlmStep1Player(GlmSetPlayer):
    name, question_set = "glm_step1", STEP1


class GlmGuidedPlayer(GlmSetPlayer):
    name, question_set = "glm_guided", GUIDED


class GlmStep2Player(GlmSetPlayer):
    name, question_set = "glm_step2", STEP2


class GlmMapPlayer(GlmSetPlayer):
    name, question_set = "glm_map", MAP


SET_PLAYERS = (JevGuidedPlayer, JevStep2Player, JevMapPlayer,
               HaikuStep1Player, HaikuGuidedPlayer, HaikuStep2Player, HaikuMapPlayer,
               GlmStep1Player, GlmGuidedPlayer, GlmStep2Player, GlmMapPlayer)
