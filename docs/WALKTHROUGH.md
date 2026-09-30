# Walkthrough: how to use every part of this tool

Written 2026-09-24, after the updates; brought up to date 2026-09-28 and 2026-09-30 (Brain Runners, decisions 51
and 57; Jev capped like every paid player, decision 58). What this project *is* lives in `docs/EXPLAINER.html`; this file is the
hands-on guide: every command, every flag that matters, every part of the page, and what each one costs.

Two rules to read first, because everything else assumes them:

- **Jev, Claude Haiku and GLM Flash spend nothing unless you pass `--max-requests`.** The default is 0, which
  replays answers already in the cache and stops a paid player at its first uncached question. Every request is
  cached, counted and priced (decision 58; until then Jev played without a cap, decision 50). Watching, scoring and
  replaying are always free.
- **Seeds below 1000 are held out.** Nothing is tuned on them, and no paid player may spend on one without
  `--held-out` (the study used 100–199). Seeds 1000 and up are practice.

---

## 1. Setup, once

```bash
uv sync                                    # the Python environment (Python 3.13)
uv run pytest                              # the fast tests, about 20 s: proves the install
uv run python -m scripts.fetch_fly_data    # only if you want the fly: ~400 MB into data/
```

For the paid players, put keys in a git-ignored `.env` at the repo root (template: `.env.example`):

| Key | For |
| --- | --- |
| `TYPESAFE_API_KEY` | the Jev players (`jev_plain`, `jev_step1`, `jev_guided`, `jev_step2`, `jev_map`) |
| `ANTHROPIC_API_KEY` | the Claude Haiku players (`haiku_plain`, `haiku_step1`, `haiku_guided`, `haiku_step2`, `haiku_map`) |
| `ZHIPU_API_KEY` | the GLM Flash players (`glm_step1`, `glm_guided`, `glm_step2`, `glm_map`) |
| `GLM_BASE_URL` | only for a mainland Zhipu account |

Programs read `.env` themselves. Never type `.env` into a shell command here: a guard blocks any command
containing that text, so the keys cannot be echoed by accident.

---

## 2. The pieces, in one page

**Players** (`--players a,b,c`). Free ones cost nothing and need no key:

| Player | What it is | Costs |
| --- | --- | --- |
| `solver` | perfect search with the same 6-row view — the ceiling | free |
| `random`, `always_jump` | the floors | free |
| `fly` | the fruit fly connectome, untrained | free, ~0.7 s a row, ~1 GB of RAM |
| `fly2` | a second pure fly, same connectome, a richer input of ours, a sideways channel (M3) (decision 43) | free, ~0.5 s a row, shares `fly`'s brain when run together |
| `jev_plain`, `haiku_plain`, `glm_plain` | the plain set: one broad question, one move | paid / free tier |
| `jev_step1`, `haiku_step1`, `glm_step1` | "would each move land on a gap?" (4 questions) | paid / free tier |
| `jev_guided`, `haiku_guided`, `glm_guided` | one Choice over the four moves | paid / free tier |
| `jev_step2`, `haiku_step2`, `glm_step2` | landing *and* whether it leaves a way on (8 questions) | paid / free tier |
| `jev_map`, `haiku_map`, `glm_map` | every visible tile (42 questions), then plan | paid / free tier |

Worst-case price per request, as the page quotes it (measured in `docs/COSTS.md`, rounded up):
`haiku_map` 0.0065 USD · `haiku_step2` 0.0016 · `haiku_step1` 0.0010 · `haiku_guided` 0.0009 · `haiku_plain` 0.0006 ·
the Jev players 0.00003–0.00012 (estimates) · the GLM players 0 while the free tier lasts. One request per row, so
a 150-row track costs at worst 150 × that.

**A note on names.** Claude Haiku's players were called `llm*` until 2026-09-24 (decision 39); they are `haiku*`
now, so that `haiku_step1` and `glm_step1` read as the pair they are. The old names still work everywhere a
name is typed, and runs recorded under them are read back under the new ones, so old and new runs merge as one
player. Nothing on disk was rewritten and no cached answer was lost.

