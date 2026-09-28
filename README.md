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

Status: phases 1 to 5 of 6 built (phase 6 is the tournament and the write-up), and the ten updates that come
first (`docs/UPDATES.md`) are done bar one: game v2; the Jev family and its LLM twins with their paid runs (update
2a); the fly's richer-input probe, stopped there (update 2b); the benchmark (item 7); the GLM Flash twins, parked
after one track while the free tier throttles (item 10); and the page that runs the show (updates 3a and 3b).
Details in `docs/NEXT.md`. The untrained fly plays: on seeds 0–19 of game v1 it survives 127 rows on average
(random 35, always-jump 48, solver 300; `calibration/RESULTS.md`).

A second pure fly, `fly2`, adds a richer input of ours, a sideways channel (M3) (the wiring, the model and the neurons are
still the fly's; the mapping, the read-out and the rule are ours). It is built, calibrated and played (decisions
41–43, on `main` since PR #7): on v2 seeds 1000–1019 fly2 scores 78.20 rows on average against fly's
66.55, but `bakeoff bench` cannot yet tell them apart with confidence.

The game comes in versions (`bakeoff/game/rules.py`): `v1`, the 300-row game phases 1 to 5 were played on, and
`v2`, the default, 150 rows that reach full difficulty by row 100. `--game v1` plays the old one; `--lookahead` and
`--window` change how far players see and rename the game (`v2+look3`). Each run records its game, and `view`
refuses to mix two games. Jev and the LLM
(Claude Haiku 4.5) play behind a response cache; the LLM also behind a hard request cap, while Jev, whose requests
cost you nothing, plays without one (decision 50); first measured costs are in `docs/COSTS.md`.

    uv run pytest                                    # fast tests, ~20 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20 --seed-start 1000
    uv run python -m bakeoff report runs/<run_id>
    uv run python -m bakeoff view runs/<run_id> [runs/<other_run_id> ...]   # writes replay.html
    uv run python -m bakeoff bench runs/<run_id>[:player,...] [...]          # writes bench.html and bench.json

    uv run python -m bakeoff live --port 8765             # Brain Run: the browser picks the players and the track
    uv run python -m bakeoff live --start --seed 1001 --players fly,jev_step1,haiku_plain --max-requests 150
    uv run python -m bakeoff live --game v1 --seed 1001 --start   # free: replays that run's answers from the cache

`bench` scores recorded runs and spends nothing. It merges run directories like `view` (one game; each player and
seed from one directory; `DIR:player,player` takes only those players from a directory) and leaves out episodes a
stopped run cut off; it refuses runs of different track lengths. Per player: mean rows with a 95% t interval over
tracks, the median, the share finished, a survival curve, and seconds and USD per row from live decisions (a cache
hit records neither; the fly and the baselines are "free", Jev has no per-token price, "no price"). Per pair, on the
tracks both played: the mean difference, its paired t interval, wins, ties and losses, a verdict only when the
interval leaves out zero, and how many tracks would give an 80% chance of a verdict (an estimate). Below 5 tracks
there is no interval, no verdict and no estimate, and such a player is not ranked. With many pairs some verdicts
come by chance; the page counts the pairs and says so. The page is one offline file like the replay.

`live` plays one track in real time: every mind decides the same row before anyone moves on (a jumper skips
the next row; the slowest mind sets the pace, about a row a second with the fly), each decision goes into a
normal run directory and, through a server on `127.0.0.1` only, into the same page as it happens. The command
binds the port and sets the ceiling; the page does the rest, through Brain Run's screens (decisions 45 and 51, spec
`docs/superpowers/specs/2026-09-25-brain-battle-design.md`; it was called Brain Battle until decision 51): home,
"Choose your runners" (up to eight runners, each a character in one of its skins), the track select (the track, its
preview, and each runner's worst case, Jev's included; a run that can spend asks for a second press, `RUN` then
`CONFIRM` with "spend at most …", but a lineup whose only spending is Jev's is not asked), the run screen (with
Cancel), and the results (a card per runner; its requests read "N live" over "M cached" when some answers came
from the cache, so a runner that replayed a track shows 0 live and 0.00 USD), which open by themselves when the run ends and lead to another run without restarting
the command. Records holds the leaderboard of the practice tracks, head to head for two players, and the past runs
to watch again or see the results of. The page reads these through three routes that only read files and spend
nothing, behind the same token as the rest: `GET /results?run=`, `GET /records` and `GET /replay?run=`. `--seed`
and `--players` fill the character select and the track select; `--start` plays the command line's own run at
once instead, waiting for a browser first and serving until Ctrl-C (`--no-wait` does neither). The cap is the session's, per capped paid player (Claude Haiku, GLM
Flash), default 0, which makes a free live run of a track whose answers are already cached; Jev has no cap; a live paid run on a seed below 1000 is refused without `--tournament`. `live`
builds one fly brain; do not start a second fly process next to it. Afterwards `view` replays the directory.

