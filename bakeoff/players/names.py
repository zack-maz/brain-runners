"""Player names, and the one rename this project has made.

Claude Haiku's players were called `llm*` while it was the only chat model. GLM Flash made that
name ambiguous — `llm_composed` and `glm_composed` read as a pair of unlike things — so they are
`haiku*` now (decision 39).

Nothing on disk changes. The response cache is keyed by provider, model, senses and questions, not
by a player's name, so every answer already paid for still replays; the provider ids in
`bakeoff/clients/` are part of the cache path and stay as they are. Run directories recorded before
the rename keep their `llm*.jsonl` files and their `"player": "llm"` records, and are read through
`canonical()`, so one player appears once wherever old and new runs are merged.
"""

from __future__ import annotations

RENAMED = {
    "llm": "haiku",
    "llm_composed": "haiku_composed",
    "llm_choice": "haiku_choice",
    "llm_two_step": "haiku_two_step",
    "llm_reader": "haiku_reader",
}


def canonical(name: str) -> str:
    """The name a player goes by now. Old names are accepted everywhere they used to work: on the
    command line, in a `DIR:player,...` source, and in a record read back from an old run."""
    return RENAMED.get(name, name)
