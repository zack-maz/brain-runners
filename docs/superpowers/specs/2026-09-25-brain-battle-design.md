# Brain Battle: the front of `bakeoff live`: design

Date: 2026-09-25 · Status: approved by the user in chat, with all seven calls below (decision 45) · Request, answers and mock-ups: `docs/FRONTEND.md` ·
Mock-up sources: `docs/mockups/brain-battle/` (the approved look) · Names: decision 44 · Builds on the page control
(`docs/superpowers/specs/2026-09-22-page-control-design.md`, binding) and the demo player
(`docs/superpowers/specs/2026-09-20-demo-player-design.md`, binding)

## Goal

`bakeoff live` opens on a game, not a control panel. Built in the style of Super Smash Bros, in the user's brand:
a home screen, a character select where the variants are skins, a track select, the race, then a results screen,
with Records for everything played before. What the lobby and the Analysis tab did is all still there, moved to
the screen where it is needed. The rules, the numbers and the money stay in Python. The page only draws what the
server gives it.

`bakeoff view` (a replay file opened from disk) keeps today's page: the Run and Analysis tabs, no front. It does
get two things from this work: the runners in their skin colours and the mind panels' new tags (section D).

## The flow

```
home ──Launch──▶ character select ──Ready──▶ track select ──RUN──▶ Run screen ──(run ends)──▶ results
 │                   ▲                           ▲                                             │
 └──Records──▶ records ◀─────────────────────────┼───────────── Records ◀──────────────────────┤
                  │  Watch · Results              └─ New track ◀─────────────────────────────────┤
                  └─▶ Run screen (replay) / results (past run)     Fighters ─▶ character select ◀─┤
                                                                    Run again ─▶ Run screen (same lineup, same track)
```

- The screens live in one page, with no routing and no build step, the same way the tabs do today.
  `viewer/screens.js` is a small pure state machine: it knows the screens, the moves between them, and Back and
  Escape on each. `app.js` shows one screen at a time. Nothing about a run is kept in the URL.
- Launching from the command line works as today:
  - `--seed` and `--players` without `--start` fill the character select with those fighters and the track
    select with that track.
  - `--start` opens straight on the Run screen with the command line's run.
  - Either way, a run's end leads to results.
- A run that ends goes to results by itself once the tunnel on screen has reached its last row. A viewer who is
  scrubbing back sees a "Results ▶" button instead and is not pulled away. A cancelled run goes to results too,
  marked "stopped: not a death" (the report's `incomplete`).

## A. The roster (`bakeoff/roster.py`, new)

One place says which characters exist, which skins each has, and what each skin is called and looks like. Today
this is spread across `REGISTRY`, `CONTESTANTS`, `Minds.TAGS` and the mock-ups.

| character | skins, in order (first = default) | sprite |
|---|---|---|
| Fly | Looming `fly`, Sideways `fly2` | the fly |
| Jev | Plain `jev_plain`, Guided `jev_guided`, Step 1 `jev_step1`, Step 2 `jev_step2`, Map `jev_map` | the visor |
| Haiku | Plain, Guided, Step 1, Step 2, Map (`haiku_<set>`) | the critter |
| GLM Flash | Plain, Guided, Step 1, Step 2, Map (`glm_<set>`) | the ox |
| Bot | Random `random`, Solver `solver`, Always jump `always_jump` | the boxy robot |

- Every skin carries: its player name, character and skin names, its colour and any extra inks, and its `about`
  line. The inks come from FRONTEND.md's colour table. The `about` lines are the mock-up's, each saying what is
  ours.
- A test keeps `roster.py` and `REGISTRY` equal. Every registered player is exactly one skin, and every skin is a
  registered player. A new player cannot be added without a place on the select screen.
- The roster is JSON. `bakeoff/view.py` embeds it in every page it renders (`<script id="roster-data">`), live or
  replay. That is how the tunnel and the mind strip colour a runner by its skin in both modes.
- `viewer/sprites.js` gains the ox and the robot grids, and an `inks` option that recolours a sprite's body and
  named cells for a skin. The existing grids and `pixels` stay as they are, so the demo's look is unchanged for
  anything the roster does not recolour. The home screen's brain logo is one more grid, used only there.

## B. What the server gives the page (`bakeoff/live_server.py`, `bakeoff/session.py`)

The token, the loopback-only rule, one run at a time and the session's ceiling all stay as update 3a built them.
The existing routes keep their meaning. New or extended:

| route | what it gives |
|---|---|
| `GET /state?seed=` | as today, plus: each player's `seeds_played` (the practice seeds 1000–1019 it has a recorded run of, from `played_before`), and, when a seed is given, `track` (that seed's real track, `generate_track(seed, rules).to_json()`, for the preview) |
| `GET /results?run=` | the results of one recorded run (section E), for Records' "Results" |
| `GET /records` | the leaderboard, the pairs and the past runs (section F) |
| `GET /replay?run=` | `build_replay` of one recorded run, for Records' "Watch" |
| `event: end` | as today, plus the run's `results`, computed the same way as `/results`. As with the benchmark, a failure there becomes a reason shown on the page and never costs the event itself |

