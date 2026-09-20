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
