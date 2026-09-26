> Names: these runs were recorded under the players' old names (`llm*` until decision 39, then `jev`, `haiku`,
> `jev_composed`, `jev_choice`, `haiku_two_step`, `haiku_reader` and the like until decision 44). This file uses the
> names of today (`jev_plain`, `haiku_plain`, `jev_step1`, `jev_guided`, `haiku_step2`, `haiku_map`, ...); the run
> directories keep their old file names and the tool reads them, and the cached answers, as the new names.

2026-09-20. One track each, practice seed 1000, each player run alone, SDK retries off, code at `89dcb7a`.
Run ids: `20260920-102909` (jev_plain), `20260920-102919` (haiku_plain). Runs and the response cache are git-ignored; the
run ids are the paper trail. Before the tracks, `pytest -m live` made one more request per provider.

| player | model | rows survived | live requests | failed requests | mean latency ms | median / max ms | input tokens | output tokens | cost USD | USD per request |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jev_plain | jev-latest | 23 | 24 | 0 | 159 | 150 / 383 | 19,082 (795 per request) | 1,944 (81 per request) | about 0.0008 (estimate) | about 0.00003 (estimate) |
| haiku_plain | claude-haiku-4-5-20251001 | 199 | 200 | 0 | 806 | 719 / 2,257 | 109,767 (549 per request) | 1,800 (9 per request) | 0.1188 | 0.00059 |

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
| jev_plain | about 0.20 (estimate) | about 0.02 (20 x 24 requests, estimate) |
| haiku_plain | 3.56 | 2.38 (20 x 200 requests) |

One track is a weak basis for the second column: a player that survives longer costs more.

This projection is phase 3's, on game v1 (300 rows a track). On v2 (150 rows a track, this file's `haiku_plain` rate of
0.00059 USD a request) `haiku_plain`'s worst case for 20 tracks is about 1.78 USD (20 x 150 requests); the
priciest twin, `haiku_map` (about 0.0063 USD a row, "Update 2a" above), would be about 19 USD for 20 x 150 rows.

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
- Agreement with the solver: jev_plain 0.96, haiku_plain 0.99. No invalid answers, no provider errors, no fallbacks.
- The prompts stay as they are: they were written before any paid request, and tuning them on what a track showed
  is what the seed rule exists to prevent. The write-up names the observation instead.

## `jev_step1`'s first recorded track (phase 5a, 2026-09-21)

`uv run python -m bakeoff run --players jev_step1 --seeds 1 --seed-start 1000 --max-requests 300` (game v1: now
needs `--game v1`), run `runs/20260921-120903`, practice seed 1000, status `completed`. Inside the budget of
decision 19 (232 of the 1,000 Jev requests pre-authorized for phase 5).

| player | model | rows survived | live requests | failed requests | mean latency ms | median / max ms | input tokens | output tokens | cost USD | USD per request |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jev_step1 | jev-latest | 247 | 232 | 0 | 197 | 186 / 681 | 139,650 (602 per request) | 16,936 (73 per request) | about 0.006 (estimate) | about 0.00003 (estimate) |

The cost is the same kind of estimate as above: 156,586 tokens at the blended rate of the one console reading
(29,457 tokens for 0.0011 USD). Four Nouls in one request cost about what `jev_plain`'s Choice and two Nouls
cost, and take about 40 ms longer.

What the track showed (one track: an impression, not a result):

- **It reached the ceiling of its rule.** With perfect answers the pick-the-safest rule survives 246 rows of this
  track and dies where all four landing tiles are gaps one step ahead; `jev_step1` died in that same place
  (row 246, all four Nouls between 0.80 and 0.89, the lowest was `jump`, so it counts the row it flew over: 247).
  `jev_plain` survived 23 rows of the same track, the LLM 199.
- **One answer in 928 was on the wrong side of 0.5** (spike 02: 1 in 800). Brier: `gap_left` 0.0040, `gap_stay`
  0.0025, `gap_right` 0.0089, `gap_jump` 0.0121. No move landed on a gap that a safe alternative existed for.
- **It wanders.** On a row where every action is safe Jev's four answers differ by a hundredth (0.03 against
  0.04), so rounding to two decimals rarely produces the tie that would make it run straight: 95 of its 232
  moves differ from what perfect answers would have chosen, nearly all of them a sideways step or a jump where
  `stay` was just as safe. None was fatal. The rule is ours and stays as specified; the demo shows the wandering
  and the write-up names it.
- Agreement with the solver 1.00; no invalid answers, no provider errors, no fallbacks.

## The first real go-live (phase 5c, 2026-09-21)

