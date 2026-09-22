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

Status: phases 1 to 5 of 6 built (phase 6 is the tournament and the write-up); eight updates come first
(`docs/UPDATES.md`), of which game v2 is built. The untrained fly plays: on seeds 0–19 of game v1 it survives 127
rows on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`).

The game comes in versions (`bakeoff/game/rules.py`): `v1`, the 300-row game phases 1 to 5 were played on, and
`v2`, the default, 150 rows that reach full difficulty by row 100. `--game v1` plays the old one; `--lookahead` and
`--window` change how far players see and rename the game (`v2+look3`). Each run records its game, and `view`
refuses to mix two games. Jev and the LLM
(Claude Haiku 4.5) play behind a response cache and a hard request cap; first measured costs
are in `docs/COSTS.md`.

    uv run pytest                                    # fast tests, 5 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>
    uv run python -m bakeoff view runs/<run_id> [runs/<other_run_id> ...]   # writes replay.html

    uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 150   # watch it happen
    uv run python -m bakeoff live --game v1 --seed 1001    # free: replays the recorded v1 run's answers from the cache

`live` plays one track in real time: every mind decides the same row before anyone moves on (a jumper skips
the next row; the slowest mind sets the pace, about a row a second with the fly), each decision goes into a
normal run directory and, through a server on `127.0.0.1` only, into the same page as it happens. It waits
for a browser to open the page before it starts and keeps serving afterwards until Ctrl-C (`--no-wait` does
neither). The cap works as in `run`: per paid player, default 0, which makes a free live run of a track whose
answers are already cached; a live paid run on a seed below 1000 is refused without `--tournament`. `live`
builds one fly brain; do not start a second fly process next to it. Afterwards `view` replays the directory.

Paid players (`jev`, `jev_composed`, `llm` and the question-set players below) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
file at the repo root (template: `.env.example`). They spend nothing unless told to:

    uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300 --game v1

`jev_composed` is the Jev of the demo: instead of one broad question it asks Jev four pointed yes/no
questions in one request ("would `left` land on a gap, that is, does `ahead[0].gaps_relative` contain
-1?") and code picks the action least likely to land on a gap, ties in the order stay, left, right,
jump. The wording and that rule are ours, not TypeSafe's, and it looks one step ahead only. The
one-shot `jev` stays for comparison: on the dangerous states of practice track 1000 its single Choice
landed on a gap about as often as always staying (`docs/DECISIONS.md`, decisions 14 and 15).

Three more ways to ask Jev, and an LLM twin for each way (decisions 25 and 26): `jev_choice` asks one Choice whose
options name each move's landing tile, `jev_two_step` asks eight yes/no questions (each move's landing, and whether it
leaves a way on), `jev_reader` asks about every visible tile and code plans over its answers like the solver.
`llm_composed`, `llm_choice`, `llm_two_step` and `llm_reader` ask Claude Haiku exactly the same questions and use the
same rule. Three things still differ: the LLM is also given the briefing of the rules (for three of the four sets
Jev's yes/no questions carry only the question), Jev answers its questions in parallel while the LLM writes them in
one reply, and the LLM's probabilities are numbers it writes down. The questions and the rules are ours
(`bakeoff/players/question_sets.py`).

`--max-requests` is a hard cap on live requests for **each** paid player in the run; the default 0
only replays `.cache/responses`. Every answer is cached, so a repeated run of the same game and track
is free, and a run stopped by the cap (`status: budget_exhausted`) continues from the cache next time.
`uv run pytest -m live`
makes one real request per provider. A live paid run on seeds below 1000 is refused unless
`--tournament` is passed (tournament seeds stay untouched until phase 6). A run stopped by the cap
ends there, so later players in the list do not play: put free players first, or run paid players
alone.

`view` writes one self-contained HTML file (no server, no network, fonts embedded): the demo player. The
fly, the composed Jev and the LLM run one tunnel together as pixel figures (fixed camera, everyone on the
same row at the same time), with a strip of panels underneath showing what each had in mind (the fly's
spikes and read-out signals, Jev's four answers, the LLM's answer). Blue is the cursor: it marks the mind
in focus and the tiles that mind was shown, and with auto on it cuts to whoever faces a gap (keys 1, 2, 3
or a click choose by hand; space plays, the arrows step a row). Below are the level table (rows survived
per track; it picks the track and shows or hides runners, baselines and the one-shot Jev included), the
scoreboard, and what in the set-up is ours rather than the fly's or TypeSafe's. The look is the user's
brand (`~/Documents/PROJECTS/BRAND/brand.css`). Several run directories are merged, since the fly and
the paid players usually run separately; one (player, seed) may appear only once. Viewing costs
nothing: it reads logs only. The viewer's JavaScript has its own tests, which `uv run pytest` runs
through `node --test` (skipped when node is not installed).

New here? Open `docs/EXPLAINER.html` in a browser: what this project is and how it works, from the idea down to
the code. See `docs/DECISIONS.md` for what has been decided and `docs/NEXT.md` for what comes next.
