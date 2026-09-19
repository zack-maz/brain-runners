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

Status: phase 2 of 5 built. The untrained fly plays: on seeds 0–19 it survives 127 rows
on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`).

    uv run pytest -m "not slow"                      # 2 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>

See `docs/DECISIONS.md` for what has been decided and what comes next.
