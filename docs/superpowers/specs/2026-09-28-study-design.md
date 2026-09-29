# The study: which mind performs best for its cost and speed: design

Date: 2026-09-28 · Status: designed with the user in chat, written for their review (decision 53) · Replaces the
tournament of the original design (`2026-09-19-tunnel-run-design.md`, build order step 6): there is no tournament
any more, no brackets, no event. Phase 6 is this study.

## Goal

A research project: which mind (Jev, Claude Haiku, GLM Flash, the fly, fly2, the yardsticks) performs best **for its
cost and its speed**. The output is data accurate enough for a write-up, shown in Brain Run (a new Charts tab) and in
one report page that the user will later rewrite in their own words.

The user, 2026-09-28: "this should now turn into a research project where we're seeing what performs best at cost
and speed"; "the important [thing] is getting hella runs in and getting accurate data for the writeup/report".

## 1. The data

- **Held-out tracks: seeds 100–199**, game v2 (150 rows). No player was tuned on them and none has played them (seeds
  0–19 carry v1 history under the same numbers, so they are avoided).
- **Who plays which tracks:**

  | players | tracks | cost |
  |---|---|---|
  | Jev ×5, fly, fly2, solver, random, always jump | all 100 (100–199) | free; about 5 hours, one fly process at a time |
  | Claude Haiku ×5 | the first 15 (100–114) | at most 23.85 USD, guaranteed by `--max-requests 2250` (15 × 150 rows) |
  | GLM Flash ×5 | the first 15 (100–114), **only if** the drain shows under 2% failed decisions over at least 5 practice tracks for all five skins | free (0 USD, `glm-4.5-flash`); otherwise out, and the report says why with the drain's numbers |

- Every comparison uses only the tracks both players ran (as `bakeoff bench` already does), so Haiku or GLM against
  anyone rests on 15 tracks and free against free on 100. The report says so beside every comparison.
- Budget: the user buys about 25 USD of Anthropic API credit (pay as you go; a Claude subscription does not cover
  API use). Jev's requests cost the user nothing (decision 50). GLM Flash costs 0 USD; its limit is the free tier's
  throttle, which the drain on practice tracks 1001–1019 (started 2026-09-28) measures.

## 2. What is measured, per player

All from the recorded runs, by the benchmark (`bakeoff/bench.py`), which Records, `bakeoff bench` and the page
already use: one source of numbers, so the Charts tab, `bench.html` and the report cannot disagree.

| measure | definition |
|---|---|
| performance | mean rows survived, 95% t interval, share of tracks finished |
| cost | USD per track and per decision at the listed price (`session.PRICE_USD`: measured, rounded up); cached answers are counted at full price, so a replay never looks cheaper. Jev at its estimated price (free to the user, said so); GLM, the flies and the bots at 0 |
| speed | median and mean seconds per decision (live decisions only), and seconds per track |
| reliability | failed-decision rate (errors and invalid answers), beside performance |

`player_numbers` already has `s_per_row` and `usd_per_row`; the study adds the per-decision median, cost per track
at full price, and reliability where missing.

## 3. The verdict: trade-off charts, plus named scores

- **Two charts:** rows survived against USD per track, and rows survived against seconds per decision. Each marks
  its **frontier**: the players no other player beats on both axes. No single winner is declared.
- **Named scores, as extras, never as the verdict:** rows per cent, and rows per second of thinking. A free player
  shows "free" instead of a division by zero.
- The report then answers questions such as "best under 1 cent a track" or "best under 200 ms a decision".

## 4. The page: Records stays the log, Charts holds the data

- **Records** is the historical log: past runs (newest first, Watch and Results), as now. There is no practice and
  evaluation split.
- **Charts**, a new screen reached from home beside Records, holds all the data: every recorded v2 episode (newest
  per player and track), the performance table with intervals, the head to head, the two trade-off charts with
  their frontiers, and the named scores. fly2's tracks it was tuned on (1000–1199) stay marked, as decision 46 does
  today.
- The server gives the numbers (a read-only route behind the token, like `/records`); the page only draws them.
  `bakeoff bench` writes the same charts into its offline `bench.html`.

## 5. The report and the Writeup page are one

- One **Writeup** page in Brain Run (from home, beside Records and Charts), and its source in `docs/`. For now
  Claude writes it as a draft, marked as a draft on the page; the user will later rewrite it entirely in their own
  words (FRONTEND.md, "Later: the Writeup page").
- The draft carries: the question, the method (held-out seeds, who played what, prices), the charts and tables,
  how many tracks each comparison rests on, GLM's in-or-out with the drain's numbers, and everything
  `docs/NEXT.md` lists under "What the write-up must carry" (what is ours; the differences between Jev and the chat
  models; the fly's input is ours; spike 03's and spike 05's results).
- Its numbers come from the benchmark; it never types a number the data does not give.

## 6. Running it

- The existing `bakeoff run`, in batches of 25 tracks so progress shows and a failure costs little; the flies in a
  batch of their own. The drop-out rule (decision 52) applies.
- **The seed flag is renamed** from `--tournament` to `--held-out` (the gate that lets paid players onto seeds below
  1000); the session's refusal text and `--help` follow. `FIRST_PRACTICE_SEED` and the rule itself are unchanged.
- **Haiku runs last**, only after the user has bought the credit and given the go-ahead, with the exact command and
  its worst case shown first.

## 7. Testing

Fast tests, no network:
- the benchmark's new numbers on hand-made step records: cost per track at full price, seconds per decision
  (median), reliability, the frontier (ties, free players, one player), the named scores;
- the Charts route (including a failure answered with a reason, like the benchmark's `benchmark_of`);
- the Charts and Writeup screens: rendering and escaping of every string (`Minds.esc`);
- the `--held-out` rename in the CLI, the session and `--help`;
- by hand: one small free batch played end to end and the Charts tab looked at in a browser before the full runs.

## 8. Order

1. The code (Charts, the benchmark's additions, the rename, the Writeup page with an empty draft), as one plan,
   prototyped and reviewed.
2. The free runs: 100 tracks.
3. GLM's decision, from the drain.
4. The Haiku runs, after the credit and the go-ahead.
5. The Writeup draft, from the numbers.

## Open for the user's review of this spec

- Charts uses all recorded v2 data, as asked. fly2's tuned tracks are marked but counted; the practice tracks
  1000–1019 have been played many times by some players and never by others. Every pair still compares only the
  tracks both ran, but a player's overall mean mixes held-out and practice tracks. The alternative is for Charts to
  compute only on 100–199 by default. Left as asked unless the user changes it.