`uv run python -m bakeoff live --seed 1001 --players fly,jev_step1,haiku_plain --max-requests 300` (game v1: now needs
`--game v1`), run `runs/20260921-132459`, fresh practice seed 1001, status `completed`, watched in a browser. Inside
decision 19's budget: 228 Jev requests (460 of the 1,000 in total) and 92 of the 300 Claude Haiku requests.

| player | model | rows survived | live requests | failed requests | mean latency ms | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fly | (local simulation) | 212 | 0 | 0 | 1,193 per decision (wall clock) | 0 | 0 | 0 |
| jev_step1 | jev-latest | 241 | 228 | 0 | 213 | 137,342 | 16,644 | about 0.006 (estimate, as above) |
| haiku_plain | claude-haiku-4-5-20251001 | 95 | 92 | 0 | 837 | 50,287 | 828 | 0.0544 |

- **Pace:** 6 minutes 30 seconds from start to end including about a minute to build the fly's brain: a bit more
  than two seconds a row while all three ran (the minds decide one after the other: about 1.2 s for the fly, 0.8 s
  for the LLM, 0.2 s for Jev), one and a half once the LLM had fallen, a quarter of a second once only Jev was left.
- The first rows of every track are the same all-floor runway, so 4 of the LLM's and 3 of Jev's first answers came
  from the cache of track 1000; they are not in the request counts.
- **The live loop plays what the runner plays:** the fly's 185 moves are move for move those of its batch run on
  the same seed two days earlier (`runs/20260919-151934`, also 212 rows).
- **How they ended (one track: an impression, not a result):** the LLM stepped right into a gap at row 95 while
  `stay` was safe. The fly jumped into a gap at row 211. `jev_step1` died at row 240 where all four landing
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
| jev_step1 | 150, finished | 128 | 201 | 78,063 | 9,344 | - | 0.011 |
| jev_step2 | 150, finished | 136 | 208 | 124,070 | 19,856 | - | 0.007 |
| jev_guided | 94 | 81 | 204 | 68,752 | 3,645 | - | - |
| jev_map | 38 | 39 | 223 | 79,692 | 32,682 | - | 0.005 |
| haiku_plain | 93 | 85 | 740 | 47,209 | 765 | 0.051 | - |
| haiku_step1 | 132 | 131 | 939 | 107,816 | 4,586 | 0.130 | 0.019 |
| haiku_guided | 93 | 92 | 750 | 71,435 | 828 | 0.076 | - |
| haiku_step2 | 95 | 95 | 1,700 | 119,115 | 6,321 | 0.150 | 0.013 |
| haiku_map | 150, finished | 150 | 2,991 | 596,551 | 74,986 | 0.970 | 0.003 |

**Run 2** (`runs/20260921-171044`, seeds 1001–1004, cap 600 each, `aborted` on Anthropic connection errors while
the API was down): all four Jev players completed all four tracks; `haiku_plain` was cut on 1001; the other LLM twins did
not start. Jev over the five tracks 1000–1004 (runs 1 and 2 together):

| player | mean rows (of 150) | finished | Brier |
| --- | --- | --- | --- |
| jev_step2 | 144.6 | 4 of 5 | 0.007 |
| jev_step1 | 124.2 | 2 of 5 | 0.008–0.011 |
| jev_guided | 78.2 | 0 of 5 | - |
| jev_map | 49.6 | 0 of 5 | 0.005–0.009 |

**Run 3** (`runs/20260921-184858`, seeds 1001–1004, the four cheaper LLM twins, cap 600 each): stopped by the
controller at the user's request before a context reset (its `meta.json` still says `running`: a hard stop, the
known gap of the phase 5 review). `haiku_plain` finished its four tracks (mean 47.5 rows), `haiku_guided` had played part of
1001; `haiku_step1` and `haiku_step2` had not started. Everything answered is cached: rerunning the same command
replays it for free and continues.

**Run 4** (`runs/20260921-185546`, seeds 1001–1004, the four cheaper LLM twins, cap 600 each, `completed`, no
error or fallback): run 3's answers replayed from the cache (`haiku_plain` entirely). Live: `haiku_guided` 190 requests (0.16
USD), `haiku_step1` 516 (0.51), `haiku_step2` 443 (0.70); mean latency 700–990 ms.

**Run 5** (`runs/20260921-191326`, seed 1001, `haiku_map`, cap 150, `completed`): 150 rows, finished; 144 requests,
2,863 ms mean latency, 573,101 input and 71,729 output tokens, 0.93 USD.

**Run 6** (`runs/20260921-192037`, seeds 1000–1004, the fly, free, `completed`): mean 68.0 rows, median 64, none
finished, all five deaths jumps into a gap. This is the v1-calibrated fly on v2 (decision 23) and matches the stand-in
brain's 68-row average of decision 21.

