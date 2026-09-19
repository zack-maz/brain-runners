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

## Open

- Jev pricing and latency (first measured in phase 3, on one capped track).
- The fly's looming weighting and its two thresholds (fixed in phase 2 on practice seeds).

## Next step

Write the phase 1 implementation plan (game engine, track generator, senses, `random` and
`solver` players, runner, report, CLI) from the spec, then build it.

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
