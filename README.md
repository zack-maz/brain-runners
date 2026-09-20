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

Status: phase 3 of 5 built. The untrained fly plays: on seeds 0–19 it survives 127 rows
on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`). Jev and the LLM
(Claude Haiku 4.5) play behind a response cache and a hard request cap; first measured costs
will be recorded in `docs/COSTS.md` (not run yet).

    uv run pytest                                    # fast tests, 5 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>

Paid players (`jev`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
file at the repo root (template: `.env.example`). They spend nothing unless told to:

    uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300

`--max-requests` is a hard cap on live requests for **each** paid player in the run; the default 0
only replays `.cache/responses`. Every answer is cached, so a repeated run is free and a run stopped
by the cap (`status: budget_exhausted`) continues from the cache next time. `uv run pytest -m live`
makes one real request per provider. A live paid run on seeds below 1000 is refused unless
`--tournament` is passed (tournament seeds stay untouched until phase 5). A run stopped by the cap
ends there, so later players in the list do not play: put free players first, or run paid players
alone.

See `docs/DECISIONS.md` for what has been decided and what comes next.
