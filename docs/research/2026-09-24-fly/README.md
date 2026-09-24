# Fly research, 2026-09-24

Three research agents answered the briefs here, before the design of `fly2`
(`docs/superpowers/specs/2026-09-24-fly2-design.md`). The context all three were given is in `COMMON.md`.

- `diagnosis-report.md` (`brief-diagnosis.md`): why `fly` dies, from recorded runs and the stand-in brain, and the
  best any policy could score on each input.
  - Today's input caps any policy at 66.7 rows on v2 held-out seeds, and the fly scores 66.0.
  - Re-fixing the thresholds on v2 buys nothing.
  - Richer inputs of ours raise the cap to 91–136.
- `circuits-report.md` (`brief-circuits.md`, plus the user's `addendum-flywire-tool.md`): which inborn circuits fit
  the game, with a path analysis in the Shiu connectivity and in the user's FlyWire viewer data.
- `ecosystem-report.md` (`brief-ecosystem.md`): what other projects did with this model, designs for a trained fly,
  and faster simulators.

The scripts were run from the repo root at their original place, `.superpowers/research/2026-09-24-fly/`. They
read only local data and the stand-in brain, and they spend nothing. Their outputs are kept next to them.
