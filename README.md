# brain-bakeoff

Three very different kinds of mind play the same tiny video games:

- **a traditional LLM** — prompted with the game state, replies with a move;
- **Jev** — TypeSafe's System One model, which returns typed probabilities instead of text;
- **a fruit fly brain** — the adult *Drosophila* connectome run as an untrained spiking
  simulation: game events stimulate real sensory neurons, real motor and descending
  neurons press the buttons. No learning, only innate wiring.

Every contestant plays the same seeded rounds. The output is a watchable tournament:
replays with each player's "mind" shown next to the game (Jev's probabilities, the LLM's
answer, the fly's neurons firing) and a scoreboard across games.

Status: phase 1 of 5 built (game, senses, `random` and `solver` baselines, runner, report).

    uv run pytest
    uv run python -m bakeoff run --players random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>

See `docs/DECISIONS.md` for what has been decided and what comes next.
