# Tunnel Run demo player: design

Date: 2026-09-20 · Status: design approved in chat by the user (sections 1 to 4, with the amendment
"all players start in the same spot, overlapping sprites get transparency"); implementation not started ·
Extends `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (still binding where this document is
silent) · Background: `docs/DECISIONS.md` decisions 14 to 19, `spikes/02-jev-questions/REPORT.md` on branch
`spike/jev-questions`

## Goal

The main tool of the project: **a demo player in which the three competitors play one Run level together**,
the fruit fly, Jev and the LLM in a single concrete tunnel with their minds underneath, in the visual
language of the user's brand (`~/Documents/PROJECTS/BRAND/brand.css`; seasoning: BLAME!, Zima Blue).
Everything built so far (level table, scoreboard, the "what is ours" section) is restyled the same way and
arranged around the player. It plays recorded runs for free, and it can **go live**: a local server runs
the three minds in real time, streams them into the same page and records the run as it goes.

## Non-goals

- No pacing of replays by each mind's real latency (the latency is shown per decision; going live is where
  it is felt). No sound. No Next.js/React version: the output stays one self-contained HTML file that can be
  embedded in the portfolio later.
- No change to the fly, its constants, the senses, the game, the step record (`schema_version` stays 1) or the
  one-shot `jev` and `llm` players.
- No tournament in these phases. The tournament and write-up become phase 6.

## The three competitors in the demo

| tag | player | figure |
| --- | --- | --- |
| FLY | `fly` | a pixel fruit fly seen from behind: pale folded wings, dark body, red eyes; wings open during a jump |
| JEV | `jev_composed` (new, phase 5a) | "the visor": a pale pixel monolith with one horizontal slit; the slit's lit cells show how sure Jev is that the move it made is safe |
| LLM | `llm` (Claude Haiku 4.5) | an orange pixel critter, our own rendition in the spirit of the Claude Code mascot (never the official artwork); the panel names the model |

Baselines (`random`, `always_jump`, `solver`) and the one-shot `jev` stay selectable from the level table
and are drawn as plain grey pixel blocks with their tag; the default view is the three above.

Sprites are grids of characters (one character = one pixel; `.` is empty). These are the approved ones
(mockup: `docs/superpowers/specs/mockups/2026-09-20-demo-player-figures.html`):

```
fly     ..ee.ee..  ...bbb...  .w.bbb.w.  ww.bbb.ww  wwwbbbwww  ww.bbb.ww  .w.bbb.w.  ...b.b...  ..b...b..
llm     .ooooooo.  .ooooooo.  .okoookoo  ooooooooo  .ooooooo.  .ooooooo.  .o.o.o.o.  .o.o.o.o.
visor   .jjjjj.  jjjjjjj  jVVVvvj  jjjjjjj  .jjjjj.  ..jjj..  .jjjjj.  .jjjjj.  .j...j.  .j...j.
ink     w #AEB4BA  b #3A4046  e #F7768E  o #D97757  k #1A0E0A  j #B9BEC4  V #FFFFFF (lit)  v #15181C (unlit)
```

The visor's slit has five cells; `round(5 * p)` of them are lit, left to right, where `p` is the
probability Jev gave that its chosen action does **not** land on a gap (one minus that action's Noul).

## What you see

1. **The tunnel** (top of the page, as large as the window allows, square). One tube of poured concrete,
   **fixed camera**: lane 6 is at the bottom, the tube never turns. Tiles are filled in slightly uneven
   dark greys with hairline edges and fade into the void with distance; a gap is a missing tile; rows at or
   past the finish line are a lighter band. Two mono labels in the corners: `ROW 0137 / 0300` and
   `TRACK 1000`.
2. **The runners** stand on the tube wall at their lane, heads toward the axis, so a runner on lane 0 runs on
   the ceiling, as in Run. Everyone starts on the same tile (row 0, lane 6). **Overlap:** when two or more
   runners are within half a lane of each other on the same row they are drawn at 55% opacity and fanned
   out sideways by a few pixels, so every one stays readable; their tags stack instead of overprinting.
   A jump lifts the figure toward the axis (and opens the fly's wings). A runner that lands on a gap drops
   through and fades out over one row of time.
3. **The clock is the track** (unchanged from phase 4): time is measured in rows, everyone still alive is on
   the same row, a jump takes two ticks and keeps its frame.
4. **The mind strip**: three panels under the tunnel, in the order FLY, JEV, LLM. Every panel has the 7 by 6
   grid of what that mind was shown, the move (and what the game ran when that differs, and why), and the
   solver's verdict. Then its own part: the fly's eye inputs, spike raster, turn and jump signals against our
   thresholds; composed Jev's four bars "lands on a gap" with the chosen action marked; the LLM's raw
   answer, latency and tokens. A fallen runner's panel dims and says how it ended ("Fell after 23 rows:
   stepped sideways into a gap"; a run that was cut off says so and is not a death).
5. **The blue cursor.** Blue marks the mind in focus and nothing else: its tag in the tunnel (`[ JEV ]`),
   the top edge of its panel, and the outline of the tiles it was shown. Focus changes by clicking a runner
   or a panel, or with the keys 1, 2, 3. With **auto** on (the default) focus cuts to a runner whose
   current decision has at least one action that lands on a gap; among several, the one with the fewest
   safe actions, ties to the current focus, and it holds for at least 3 rows so it does not flicker. Any
   manual choice turns auto off until it is switched back on.
6. **Transport**, docked at the bottom of the window: play/pause, step back and forward one row, speed
   (1, 3, 8, 20 rows a second), scrubber, row readout, the auto-focus switch, and in live mode a `LIVE`
   label instead of the scrubber's right half.
7. **Below the player**, restyled: the level table (rows survived per track and player; picks the track and
   shows or hides runners; legend for the marks), the scoreboard with its fairness note, and "What is the
   fly's and what is ours", which gains one paragraph: composed Jev's question wording and its
   pick-the-safest rule are ours, the one-shot Choice was about as good as always staying (spike 02), and
   the LLM answers one question.

## Look

`brand.css` tokens verbatim: `--void #0A0A0A`, `--panel #0D0F12`, `--hairline #1E2227`,
`--line-strong #2A2F35`, `--muted #7C848D`, `--text #C9CDD2`, `--bright #E8EBED`, `--accent #7AA2F7`,
`--good #9ECE6A`, `--warn #E0AF68`, `--bad #F7768E`; type scale, spacing and easing from the same file.
Hanken Grotesk for text, JetBrains Mono for short uppercase labels only (never paragraphs). Dark only.

