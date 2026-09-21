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
