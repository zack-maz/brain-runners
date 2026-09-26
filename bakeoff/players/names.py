"""Player names, and the two renames this project has made.

Claude Haiku's players were called `llm*` while it was the only chat model. GLM Flash made that
name ambiguous — `llm_composed` and `glm_composed` read as a pair of unlike things — so they became
`haiku*` (decision 39). Then the question sets were renamed for the Brain Battle character select,
where each set is a skin (decision 44): the one-shot is `plain`, `choice` is `guided`, `composed` is
`step1`, `two_step` is `step2` and `reader` is `map`, so `jev` is `jev_plain` and `jev_composed` is
`jev_step1`. Every old name maps straight to the name it has now, never through another old name.

Nothing on disk changes. The response cache is keyed by provider, model, senses and questions, not
by a player's name, so every answer already paid for still replays; the provider ids in
`bakeoff/clients/` are part of the cache path and stay as they are. Run directories recorded before
a rename keep their old files (`llm.jsonl`, `jev_composed.jsonl`) and their old `"player"` records,
and are read through `canonical()`, so one player appears once wherever old and new runs are merged.
"""

from __future__ import annotations

RENAMED = {
    # decision 39's llm* names, brought up to decision 44
    "llm": "haiku_plain",
    "llm_composed": "haiku_step1",
    "llm_choice": "haiku_guided",
    "llm_two_step": "haiku_step2",
    "llm_reader": "haiku_map",
    # decision 44
    "jev": "jev_plain",
    "jev_composed": "jev_step1",
    "jev_choice": "jev_guided",
    "jev_two_step": "jev_step2",
    "jev_reader": "jev_map",
    "haiku": "haiku_plain",
    "haiku_composed": "haiku_step1",
    "haiku_choice": "haiku_guided",
    "haiku_two_step": "haiku_step2",
    "haiku_reader": "haiku_map",
    "glm": "glm_plain",
    "glm_composed": "glm_step1",
    "glm_choice": "glm_guided",
    "glm_two_step": "glm_step2",
    "glm_reader": "glm_map",
}


def canonical(name: str) -> str:
    """The name a player goes by now. Old names are accepted everywhere they used to work: on the
    command line, in a `DIR:player,...` source, and in a record read back from an old run."""
    return RENAMED.get(name, name)