- `run=` must be the name of a directory that is directly under the session's `out_root` and holds a `meta.json`.
  Any other value is a 404, so no path is ever built from what the page sends.
- `/records` and `/results` only read files and spend nothing.
- `/records` reads every run directory, which is not free. It is computed when asked for, never on a timer. The
  page asks when Records opens.

## C. The screens (`viewer/`)

Each screen follows its approved mock-up for layout, type, colour and motion. The build writes plain JavaScript,
and the `.dc.html` files are not viewer code. As everywhere on the page: blue is the cursor (the home brain is the
one exception, the user's call), deaths and errors are `--bad`, money is `--warn`, and every string that comes
from the server or a log goes through `Minds.esc`.

**Home.**
- The logo: "BRAIN BATTLE" centred over the pulsing pixel brain.
- The four characters bobbing.
- ▶ LAUNCH (Enter) and Records.
- The corner line: `127.0.0.1:<port> · ceiling <N> requests` from `/state`.
- The footer: the game version and its rows, from `/state`, never typed in.

**Character select** (`viewer/select.js`, pure: the slots and every rule below).
- Five portraits, eight slots P1–P8.
- A click on a portrait, or Space on the cursor's portrait, drops the next token there. The new slot gets that
  character's first skin not already in a slot.
- A slot's dots, or X and Y on the focused slot, cycle its skin, skipping skins already taken. The same skin twice
  can never be chosen.
- ← → move the cursor. Backspace or a slot's ✕ removes the slot.
- "READY TO FIGHT" appears from one fighter on, and Enter goes to the track select.
- A portrait whose skins are all taken, or any portrait once all eight slots are full, is dimmed and takes no
  token.
- The line under the portraits describes the focused slot:
  - its character and skin, its player name, its `about`;
  - its price, from `/state`: "paid · <price> USD / request", "free tier", "free · simulated" or "free";
  - a skin `why_not` refuses (no cap left, tournament seed) says why.

**Track select** (`viewer/trackpick.js`, pure: the seed rules and the list).
- The track number, with ‹ › and Random. Random picks a practice seed, 1000 and up.
- The preview draws the real track from `/state`'s `track`, row 0 to the game's last row.
- Practice tracks 1000–1019, each marked with how many of this lineup have played it before (`seeds_played`).
- Seeds below 1000 are locked unless the command was started with `--tournament`, and the screen says so.
- The lineup, one line per fighter:
  - sprite in its skin, "Character · Skin", player name;
  - "played before" or "new track";
  - its worst-case requests and cost.
- The total, then RUN (Enter). This is where the lobby's money confirmation now lives (section G).
- ‹ Fighters goes back with the lineup kept.

**Run screen.** Today's Run tab, minus the lobby:
- the tunnel, the mind strip with its logs, the transport;
- "Who is in the tunnel" (show and hide runners);
- Cancel the run, while one is going;
- ‹ Home, which asks first while a run is going: going home does not cancel the run.

**Results** (`viewer/results.js`, pure: the ranking and the text).
- "Run ended · N fighters", "Track <seed> · game <v> · <rows> rows".
- A card per fighter, ranked by rows survived: place, sprite in its skin, rows, how it died and on which row, time
  per row, requests, cost.
  - Ties share a place.
  - A stopped runner is ranked last and marked "stopped".
- A bar per fighter against the solver's line, which is the track's length: every v2 track can be finished.
- The warning that one track is not a result, pointing to Records.
- No winner banner.
- **More numbers** shrinks the cards and opens the table:
  - rows, death, share of jumps, **wrong moves** (section E);
  - asked live and from cache, as two rows;
  - time per row, tokens, cost.
- A failures line (fallbacks, invalid answers, errors) appears only when there were any.
- The note under the table says which numbers are left out and why (the mock-up's "Probability scores are left
  out…"). It is written from the lineup, not fixed text.
- Buttons:
  - ▶ Run again: same lineup, same track, straight to RUN's confirmation.
  - New track: to the track select.
  - Fighters: to the character select, with the lineup kept.
  - Watch the replay: the Run screen at row 0 of this run.
  - Records, and Home.
- A run of several tracks (a past `bakeoff run` directory opened from Records) shows the same cards with mean rows,
  the deaths counted by cause, and "over N tracks" in the header.

**Records** (`viewer/records.js`, pure; the benchmark drawing stays in `bench_view.js`).
- The leaderboard, the head to head, the past runs, and "What is ours". Section F says what they read.
- The leaderboard: mean rows and the 95% interval.
  - A player with under 3 tracks shows "not ranked", with its track count.
  - The yardsticks are greyed and never ranked.
  - The warning that overlapping intervals are no verdict.
- Head to head: pick two players.
  - Shown: their difference, its interval around 0, wins / ties / losses, the tracks needed, and the verdict.
  - These are `bench.pair_numbers`' own words and numbers.
- Past runs, newest first: when, tracks, players, status, then Watch and Results.
  - Only the run this session is playing now pulses and offers Watch live.
  - A `meta.json` that says `running` for any other run shows "running elsewhere, or stopped without closing".
    It is not offered as live, since this page cannot stream another process's run.
  - The ten newest show at first, and "Show all" lists the rest.
- **What is ours** opens as a panel:
  - the mock-up's three paragraphs first;
  - then the current "What is the fly's and what is ours" section, moved here unchanged, with its frozen numbers
    and known weaknesses.
  - The honesty rule does not allow shortening it.

## D. The Run screen, in the fighters' colours (both modes)

- Runners in the tunnel are drawn in their skin's colours, from the embedded roster.
- Mind panels are tagged as on the character select, "Jev · Step 1", in the skin's colour (settled 2026-09-25).
  This replaces `Minds.TAGS` ("JEV STEP 1").
- A player missing from the roster keeps its upper-case name and the grey block, so an old run still opens.
- The blue cursor stays what it is: the mind in focus and the tiles it was shown.
- Where a skin's own colour is blue (Solver, the Map skins' eyes), the focus is marked by the panel's frame and
  the tiles, never by recolouring the runner.

## E. Results' numbers (`bakeoff/results.py`, new; `bakeoff/report.py`)

`results_of(run_dir)` returns one entry per player of the run, all from its step logs and `meta.json`:
- the report's row for that player (`summarize`);
- the benchmark's time per row (`player_numbers`' `s_per_row`, live decisions only);
- `cost_estimate_usd`: live requests × `session.PRICE_USD`, labelled an estimate on the page, as the mock-up says.
  The report's per-token `cost_usd` stays in More numbers' notes where it exists; Jev has none.