**Tracks.** A seed is a track. `--game v2` (the default) is 150 rows and reaches full difficulty by row 100;
`--game v1` is the old 300-row game. The same seed is a *different* track in each version, so the two never share
a scoreboard and `view` refuses to mix them.

**Run directories.** Everything that plays writes `runs/<timestamp>/`: a `meta.json` (status, git commit,
arguments, model ids, what was spent) and one `<player>.jsonl` with one line per move. Everything that reads —
`report`, `view`, `bench` — only reads those, which is why it is free.

---

## 3. The five commands

### `run` — play tracks and record them

```bash
uv run python -m bakeoff run --players fly,random,solver --seeds 20 --seed-start 1000
```

| Flag | What it does |
| --- | --- |
| `--players a,b,c` | who plays (default `random,solver`) |
| `--seeds N --seed-start S` | N tracks starting at seed S (default 20 from 0 — pass `--seed-start 1000` for practice) |
| `--game v1\|v2` | the game version (default `v2`) |
| `--lookahead N`, `--window N` | change how far players see; this renames the game (`v2+look3`) so results never mix |
| `--max-rows N` | play only the first N rows of each track |
| `--max-requests N` | the hard cap, **per paid player** (Jev, Claude Haiku, GLM Flash; decision 58); 0 (default) replays the cache only |
| `--held-out` | allows paid play on seeds below 1000, the held-out seeds — for the study's runs |
| `--out DIR`, `--cache DIR` | where runs and cached answers go (`runs/`, `.cache/responses`) |

A capped player whose cap runs out, or whose provider fails six times in a row, drops out; the others still play
every track (decision 52). The command names who stopped and why and exits 1, and `meta.json` records it under
`stopped`. Only when every player has stopped does the run end as `budget_exhausted` or `aborted`.

### `report` — the scoreboard of one run directory, as text

```bash
uv run python -m bakeoff report runs/20260921-155758
```

One row per player: mean and median rows, how many finished, how it died (ran into / jumped into / dodged into a
gap), agreement with the solver, invalid and error rates, requests, cache hits, latency, tokens, cost, and Brier
scores for the players that answer with probabilities.

### `view` — turn runs into one offline page

```bash
uv run python -m bakeoff view runs/<id> [runs/<other> ...] --output replay.html
```

Merges several run directories into one replay (the fly and the paid players usually run separately). One
(player, seed) may appear only once, and every directory must be the same game version. The result is a single
HTML file with the data, the JavaScript, the fonts and the benchmark inside it — no server, nothing fetched. Mail
it to someone and it works.

### `bench` — how sure are we?

```bash
uv run python -m bakeoff bench runs/<id> "runs/<other>:jev_step1,jev_step2" --output bench.html
```

Scores runs that already exist, so it spends nothing. `DIR:player,player` takes only those players from a
directory. It prints its tables, writes `bench.html` (standalone) and `bench.json` next to it, and gives you:

- per player: mean rows with a **95% t interval over tracks**, median, share finished, a survival curve, and
  seconds and USD per row from live decisions only (a cache hit records neither);
- per pair, on the tracks both played: the mean difference, its paired interval, wins/ties/losses, a **verdict only
  when the interval excludes zero**, and how many tracks would give an 80% chance of a verdict;
- `--pair A,B` (repeatable) to print only the pairs you care about; the page always shows them all.

Below five tracks there is no interval, no verdict and no rank — it says so rather than guessing. With many pairs
some verdicts arrive by chance, and the notes count how many.

### `live` — play a track in real time, driven from the browser

```bash
uv run python -m bakeoff live --port 8765
```

This opens **Brain Runners** (called Brain Battle until decision 51, Brain Run until decision 57), the front of the live page: the command binds the port and sets the money ceiling, the
browser does the rest. Open the address it prints: the home screen leads to the character select (who plays), the
track select (which track, and what it can cost at worst), the run, and the results, which open by themselves when
the run ends. From the results you can run again, pick a new track or other runners, so you can play another track
without restarting the command. Records holds everything played before. Ctrl-C stops serving.

