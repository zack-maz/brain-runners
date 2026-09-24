# Brief: diagnose the fly from its recorded runs (local data only)

Read `COMMON.md` in this directory first.

Question: exactly why and where does the current fly fail, and what is the ceiling of any design that keeps its
two-number (left/right looming) input? Use ONLY recorded data and the free stand-in brain -- do not build the real
Brian2 brain, spend nothing.

Data: fly runs are JSONL in `runs/` (one record per decision: senses, looming, info.rates_hz, chosen/executed action,
solver_action, solver_depths, death_cause). v2: `runs/20260921-192037` (seeds 1000-1004). v1: `runs/20260919-151934`
and any other `runs/*/fly.jsonl` (check `meta.json` for the game). The stand-in brain is `bakeoff/fly/surface.py`
(measured response surface, 121 inputs) used by `bakeoff/fly/calibrate.py`.

Do:
1. Failure anatomy: for every death, the last ~5 decisions: what the fly saw, its signals, what it did, what the
   solver would do. Classify the situations (gap straight ahead, gap to one side, gaps both sides, jump landing on a
   gap, ...). How often does the fly pick an action that lands on a gap when a safe one exists (per v1 and v2)?
2. Information ceiling: with input = (left level, right level) only, what is the best possible fixed policy
   (lookup table from the 121 input pairs to an action) on v2 practice seeds 1000-1199? Compute it offline from the
   game engine (`bakeoff/game/`) -- this is an upper bound for any readout on today's input and tells us whether
   the input or the readout is the bottleneck. Do the same for a few richer ours-to-choose inputs (e.g. separate
   "straight ahead" channel, near vs far rows) to show how much information each adds.
3. Re-fixing the two thresholds on v2 with the stand-in brain (v2 practice seeds 1000-1199, the calibrate grid):
   how many rows would that buy? (Report only; do not write to `calibration/`.)

Deliverable: `diagnosis-report.md` in this directory, 10-line summary first, then tables and the scripts' paths
(put scripts under this directory). Say plainly which bottleneck dominates: input, readout, or the jump reflex.
