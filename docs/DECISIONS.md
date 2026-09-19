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

## Open

- Which fly circuits the public models let us stimulate and read (research in progress);
  the game list follows from that.
- Which games, and how each is presented fairly to all three contestants.
- LLM choice (Claude Haiku 4.5 was picked for the predecessor project).

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