| Flag | What it does |
| --- | --- |
| `--port N` | serve on `127.0.0.1:N` only (default 8000) |
| `--start` | play the command line's own run at once: the page opens on the run screen, and the first decision waits for a browser |
| `--seed N`, `--players a,b` | the runners the character select opens with and the track the track select opens on (and what `--start` plays); without them, the demo's three (`fly,jev_step1,haiku_plain`) on track 1001 |
| `--max-requests N` | the ceiling for the **whole session**, per capped paid player (Claude Haiku, GLM Flash) — the page can never raise it; Jev has none |
| `--max-rows`, `--game`, `--lookahead`, `--window`, `--cache`, `--out`, `--held-out` | as in `run` |
| `--no-wait` | do not wait for a browser and do not keep serving afterwards (needs `--start`) |

Every player decides the same row before anyone moves on, so the slowest mind sets the pace (about a row a second
with the fly). It builds one fly brain: never start a second fly process beside it. The run is recorded as a normal
directory, so `view` replays it afterwards.

---

## 4. The page, part by part

The same page serves a saved replay and a live run. A replay file has no server and no front: it opens on the two
tabs below. A live run opens on Brain Runners' screens instead (see "Starting a run" below); its run screen is the
Run tab without the tabs, and what the Analysis tab shows moves to the results and Records screens.

### The Run tab

- **The tunnel.** Every runner is on the same row at the same time (a jump covers two rows, so it takes two
  ticks). **Blue is the cursor**: it marks the mind in focus and the tiles that mind was shown, nothing else.
- **The mind panels**, one per runner: what it was asked and what it answered on the row you are watching — the
  fly's eye rates and spikes, a Jev player's probabilities, a chat model's reply.
- **"Its log"** inside each panel: one line per row — the row number, the move, what it was asked, what it
  answered, how long it took (or `cached`), and any error in red. It follows the row on screen, so it never gives
  a replay's ending away; scrub back and the later lines come off. One log is open at a time, and it keeps your
  place while new rows arrive.
- **Who is in the tunnel** — shows and hides runners in what is on screen. A player that never ran the track in
  view cannot be turned on, and says so. (Who runs next is picked on the character select, live only.)
- **The transport** at the bottom: play, step, speed, and `LIVE`/`AUTO`. Keys: space plays, ← → step a row,
  `a` toggles auto-focus, `1`–`9` put that runner's mind in focus. The transport and its keys are the Run tab's
  alone.

### The Analysis tab

- **Levels** — rows survived per track, one column per track. Click a track to watch it; that takes you back to
  the Run tab. (It no longer toggles players; the picker does that.)
- **Scoreboard**, with a warning when its rows do not all average the same tracks.
- **What is ours** — the notes saying which parts of the set-up are our mapping rather than the fly's biology or
  the model's own words. They are part of the honesty rule, not decoration.
- **Benchmark** — the same charts and tables as `bench.html`, drawn by the same code. A benchmark of one track says
  above its own table that it is what happened, not a result.

### Starting a run: select, track, RUN/CONFIRM

1. **Home.** LAUNCH (or Enter) opens the character select; Records opens the records. The corner line shows the
   address and the session's ceiling, the footer the game version and its rows.
2. **Character select** ("Choose your runners"). Five characters (Fly, Jev, Haiku, GLM Flash, Bot), up to eight slots. A click on a
   portrait, or Space on the one under the cursor (← →), drops the next runner in that character's first skin not
   already taken; a slot's dots, or X and Y, change its skin, and the same skin can never be chosen twice.
   Backspace or a slot's ✕ removes it. The line under the portraits describes the focused slot: who it is, what it
   does, its price, and why it may not play if it may not (a held-out seed, no cap left). With one runner or
   more, READY TO RUN (or Enter) goes on; the count in the corner reads "N / 8 runners".
3. **Track select.** ‹ › or ← → step the track, Random (or R) picks a practice track, and the tiles offer the
   practice tracks 1000–1019, each marked with how many of this lineup played it before. Seeds below 1000 are
   locked unless the command was started with `--held-out`. The preview draws the real track. Each runner's
   line says whether it played this track before and its **worst case**: rows × requests per row × price, capped
   by what is left of the session's budget, assuming nothing is cached; the total is under it. ‹ Runners goes back with the lineup kept.
