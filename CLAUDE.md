# brain-bakeoff

An LLM (Claude Haiku 4.5), Jev (TypeSafe System One) and an untrained fruit-fly connectome
simulation play the same seeded runs of a "Run"-style tunnel game; output is a watchable replay
tournament. Read these before doing anything:

1. `docs/DECISIONS.md` — what the user has decided, in order, and the next step.
2. `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` — the approved design (binding).
3. `docs/RESEARCH.md` — fly-brain resources. Spike results: branch `spike/fly-steering`,
   `spikes/01-fly-steering/REPORT.md` (throwaway code; port ideas, do not merge it).

## Status

Design approved 2026-09-19. Phase 1 built (game, senses, baselines, runner, report, CLI). Phase 2
built (plan: `docs/superpowers/plans/2026-09-19-phase2-fly-player.md`): fly player on the real
Brian2 model, looming weighting and two thresholds fixed on practice seeds 1000–1199 and frozen
(`calibration/REPORT.md`; never retune, never let seeds below 1000 influence them). First
scoreboard in `calibration/RESULTS.md`. Phase 3 built (plan:
`docs/superpowers/plans/2026-09-20-phase3-paid-players.md`): `jev` and `llm` players behind
`bakeoff/clients/core.py` (disk cache, hard cap per paid player, no SDK retries). First costs in
`docs/COSTS.md`. Next: write the phase 4 plan (replay viewer). Each phase gets its own plan.

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
- Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
  raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
  request on a seed below 1000 before the tournament; the CLI refuses a live paid run on seeds
  below 1000 without `--tournament`.
