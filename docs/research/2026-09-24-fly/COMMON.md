# Common context for the fly research (2026-09-24)

Project: brain-bakeoff (this repo). Read `CLAUDE.md` first, then `docs/NEXT.md`. An untrained fruit-fly connectome
simulation (Shiu et al. 2024 Brian2 LIF model, FlyWire v783, 138,639 neurons; data in `data/Drosophila_brain_model/`,
annotations `data/neuron_annotations.tsv`) plays a "Run"-style tunnel game (game v2: 150 rows, 12 lanes, actions
stay / left / right / jump; a jump clears the next row and lands on the one after; gaps in the floor kill).

How the fly plays today (`bakeoff/players/fly.py`, `bakeoff/senses.py`, `bakeoff/fly/brain.py`, `bakeoff/fly/neurons.py`):
- Input (ours): each visible gap adds `250 / row**3` Hz to the left eye (offset <= 0) and/or right eye (offset >= 0);
  each eye's total, quantized to 11 levels, drives that eye's LPLC2 + LC4 cells as Poisson input.
- 100 ms window from a restored clean state per decision (no memory between decisions).
- Readout (ours): turn = (DNa01+DNb01 right) - (left), jump = Giant Fiber (DNp01) mean; jump if > 200 Hz, else turn
  if |turn| > 0, else stay. Thresholds frozen on v1 practice seeds 1000-1199 (`calibration/REPORT.md`).
- Results: v1 ~120-212 rows of 300; v2 (thresholds not retuned) mean 68 of 150 on seeds 1000-1004, every death a jump
  into a gap. Random 24, always-jump 39, solver 150.
- Spike 01 (`git show spike/fly-steering:spikes/01-fly-steering/REPORT.md`): looming on one eye -> contralateral
  DNa01/DNa02/DNb01 (turn away) + Giant Fiber; smell/taste give no lateralized steering.
- Spike 03 (`git show spike/fly-bands:spikes/03-fly-bands/REPORT.md`): banding each eye's looming cells changes only
  response strength, never the action; band flies played worse. Nothing in the escape path knows where a jump lands.

The user's goal: improve the fly. Two tracks, in order:
1. **Pure fly** (decision 2 stays binding): untrained innate wiring only. We may change what is OURS -- how the game
   is presented to the fly (which sensory neurons, what signal), which of the fly's own neurons are read and how,
   state carried between decisions, thresholds re-fixed on v2 practice seeds (>= 1000 only, never below 1000) by a
   rule fixed beforehand -- and every such mapping is labelled as ours.
2. **A second, trained fly** (separate player, clearly labelled): connectome plus learned parts (a small learned
   readout, a connectome-constrained visual front end like flyvis, etc.).

Hard rules: no paid API calls; never run two fly (real-brain) processes at once, 8 GB Mac, the real brain needs ~1 GB;
do not modify tracked files or commit anything; write only your report file (and scratch files under this
directory). Cite sources with URLs; mark anything you did not verify as (unverified). Be concrete: neuron type names,
FlyWire cell-type labels, papers with year, repos with licence and last activity.