Two new report columns, added to `COLUMNS` so `bakeoff report` prints them too:

- **`wrong_moves`**: the rows where the move made (`executed_action`, the fallback included) reaches less far than
  the best move (`solver_depths[executed] < max(solver_depths)`). This replaces "agreed with the solver", which is
  97–100% for every recorded player and so says nothing. `solver_agreement` stays in the report. The page just no
  longer shows it.
- **`fatal_wrong_move`**: the episode ended on a wrong move, that is, it died on a row where some other move
  survived. A death on a row where every move falls (depths all 0) is "trapped": the wrong move came earlier, and
  the page says so.

Failures are not rows of the table. `fallback_rate`, `invalid_rate` and `error_rate` feed the failures line, shown
only when one of them is above 0.

## F. Records' numbers (`bakeoff/records.py`, new)

- **Which runs.** Every run directory under `out_root` that recorded the session's game version and length, and
  only its practice seeds (1000 and up). Tournament seeds stay out of Records until phase 6 decides how the
  tournament is shown.
- **Which episode per player and track.** A live session replays tracks, so one (player, seed) can sit in several
  run directories. `bench.load` rightly refuses that. Records keeps the newest complete episode of each (player,
  seed) and leaves the older ones out. The leaderboard's note says how many were left out. `bench.Source` gains a
  seed filter so the benchmark is still computed by `bench.benchmark`, not re-derived.
