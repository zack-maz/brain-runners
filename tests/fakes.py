"""Stand-ins for the two provider SDKs. No test touches the network."""

from __future__ import annotations


class FakeTypeSafe:
    """Looks like typesafe_sdk.TypeSafeClient. `reply` is a SystemOneResponse-shaped dict, or an exception to raise."""

    def __init__(self, reply):
        self.reply, self.calls, self.closed = reply, [], False

    def system_one(self, state, questions, model=None):
        from typesafe_sdk import SystemOneResponse

        self.calls.append({"state": state, "questions": questions, "model": model})
        if isinstance(self.reply, Exception):
            raise self.reply
        return SystemOneResponse.model_validate(self.reply)

    def close(self):
        self.closed = True


def jev_reply(action="stay", gap_ahead=0.1, left_safe=0.9):
    return {"model": "jev-latest", "usage": {"input_tokens": 400, "output_tokens": 3},
            "answers": {"action": {"type": "choice", "choice": action, "confidence": 0.7,
                                   "probabilities": {a: 0.7 if a == action else 0.1
                                                     for a in ("left", "right", "jump", "stay")}},
                        "gap_ahead": {"type": "noul", "noul": gap_ahead},
                        "left_safe": {"type": "noul", "noul": left_safe}}}


def jev_step1_reply(left=0.1, stay=0.1, right=0.1, jump=0.1):
    """P(lands on a gap) per action, as the four Nouls of jev_step1."""
    nouls = {"left": left, "stay": stay, "right": right, "jump": jump}
    return {"model": "jev-latest", "usage": {"input_tokens": 300, "output_tokens": 4},
            "answers": {f"gap_{action}": {"type": "noul", "noul": p} for action, p in nouls.items()}}


class FakeAnthropic:
    """Looks like anthropic.Anthropic. `reply` is a Message-shaped dict, or an exception to raise."""

    def __init__(self, reply):
        self.reply, self.calls, self.closed = reply, [], False
        self.messages = self

    def create(self, **kwargs):
        import anthropic

        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return anthropic.types.Message.model_validate(self.reply)

    def close(self):
        self.closed = True


def llm_reply(text='{"action": "stay"}', stop_reason="end_turn"):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": text}], "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 520, "output_tokens": 9}}


def jev_set_reply(values: dict):
    """A Jev reply to a question set: {id: P(yes)} for Nouls, {id: move} for a Choice."""
    answers = {qid: {"type": "choice", "choice": v, "confidence": 0.7} if isinstance(v, str)
               else {"type": "noul", "noul": v} for qid, v in values.items()}
    return {"model": "jev-latest", "usage": {"input_tokens": 300, "output_tokens": 4 * len(values)}, "answers": answers}


class FakeHttp:
    """Looks like bakeoff.clients.glm.HttpTransport. `reply` is a chat-completion-shaped dict, or an exception."""

    def __init__(self, reply):
        self.reply, self.calls, self.closed = reply, [], False

    def post(self, body):
        self.calls.append(body)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def close(self):
        self.closed = True


def glm_reply(text='{"action": "stay"}', finish_reason="stop", model="glm-4.5-flash"):
    return {"id": "1", "model": model, "choices": [{"index": 0, "finish_reason": finish_reason,
                                                    "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 480, "completion_tokens": 7, "total_tokens": 487}}


class SlowPlayer:
    """A free player that takes its time, so a test can cancel a run while it is going. Registered
    under a name of its own by `slow_player()`; it never asks anyone anything."""

    name = "slow"

    def __init__(self, seconds: float = 0.05):
        self.seconds = seconds

    def reset(self, game, seed) -> None:
        pass

    def act(self, senses: dict):
        import time

        from bakeoff.players.base import Decision

        time.sleep(self.seconds)
        return Decision(chosen_action="stay")

    def observe(self, executed_action: str) -> None:
        pass


def slow_player(monkeypatch, seconds: float = 0.05) -> str:
    """Puts `SlowPlayer` in the registry for one test and gives back its name."""
    from bakeoff.players import REGISTRY

    monkeypatch.setitem(REGISTRY, SlowPlayer.name, lambda: SlowPlayer(seconds))
    return SlowPlayer.name
