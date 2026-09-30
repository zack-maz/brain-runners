# Fly: first results with the real brain

Constants from `docs/calibration/REPORT.md` (ours, not the fly's biology), real Brian2 brain, one
decision per 100 ms window, input noise seeded per (track seed, row) so these runs repeat exactly.

On check seeds 1000-1019 the real brain averaged 117.95 rows; the stand-in brain used for
calibration predicted 118.70 (ratio 0.99).

## Check seeds 1000-1019 (practice)

| player | runs | incomplete | missing | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | jump_share | solver_agreement | fallback_rate | invalid_rate | error_rate | requests | mean_latency_ms | input_tokens | output_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fly | 20 | 0 | 0 | 117.95 | 113.00 | 0 | 0 | 20 | 0 | 0.08 | 0.99 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |

Run runs/20260919-151934, code a130aa2, clean tree.

## First scoreboard, seeds 0-19

| player | runs | incomplete | missing | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | jump_share | solver_agreement | fallback_rate | invalid_rate | error_rate | requests | mean_latency_ms | input_tokens | output_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_jump | 20 | 0 | 0 | 47.80 | 39.00 | 0 | 0 | 20 | 0 | 1.00 | 0.96 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| fly | 20 | 0 | 0 | 126.70 | 124.00 | 0 | 0 | 20 | 0 | 0.08 | 0.99 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| random | 20 | 0 | 0 | 34.70 | 30.00 | 0 | 8 | 4 | 8 | 0.26 | 0.96 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| solver | 20 | 0 | 0 | 299.70 | 300.00 | 19 | 1 | 0 | 0 | 0.02 | 1.00 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |

Run runs/20260919-154809, code a130aa2, clean tree.

`always_jump` is the floor for a jump-heavy player, `random` the floor for everything else, `solver`
the reference (same 6-row, ±3-lane view; not a contestant).

## Check seeds, seed by seed

Real: last record per seed in `runs/20260919-151934/fly.jsonl` (`rows_survived`). Stand-in: for
each seed, `play(FlyPlayer(brain_factory=lambda: brain), generate_track(seed))[0].rows_survived`
with `brain = SurrogateBrain(load_surface("docs/calibration/response_surface.json"))`.

| seed | real brain rows | stand-in rows |
| --- | --- | --- |
| 1000 | 58 | 123 |
| 1001 | 212 | 149 |
| 1002 | 113 | 113 |
| 1003 | 150 | 52 |
| 1004 | 130 | 130 |
| 1005 | 84 | 84 |
| 1006 | 174 | 242 |
| 1007 | 184 | 184 |
| 1008 | 91 | 91 |
| 1009 | 113 | 113 |
| 1010 | 103 | 123 |
| 1011 | 113 | 13 |
| 1012 | 75 | 118 |
| 1013 | 118 | 118 |
| 1014 | 7 | 147 |
| 1015 | 126 | 140 |
| 1016 | 90 | 128 |
| 1017 | 209 | 145 |
| 1018 | 93 | 45 |
| 1019 | 116 | 116 |

The means agree (117.95 vs 118.70) while single tracks differ, because one different noise draw
changes the rest of a run.

## Known asymmetry: the fly leans right

Measured from the committed `docs/calibration/response_surface.json` (8 trials per input), mean turn
signal (DNa01 + DNb01, right minus left) when both eyes get the same rate:

| both eyes (Hz) | 25 | 50 | 75 | 100 | 125 | 150 | 175 | 200 | 225 | 250 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean turn signal (Hz) | 0.0 | +7.5 | +10.0 | +8.75 | +7.5 | +1.25 | +10.0 | +20.0 | +10.0 | +10.0 |

The model's left eye has 162 looming cells (LPLC2 108 + LC4 54) and its right eye has 152
(LPLC2 102 + LC4 50). With the calibrated turn threshold of 0 Hz this lean decides moves on
symmetric input: a gap straight ahead that does not trigger a jump usually becomes a step to the
right. It is the fly's own asymmetry, not ours; the threshold that exposes it is ours. Nothing was
changed because of it.

## Neurons used (coverage)

From `Selection.coverage` (`uv run python -c "from bakeoff.fly import data; from bakeoff.fly.neurons
import load_selection; print(load_selection(data.ANNOTATIONS, data.COMPLETENESS).coverage)"`):

| group | annotated | in model | role |
| --- | --- | --- | --- |
| LPLC2_left | 108 | 108 | input (looming detector) |
| LPLC2_right | 102 | 102 | input (looming detector) |
| LC4_left | 54 | 54 | input (looming detector) |
| LC4_right | 50 | 50 | input (looming detector) |
| DNa01_left | 1 | 1 | read-out (steering) |
| DNa01_right | 1 | 1 | read-out (steering) |
| DNb01_left | 1 | 1 | read-out (steering) |
| DNb01_right | 1 | 1 | read-out (steering) |
| DNp01_left | 1 | 1 | read-out (Giant Fiber) |
| DNp01_right | 1 | 1 | read-out (Giant Fiber) |
| DNa02_left | 1 | 1 | logged only, never decides |
| DNa02_right | 1 | 1 | logged only, never decides |