- **Past runs.** Each directory's `meta.json`: run id, when, seeds, players (through `canonical`), status. Also
  whether it is this session's current run.
- The numbers are `bakeoff bench`'s. The page adds no statistics.

## G. Money

Nothing here can raise the ceiling. The command sets it, the session holds it, and the server refuses whatever
exceeds it, as today.

- The worst case moves from the lobby to the track select. It is computed as now (`Lobby.estimate`: rows ×
  requests per row, capped by what each paid player has left, × its price). It shows per fighter and in total.
- A lineup that can spend turns RUN into "Confirm: run and spend at most <total>". A second press, or Enter,
  starts the run. A lineup that spends nothing starts at once.
- With the default cap of 0, the track select says the paid fighters replay the cache and stop at their first
  uncached question, as the lobby does today.
- ▶ Run again goes through the same confirmation. It never skips it.
- `lobby.js` keeps `usd`, `estimate`, `estimateText`, `whyNot`, `spends` and `ceilingText`. Its player list and the
  "Who runs next" row go, since the character select replaces them. This amends decision 38 for the live page (see
  Review).

## Testing

- **Python:**
  - the roster equals the registry;
  - `/state`'s `seeds_played` and `track`;
  - `/results`, `/records` and `/replay`, including a `run=` that is not a run directory (404);
  - the `end` event's results, and that a failure in them keeps the event;
  - `wrong_moves` and `fatal_wrong_move` on hand-made step records: a wrong non-fatal move, a fatal one, a trapped
    death, a fallback;
  - Records' newest-episode rule, and that a tournament seed is left out.
- **JavaScript** (`node --test`):
  - the screen machine and its keys;
  - the select rules: next free skin, cycling past taken skins, the eight-slot limit, removal, ready;
  - the track select's seed rules and lineup lines;
  - the results ranking, ties and stopped runners;
  - the records text;
  - the skin inks;
  - that every server string is escaped.
- No test touches the network or a provider. The live tests use free players.
- **By hand, before the design review:**
  - open the built page in a browser and look at every screen and at the tunnel in skin colours (nothing in the
    suite sees colour);
  - run a live smoke with a fly, since the run path changes (`end` carries results). The smoke waits until no
    other session is running a fly.

## Build order

Two plans, each prototyped first as the project does:

1. **Brain Battle a, the server and the numbers.** `roster.py`, `results.py`, `records.py`, the report's two
   columns, the routes and the `end` event. The page is unchanged apart from the tags and the colours (section D).
2. **Brain Battle b, the screens.** Home, the character select, the track select, the Run screen's changes,
   results, records. The lobby's list goes.

## Not in scope

- The Writeup page. It is the last step, with its own brainstorm (FRONTEND.md).
- A stage select, since Run is the only game.
- A gamepad.
- A front for `bakeoff view`.
- Sound.
- Anything that changes how a run is played or recorded.
- New statistics beyond the two wrong-move columns.
- Remote access.

## Settled at review (decision 45)

Calls this spec made that the mock-ups and answers had not settled; the user approved all seven:

1. **Wrong moves count what was done**: the executed move, a fallback `stay` included, not only the model's
   choice. A death with no surviving move is "trapped", not a fatal wrong move.
2. **Records dedupe**: the newest complete episode of each (player, track) counts, older copies are left out (and
   counted in a note), and tournament seeds stay out until phase 6.
3. **Results come by themselves** when the tunnel reaches the last row. A viewer who has scrubbed back gets a
   button instead.
4. **"What is ours" keeps the whole current section** under the mock-up's three paragraphs, rather than shrinking
   to them.
5. **The live page loses the lobby's grid and "Who runs next"**, which amends decision 38. This spec, once
   approved, becomes decision 45.
6. **Skin colours and tags reach `bakeoff view` too**, because the roster is embedded in every page. The replay
   page's layout is otherwise unchanged.
7. **Cost on a results card is live requests × the page's price per request** (the mock-up's own note). It is
   an estimate, not the per-token bill.
