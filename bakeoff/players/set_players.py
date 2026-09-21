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
