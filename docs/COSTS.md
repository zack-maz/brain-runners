# First measured costs (phase 3)

2026-09-20. One track each, practice seed 1000, each player run alone, SDK retries off, code at `89dcb7a`.
Run ids: `20260920-102909` (jev), `20260920-102919` (llm). Runs and the response cache are git-ignored; the
run ids are the paper trail. Before the tracks, `pytest -m live` made one more request per provider.

| player | model | rows survived | live requests | failed requests | mean latency ms | median / max ms | input tokens | output tokens | cost USD | USD per request |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jev | jev-latest | 23 | 24 | 0 | 159 | 150 / 383 | 19,082 (795 per request) | 1,944 (81 per request) | about 0.0008 (estimate) | about 0.00003 (estimate) |
| llm | claude-haiku-4-5-20251001 | 199 | 200 | 0 | 806 | 719 / 2,257 | 109,767 (549 per request) | 1,800 (9 per request) | 0.1188 | 0.00059 |

The LLM's cost is its tokens at 1.00 / 5.00 USD per million input / output tokens. Jev's cost is an
estimate from one console reading: after the run the TypeSafe console showed **29,457 tokens for 0.0011 USD**, a
blended rate of about 0.037 USD per million tokens (0.036 to 0.039, the dollar figure has two digits). Applied to
this track's 21,026 tokens that is about 0.0008 USD, or 0.00003 USD per request: roughly 18 times cheaper per
request than the LLM, and five times faster. Two caveats. The console's token count is higher than what this
project's records add up to (21,026 for the track plus about 880 for the one live-test request, 21,900 in all);
the other 7,500 tokens are either earlier use of the same key or a different way of counting, and no reading was
taken before the run to tell which. And the console gives one figure for all tokens, so separate input and output
prices are not known: the report therefore still shows Jev's `cost_usd` as `-`.

A replay of both players afterwards (`20260920-103208`, no `--max-requests`) made 0 requests, was answered by
24 + 200 cache hits and reproduced both runs row for row: re-runs and replays are free.

## Projection for the tournament

20 seeds, one request per row survived, at most 300 rows per track.

| player | worst case (20 x 300 requests) USD | at the rows survived above USD |
| --- | --- | --- |
| jev | about 0.20 (estimate) | about 0.02 (20 x 24 requests, estimate) |
| llm | 3.56 | 2.38 (20 x 200 requests) |

One track is a weak basis for the second column: a player that survives longer costs more.

## What else the track showed (one track: an impression, not a result)

- **Neither paid player ever jumped.** Jev chose `stay` 23 times and `left` once; the LLM chose `stay` 143,
  `left` 33 and `right` 24 times.
- **Both died by stepping sideways into a gap while `stay` was safe.** Jev's only sideways move was its last: with
  gaps at offsets -1 and 3 in the next row it chose `left` (probabilities left 0.33, jump 0.25, stay 0.21, right
  0.21), that is, into the gap, on the first row where a gap was next to it. The LLM, with gaps at -1, 1, 2 and 3,
  chose `right`. In both cases the solver's `stay` reached the end of the visible window.
- **Jev's two Nouls were almost perfectly calibrated:** Brier 0.0011 for `gap_ahead` and 0.0020 for `left_safe`
  (0 is perfect, 0.25 is what always answering 0.5 scores). It reads the next row correctly when asked directly;
  its Choice did not use that on the row that killed it.
- Agreement with the solver: jev 0.96, llm 0.99. No invalid answers, no provider errors, no fallbacks.
- The prompts stay as they are: they were written before any paid request, and tuning them on what a track showed
  is what the seed rule exists to prevent. The write-up names the observation instead.

## The composed Jev's first recorded track (phase 5a, 2026-09-21)

`uv run python -m bakeoff run --players jev_composed --seeds 1 --seed-start 1000 --max-requests 300`, run
`runs/20260921-120903`, practice seed 1000, status `completed`. Inside the budget of decision 19 (232 of the 1,000
Jev requests pre-authorized for phase 5).

