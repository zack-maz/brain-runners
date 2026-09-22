# Measured runs and costs

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

## Projection for the tournament (phase 3, game v1: at most 300 rows a track)

20 seeds, one request per row survived, at most 300 rows per track.

| player | worst case (20 x 300 requests) USD | at the rows survived above USD |
| --- | --- | --- |
| jev | about 0.20 (estimate) | about 0.02 (20 x 24 requests, estimate) |
| llm | 3.56 | 2.38 (20 x 200 requests) |

One track is a weak basis for the second column: a player that survives longer costs more.

This projection is phase 3's, on game v1 (300 rows a track). On v2 (150 rows a track, this file's `llm` rate of
0.00059 USD a request) the one-shot LLM's worst case for 20 tracks is about 1.78 USD (20 x 150 requests); the
priciest twin, `llm_reader` (about 0.0063 USD a row, "Update 2a" above), would be about 19 USD for 20 x 150 rows.

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

`uv run python -m bakeoff run --players jev_composed --seeds 1 --seed-start 1000 --max-requests 300` (game v1: now
needs `--game v1`), run `runs/20260921-120903`, practice seed 1000, status `completed`. Inside the budget of
decision 19 (232 of the 1,000 Jev requests pre-authorized for phase 5).

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

`uv run python -m bakeoff live --seed 1001 --players fly,jev_composed,llm --max-requests 300` (game v1: now needs
`--game v1`), run `runs/20260921-132459`, fresh practice seed 1001, status `completed`, watched in a browser. Inside
decision 19's budget: 228 Jev requests (460 of the 1,000 in total) and 92 of the 300 Claude Haiku requests.

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


## Update 2a: the Jev family and its LLM twins (game v2, 2026-09-21, paid runs done)

Inside decision 26: Claude Haiku at most 5.00 USD for update 2, v2 practice seeds 1000 and up only. **Spent: 3.85
USD of Haiku** (run 1: 1.38; run 2: 0.044; run 3: 0.126; run 4: 1.37; run 5: 0.93), 1.15 USD of the budget left. Jev's cost is not known per request (see above);
the user does not count it.

**Run 1** (`runs/20260921-165433`, seed 1000, every paid player, cap 150 each, `completed`):

| player | rows (of 150) | live requests | mean latency ms | input tokens | output tokens | cost USD | Brier (all Nouls) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| jev_composed | 150, finished | 128 | 201 | 78,063 | 9,344 | - | 0.011 |
| jev_two_step | 150, finished | 136 | 208 | 124,070 | 19,856 | - | 0.007 |
| jev_choice | 94 | 81 | 204 | 68,752 | 3,645 | - | - |
| jev_reader | 38 | 39 | 223 | 79,692 | 32,682 | - | 0.005 |
| llm (one-shot) | 93 | 85 | 740 | 47,209 | 765 | 0.051 | - |
| llm_composed | 132 | 131 | 939 | 107,816 | 4,586 | 0.130 | 0.019 |
| llm_choice | 93 | 92 | 750 | 71,435 | 828 | 0.076 | - |
| llm_two_step | 95 | 95 | 1,700 | 119,115 | 6,321 | 0.150 | 0.013 |
| llm_reader | 150, finished | 150 | 2,991 | 596,551 | 74,986 | 0.970 | 0.003 |

**Run 2** (`runs/20260921-171044`, seeds 1001–1004, cap 600 each, `aborted` on Anthropic connection errors while
the API was down): all four Jev players completed all four tracks; `llm` was cut on 1001; the other LLM twins did
not start. Jev over the five tracks 1000–1004 (runs 1 and 2 together):

| player | mean rows (of 150) | finished | Brier |
| --- | --- | --- | --- |
| jev_two_step | 144.6 | 4 of 5 | 0.007 |
| jev_composed | 124.2 | 2 of 5 | 0.008–0.011 |
| jev_choice | 78.2 | 0 of 5 | - |
| jev_reader | 49.6 | 0 of 5 | 0.005–0.009 |

**Run 3** (`runs/20260921-184858`, seeds 1001–1004, the four cheaper LLM twins, cap 600 each): stopped by the
controller at the user's request before a context reset (its `meta.json` still says `running`: a hard stop, the
known gap of the phase 5 review). `llm` finished its four tracks (mean 47.5 rows), `llm_choice` had played part of
1001; `llm_composed` and `llm_two_step` had not started. Everything answered is cached: rerunning the same command
replays it for free and continues.

