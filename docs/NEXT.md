# Where we are and what comes next

This file is rewritten whenever the state changes. What the user has decided stays in `docs/DECISIONS.md`
(numbered, only ever added to); measured runs and money are in `docs/COSTS.md`.

## Where we are

Phases 1 to 5 are built and on `main` (phase 5 was PR #4, merged 2026-09-21). Before phase 6 come the updates of
`docs/UPDATES.md` (decision 20), on branch `phase6-updates`:

- **Game v2** (items 3 and 6, decisions 21–24): built.
- **Update 2a, the Jev family and its LLM twins** (decisions 25–27): built and reviewed task by task (spec
  `docs/superpowers/specs/2026-09-21-jev-family-design.md`, plan `docs/superpowers/plans/2026-09-21-update2a-jev-family.md`).
  **Its paid runs are done** (2026-09-21): every player over v2 practice seeds 1000–1004, `llm_reader` on 1000–1001,
  the fly on the same five tracks. Scoreboard and costs: `docs/COSTS.md`, "Update 2a". Claude Haiku spent 3.85 of the
  5.00 USD of decision 26; nothing on a seed below 1000.

## Where to resume (in this order)

1. A final whole-branch review of update 2a: money safety, the same signals for both models, honest labels,
   `jev_composed`'s cache still replaying.
2. Update 2b, the fly (decision 25): `fly_rich` (richer input, untrained, calibrated once on practice seeds), then
   `fly_trained` (a readout of ours on the same wiring). Its own spec.
3. Item 10, the GLM Flash twin (the user will add a Zhipu key to `.env` later), then item 7 (the benchmark), then
   the page: items 4, 5, 8 and 9 (per-mind live log tabs, pick seed and players from the page, GLM Flash among them,
   the analysis on its own tab).
4. When all updates are done: refresh `docs/EXPLAINER.html` (it knows game v2, not yet the Jev family), then one PR
   titled **"Opus v1"** from `phase6-updates` (the user's instruction; not before).
5. Then phase 6, the tournament and the write-up. It starts by settling which seeds (see "Open"), and it needs a new
   budget go-ahead: the tournament is the first paid use of seeds below 1000 (`--tournament`).

## To look at it

- Update 2a, v2 practice tracks: `uv run python -m bakeoff view runs/20260921-165433` (track 1000, every paid
  player); the other tracks are spread over `runs/20260921-171044` (Jev), `runs/20260921-185546` (LLM twins),
  `runs/20260921-191326` (`llm_reader`, 1001) and `runs/20260921-192037` (the fly). `view` refuses the same (player,
  seed) twice, so pick directories that do not overlap.
- Free yardsticks on v2: `runs/20260921-155758` (seeds 1000–1019: solver 150, always-jump 39, random 24).
- Game v1 (phases 1 to 5): `uv run python -m bakeoff view runs/20260919-151934 runs/20260920-102919 runs/20260921-120903`
  (practice track 1000: the fly, the LLM, the composed Jev) and `uv run python -m bakeoff view runs/20260921-132459`
  (the live run on track 1001); or `uv run python -m bakeoff live --game v1 --seed 1001` with the default cap of 0,
  which replays that run's paid answers from the cache for free (the fly is simulated again, about a minute to
  build and a second a row).
- `live` without `--game v1` plays v2. With a cap of 0 a paid player replays what is cached and stops at its first
  uncached question.

## Tooling

Plans are generated from a prototype (`.superpowers/tools/genplan.py`; prototypes kept as local branches
`proto/game-v2`, `proto/jev-family`). The SDD ledger of update 2a is `.superpowers/sdd/2026-09-21-update2a-jev-family/`
(git-ignored).

## What the write-up must carry

From phase 5: the composed Jev's wording and rule are ours and it looks one step ahead only; it wanders on safe rows
because its four answers rarely tie; on both v1 practice tracks it died only where all four landing tiles were gaps;
the one-shot Jev stays in for comparison.

From update 2a: every question set and rule is ours, and each LLM twin gets the same questions and the same rule as
its Jev, so the model is the only difference. The fly on v2 still runs on thresholds frozen on v1 tracks.

All of this is one to five practice tracks: an impression, not a result.

## Open

- Whether the tournament reuses seeds 0–19 or takes fresh seeds below 1000.
- Left from the PR #2 review for phase 3 or later (details in the PR comments): `meta.json` and the logged `looming`
  ignore per-player overrides of the fly constants; `calibrate.play` duplicates the game loop without the fallback
  rule; `fetch_fly_data` cannot repair an existing clone; `Network.restore` copies static synapse arrays every
  decision (measure before optimising).
- Left from the second PR #2 review: the fly data is hashed twice per CLI run (preflight, then
  `Brain`); `SurrogateBrain` raises a bare `KeyError` on a surface file missing a pin field. Done in
  phase 3: `preflight()` runs inside `Runner.run`. Declined: turning a brain exception into a `stay`
  fallback; phase 2 decided a simulator failure must end the run, because a silent `stay` would
  change the fly's score.
- Left from the final review of phase 5 (Minor): a crash in `live` (and in `run`) closes the run as `interrupted`,
  the same status as Ctrl-C; a status of its own would be the more honest record. A hard kill leaves `status:
  running` behind (run 3 of update 2a, `runs/20260921-184858`, is one). `viewer/tunnel.js` knows that rows past the
  finish line never kill (drawing only, commented and tested); a `finish_row` in the track JSON would remove the one
  rule of the game that also lives in JavaScript. The live `episode` event carries the question sets known at that
  moment; a player that changed its questions mid-episode would show nothing under "What it was asked" for the later
  ones (no player does).
- There is no command that scores several run directories as one table; the update 2a scoreboard in `docs/COSTS.md`
  was merged by a throwaway script. Worth folding into item 7 (the benchmark).
