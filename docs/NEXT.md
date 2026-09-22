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
  5.00 USD of decision 26; nothing on a seed below 1000. **Final whole-branch review done** (2026-09-21, "ready with
  fixes", nothing critical; report `.superpowers/sdd/2026-09-21-update2a-jev-family/final-review-report.md`): money
  safety, `jev_composed`'s phase 5 cache (still 247 rows on v1 track 1000, all from cache) and the rules all hold.
  Fixed: the docs name what still differs between the two models; a question set that needs more vision is now a
  usage error before anything is played; `brier_all` leaves out answers outside 0 to 1.
- **Update 2b, the fly** (decisions 29–30): `fly_trained` dropped by the user; `fly_rich` stopped at its probe (spike
  03, branch `spike/fly-bands`, local): the wiring carries "where" only as strength, and band input made the fly
  worse. `fly` stays the only fly.
- **Item 10, GLM Flash** (decisions 33–34): the four `glm_<set>` players are built and track 1000 is recorded;
  tracks 1001–1004 are parked while the free tier throttles (`docs/COSTS.md`, "Item 10").
- **Item 7, the benchmark** (decision 31, spec `docs/superpowers/specs/2026-09-22-benchmark-design.md`): built
  2026-09-22. `python -m bakeoff bench RUN_DIR[:PLAYER,...] ...` scores recorded runs (spends nothing), prints the
  tables and writes `bench.json` and an offline `bench.html`. Prototyped, then its five tested commits taken as they
  were (not re-typed by implementers). Final design review done ("ready with fixes"; report
  `.superpowers/sdd/2026-09-22-benchmark/final-review-report.md`), all its findings fixed (decision 32): t
  intervals instead of a percentile bootstrap, which gave a verdict about 1 time in 7 at 5 tracks with no real
  difference; runs of one length only; a note on how many verdicts chance gives among many pairs.

## Where to resume (in this order)

1. The page (items 4, 5, 8, 9; decision 35, design `docs/superpowers/specs/2026-09-22-page-control-design.md`,
   approved): **update 3a** first, the control channel and the lobby (`/state`, `/run`, `/cancel`, the local token,
   the session cap, `--start`), then **3b**, the logs in the mind panels, the Run and Analysis tabs and the player
   picker. Each gets a plan; the house workflow is to prototype it in a scratch clone first
   ([[prototyped-plans-workflow]] in the memory notes; prototypes kept as local `proto/*` branches).
2. **Parked**: GLM Flash's tracks 1001–1004 (decision 34), while Zhipu's free tier throttles. To pick it up, check
   it answers (a few requests through `bakeoff.clients.glm.HttpTransport`), then
   `uv run python -m bakeoff run --players glm_composed,glm_choice,glm_two_step --seeds 5 --seed-start 1000 --max-requests 700`
   and `--players glm_reader --seeds 2 --seed-start 1000 --max-requests 350`. Track 1000 replays free from the cache.
3. When all updates are done: refresh `docs/EXPLAINER.html` (it knows game v2, not yet the Jev family), then one PR
   titled **"Opus v1"** from `phase6-updates` (the user's instruction; not before).
4. Then phase 6, the tournament and the write-up. It starts by settling which seeds (see "Open"), and it needs a new
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
- Update 2a as one scoreboard with intervals and pairs: `uv run python -m bakeoff bench runs/20260921-165433 "runs/20260921-171044:jev_composed,jev_choice,jev_two_step,jev_reader" runs/20260921-185546 runs/20260921-191326 runs/20260921-192037` (writes `bench.html`).
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

From update 2a: every question set and rule is ours. Each LLM twin gets the same questions and the same rule as its
Jev, but the model is not the only difference: the twin is also given the briefing of the rules (Jev's yes/no
questions carry only the question, except in the choice set); Jev's answers in one request are made in parallel and
cannot see each other, while the LLM writes all of its answers in one reply; and an LLM probability is a number it
states. The Brier comparison between the models must carry all three. `brier_all` compares the two models within a set,
not sets with each other (the reader's tiles are about 90% floor). `jev_reader` dies because it misses the gap straight
ahead (44% of them), a failure of the reader's wording or of the 42-question request, not of Jev's reading: the
composed wording for the same tile was never missed. The fly on v2 still runs on thresholds frozen on v1 tracks.

From update 2b: spike 03's result (decision 30): the looming cells, ordered by where their inputs sit in the eye,
change only how hard the fly turns or jumps, never what it does; band input made it worse.

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
- Left from the final review of update 2a (Minor): `jev_composed` accepts any finite answer while `llm_composed`
  requires 0 to 1, and `jev_composed` logs no `info.set` (leave its class alone: its cache and records must not
  change); the reader LLM's `max_tokens` (256 + 12 per question, about 50% headroom) is untested on larger visions;
  the `CONTESTANTS` order in `replay.py`, for update 8.
- For the user: whether to test the briefing difference on practice seeds with a new Jev set whose yes/no questions
  carry the briefing (e.g. `reader_briefed`; a new set, so `jev_composed`'s cache is untouched), and whether to add gap
  recall to the report beside `brier_all`.
