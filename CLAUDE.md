# brain-bakeoff

An LLM (Claude Haiku 4.5), Jev (TypeSafe System One) and an untrained fruit-fly connectome
simulation play the same seeded runs of a "Run"-style tunnel game; output is a watchable replay and a study of
which mind performs best for its cost and speed (decision 53). Read these before doing anything:

0. `docs/EXPLAINER.html` — the plain-language tour of the whole project, high level first, then technical
   (written 2026-09-21, refreshed 2026-09-24 after the updates and 2026-09-25 for fly2).
1. `docs/NEXT.md` — where things stand and what to do next, in order (rewritten as the state changes).
   `docs/DECISIONS.md` — what the user has decided, numbered, only ever added to.
2. `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` — the approved design (binding), extended by
   `docs/superpowers/specs/2026-09-20-demo-player-design.md` (the demo player; also binding).
3. `docs/RESEARCH.md` — fly-brain resources. Spike results: branch `spike/fly-steering`,
   `docs/spikes/01-fly-steering/REPORT.md` (throwaway code; port ideas, do not merge it). Also spike 02, branch
   `spike/jev-questions`, `docs/spikes/02-jev-questions/REPORT.md` (why Jev's one-shot Choice, now `jev_plain`, fails), and spike 03,
   branch `spike/fly-bands`, `docs/spikes/03-fly-bands/REPORT.md` (update 2b's probe result).

## Status

Design approved 2026-09-19. Phase 1 built (game, senses, baselines, runner, report, CLI). Phase 2
built (plan: `docs/superpowers/plans/2026-09-19-phase2-fly-player.md`): fly player on the real
Brian2 model, looming weighting and two thresholds fixed on practice seeds 1000–1199 and frozen
(`docs/calibration/REPORT.md`; never retune, never let seeds below 1000 influence them). First
scoreboard in `docs/calibration/RESULTS.md`. Phase 3 built (plan:
`docs/superpowers/plans/2026-09-20-phase3-paid-players.md`): `jev_plain` and `haiku_plain` players (then `jev` and `haiku`) behind
`bakeoff/clients/core.py` (disk cache, hard cap per paid player, no SDK retries). First costs in
`docs/COSTS.md`. Phase 4 built (plan: `docs/superpowers/plans/2026-09-20-phase4-replay-viewer.md`):
`bakeoff/replay.py` merges run directories into one replay object (`docs/REPLAY_DATA.md`) and
`python -m bakeoff view` embeds it with `viewer/` in one offline HTML file (PR #3, merged). Phase 5a built
(plan: `docs/superpowers/plans/2026-09-21-phase5a-jev-composed.md`): the `jev_step1` player (four pointed
Nouls, code picks the action least likely to land on a gap; the wording and the rule are ours), 247 rows on
practice track 1000 (`docs/COSTS.md`). Phase 5b built (plan: `...-phase5b-demo-player.md`): the replay page is the
demo player, the project's main tool (design: `docs/superpowers/specs/2026-09-20-demo-player-design.md`): one tunnel,
three pixel runners, the mind strip, blue as the cursor, the user's brand, one offline file. Phase 5c built (plan:
`...-phase5c-go-live.md`): `python -m bakeoff live` plays a track in lockstep in real time, records a normal run
directory and streams it into the same page from a loopback server; first real go-live on practice seed 1001
(`runs/20260921-132459`). Phase 5 is merged (PR #4). Before phase 6 come ten
updates (`docs/UPDATES.md`, decision 20), on branch `phase6-updates`. Update 1, game v2, is built (plan
`...-update1-game-v2.md`): named game versions in `bakeoff/game/rules.py`; `v2` (default) is 150 rows at full
difficulty by row 100, `v1` is the old 300-row game, pinned tile for tile; runs record their game and `view` never
mixes two; everything recorded so far is v1 (`--game v1` replays it). Update 2a, the Jev family, is built (plan
`...-update2a-jev-family.md`): `bakeoff/players/question_sets.py` (step1, guided, step2, map: questions and a
rule, ours; the one-shot players are the plain set) played by `jev_<set>` and by Claude Haiku twins `haiku_<set>`
(`set_players.py`). The sets were renamed by decision 44 (composed → step1, choice → guided, two_step → step2,
reader → map, the one-shot `jev`/`haiku`/`glm` → `*_plain`) and Haiku's players were `llm_<set>` until decision 39;
`bakeoff/players/names.py` still reads every old name everywhere, so old runs and commands keep working; the report's `brier_all`;
its paid runs are done (five v2 practice tracks, `docs/COSTS.md`). Update 2b, the fly, stopped at its probe (spike 03, decision 30). Item 7, the benchmark, is built:
`python -m bakeoff bench` (`bakeoff/bench.py`, page `viewer/bench.html`), decision 31. Item 10, the GLM Flash twins, is
built and parked after one track (decisions 33–34). The page (items 4, 5, 8 and 9; decision 35, design
`docs/superpowers/specs/2026-09-22-page-control-design.md`) is built as updates 3a (the control channel, the session
ceiling, the lobby) and 3b (the logs, the Run and Analysis tabs, the picker, the benchmark in the page), each
reviewed and fixed; decisions 36–39 settle their open questions and the rename of Claude Haiku's players.
**Everything before phase 6 is built and on `main`** (PR #6 "Opus v1", merged 2026-09-25); what is left of it is
GLM Flash's parked tracks. `fly2`, a second pure fly with a richer input of ours (M3, a sideways channel), is
built, calibrated, played and on `main` (PR #7, merged 2026-09-25; decisions 41–43, spec
`docs/superpowers/specs/2026-09-24-fly2-design.md`, plan `docs/superpowers/plans/2026-09-24-fly2.md`): its numbers
are frozen (`docs/calibration/FLY2_REPORT.md`), its real run and its live smoke are done; on 100 fresh seeds it beats `fly` by 13.4 rows (decision 47).
`fly3`, a trained readout on the frozen wiring (decision 48), stopped at its probe: the same learner with no brain
played better (spike 05, decision 49), so it is not built. Brain Runners (called Brain Battle until decision 51, Brain Run until decision 57), the
front of `bakeoff live`, is on `main` (PR #9, merged 2026-09-26; renamed in PR #11). PR #11 (merged 2026-09-26) also
lets Jev play without a cap (decision 50). PRs #8–#12 are merged; since #12 a results card reads
"N live" over "M cached". Phase 6 is the study (decision 53, spec `docs/superpowers/specs/2026-09-28-study-design.md`),
not a tournament: its code is built on branch `study` (plan `docs/superpowers/plans/2026-09-28-study.md`): the seed
flag `--held-out`, the benchmark's cost per track, time per decision, failures and frontiers, and Brain Runners's
Charts and Writeup screens. Its runs are done (decisions 54–56), and the project is released as the public
repository Brain Runners (decision 57; Jev capped again, decision 58). Probe reports are copied into `docs/spikes/`;
`calibration/` lives under `docs/`. Each phase gets its own plan. Resume from `docs/NEXT.md`.

## How we work here

- The user drives with the superpowers workflow: brainstorm → spec → writing-plans →
  subagent-driven-development (implementer per task, reviewer per task, one final review),
  then finishing-a-development-branch. Never build on `main`; branch first.
- Python via `uv` only (`uv add`, `uv run pytest`), Python 3.13, TDD, no test touches the network.
- Reuse the reviewed harness in `zack-maz/jev-testing` PR #1 (local: `../testing`, package
  `glassbox/`): `Decision`/`Policy`, streaming JSONL runner with run status, report. Its
  phase 1 plan ends with review notes worth reading before planning.
- Keys live in a git-ignored `.env`. A guard blocks every shell command that mentions `.env`,
  so programs must load it themselves (python-dotenv) and never print values.
- Budget is limited: paid players need a response cache and a hard request cap from their
  first commit; start paid runs with one capped track. Jev included (decision 58): a stranger's TypeSafe key may be
  billed, so `UNCAPPED` is empty (decision 50 had Jev uncapped while its requests cost the one user nothing).
  Measured: the LLM about 0.0006 USD per request, Jev about
  0.00003 USD (an estimate, `docs/COSTS.md`).
- The fly simulation needs about 1 GB and must run one process at a time on this 8 GB Mac.
- Honesty rule for the fly: untrained, innate wiring only; any mapping that is ours rather than
  the fly's biology is labelled as such on screen and in the write-up.
- `uv run pytest` runs the fast tests only. `uv run pytest -m slow` builds the real fly brain (about 1 GB,
  one minute); never run two fly processes at once.
- The viewer is plain JavaScript with no build step and no npm packages. Rules of the game stay in
  Python (`bakeoff/replay.py`); the pure JavaScript (`timeline.js`, `tunnel.js`, `sprites.js`, `roster.js`, `stage.js`, `minds.js`,
  `log.js`, `picker.js`, `tabs.js`, `feed.js`, `lobby.js`, `bench_view.js`, and Brain Runners's `screens.js`, `select.js`,
  `trackpick.js`, `results.js`, `records.js`, `writeup.js`) is tested by
  `viewer/tests/*.test.js`, which `uv run pytest` runs through `node --test`. Text from a log is always
  escaped (`Minds.esc`) and the page must never load anything from the network (the two brand fonts in
  `viewer/fonts/` are embedded as base64 by `bakeoff/view.py`). The page is the user's brand: tokens from
  `~/Documents/PROJECTS/BRAND/brand.css`, blue only for the cursor (the mind in focus and its tiles), mono for short
  labels only, deaths and errors `--bad`, warnings `--warn`. Frames reach `app.js` through `Feed` alone.
  `viewer/front.js` is the DOM glue of the live front (it fetches and shows the screens; in a replay file it returns
  at once), and `app.js` exposes the run screen to it as `window.Race`.
- The page has two tabs (update 3b): Run holds the tunnel, the mind strip and the transport; Analysis
  holds the levels, the scoreboard, what is ours and the benchmark. Every mind panel carries a running log, one line
  per row up to the row on screen and one log open at a time, appended as the frames arrive so it keeps its scroll
  and never runs ahead of the tunnel. One section, "Players", holds both lists as
  labelled rows (decision 38); since Brain Runners (then Brain Battle) only one is left: who is in the tunnel (shows and hides the
  runners on screen, live or replay), while who runs next is picked on the character select. The level table only picks the track, and a player that did not run
  the track in view can never be turned on. `viewer/bench_view.js` is the one drawing code for the benchmark, mounted by both
  `bench.html` and the Analysis tab, and `viewer/bench.css` styles it on both pages (keyed to its `data-bench`
  names, not to ids); `bakeoff.bench.benchmark_of` scores runs for a page and answers with a reason instead of
  failing, so `view` embeds the numbers of what it merged and a live run's `end` event carries the benchmark of
  what it just played — never at the cost of the event itself, which is what the page waits for.
- `bakeoff live` (`bakeoff/live.py`, `bakeoff/live_server.py`, `bakeoff/session.py`) plays one track in lockstep by
  row, records a normal run directory and streams it to the page over Server-Sent Events on `127.0.0.1` only
  (standard library, no dependency). It builds one fly brain in its own process, shared by every fly of a run
  (`bakeoff/fly/shared.py`): never start it next to another fly run. Its records come from `runner.play_row` and
  its frames from `replay.frame_of`, the same functions `run` and `view` use; keep it that way.
- The page runs the show (update 3a, design `docs/superpowers/specs/2026-09-22-page-control-design.md`): the command
  binds the port and sets the ceiling, the page (since Brain Battle, now Brain Runners, its front: the character select picks the
  players, the track select the track and holds the money confirmation) starts and cancels the run (`GET /state`, `POST /run`, `POST /cancel`, `GET /events?run=`). Every request but the page itself
  carries a token minted at startup and embedded in the page (in the header; in the query for the event stream
  alone, which cannot send headers), so no other page in the browser can drive the run. It is not a defence
  against a program on this machine: whatever may fetch `/` may read the token out of the page. One
  `LiveSession` per command holds one budget per
  paid player for the whole session (`SharedBudget` gives each run its
  own record of what it spent), runs one
  `LiveRun` at a time and keeps serving so another track can be played without restarting. `--start` plays the
  command line's own run at once, as before, and holds its first decision until a browser is listening.
- Brain Runners (decision 45, spec `docs/superpowers/specs/2026-09-25-brain-battle-design.md`) is on `main` (PR #9,
  merged 2026-09-26), built in two plans as Brain Battle and renamed by decision 51 (PR #11): on screen it is Brain
  Run and its fighters are runners ("Choose your runners", "Ready to run", "‹ Runners", "N runners"), and the home
  brain's glow pulses; code ids, file names and comments keep the old names. Plan a: `bakeoff/roster.py` is the one list of characters and skins (a test
  keeps it equal to the registry), embedded in every page, so runners wear their skin's colours and are labelled
  "Jev · Step 1" (`viewer/roster.js`); `bakeoff/results.py` gives a run's numbers (also on the `end` event),
  `bakeoff/records.py` the leaderboard, pairs and past runs (each player and track from the newest run that completed
  it); the report has `wrong_moves` and `fatal_wrong_moves`. Read-only routes sit behind the token:
  `GET /results?run=`, `GET /records`, `GET /charts`, `GET /writeup`, `GET /replay?run=`; `run=` must be a run id naming a directory
  under the session's `--out` with a `meta.json`, or it is a 404. Plan b, the screens
  (`docs/superpowers/plans/2026-09-25-brain-battle-b.md`, decision 46): `bakeoff live` opens on the front
  (home, character select, track select, the run screen, results that open by themselves, Records with the past
  runs and the whole "what is ours" section); since the study (decision 53) the leaderboard and the head to head
  are on Charts (`bakeoff/charts.py`: every recorded track of the game, with the benchmark's trade-off charts
  below), and Writeup shows `docs/WRITEUP.html` as written, its numbers cited with `data-stat` and filled from the
  charts, never typed; the
  lobby's grid is gone (`lobby.js` keeps the money helpers). A lineup that can spend is confirmed once, with its
  worst case on the RUN button, and Run again goes through the same confirmation; a lineup whose only spending is
  Jev's shows its worst case but is not asked (decision 50). A results card's Requests read "N live" over "M cached"
  when some answers came from the cache. `bakeoff view` keeps its replay page.
- Capped paid players (Claude Haiku, GLM Flash) spend nothing without `--max-requests` (default 0 replays
  `.cache/responses`); Jev asks whenever its answer is not cached. No fast test can reach a provider:
  `tests/conftest.py` hides every provider key unless a test is marked `live`. A player that reaches its cap or whose provider
  keeps failing drops out and the others play on (`stopped` in `meta.json`, decision 52). Never raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
  request on a seed below 1000 outside the study's runs; the CLI refuses a live paid run on seeds
  below 1000 without `--held-out`. Prices per player are in `bakeoff/prices.py`.
