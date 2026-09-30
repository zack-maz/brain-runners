"""GLM Flash asked the one broad question: the twin of `haiku_plain`, sent exactly what Claude Haiku is sent (the same
briefing, the same one-action schema), so the model is what differs. It reads the reply in two ways Claude Haiku's
twin does not need: the markdown fence GLM likes to wrap its JSON in is stripped, and a reply that is exactly one bare
move word ("stay", as GLM answers instead of {"action": "stay"}) is read as that move (decision 55). Both are ours;
anything looser stays invalid."""

from __future__ import annotations

import json

from bakeoff.clients.glm import GlmClient
from bakeoff.game.engine import ACTIONS
from bakeoff.players.haiku import HaikuPlayer
from bakeoff.players.paid import unfenced


class GlmPlayer(HaikuPlayer):
    name = "glm_plain"
    client_class = GlmClient

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        # the fence is stripped for the parse only: the log keeps the answer as it came.
        text = unfenced(payload.get("text") or "")
        if text in ACTIONS:  # the bare word, exactly: read as the JSON it was asked for
            text = json.dumps({"action": text})
        action, invalid, answers = super().read({**payload, "text": text})
        return action, invalid, {**answers, "text": payload.get("text")}