Paid players (`jev_plain`, `jev_step1`, `haiku_plain` and the question-set players below) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
file at the repo root (template: `.env.example`). Claude Haiku and GLM Flash spend nothing unless told to; Jev asks whenever
its answer is not cached (decision 50):

    uv run python -m bakeoff run --players haiku_plain --seeds 1 --seed-start 1000 --max-requests 300 --game v1

`jev_step1` is the Jev of the demo: instead of one broad question it asks Jev four pointed yes/no
questions in one request ("would `left` land on a gap, that is, does `ahead[0].gaps_relative` contain
-1?") and code picks the action least likely to land on a gap, ties in the order stay, left, right,
jump. The wording and that rule are ours, not TypeSafe's, and it looks one step ahead only. The
one-shot `jev_plain` (the plain set) stays for comparison: on the dangerous states of practice track 1000 its single Choice
landed on a gap about as often as always staying (`docs/DECISIONS.md`, decisions 14 and 15).

Three more ways to ask Jev, and an LLM twin for each way (decisions 25 and 26): `jev_guided` asks one Choice whose
options name each move's landing tile, `jev_step2` asks eight yes/no questions (each move's landing, and whether it
leaves a way on), `jev_map` asks about every visible tile and code plans over its answers like the solver.
`haiku_step1`, `haiku_guided`, `haiku_step2` and `haiku_map` ask Claude Haiku exactly the same questions and use the
same rule, and `glm_step1`, `glm_guided`, `glm_step2` and `glm_map` ask GLM Flash (Zhipu's free tier,
`ZHIPU_API_KEY`) the same again. Three things still differ: the LLM is also given the briefing of the rules (for three of the four sets
Jev's yes/no questions carry only the question), Jev answers its questions in parallel while the LLM writes them in
one reply, and the LLM's probabilities are numbers it writes down. The questions and the rules are ours
(`bakeoff/players/question_sets.py`).

The five ways are named `plain`, `guided`, `step1`, `step2` and `map` (decision 44, for the character
select of Brain Run, then called Brain Battle). Before that they were the one-shot `jev`/`haiku`/`glm`, `choice`, `composed`, `two_step` and `reader`, and
Claude Haiku's players were `llm*` before decision 39. Old names still work wherever a player is named, and runs
recorded under them (with their cached answers) are read as the new ones.

`--max-requests` is a hard cap on live requests for **each** capped paid player in the run (Claude Haiku, GLM
Flash); the default 0 only replays `.cache/responses`. Jev (every `jev_*`) plays without a cap (decision 50): its
requests cost you nothing, and they are still cached, counted, priced and recorded (`"max": null` in `meta.json`).
Every answer is cached, so a repeated run of the same game and track
is free, and a run stopped by the cap (`status: budget_exhausted`) continues from the cache next time.
`uv run pytest -m live`
makes one real request per provider. A live paid run on seeds below 1000 is refused unless
`--tournament` is passed (tournament seeds stay untouched until phase 6). A run stopped by the cap
ends there, so later players in the list do not play: put free players first, or run paid players
alone.

`view` writes one self-contained HTML file (no server, no network, fonts embedded): the demo player. The
fly, `jev_step1` and `haiku_plain` run one tunnel together as pixel figures (fixed camera, everyone on the
same row at the same time), with a strip of panels underneath showing what each had in mind (the fly's
spikes and read-out signals, Jev's four answers, the LLM's answer). Any other players in the merged run
directories (the other question-set players, `jev_plain`) join the same tunnel with their own tags. Blue is
the cursor: it marks the mind in focus and the tiles that mind was shown, and with auto on it cuts to
whoever faces a gap (a click chooses by hand, or keys 1 to 9 pick the runner in that position; space
plays, the arrows step a row). The replay page has two tabs. **Run** holds the tunnel, the
mind panels (each with a running log, one line per row, that follows the row on screen), and **Who is in the
tunnel**, which shows and hides runners. **Analysis** holds the level table (rows survived per track; it picks the
track), the scoreboard, what in the set-up is ours rather than the fly's or TypeSafe's, and the benchmark, drawn
by the same code as `bench.html`. A live page has no tabs: its run screen is the Run tab, who runs next is picked
on the character select, and the numbers and "what is ours" are on the results and Records screens. The look is the user's
brand (`~/Documents/PROJECTS/BRAND/brand.css`). Several run directories are merged, since the fly and
the paid players usually run separately; one (player, seed) may appear only once. Viewing costs
nothing: it reads logs only. The viewer's JavaScript has its own tests, which `uv run pytest` runs
through `node --test` (skipped when node is not installed).

New here? Open `docs/EXPLAINER.html` in a browser: what this project is and how it works, from the idea down to
the code. To use it, `docs/WALKTHROUGH.md` walks through every command, every part of the page and what each costs. See `docs/DECISIONS.md` for what has been decided and `docs/NEXT.md` for what comes next.
