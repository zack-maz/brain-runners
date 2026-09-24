# Walkthrough: how to use every part of this tool

Written 2026-09-24, after the updates. What this project *is* lives in `docs/EXPLAINER.html`; this file is the
hands-on guide: every command, every flag that matters, every part of the page, and what each one costs.

Two rules to read first, because everything else assumes them:

- **Nothing spends money unless you pass `--max-requests`.** The default is 0, which replays answers already in
  the cache and stops a paid player at its first uncached question. Watching, scoring and replaying are always free.
- **Seeds below 1000 are tournament seeds.** Nothing is tuned on them and no paid player may play one until the
  tournament (`--tournament`). Seeds 1000 and up are practice.

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
| `TYPESAFE_API_KEY` | the Jev players (`jev`, `jev_composed`, `jev_choice`, `jev_two_step`, `jev_reader`) |
| `ANTHROPIC_API_KEY` | the Claude Haiku players (`llm`, `llm_composed`, `llm_choice`, `llm_two_step`, `llm_reader`) |
| `ZHIPU_API_KEY` | the GLM Flash players (`glm_composed`, `glm_choice`, `glm_two_step`, `glm_reader`) |
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
| `jev`, `llm` | the one-shot pair: one broad question, one move | paid |
| `jev_composed`, `llm_composed`, `glm_composed` | "would each move land on a gap?" (4 questions) | paid / free tier |
| `jev_choice`, `llm_choice`, `glm_choice` | one Choice over the four moves | paid / free tier |
| `jev_two_step`, `llm_two_step`, `glm_two_step` | landing *and* whether it leaves a way on (8 questions) | paid / free tier |
| `jev_reader`, `llm_reader`, `glm_reader` | every visible tile (42 questions), then plan | paid / free tier |

Worst-case price per request, as the page quotes it (measured in `docs/COSTS.md`, rounded up):
`llm_reader` 0.0065 USD · `llm_two_step` 0.0016 · `llm_composed` 0.0010 · `llm_choice` 0.0009 · `llm` 0.0006 ·
the Jev players 0.00003–0.00012 (estimates) · the GLM players 0 while the free tier lasts. One request per row, so
a 150-row track costs at worst 150 × that.

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
| `--max-requests N` | the hard cap, **per paid player**; 0 (default) replays the cache only |
| `--tournament` | allows paid play on seeds below 1000 — for phase 6 only |
| `--out DIR`, `--cache DIR` | where runs and cached answers go (`runs/`, `.cache/responses`) |

A run stopped by the cap ends there (`status: budget_exhausted`) and later players in the list never play — so put
free players first, or run paid players on their own.

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
uv run python -m bakeoff bench runs/<id> "runs/<other>:jev_composed,jev_two_step" --output bench.html
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

This opens the **lobby**: the command binds the port and sets the money ceiling, the browser does the rest. Open
the address it prints, pick the track, tick who plays, press Start. When the run ends the lobby comes back, so you
can play another track without restarting the command. Ctrl-C stops serving.

| Flag | What it does |
| --- | --- |
| `--port N` | serve on `127.0.0.1:N` only (default 8000) |
| `--start` | play the command line's own run at once, the old behaviour, instead of waiting in the lobby |
| `--seed N`, `--players a,b` | what the lobby offers first (and what `--start` plays) |
| `--max-requests N` | the ceiling for the **whole session**, per paid player — the page can never raise it |
| `--max-rows`, `--game`, `--lookahead`, `--window`, `--cache`, `--out`, `--tournament` | as in `run` |
| `--no-wait` | do not wait for a browser and do not keep serving afterwards (needs `--start`) |

Every player decides the same row before anyone moves on, so the slowest mind sets the pace (about a row a second
with the fly). It builds one fly brain: never start a second fly process beside it. The run is recorded as a normal
directory, so `view` replays it afterwards.

---

## 4. The page, part by part

The same page serves a saved replay and a live run; a replay simply has no lobby and no server.

### The Run tab

- **The tunnel.** Every runner is on the same row at the same time (a jump covers two rows, so it takes two
  ticks). **Blue is the cursor**: it marks the mind in focus and the tiles that mind was shown, nothing else.
- **The mind panels**, one per runner: what it was asked and what it answered on the row you are watching — the
  fly's eye rates and spikes, a Jev player's probabilities, a chat model's reply.
- **"Its log"** inside each panel: one line per row — the row number, the move, what it was asked, what it
  answered, how long it took (or `cached`), and any error in red. It follows the row on screen, so it never gives
  a replay's ending away; scrub back and the later lines come off. One log is open at a time, and it keeps your
  place while new rows arrive.
- **Players**, two labelled rows of one control:
  - *Who runs next* — the ticks that choose who plays the next run, with each player's price, what is left of the
    cap, and whether that track was played before (so some answers may be cached). Live only.
  - *Who is in the tunnel* — shows and hides runners in what is on screen. A player that never ran the track in
    view cannot be turned on, and says so.
- **The transport** at the bottom: play, step, speed, and `LIVE`/`AUTO`. Keys: space plays, ← → step a row,
  `a` toggles auto-focus, `1`–`9` put that runner's mind in focus. The transport and its keys are the Run tab's
  alone.

### The Analysis tab

- **Levels** — rows survived per track, one column per track. Click a track to watch it; that takes you back to
  the Run tab. (It no longer toggles players; the picker does that.)
- **Scoreboard**, with a warning when its rows do not all average the same tracks.
- **What is ours** — the notes saying which parts of the set-up are our mapping rather than the fly's biology or
  the model's own words. They are part of the honesty rule, not decoration.
