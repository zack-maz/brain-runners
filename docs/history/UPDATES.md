# Updates requested on 2026-09-21

The user's list of changes after phase 5 was merged, recorded as given, each with where the project stood that day
and the questions to settle when it is brainstormed. Decisions go to `DECISIONS.md` once made (decisions 20 on).
Branch: `phase6-updates`.

## The list

1. **A trained fly, and a better fly.** What about a trained fly? And the current fly logic: is there a way to
   improve it or ideate on it?
2. **Two more Jev variants.** We have `jev_plain` and `jev_step1`. Ideate on and test two other versions to find the
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
9. **Selectable players** (added 2026-09-21). Make the players selectable: from the page, choose which players play
   a live run (with the seed of item 5), and which are shown in a replay. Built with the page (items 4, 5, 8).
10. **A GLM Flash toggle** (added 2026-09-21, after update 2a). A free-tier LLM twin (Zhipu's GLM Flash, through an
   OpenAI-compatible client) next to Haiku, which stays the reference LLM. It is one of the selectable players of
   item 9 (the user, 2026-09-21), so it is built before the page work.

## Built

- Items 3 and 6: game v2 (decisions 21–24 in `DECISIONS.md`; spec `docs/superpowers/specs/2026-09-21-game-v2-design.md`,
  plan `docs/superpowers/plans/2026-09-21-update1-game-v2.md`). Vision stays 6 rows × 3 lanes and is now a setting;
  v2 is 150 rows at full difficulty by row 100; v1 stays playable.
- Item 2 (update 2a): `jev_guided`, `jev_step2`, `jev_map` and an LLM twin for every question set (decisions
  25–27; spec `docs/superpowers/specs/2026-09-21-jev-family-design.md`). Code built and reviewed; paid runs done
  (`docs/COSTS.md`). Item 1 (the fly) is update 2b: the trained fly dropped for now, `fly_rich` stopped at its probe (decisions 29–30).
- Item 10, the GLM Flash twins (decisions 33–34): `glm_step1`, `glm_guided`, `glm_step2` and `glm_map` on
  `glm-4.5-flash`, the same questions and rules as their Jev and Haiku twins. Built; track 1000 recorded, the rest
  parked while the free tier throttles (`docs/COSTS.md`).
- Items 4, 5, 8, 9, the page: approved design (decision 35,
  `docs/superpowers/specs/2026-09-22-page-control-design.md`), built as updates 3a and 3b. **Update 3a is built**
  (plan `docs/superpowers/plans/2026-09-22-update3a-page-control.md`): the control channel, the money ceiling for a
  whole session and the lobby, so the page picks the track and the players and starts and cancels the run.
  **Update 3b is built** (plan `docs/superpowers/plans/2026-09-23-update3b-page-rest.md`): a running log in every
  mind panel (item 4), the Run and Analysis tabs (item 8) and one player picker over the tunnel (item 9), with the
  level table left to pick the track alone (decision 37) and the benchmark drawn in the Analysis tab by the same
  code as its own page (decision 36). Items 4, 8 and 9 are done; item 5 was done by 3a.
- Item 7, the benchmark (decision 31, `docs/superpowers/specs/2026-09-22-benchmark-design.md`): built; `python -m
  bakeoff bench` scores recorded runs with intervals, pairs, time and cost per row, and writes its own page.

## Where each one stood on 2026-09-21

1. The fly is untrained by rule (`CLAUDE.md`, honesty rule): innate wiring only, looming weighting and two
   thresholds frozen on practice seeds 1000–1199 (`docs/calibration/REPORT.md`, "never retune"). A trained fly or a new
   fly mapping would have to be a new player next to `fly`, not a change to it, with its own calibration on
   practice seeds and its own on-screen label saying what is ours. "Trained" also needs defining: plasticity inside
   the connectome model, or a learned readout on top of fixed wiring (the second is much cheaper to honestly
   label). Background: `docs/RESEARCH.md`, spike `spike/fly-steering`.
2. Today: `jev_plain` (one broad Choice, dies early; spike 02) and `jev_step1` (four pointed Nouls, code picks the
   action least likely to land on a gap). Candidates to brainstorm: fewer questions per row, looking two steps
   ahead, asking only when the row ahead is not trivially safe. "Same signals" means the LLM would get the same
   per-action questions or the same step1 view, so the comparison is about the model, not the prompt. Testing
   any paid variant needs a budget go-ahead (Jev about 0.00003 USD a request, the LLM about 0.0006; `COSTS.md`).
3. `LOOKAHEAD = 6` in `bakeoff/game/track.py` (now the `lookahead` field of `Rules` in `bakeoff/game/rules.py`); the gap width is at most 3 and a jump covers 2 rows, so the
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
6. Gap density ramps from `START_GAP_RATE = 0.04` to `END_GAP_RATE = 0.16` over `DIFFICULTY_ROWS = 300` (now
   `start_gap_rate`, `end_gap_rate`, `difficulty_rows` fields of `Rules` in `bakeoff/game/rules.py`). A faster
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
- Items 4, 5, 8 and 9 are the viewer and the live server, one piece of work.

## Next step

Decided (decision 20 in `DECISIONS.md`): all of these come before phase 6, each brainstormed as its own spec. Order:
the game (3, 6: done), the players (2: built, runs done; 1: stopped at its probe), the benchmark (7), GLM Flash (10, needs a key), the page
(4, 5, 8, 9). The step-by-step resume list is `docs/NEXT.md`. When all are done: one PR, "Opus v1".