4. **RUN.** A lineup that spends nothing starts at once. If the run can spend, the first press of RUN (or Enter)
   turns it into `CONFIRM` with `spend at most …` underneath, and a second, separate press starts the run; a press
   within half a second of the first, or a held Enter, does not count. Changing the track or the lineup disarms
   it. If the run is refused, the reason shows above the button.
5. **The run screen.** While it runs, Cancel stops it between decisions: a decision already in flight is finished
   and recorded, and the run closes as a normal directory with status `interrupted`. ‹ Home (or Escape) asks
   first while a run is going, because going home does not cancel it.
6. **Results** open by themselves once the tunnel on screen reaches the last row; if you scrubbed back, a Results
   button waits instead. One card per runner, ranked by rows survived, with a bar against the track's length and
   the warning that one track is not a result. A paid runner's Requests read "N live" over "M cached" when some
   answers came from the cache, so a runner that replayed a whole track shows "0 live / 146 cached" and 0.00 USD. More numbers opens the table (wrong moves, asked live and from
   cache, time per row, tokens, cost). Run again goes through the same confirmation; New track, Runners, Watch
   the replay, Records and Home do what they say.
7. **Records** — the leaderboard of the practice tracks with 95% intervals, head to head for any two players, the
   past runs, newest first (Watch and Results; this session's run, while it plays, offers Watch live only), and
   "What is ours".

Besides `/state`, `/run`, `/cancel` and `/events`, the page reads three routes that only read files and spend
nothing: `GET /results?run=` (one recorded run's results), `GET /records` (the leaderboard, the pairs and the past
runs) and `GET /replay?run=` (a recorded run to watch). `run=` must name a run directory under `--out`.

The page's requests carry a token minted at startup and embedded in the page, so no other page in your browser can
drive the run. It is not a defence against another program on this machine: whatever can fetch the page can read
the token.

---

## 5. Money, and the rules that hold it

Every paid request goes through three gates, in order:

1. **The disk cache** (`.cache/responses`). The key is a hash of provider, model, the senses and the full question
   set, so a changed prompt can never reuse an old answer. A track that was played before replays for free.
2. **The hard cap** (`--max-requests`, per capped paid player, default 0). SDK retries are off, so the cap is exact.
   Jev included (decision 58). Every request is counted and priced on the track select, the results and in
   `meta.json`. In a
   live session the cap belongs to the session, not the run: each run records only what it spent, and nothing the
   page sends can raise the ceiling.
3. **The seed rule.** Paid players may not play seeds below 1000 without `--held-out`.

A provider failure is logged as an error and the game runs `stay` — never the solver's move, because being rescued
would hide exactly what we want to see.

To spend nothing while still watching a real run: leave `--max-requests` off and play a track that was played
before (a Jev player asks only for what is not cached). To spend something deliberately, pass a cap that is the most you are willing to lose.

---

## 6. The fly, in practice

- `uv run python -m scripts.fetch_fly_data` once (~400 MB, pinned and checksummed).
- It needs about 1 GB and about a minute to build the brain, then about a second a row. **One fly process at a
  time** on an 8 GB machine — never a `run` and a `live` together.
- Its four numbers (the eye gain and falloff, the turn and jump thresholds) were frozen on practice seeds
  1000–1199 (`docs/calibration/REPORT.md`) and must never be retuned.
- `uv run pytest -m slow` builds the real brain in the tests; the fast suite uses a stand-in.
- The calibration itself can be reproduced — `uv run python -m bakeoff.fly.calibrate docs/calibration/response_surface.json /tmp/REPORT.md` —
  but its result is frozen: run it to check, not to change anything.
- `fly2` adds a richer input of ours, a sideways channel (M3) (the mapping, the read-out and the rule are ours; the wiring,
  the model and the neurons are still the fly's). Its numbers (gain 250 Hz, falloff 2, turn threshold 40 Hz, jump
  threshold 175 Hz) were frozen the same way, on the same practice seeds (`docs/calibration/FLY2_REPORT.md`, decision
  43), and must never be retuned either. Its own two commands, also reproducible but frozen: `uv run python -m
  bakeoff.fly.surface --mapping M3 docs/calibration/fly2_surface_M3.json` measures a candidate mapping's response
  surface (~25 minutes; `--shuffle-seed 1` measures the shuffled-wiring control instead), and `uv run python -m
  bakeoff.fly.calibrate2 --surface M1=... --surface M2=... --surface M3=... docs/calibration/FLY2_REPORT.md` turns
  measured surfaces into the calibration and its controls (~3 minutes, no brain built).

---

## 7. Recipes

**Watch what has already been played, free**
```bash
uv run python -m bakeoff view runs/20260921-165433 --output /tmp/replay.html   # every paid player, v2 track 1000
```

**See the whole update-2a scoreboard with intervals and pairs**
```bash
uv run python -m bakeoff bench runs/20260921-165433 \
  "runs/20260921-171044:jev_step1,jev_guided,jev_step2,jev_map" \
  runs/20260921-185546 runs/20260921-191326 runs/20260921-192037
```
These runs were recorded under the players' old names (`jev_composed.jsonl`, `llm_reader.jsonl` and the like, before
decisions 39 and 44); they keep those files, and `view`, `bench` and `report` read them as the names above. An old
name still works wherever a player is named, so a saved command keeps working.