**Run 4** (`runs/20260921-185546`, seeds 1001–1004, the four cheaper LLM twins, cap 600 each, `completed`, no
error or fallback): run 3's answers replayed from the cache (`llm` entirely). Live: `llm_choice` 190 requests (0.16
USD), `llm_composed` 516 (0.51), `llm_two_step` 443 (0.70); mean latency 700–990 ms.

**Run 5** (`runs/20260921-191326`, seed 1001, `llm_reader`, cap 150, `completed`): 150 rows, finished; 144 requests,
2,863 ms mean latency, 573,101 input and 71,729 output tokens, 0.93 USD.

**Run 6** (`runs/20260921-192037`, seeds 1000–1004, the fly, free, `completed`): mean 68.0 rows, median 64, none
finished, all five deaths jumps into a gap. This is the v1-calibrated fly on v2 (decision 23) and matches the stand-in
brain's 68-row average of decision 21.

**All players over v2 practice seeds 1000–1004** (`llm_reader` on 1000–1001 only, decision 26; each (player, seed)
taken from exactly one of runs 1, 2, 4, 5, 6; deaths are "ran into / jumped into / dodged into" a gap):

| player | tracks | mean rows | median | finished | deaths ran / jumped / dodged | Brier (all Nouls) |
| --- | --- | --- | --- | --- | --- | --- |
| llm_reader | 2 | 150.0 | 150 | 2 of 2 | - | 0.003 |
| jev_two_step | 5 | 144.6 | 150 | 4 of 5 | 0 / 1 / 0 | 0.007 |
| llm_composed | 5 | 132.2 | 132 | 1 of 5 | 4 / 0 / 0 | 0.017 |
| jev_composed | 5 | 124.2 | 146 | 2 of 5 | 0 / 3 / 0 | 0.009 |
| llm_two_step | 5 | 109.6 | 107 | 1 of 5 | 1 / 0 / 3 | 0.020 |
| jev_choice | 5 | 78.2 | 94 | 0 of 5 | 0 / 5 / 0 | - |
| llm_choice | 5 | 72.6 | 73 | 0 of 5 | 0 / 2 / 3 | - |
| fly | 5 | 68.0 | 64 | 0 of 5 | 0 / 5 / 0 | - |
| llm (one-shot) | 5 | 56.6 | 52 | 0 of 5 | 2 / 0 / 3 | - |
| jev_reader | 5 | 49.6 | 45 | 0 of 5 | 5 / 0 / 0 | 0.008 |

(Yardsticks on the same game, `runs/20260921-155758`: solver 150, always-jump 39, random 24.)

What these five tracks suggest (an impression, not a result): looking two moves ahead is where the rows are, but
only when the answers are sharp: `jev_two_step` finishes 4 of 5, while its Haiku twin, asked the same questions under
the same rule, averages 110 rows with a Brier nearly three times Jev's, and falls below its own one-step twin. On
the pointed question sets Jev's answers score the better Brier of the two models (0.007–0.009 against 0.017–0.020);
on the reader set it is the other way round (`llm_reader` 0.003 finishes both its tracks, `jev_reader` dies in every
track). The one-shot Choice is weak for both models. `llm_reader` is the priciest player by far (about 0.0063 USD
and 3 s a row).

What the comparison between the models must carry (final review of update 2a):

- The model is not the only difference. The LLM twin is also given the briefing of the rules in its system prompt;
  Jev's yes/no questions carry only the question (the choice set gives the briefing to both). Jev's answers in one
  request are made in parallel and cannot see each other (decision 11); the LLM writes all of its answers in one
  reply, each able to see the ones before it. And an LLM probability is a number it states, while Jev's is Jev's
  probability. The Brier numbers above compare these two kinds of number.
- `brier_all` compares the two models within one set, not sets with each other: about 90% of the reader's tiles are
  floor, so `jev_reader` scores 0.008 while dying on every track.
- `jev_reader`'s five deaths are one event: the tile straight ahead (`tile_r1_c`) read as floor (p 0.09–0.19) while it
  is a gap, and the planner stays. Jev missed 35 of 80 gaps at offset 0 (44%) and 81 of 763 elsewhere (11%), and read
  no floor as a gap (0 of 9,783); `llm_reader` missed 1 of 274 and 13 of 2,119. The composed wording for the same tile
  (`gap_stay`) was never missed in 73 cases, so it is the reader's wording or the 42-question request that fails, not
  Jev's reading of the track.