- **Benchmark** — the same charts and tables as `bench.html`, drawn by the same code. After a live run it fills in
  by itself with the numbers for the run that just ended. A benchmark of one track says above its own table that
  it is what happened, not a result.

### Starting a run from the lobby

1. Type a track. A paid player on a seed below 1000 is greyed out, with the reason.
2. Tick who plays. The estimate line shows the **worst case**: rows × requests per row × price, capped by what is
   left of the session's budget. It assumes nothing is cached.
3. If any paid player is in the run, Start arms once — it becomes `Confirm: start and spend at most …`. Changing
   the track or the players disarms it.
4. While it runs, Cancel stops it between decisions: a decision already in flight is finished and recorded, and
   the run closes as a normal directory with status `interrupted`.

The page's requests carry a token minted at startup and embedded in the page, so no other page in your browser can
drive the run. It is not a defence against another program on this machine: whatever can fetch the page can read
the token.

---

## 5. Money, and the rules that hold it

Every paid request goes through three gates, in order:

1. **The disk cache** (`.cache/responses`). The key is a hash of provider, model, the senses and the full question
   set, so a changed prompt can never reuse an old answer. A track that was played before replays for free.
2. **The hard cap** (`--max-requests`, per paid player, default 0). SDK retries are off, so the cap is exact. In a
   live session the cap belongs to the session, not the run: each run records only what it spent, and nothing the
   page sends can raise the ceiling.
3. **The seed rule.** Paid players may not play seeds below 1000 without `--tournament`.

A provider failure is logged as an error and the game runs `stay` — never the solver's move, because being rescued
would hide exactly what we want to see.

To spend nothing while still watching a real run: leave `--max-requests` off and play a track that was played
before. To spend something deliberately, pass a cap that is the most you are willing to lose.

---

## 6. The fly, in practice

- `uv run python -m scripts.fetch_fly_data` once (~400 MB, pinned and checksummed).
- It needs about 1 GB and about a minute to build the brain, then about a second a row. **One fly process at a
  time** on an 8 GB machine — never a `run` and a `live` together.
- Its four numbers (the eye gain and falloff, the turn and jump thresholds) were frozen on practice seeds
  1000–1199 (`calibration/REPORT.md`) and must never be retuned.
- `uv run pytest -m slow` builds the real brain in the tests; the fast suite uses a stand-in.
- The calibration itself can be reproduced — `uv run python -m bakeoff.fly.calibrate calibration/response_surface.json /tmp/REPORT.md` —
  but its result is frozen: run it to check, not to change anything.

---

## 7. Recipes

**Watch what has already been played, free**
```bash
uv run python -m bakeoff view runs/20260921-165433 --output /tmp/replay.html   # every paid player, v2 track 1000
```

**See the whole update-2a scoreboard with intervals and pairs**
```bash
uv run python -m bakeoff bench runs/20260921-165433 \
  "runs/20260921-171044:jev_composed,jev_choice,jev_two_step,jev_reader" \
  runs/20260921-185546 runs/20260921-191326 runs/20260921-192037
```

**A live run that spends nothing**
```bash
uv run python -m bakeoff live --port 8765 --players solver,random,always_jump
```
Free players only, so any track works. With paid players, pick a track they have played before.

**Replay a paid run live, from the cache**
```bash
uv run python -m bakeoff live --game v1 --seed 1001 --start   # cap 0: the paid answers come from the cache
```

**Add free tracks to compare against**
```bash
uv run python -m bakeoff run --players solver,random,always_jump --seeds 20 --seed-start 1000
```

**Spend money on purpose, one track, one player**
```bash
uv run python -m bakeoff run --players jev_composed --seeds 1 --seed-start 1000 --max-requests 150
```

---

## 8. Tests

```bash
uv run pytest            # fast: Python + the viewer's JavaScript through node --test
uv run pytest -m slow    # builds the real fly brain (~1 GB, ~1 minute)
uv run pytest -m live    # one real request per provider — spends money, opt in only
```

No fast test touches the network. The viewer's pure modules (`log.js`, `tabs.js`, `picker.js`, `lobby.js`,
`timeline.js`, `tunnel.js`, `sprites.js`, `stage.js`, `minds.js`, `feed.js`, `bench.js`, `bench_view.js`) have
their own tests, skipped when node is not installed.

---

## 9. When something looks wrong

| What you see | What it means |
| --- | --- |
| A paid player stops after a few rows | the cap is 0 and the rest of the track is not cached — this is the safe default |
| `status: budget_exhausted` | the cap ran out; the answers so far are cached, so continuing later is cheaper |
| `status: interrupted` | Ctrl-C, Cancel, or a crash. A hard kill can leave `running` behind |
| `view` refuses two directories | they are different game versions, or the same (player, seed) appears twice |
| `bench` refuses | runs of different track lengths, or fewer than five tracks for an interval |
| "No completed run to score" on the Analysis tab | nothing in view has ended yet |
| A greyed-out player in the lobby | the reason is written next to it: a tournament seed, or no cap left |
| The fly is slow or the machine swaps | two fly processes are running; there must only ever be one |

---

## Where to go next

- `docs/EXPLAINER.html` — what the project is, from the idea down to the code.
- `docs/NEXT.md` — where things stand and what comes next. `docs/DECISIONS.md` — every decision, numbered.
- `docs/COSTS.md` — what every paid run actually cost and showed.
- `docs/STEP_RECORD.md` and `docs/REPLAY_DATA.md` — the record and replay formats.
