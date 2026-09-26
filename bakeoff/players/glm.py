"""GLM Flash asked the one broad question: the twin of `haiku_plain`, sent exactly what Claude Haiku is sent (the same
briefing, the same one-action schema), so the model is what differs. Its only difference in reading the reply is
the markdown fence GLM likes to wrap its JSON in."""

from __future__ import annotations

from bakeoff.clients.glm import GlmClient
from bakeoff.players.haiku import HaikuPlayer
from bakeoff.players.paid import unfenced


class GlmPlayer(HaikuPlayer):
    name = "glm_plain"
    client_class = GlmClient

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        # the fence is stripped for the parse only: the log keeps the answer as it came.
        action, invalid, answers = super().read({**payload, "text": unfenced(payload.get("text") or "")})
        return action, invalid, {**answers, "text": payload.get("text")}
