# brain-bakeoff

An LLM (Claude Haiku 4.5), Jev (TypeSafe System One) and an untrained fruit-fly connectome
simulation play the same seeded runs of a "Run"-style tunnel game; output is a watchable replay
tournament. Read these before doing anything:

0. `docs/EXPLAINER.html` — the plain-language tour of the whole project, high level first, then technical
   (dated 2026-09-21: predates the Jev family; refreshed when all updates are done).
1. `docs/NEXT.md` — where things stand and what to do next, in order (rewritten as the state changes).
   `docs/DECISIONS.md` — what the user has decided, numbered, only ever added to.
2. `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` — the approved design (binding), extended by
   `docs/superpowers/specs/2026-09-20-demo-player-design.md` (the demo player; also binding).
3. `docs/RESEARCH.md` — fly-brain resources. Spike results: branch `spike/fly-steering`,
   `spikes/01-fly-steering/REPORT.md` (throwaway code; port ideas, do not merge it). Also spike 02, branch
   `spike/jev-questions`, `spikes/02-jev-questions/REPORT.md` (why Jev's one-shot Choice fails), and spike 03,
   branch `spike/fly-bands`, `spikes/03-fly-bands/REPORT.md` (update 2b's probe result).

## Status

Design approved 2026-09-19. Phase 1 built (game, senses, baselines, runner, report, CLI). Phase 2
built (plan: `docs/superpowers/plans/2026-09-19-phase2-fly-player.md`): fly player on the real
Brian2 model, looming weighting and two thresholds fixed on practice seeds 1000–1199 and frozen
(`calibration/REPORT.md`; never retune, never let seeds below 1000 influence them). First
scoreboard in `calibration/RESULTS.md`. Phase 3 built (plan:
`docs/superpowers/plans/2026-09-20-phase3-paid-players.md`): `jev` and `llm` players behind
`bakeoff/clients/core.py` (disk cache, hard cap per paid player, no SDK retries). First costs in
`docs/COSTS.md`. Phase 4 built (plan: `docs/superpowers/plans/2026-09-20-phase4-replay-viewer.md`):
`bakeoff/replay.py` merges run directories into one replay object (`docs/REPLAY_DATA.md`) and
`python -m bakeoff view` embeds it with `viewer/` in one offline HTML file (PR #3, merged). Phase 5a built
(plan: `docs/superpowers/plans/2026-09-21-phase5a-jev-composed.md`): the `jev_composed` player (four pointed
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
`...-update2a-jev-family.md`): `bakeoff/players/question_sets.py` (composed, choice, two_step, reader: questions and a
rule, ours) played by `jev_<set>` and by Claude Haiku twins `llm_<set>` (`set_players.py`); the report's `brier_all`;
its paid runs are done (five v2 practice tracks, `docs/COSTS.md`). Update 2b, the fly, stopped at its probe (spike 03, decision 30). Item 7, the benchmark, is built:
`python -m bakeoff bench` (`bakeoff/bench.py`, page `viewer/bench.html`), decision 31. Resume from `docs/NEXT.md`; one PR "Opus v1" when
all updates are done. Then phase 6, the tournament and the write-up, which needs a new budget go-ahead. Each phase
gets its own plan.

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
  first commit; start paid runs with one capped track. Measured: the LLM about 0.0006 USD per request, Jev about
  0.00003 USD (an estimate, `docs/COSTS.md`).
- The fly simulation needs about 1 GB and must run one process at a time on this 8 GB Mac.
- Honesty rule for the fly: untrained, innate wiring only; any mapping that is ours rather than
  the fly's biology is labelled as such on screen and in the write-up.
- `uv run pytest` runs the fast tests only. `uv run pytest -m slow` builds the real fly brain (about 1 GB,
  one minute); never run two fly processes at once.
- The viewer is plain JavaScript with no build step and no npm packages. Rules of the game stay in
  Python (`bakeoff/replay.py`); the pure JavaScript (`timeline.js`, `tunnel.js`, `sprites.js`, `stage.js`, `minds.js`,
  `feed.js`) is tested by
  `viewer/tests/*.test.js`, which `uv run pytest` runs through `node --test`. Text from a log is always
  escaped (`Minds.esc`) and the page must never load anything from the network (the two brand fonts in
  `viewer/fonts/` are embedded as base64 by `bakeoff/view.py`). The page is the user's brand: tokens from
  `~/Documents/PROJECTS/BRAND/brand.css`, blue only for the cursor (the mind in focus and its tiles), mono for short
  labels only, deaths and errors `--bad`, warnings `--warn`. Frames reach `app.js` through `Feed` alone.
- `bakeoff live` (`bakeoff/live.py`, `bakeoff/live_server.py`) plays one track in lockstep by row, records a
  normal run directory and streams it to the page over Server-Sent Events on `127.0.0.1` only (standard
  library, no dependency). It builds one fly brain in its own process: never start it next to another fly run.
  Its records come from `runner.play_row` and its frames from `replay.frame_of`, the same functions `run` and
  `view` use; keep it that way.
- Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
  raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
  request on a seed below 1000 before the tournament; the CLI refuses a live paid run on seeds
  below 1000 without `--tournament`.