**All players over v2 practice seeds 1000–1004** (`haiku_map` on 1000–1001 only, decision 26; each (player, seed)
taken from exactly one of runs 1, 2, 4, 5, 6; deaths are "ran into / jumped into / dodged into" a gap):

| player | tracks | mean rows | median | finished | deaths ran / jumped / dodged | Brier (all Nouls) |
| --- | --- | --- | --- | --- | --- | --- |
| haiku_map | 2 | 150.0 | 150 | 2 of 2 | - | 0.003 |
| jev_step2 | 5 | 144.6 | 150 | 4 of 5 | 0 / 1 / 0 | 0.007 |
| haiku_step1 | 5 | 132.2 | 132 | 1 of 5 | 4 / 0 / 0 | 0.017 |
| jev_step1 | 5 | 124.2 | 146 | 2 of 5 | 0 / 3 / 0 | 0.009 |
| haiku_step2 | 5 | 109.6 | 107 | 1 of 5 | 1 / 0 / 3 | 0.020 |
| jev_guided | 5 | 78.2 | 94 | 0 of 5 | 0 / 5 / 0 | - |
| haiku_guided | 5 | 72.6 | 73 | 0 of 5 | 0 / 2 / 3 | - |
| fly | 5 | 68.0 | 64 | 0 of 5 | 0 / 5 / 0 | - |
| haiku_plain | 5 | 56.6 | 52 | 0 of 5 | 2 / 0 / 3 | - |
| jev_map | 5 | 49.6 | 45 | 0 of 5 | 5 / 0 / 0 | 0.008 |

(Yardsticks on the same game, `runs/20260921-155758`: solver 150, always-jump 39, random 24.)

The same scoreboard with 95% intervals, time and cost per row and every pair (2026-09-22, the benchmark of item 7):
`uv run python -m bakeoff bench runs/20260921-165433 "runs/20260921-171044:jev_step1,jev_guided,jev_step2,jev_map" runs/20260921-185546 runs/20260921-191326 runs/20260921-192037`. With 95% paired t intervals over five tracks (decision 32) it separates, among others, `jev_step2` from its
Haiku twin `haiku_step2` (+35.0 rows, interval 2.0 to 68.0, 4 wins, 1 tie, 0 losses) and from the fly (+76.6, 37.7
to 115.5). It cannot yet tell `haiku_step1` from `haiku_step2` (+22.6, -7.1 to 52.3; about 9 tracks for an 80%
chance of a verdict), `jev_step2` from `haiku_step1` (+12.4, about 31) nor `jev_step1` from `haiku_step1`
(+8.0 for Haiku, about 152). These are 36 pairs at 95% each, so about 2 verdicts would come by chance alone: read
each as a lead. `haiku_map`, on 2 tracks, gets no interval, no verdict and no rank. Per row: `haiku_map` 2.88 s and 0.0064 USD, the other
Haiku twins 0.7 to 1.1 s and 0.0008 to 0.0016 USD, the Jev players 0.17 to 0.23 s (price unknown), the fly 0.66 s.

What these five tracks suggest (an impression, not a result): looking two moves ahead is where the rows are, but
only when the answers are sharp: `jev_step2` finishes 4 of 5, while its Haiku twin, asked the same questions under
the same rule, averages 110 rows with a Brier nearly three times Jev's, and falls below its own one-step twin. On
the pointed question sets Jev's answers score the better Brier of the two models (0.007–0.009 against 0.017–0.020);
on the map set it is the other way round (`haiku_map` 0.003 finishes both its tracks, `jev_map` dies in every
track). The plain set's one Choice is weak for both models. `haiku_map` is the priciest player by far (about 0.0063 USD
and 3 s a row).

What the comparison between the models must carry (final review of update 2a):

- The model is not the only difference. The LLM twin is also given the briefing of the rules in its system prompt;
  Jev's yes/no questions carry only the question (the guided set gives the briefing to both). Jev's answers in one
  request are made in parallel and cannot see each other (decision 11); the LLM writes all of its answers in one
  reply, each able to see the ones before it. And an LLM probability is a number it states, while Jev's is Jev's
  probability. The Brier numbers above compare these two kinds of number.
- `brier_all` compares the two models within one set, not sets with each other: about 90% of the map set's tiles are
  floor, so `jev_map` scores 0.008 while dying on every track.
- `jev_map`'s five deaths are one event: the tile straight ahead (`tile_r1_c`) read as floor (p 0.09–0.19) while it
  is a gap, and the planner stays. Jev missed 35 of 80 gaps at offset 0 (44%) and 81 of 763 elsewhere (11%), and read
  no floor as a gap (0 of 9,783); `haiku_map` missed 1 of 274 and 13 of 2,119. The step1 wording for the same tile
  (`gap_stay`) was never missed in 73 cases, so it is the map set's wording or the 42-question request that fails, not
  Jev's reading of the track.