| player | model | rows survived | live requests | failed requests | mean latency ms | median / max ms | input tokens | output tokens | cost USD | USD per request |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jev_composed | jev-latest | 247 | 232 | 0 | 197 | 186 / 681 | 139,650 (602 per request) | 16,936 (73 per request) | about 0.006 (estimate) | about 0.00003 (estimate) |

The cost is the same kind of estimate as above: 156,586 tokens at the blended rate of the one console reading
(29,457 tokens for 0.0011 USD). Four Nouls in one request cost about what the one-shot Jev's Choice and two Nouls
cost, and take about 40 ms longer.

What the track showed (one track: an impression, not a result):

- **It reached the ceiling of its rule.** With perfect answers the pick-the-safest rule survives 246 rows of this
  track and dies where all four landing tiles are gaps one step ahead; the composed Jev died in that same place
  (row 246, all four Nouls between 0.80 and 0.89, the lowest was `jump`, so it counts the row it flew over: 247).
  The one-shot `jev` survived 23 rows of the same track, the LLM 199.
- **One answer in 928 was on the wrong side of 0.5** (spike 02: 1 in 800). Brier: `gap_left` 0.0040, `gap_stay`
  0.0025, `gap_right` 0.0089, `gap_jump` 0.0121. No move landed on a gap that a safe alternative existed for.
- **It wanders.** On a row where every action is safe Jev's four answers differ by a hundredth (0.03 against
  0.04), so rounding to two decimals rarely produces the tie that would make it run straight: 95 of its 232
  moves differ from what perfect answers would have chosen, nearly all of them a sideways step or a jump where
  `stay` was just as safe. None was fatal. The rule is ours and stays as specified; the demo shows the wandering
  and the write-up names it.
- Agreement with the solver 1.00; no invalid answers, no provider errors, no fallbacks.

## The first real go-live (phase 5c, 2026-09-21)

`uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 300`, run
`runs/20260921-132459`, fresh practice seed 1001, status `completed`, watched in a browser. Inside decision 19's
budget: 228 Jev requests (460 of the 1,000 in total) and 92 of the 300 Claude Haiku requests.

| player | model | rows survived | live requests | failed requests | mean latency ms | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fly | (local simulation) | 212 | 0 | 0 | 1,193 per decision (wall clock) | 0 | 0 | 0 |
| jev_composed | jev-latest | 241 | 228 | 0 | 213 | 137,342 | 16,644 | about 0.006 (estimate, as above) |
| llm | claude-haiku-4-5-20251001 | 95 | 92 | 0 | 837 | 50,287 | 828 | 0.0544 |

- **Pace:** 6 minutes 30 seconds from start to end including about a minute to build the fly's brain: a bit more
  than two seconds a row while all three ran (the minds decide one after the other: about 1.2 s for the fly, 0.8 s
  for the LLM, 0.2 s for Jev), one and a half once the LLM had fallen, a quarter of a second once only Jev was left.
- The first rows of every track are the same all-floor runway, so 4 of the LLM's and 3 of Jev's first answers came
  from the cache of track 1000; they are not in the request counts.
- **The live loop plays what the runner plays:** the fly's 185 moves are move for move those of its batch run on
  the same seed two days earlier (`runs/20260919-151934`, also 212 rows).
- **How they ended (one track: an impression, not a result):** the LLM stepped right into a gap at row 95 while
  `stay` was safe. The fly jumped into a gap at row 211. The composed Jev died at row 240 where all four landing
  tiles were gaps, as on track 1000; 3 of its 924 answers were on the wrong side of 0.5 and none of its moves
  landed on a gap while a safe one existed. With perfect answers and no wandering the rule finishes this track,
  so here the wandering (or the three wrong answers) cost it the finish: it reached a dead end that running
  straight avoids.