- **Blue is rationed**: one thing per view, the cursor. Status never borrows it: deaths and errors use
  `--bad`, warnings `--warn`. The LLM's orange and the fly's red eyes exist only at sprite size.
- Bars and rasters in the mind panels are `--text` on `--hairline`; the focused panel's bars do not turn
  blue (only its top edge does).
- No decoration: no gradients, no glow, no rounded cards. Hairline rules, precise spacing, body text at
  least 7:1 contrast, 60 to 68 character measure for prose, tap targets at least 44 px.
- Motion is the run itself. `prefers-reduced-motion` steps the run row by row and drops the fall animation.
- The page must work offline from one file: the two font files (`HankenGrotesk-latin.woff2`,
  `JetBrainsMono-latin.woff2`, both OFL, from `~/Documents/PROJECTS/BRAND/website/ds-bundle/fonts/`) are
  copied into `viewer/fonts/` with their licence note and embedded as base64 `@font-face` sources by
  `bakeoff/view.py`. Nothing is fetched.

Approved mockups (static, they use Google Fonts and are reference only):
`docs/superpowers/specs/mockups/2026-09-20-demo-player-blue.html` (option C was chosen) and
`...-demo-player-figures.html` (option 1, the visor, was chosen).

## Phase 5a: the `jev_composed` player

Why: spike 02. On the 55 dangerous states of practice track 1000 the one-shot Choice landed on a gap in
29% (always staying: 33%), while four pointed yes/no questions were wrong 1 time in 800 and picking the
action with the lowest P(gap) was never fatal. TypeSafe's docs describe the one-shot Choice as the
anti-pattern ("ask the most explicit, narrow, specific, atomic questions you can"; "use code when you can").

- New `bakeoff/players/jev_composed.py`, registry name `jev_composed`, in `PAID`, same `PaidPlayer` base,
  same cache, cap, error and fallback rules as `jev`. One request per row with four Nouls, ids
  `gap_left`, `gap_stay`, `gap_right`, `gap_jump`, worded exactly as in the spike:
  "Would the action `left` land the runner on a gap, that is, does `ahead[0].gaps_relative` contain -1?"
  (`stay`: `ahead[0]` contains 0; `right`: `ahead[0]` contains 1; `jump`: `ahead[1]` contains 0).
