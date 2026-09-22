# Item 7: the benchmark (time, cost, performance): design

Date: 2026-09-22 · Status: approved by the user in chat ("both, one report"; "command plus its own HTML now";
design "yes") · Item 7 of `docs/UPDATES.md` · Decision 31 of `docs/DECISIONS.md`

## Goal

One command that answers, from runs already recorded, two questions at once: **which player is better, and how
sure can we be**, and **what each player costs in money and in time for what it scores**. It spends nothing: it
reads run directories. It also says how many seeds a comparison would need, so extra paid runs become a decision
with a number attached, and phase 6 can size the tournament from it.

## Command

`python -m bakeoff bench RUN_DIR[:PLAYER,PLAYER...] ... [--output bench.html] [--pair A,B ...]`

- Each argument is a run directory, optionally followed by `:` and the players to take from it. Update 2a spread
  its players over overlapping directories (for example `runs/20260921-171044` holds an `llm` episode that was cut
  off, and the `llm` of seeds 1001-1004 is complete in `runs/20260921-185546`), so the benchmark needs to pick. A
  named player missing from its directory is a usage error.
- Merging follows `view`: one game (`Rules.same_game`), each (player, seed) from exactly one directory, otherwise a
  usage error naming both directories; the same `schema_version` check.
- Writes `bench.html` (the page) and `bench.json` next to it (the same numbers, for the Analysis tab of item 8 and
  for the write-up), and prints the two tables below to the terminal. `/bench*.html` and `/bench*.json` in the repo
  root are git-ignored, like `/replay*.html`.
- An **incomplete episode** (its last record neither dead nor finished: a run that was stopped or aborted) is left
  out of every number and listed under the tables with its directory, so a stopped run never counts as a death.

## Numbers (`bakeoff/bench.py`, pure, no I/O besides loading)

Per player, over its complete episodes:

| column | meaning |
| --- | --- |
| `seeds` | complete episodes |
| `mean_rows`, `ci_low`, `ci_high` | mean rows survived and its 95% percentile bootstrap interval (resampling seeds, 10,000 draws, `numpy.random.default_rng(0)`, so a rerun prints the same numbers); no interval below 5 seeds (`MIN_SEEDS`) |
| `median_rows`, `finished` | median rows; share of tracks finished |
| `survival` | share of episodes still alive at each row 0 to the track length (a finisher counts at every row) |
| `decisions_per_row` | decisions made / rows survived, over all its episodes (a jump covers two rows) |
| `s_per_decision_median`, `s_per_decision_p90` | seconds per decision: a paid player's `latency_ms` over its **live** decisions (a cache hit records no time); the fly's simulation `info.wall_ms`; "-" for players that record neither (the free baselines) |
| `s_per_row` | mean seconds per decision × `decisions_per_row` |
| `usd_per_decision`, `usd_per_row` | tokens of its live decisions priced by `report.PRICES_USD_PER_MTOK` for the model in `meta.json`, averaged per live decision, × `decisions_per_row`; "-" for an unpriced model (Jev: only a blended console estimate exists, shown as a note from `docs/COSTS.md`, never as a number) and for free players |
| `live_decisions`, `cache_hits` | how many decisions the time and cost columns rest on |

Per pair of players (A, B), over the seeds both completed:

| column | meaning |
| --- | --- |
| `common_seeds` | seeds both played |
| `mean_diff`, `ci_low`, `ci_high` | mean of (A's rows − B's rows) per seed, paired bootstrap 95% interval (same generator) |
| `wins`, `ties`, `losses` | seeds where A survived longer, as long, shorter |
| `verdict` | "A ahead" if the interval is above 0, "B ahead" if below, otherwise "can't tell yet"; with fewer than 5 common seeds "too few seeds (n)" |
| `seeds_needed` | seeds at which the interval would exclude 0 if the difference and its spread stayed as seen: ceil((1.96 · sd / mean_diff)²) with sd the sample standard deviation of the per-seed differences, at least 5; "-" with fewer than 2 common seeds or a mean difference of 0 |

**Why 5 seeds** (found while prototyping on update 2a's runs): a bootstrap of 2 values only returns their range, so
`llm_reader`, on 2 tracks, came out "ahead" of players it had beaten by 13 and 18 rows. Below 5 seeds there is no
interval and no verdict, and the page says why.

By default every pair among the players is reported; `--pair A,B` (repeatable) limits the terminal table, the page
shows all. `seeds_needed` is an estimate from the seeds seen so far and the page says so.

## The page (`viewer/bench.html`, `viewer/bench.js`, `viewer/bench_app.js`)

One offline file built like the replay: `bakeoff/view.py`'s inliner (stylesheets with their fonts as base64,
scripts inline, the data as JSON through `embed_json`), generalised to take the page's file name. Brand as in
`CLAUDE.md`: tokens from `viewer/viewer.css`, blue only for the player in focus, mono for short labels only. No
chart library: SVG drawn by the page.

- **Players table**: the per-player columns, sorted by mean rows, the interval drawn as a bar.
- **Survival curves**: one line per player in grey, the player in focus in blue with its name at the line's end;
  clicking a row of the players table or a line sets the focus.
- **Rows against cost** and **rows against time**: one point per player (x: USD per row or seconds per row, log
  scale; y: mean rows with its interval as a whisker). Players without a price or a time sit in a separate strip
  labelled "no price" or "no time recorded", never at 0.
- **Pairs**: a table of the pairwise rows, each verdict in words.
- **Notes**, always shown: the incomplete episodes left out; "time and cost come from live decisions only"; the Jev
  price note; "seeds needed is an estimate from the seeds seen so far"; the game version and the directories read.

The pure parts (scales, tick values, the survival path, the log scale, the verdict text) are in `viewer/bench.js`
and tested by `viewer/tests/bench.test.js` through `node --test`, like the replay viewer. Everything taken from a
log (player names, directory names) is escaped.

## Not in scope

No new runs and no spending; no change to `report` or `view` behaviour; no statistics beyond the above (no survival
model fitting, no multiple-comparison correction: with at most about ten players the page states the pairs'
intervals, not a ranking claim). The Analysis tab (item 8) reuses `bench.json` later.

## Testing

`bench.py` against hand-made step records: bootstrap reproducibility, a known interval on a constant sample, the
verdicts, `seeds_needed`, incomplete episodes left out, the `dir:players` selection and its errors, the merge
errors, time from live decisions and from the fly's `wall_ms`, cost priced and "-". The CLI end to end on a
free run (`solver,random`), writing both files. `view.py`'s inliner with a second page. JavaScript: the pure
functions. No test touches the network.

## Docs kept current

README (the command), `CLAUDE.md` (status), `docs/NEXT.md` and `docs/UPDATES.md` (item 7 built), the Open item
about scoring several directories closed, and the update 2a scoreboard in `docs/COSTS.md` regenerated by the command
instead of the throwaway script.
