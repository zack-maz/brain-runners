# Fly: first results with the real brain

Constants from `calibration/REPORT.md` (ours, not the fly's biology), real Brian2 brain, one
decision per 100 ms window, input noise seeded per (track seed, row) so these runs repeat exactly.

On check seeds 1000-1019 the real brain averaged 117.95 rows; the stand-in brain used for
calibration predicted 118.70 (ratio 0.99).

## Check seeds 1000-1019 (practice)

| player | runs | incomplete | missing | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | jump_share | solver_agreement | fallback_rate | invalid_rate | error_rate | requests | mean_latency_ms | input_tokens | output_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fly | 20 | 0 | 0 | 117.95 | 113.00 | 0 | 0 | 20 | 0 | 0.08 | 0.99 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |

## First scoreboard, seeds 0-19

| player | runs | incomplete | missing | mean_rows | median_rows | finished | ran_into_gap | jumped_into_gap | dodged_into_gap | jump_share | solver_agreement | fallback_rate | invalid_rate | error_rate | requests | mean_latency_ms | input_tokens | output_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_jump | 20 | 0 | 0 | 47.80 | 39.00 | 0 | 0 | 20 | 0 | 1.00 | 0.96 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| fly | 20 | 0 | 0 | 126.70 | 124.00 | 0 | 0 | 20 | 0 | 0.08 | 0.99 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| random | 20 | 0 | 0 | 34.70 | 30.00 | 0 | 8 | 4 | 8 | 0.26 | 0.96 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |
| solver | 20 | 0 | 0 | 299.70 | 300.00 | 19 | 1 | 0 | 0 | 0.02 | 1.00 | 0.00 | 0.00 | 0.00 | 0 | - | 0 | 0 |

`always_jump` is the floor for a jump-heavy player, `random` the floor for everything else, `solver`
the reference (same 6-row, ±3-lane view; not a contestant).