- The move: the action with the lowest Noul after rounding to two decimals; ties in the order
  `stay, left, right, jump` (the reference solver's order). Invalid when any of the four Nouls is missing
  or not a number. Never gated. `answers` logs the four Nouls; `info` logs `{model, rule:
  "lowest_gap_probability", order: [...]}`.
- **Ours, and labelled as ours** on the page and in the write-up: the wording and the rule. It looks one step
  ahead only; it does not plan.
- The report scores the four Nouls (Brier) like the existing two; `meta.json` gains nothing new.
- Frozen before any tournament seed is touched. Verified on practice seeds 1000 and up only.

## Phase 5b: the player

Replaces phase 4's page; keeps its spine.

| Unit | Change |
| --- | --- |
| `bakeoff/replay.py`, `docs/REPLAY_DATA.md` | unchanged format (replay version 1); frames already arrive per (player, seed) |
| `bakeoff/view.py` | also embeds `viewer/fonts/*.woff2` as base64 `@font-face`; still one file, nothing fetched |
| `viewer/timeline.js` | unchanged |
| `viewer/tunnel.js` | fixed camera; `quads(track, row, size, maxRows)` no longer takes a camera lane or a `seen` argument; new pure `seenOutline(frame, lookahead, window)` for the focused mind's tiles; new pure `place(state, lanes, size)` giving each runner's position, rotation and lift |
| `viewer/sprites.js` (new) | the sprite grids and inks above; pure `visorCells(p)`; `drawSprite(ctx, name, px, options)` |
| `viewer/stage.js` (new) | pure `overlaps(states)` (who is drawn translucent and fanned, and by how much) and pure `autoFocus(current, states, heldSince)` (the focus rule above) |
| `viewer/minds.js` | restyled; new `jevComposedMind`; the fly and LLM panels as now; all log text through `esc` |
| `viewer/feed.js` (new) | the one way frames reach the page: `fromEmbedded(replay)` for a file, `fromStream(url)` for live; both call `onEpisode` and `onFrame` and the page never reads the replay object directly |
| `viewer/app.js`, `index.html`, `viewer.css` | rewritten: the tunnel, the strip, transport, focus, the three restyled sections |

Every pure function has `node --test` tests (through `tests/test_viewer_js.py`), including: overlap of
three runners on the start tile; a ceiling runner's rotation; the visor's cells at 0, 0.5 and 1; auto-focus
holding for 3 rows and yielding to a manual pick; the embedded fonts present and no network reference in
the built page. The page is looked at in a browser at 1440 and 390 wide before it is called done.

## Phase 5c: go live

`uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 300 [--port 8000]`

- A local server on `127.0.0.1` only, standard library only (`http.server` + Server-Sent Events). `GET /`
  serves the player page built with an empty replay and `data-live="/events"`; `GET /events` streams
  `episode`, `frame`, `end` and `error` events as JSON, in the replay's own shapes, so `feed.js` needs no
  second format.
- **Lockstep by row.** One `Game` per player on the same track. Each tick: every player still running and due
  at this row decides (the fly in the server's own process, one brain, built once; Jev and the LLM through
  their capped clients); records are written with the runner's own record builder to a normal run directory
  (`<player>.jsonl`, `meta.json`), then streamed. A jumper skips the next row. The slowest mind sets the pace
  (about one row a second). The run ends when everyone is dead or finished, on Ctrl-C (`interrupted`), or
  when a cap is reached (`budget_exhausted`); the directory is a valid replay in every case and
  `bakeoff view` plays it afterwards.
- Money and safety: the cap is per paid player as today and defaults to 0 (then paid players can only
  replay the cache, which makes a free "live" run of an already played track). A live paid run on a seed
  below 1000 is refused without `--tournament`. `live` builds exactly one fly brain; that no second fly
  process runs at the same time stays the operator's rule, as today. Keys are loaded as today and never
  printed; the server binds to loopback and serves nothing but the page and the event stream.
- To make this possible `Runner.run_seed`'s record building is extracted into a function both the runner and
  the live loop call; the runner's behaviour and its tests do not change.
- This reverses the first spec's non-goal "no real-time play" for this one local mode; replays remain what
  everyone else watches.

## Testing

TDD, `uv run pytest`, no test touches the network. 5a: fakes as for `jev` (`tests/fakes.py`), the tie-break
and the invalid cases, the report's four Brier columns. 5b: as listed above. 5c: the lockstep loop with
fake players (a jumper, a death, a finisher, a budget stop), the event stream's shapes against
`docs/REPLAY_DATA.md`, the server on an ephemeral port with a fake loop, the refusal rules. Paid and fly
runs are controller-and-user steps, never subagent tasks.

## Budget pre-authorized by the user (2026-09-20, for the session that builds this)

Practice seeds 1000 and up only, through the cache and the hard caps, no reruns of a paid command beyond
these ceilings:

- up to **1,000 Jev requests** in total (about 0.04 USD) to verify and record `jev_composed`;
- up to **300 Claude Haiku requests** in total (about 0.18 USD) for one real go-live test on a fresh
  practice seed.

The replay of practice track 1000 needs no further LLM or fly spend: the LLM's run is cached
(`runs/20260920-102919`) and the fly's exists (`runs/20260919-151934`). Anything beyond these ceilings, and
any tournament seed, needs a new go-ahead.

## Phases and order

0. PR #3 (phase 4) is reviewed and its findings fixed on `phase4-replay-viewer`; 5b builds on it.
1. 5a `jev_composed` → 2. 5b the player → 3. 5c go live. Each gets its own plan, written the prototype-first
   way and executed in order on one branch, `phase5-demo-player`, which is stacked on
   `phase4-replay-viewer` (rebase it if PR #3 changes); one PR at the end, against `main` if PR #3 has been
   merged by then, else against `phase4-replay-viewer`. Phase 6 is the tournament and the write-up.
