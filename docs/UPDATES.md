# Updates requested on 2026-09-21

The user's list of changes after phase 5 was merged, recorded as given, each with where the project stands today
and the questions to settle when it is brainstormed. Nothing here is decided yet; decisions go to `DECISIONS.md`
once made. Branch: `phase6-updates`.

## The list

1. **A trained fly, and a better fly.** What about a trained fly? And the current fly logic: is there a way to
   improve it or ideate on it?
2. **Two more Jev variants.** We have `jev` and `jev_composed`. Ideate on and test two other versions to find the
   best cost/performance approach. Feed the LLM run the same signals.
3. **Six rows of vision.** Is six a good number? Think it through.
4. **Live logs, one tab per mind.** A real-time running log of Jev, Haiku and the fly brain's processing, each
   viewable in parallel on its own tab in the HTML while it runs. So the run and the inference must also be able
   to happen live.
5. **Any track, live.** Confirm users can select any track (seed) live and run it.
6. **Harder, sooner.** Make the track get more difficult faster.
7. **Time, cost, performance.** Track all three, and research a scientific way to evaluate and benchmark success.
8. **Homepage is the run.** Move the extra findings, report, dialogue and analysis (everything below the
   scoreboard) to a separate tab. The homepage keeps the tunnel and the real-time thoughts below it.

## Where each one stands today

1. The fly is untrained by rule (`CLAUDE.md`, honesty rule): innate wiring only, looming weighting and two
   thresholds frozen on practice seeds 1000–1199 (`calibration/REPORT.md`, "never retune"). A trained fly or a new
   fly mapping would have to be a new player next to `fly`, not a change to it, with its own calibration on
   practice seeds and its own on-screen label saying what is ours. "Trained" also needs defining: plasticity inside
   the connectome model, or a learned readout on top of fixed wiring (the second is much cheaper to honestly
   label). Background: `docs/RESEARCH.md`, spike `spike/fly-steering`.
2. Today: `jev` (one-shot Choice, dies early; spike 02) and `jev_composed` (four pointed Nouls, code picks the
   action least likely to land on a gap). Candidates to brainstorm: fewer questions per row, looking two steps
   ahead, asking only when the row ahead is not trivially safe. "Same signals" means the LLM would get the same
   per-action questions or the same composed view, so the comparison is about the model, not the prompt. Testing
   any paid variant needs a budget go-ahead (Jev about 0.00003 USD a request, the LLM about 0.0006; `COSTS.md`).
3. `LOOKAHEAD = 6` in `bakeoff/game/track.py`; the gap width is at most 3 and a jump covers 2 rows, so the
   question is how far ahead a player needs to see to always have an escape, and what a shorter or longer view
   costs each player (more rows = longer prompts, more fly input). Changing it changes what every player sees, so
   all cached answers and the scoreboard stop being comparable.
4. `bakeoff live` already plays in lockstep and streams frames to one page over SSE (`live_server.py`), with the
   mind strip showing each player's latest answer. Missing: a per-player tab with the full running log (every
   question, answer, latency, and for the fly its spike activity) as it happens.
5. Partly. `bakeoff live --seed N` picks any track from the command line, and the default cap of 0 replays paid
   answers from the cache. The page itself cannot choose a seed or start a run; paid players on an uncached track
   need `--max-requests`, and seeds below 1000 need `--tournament`. A seed picker in the page would need the server
   to accept a request, which also needs the budget guard in the page flow.
6. Gap density ramps from `START_GAP_RATE = 0.04` to `END_GAP_RATE = 0.16` over `DIFFICULTY_ROWS = 300`. A faster
   ramp changes every track, so every past run and cached answer is on an old track; the track version should be
   recorded in the run so old and new runs never mix on one scoreboard.
7. Runs record cost and the step log (`docs/STEP_RECORD.md`); latency per decision is not yet a first-class
   measure. To research: a fixed seed set with confidence intervals on distance survived (bootstrap), paired
   comparison on the same seeds, survival curves (rows survived per player), cost per row survived, latency per
   decision, and how many seeds are needed to separate the players.
8. The page is `viewer/` built by `bakeoff/view.py`. Split into two tabs: Run (tunnel, scoreboard, live thoughts)
   and Analysis (findings, report, dialogue). Pure layout; brand rules in `CLAUDE.md` still apply.

## Things that interact

- Items 3 and 6 change the tracks. Do them first and together, then rerun, or every other comparison is on tracks
  that no longer exist.
- Items 1, 2 and 7 all need the benchmark method from item 7 to say which variant is "best".
- Items 2 and 4 spend money when run live on new tracks; the cap and the go-ahead rules stand.
- Items 4, 5 and 8 are the viewer and the live server, one piece of work.

## Next step

Brainstorm these (superpowers workflow), likely as separate specs: the game (3, 6), the players (1, 2), the
benchmark (7), the page (4, 5, 8). Then decide how they fit with phase 6, the tournament.