**A live run that spends nothing**
```bash
uv run python -m bakeoff live --port 8765 --players solver,random,always_jump
```
Free players only, so any track works. With paid players, pick a track they have played before.

**Replay a paid run live, from the cache**
```bash
uv run python -m bakeoff live --game v1 --seed 1001 --start   # cap 0: the paid answers come from the cache (Jev's were cached too)
```

**Add free tracks to compare against**
```bash
uv run python -m bakeoff run --players solver,random,always_jump --seeds 20 --seed-start 1000
```

**Spend money on purpose, one track, one player**
```bash
uv run python -m bakeoff run --players haiku_step1 --seeds 1 --seed-start 1000 --max-requests 150
```

---

## 8. Tests

```bash
uv run pytest            # fast: Python + the viewer's JavaScript through node --test
uv run pytest -m slow    # builds the real fly brain (~1 GB, ~1 minute)
uv run pytest -m live    # one real request per provider — spends money, opt in only
```

No fast test touches the network. The viewer's pure modules (`log.js`, `tabs.js`, `picker.js`, `lobby.js`,
`timeline.js`, `tunnel.js`, `sprites.js`, `roster.js`, `stage.js`, `minds.js`, `feed.js`, `bench.js`, `bench_view.js`,
and Brain Runners' `screens.js`, `select.js`, `trackpick.js`, `results.js`, `records.js`) have
their own tests, skipped when node is not installed.

---

## 9. When something looks wrong

| What you see | What it means |
| --- | --- |
| A Claude Haiku or GLM Flash player stops after a few rows | the cap is 0 and the rest of the track is not cached — this is the safe default |
| `status: budget_exhausted` | the cap ran out; the answers so far are cached, so continuing later is cheaper |
| `status: interrupted` | Ctrl-C or Cancel. A hard kill can leave `running` behind |
| `status: crashed` | a bug in this tool: `meta.json` carries the error and the page says it |
| `view` refuses two directories | they are different game versions, or the same (player, seed) appears twice |
| `bench` refuses | runs of different track lengths, or fewer than five tracks for an interval |
| "No completed run to score" on the Analysis tab | nothing in view has ended yet |
| A runner that may not play | the reason is on the character select's line for that slot and on its track select line, and RUN stays off: a held-out seed, or no cap left |
| The fly is slow or the machine swaps | two fly processes are running; there must only ever be one |

---

## Where to go next

- `docs/EXPLAINER.html` — what the project is, from the idea down to the code.
- `docs/NEXT.md` — where things stand and what comes next. `docs/DECISIONS.md` — every decision, numbered.
- `docs/COSTS.md` — what every paid run actually cost and showed.
- `docs/STEP_RECORD.md` and `docs/REPLAY_DATA.md` — the record and replay formats.
