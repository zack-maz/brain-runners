# Decisions so far

2026-09-19

1. **Contestants:** a traditional LLM, Jev (TypeSafe System One), and a fruit fly brain.
2. **Fly purity: pure innate wiring.** The whole-brain connectome simulation, untrained.
   Game events are hand-mapped onto real sensory neurons and real motor or descending
   neurons are read as button presses. It will lose games that match no reflex; that is
   part of the result. (Rejected for now: fly visual system plus a trained decoder.)
3. **Outcome: watchable tournament.** Seeded rounds replayed side by side with each
   contestant's internals visible, plus a scoreboard. Replays, not live play, so API calls
   are cached and viewing is free.
4. **Budget:** limited. The fly runs locally for free; Jev and the LLM are paid per step,
   so runs need a request cap and a response cache from day one.

5. **Fly route: pure fly, test first.** A throwaway spike (branch `spike/fly-steering`,
   `spikes/01-fly-steering/REPORT.md`) showed the untrained model steers *away from threats*
   reliably (36 of 36 one-sided trials, graded, cancels when both eyes are stimulated) and its
   Giant Fiber escape neuron fires graded with threat, but it cannot steer toward food: smell
   carries no side information and food input locks the left steering neuron on. About
   0.6–0.7 s wall-clock per 100 ms decision on the user's M1.
6. **Flagship game: a "Run"-style tunnel runner** (https://www.coolmathgames.com/0-run), not a
   slither-style food arena. Left/right = the fly's steering neurons, jump = its Giant Fiber.
7. **Design approved 2026-09-19:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md`.
   LLM is Claude Haiku 4.5. Turn-based, one decision per row, same seeded tracks for everyone.
8. **Fly input and tuning (phase 2, ours, not the fly's biology):** each visible gap adds
   `250 / row³` Hz to its eye, capped at 250 Hz and rounded to 25 Hz steps; any net steering
   spike turns (threshold 0 Hz); Giant Fiber mean above 200 Hz jumps. Chosen by a fixed rule from
   768 candidates on practice seeds 1000–1199 using a measured response surface as a stand-in
   brain, confirmed with the real brain. Frozen: `calibration/REPORT.md`, `calibration/RESULTS.md`.
9. **`always_jump` is a second floor** and the report shows `jump_share`, so a jump-heavy player
   is judged against the right baseline.
10. **Tournament seeds must be below 1000**; 1000–1399 were used for calibration. The fly has
    played seeds 0–19 once, after the freeze (first scoreboard); nothing was tuned on them.
11. **Paid players (phase 3):** one request per row through a disk cache (sha256 of provider, model,
    senses, questions) and a hard cap per paid player (`--max-requests`, default 0 = replay only).
    SDK retries are off so the cap is exact; a provider failure is a logged error and a `stay`.
    Jev and the LLM are told the same rules in the same words (`bakeoff/players/briefing.py`, ours,
    written before any paid request). No paid request on a seed below 1000 before the tournament.
    The CLI refuses a live paid run on seeds below 1000 unless `--tournament` is passed. Jev's
    request carries the Choice and the two calibration Nouls the spec asks for, while the LLM
    answers one question; TypeSafe documents that questions in one request run in parallel and
    cannot see one another's answers, so the Nouls are not scaffolding for the Choice, and this
    asymmetry is named in the write-up.
12. **First measured costs (2026-09-20, practice seed 1000, `docs/COSTS.md`):** the LLM costs
    0.00059 USD per request at 806 ms (survived 199 rows); Jev about 0.00003 USD per request at
    159 ms (survived 23 rows), an estimate from one console reading (29,457 tokens for 0.0011 USD,
    blended, no reading before the run). A 20-seed tournament costs at most about 3.56 USD for the
    LLM and about 0.20 USD for Jev. Neither player jumped and both died stepping sideways into a
    gap; the prompts stay as written, because tuning them on a track is what the seed rule forbids.

13. **Replay viewer (phase 4):** `python -m bakeoff view <run_dir>...` writes one self-contained HTML
    file, so a replay opens from disk, works offline and can be sent to someone. Python
    (`bakeoff/replay.py`) merges the run directories and applies the rules of the game (landing
    tiles, complete or cut off, scoreboard); the JavaScript only draws (`docs/REPLAY_DATA.md`). Players
    are lined up by row, not by decision, so every column shows the same stretch of track and a jump
    takes two ticks. The tiles a player was shown are drawn brighter. The same (player, seed) in two
    run directories is an error. When the players did not all play the same seeds, the scoreboard
    says its means are not a fair comparison. The fly's four numbers, the looming formula and the
    known weaknesses are on the page, with what is ours labelled as ours.

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

## Next step

Phases 1 to 4 are built. Write the phase 5 plan (tournament run and write-up); it starts by settling
the first open item above (which seeds).

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