## Item 10: the GLM Flash twins (game v2, 2026-09-22, parked)

Free tier (`glm-4.5-flash`, 0 USD), so the cost of these runs is nothing; what limits them is the tier's throttle.
Two fixes came out of the first requests: GLM-4.5 thinks by default and its thoughts spent the whole token budget
(empty, cut-off replies), and asked only for "an object" it wrapped its answer (`{"answer": {...}}`), which made
every `glm_guided` decision invalid. It now answers with thinking off and with the same JSON schema Claude Haiku
gets, inside a markdown fence that both chat models' reader strips.

**Track 1000** (`runs/20260922-110347`, cap 150 each, `completed`; no invalid answer):

| player | rows (of 150) | live requests | failed decisions | mean latency ms | input tokens | output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| glm_step1 | 109 | 103 | 4.6% | 5,496 | 58,754 | 3,595 |
| glm_step2 | 74 | 73 | 2.7% | 4,196 | 64,381 | 6,030 |
| glm_guided | 73 | 71 | 0% | 1,157 | 41,435 | 810 |
| glm_map | 38 | 34 | 13% | 14,151 | 74,889 | 12,832 |

On the same track: `jev_step1` 150, `haiku_step1` 132, `jev_step2` 150, `haiku_step2` 95, `jev_guided` 94,
`haiku_guided` 93, `jev_map` 38, `haiku_map` 150.

**Tracks 1001–1004 are not run** (`runs/20260922-113159`, `aborted`): the free tier began answering "the service
may be temporarily overloaded" (HTTP 429) to nearly every request, and the run's circuit breaker stopped it after
six in a row. A plain probe then got 1 request through in 5. GLM now backs off 5, 20 and 60 seconds and each retry
spends from the cap, so a throttled run waits instead of burning it. Parked by the user on 2026-09-22 (decision 34);
track 1000 stands as its record.

A failed decision is a logged error and a `stay`, which can kill a player on a bad row: GLM's rows above are a
floor, not its ability. The benchmark shows it but does not rank it, since a rank needs five tracks.

## fly2: the second pure fly (game v2, 2026-09-25, free)

fly2 is a local simulation like the fly: the response surfaces, the calibration and the real run below all cost
nothing (`calibration/FLY2_REPORT.md`, decision 43).

**Real run** (`uv run python -m bakeoff run --players fly,fly2 --seeds 20 --seed-start 1000`, `runs/20260925-101614`,
game v2, `completed`, 22 minutes wall):

| player | mean rows | median | finished | deaths jumped / dodged into a gap | median wall time per decision |
| --- | --- | --- | --- | --- | --- |
| fly | 66.55 | 70 | 0 of 20 | 20 / 0 | 489 ms |
| fly2 | 78.20 | 78 | 1 of 20 | 16 / 3 | 495 ms |

The stand-in brain (the measured response surfaces, no simulation) predicted 72.00 rows for fly2 on these same
seeds, against the 78.20 the real brain scored.

`bakeoff bench` on the same run: fly2 minus fly is +11.7 rows (95% interval -4.5 to 27.8, 12 wins / 3 ties / 5
losses) — "can't tell yet"; about 69 tracks would be needed for a verdict.

**The settle run** (`uv run python -m bakeoff run --players fly,fly2 --seeds 100 --seed-start 1400`,
`runs/20260925-163957`, game v2, `completed`, about 2 h 10 min wall). Seeds 1400–1499 were never used by either fly's
calibration (fly2's rule saw 1000–1199 and scored its winner on 1200–1399), so this is fly2's first test on tracks
nothing of ours was fitted to:

| player | mean rows | 95% interval | median | finished | deaths jumped / dodged into a gap | s per row |
| --- | --- | --- | --- | --- | --- | --- |
| fly | 66.02 | 61.5 to 70.6 | 68 | 0 of 100 | 99 / 1 | 0.46 |
| fly2 | 79.45 | 72.6 to 86.3 | 79 | 8 of 100 | 61 / 31 | 0.53 |

`bakeoff bench`: fly2 minus fly is **+13.4 rows (95% interval 5.3 to 21.6), 63 wins / 4 ties / 33 losses —
"fly2 ahead"**. The question left open by the 20-track run is settled: fly2 is the better pure fly. Its deaths
change kind: fly dies by jumping into a gap, fly2 a third of the time by dodging into one (the rule dodges before
it jumps, and a dodge does not look where it lands).
