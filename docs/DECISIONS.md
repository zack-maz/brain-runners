# Decisions so far

2026-09-19

1. **Contestants:** a traditional LLM, Jev (TypeSafe System One), and a fruit fly brain.
2. **Fly purity: pure innate wiring.** The whole-brain connectome simulation, untrained.
   Game events are hand-mapped onto real sensory neurons and real motor or descending
   neurons are read as button presses. It will lose games that match no reflex; that is
   part of the result. (Rejected for now: fly visual system plus a trained decoder.)
3. **Outcome: watchable tournament.** Seeded rounds replayed side by side with each
   contestant's internals visible, plus a scoreboard. Replays, not live play, so API calls
   are cached and viewing is free.
4. **Budget:** limited. The fly runs locally for free; Jev and the LLM are paid per step,
   so runs need a request cap and a response cache from day one.

5. **Fly route: pure fly, test first.** A throwaway spike (branch `spike/fly-steering`,
   `spikes/01-fly-steering/REPORT.md`) showed the untrained model steers *away from threats*
   reliably (36 of 36 one-sided trials, graded, cancels when both eyes are stimulated) and its
   Giant Fiber escape neuron fires graded with threat, but it cannot steer toward food: smell
   carries no side information and food input locks the left steering neuron on. About
   0.6–0.7 s wall-clock per 100 ms decision on the user's M1.
6. **Flagship game: a "Run"-style tunnel runner** (https://www.coolmathgames.com/0-run), not a
   slither-style food arena. Left/right = the fly's steering neurons, jump = its Giant Fiber.
7. **Design approved 2026-09-19:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md`.
   LLM is Claude Haiku 4.5. Turn-based, one decision per row, same seeded tracks for everyone.
8. **Fly input and tuning (phase 2, ours, not the fly's biology):** each visible gap adds
   `250 / row³` Hz to its eye, capped at 250 Hz and rounded to 25 Hz steps; any net steering
   spike turns (threshold 0 Hz); Giant Fiber mean above 200 Hz jumps. Chosen by a fixed rule from
   768 candidates on practice seeds 1000–1199 using a measured response surface as a stand-in
   brain, confirmed with the real brain. Frozen: `calibration/REPORT.md`, `calibration/RESULTS.md`.
9. **`always_jump` is a second floor** and the report shows `jump_share`, so a jump-heavy player
   is judged against the right baseline.
10. **Tournament seeds must be below 1000**; 1000–1399 were used for calibration. The fly has
    played seeds 0–19 once, after the freeze (first scoreboard); nothing was tuned on them.
11. **Paid players (phase 3):** one request per row through a disk cache (sha256 of provider, model,
    senses, questions) and a hard cap per paid player (`--max-requests`, default 0 = replay only).
    SDK retries are off so the cap is exact; a provider failure is a logged error and a `stay`.
    Jev and the LLM are told the same rules in the same words (`bakeoff/players/briefing.py`, ours,
    written before any paid request). No paid request on a seed below 1000 before the tournament.
    The CLI refuses a live paid run on seeds below 1000 unless `--tournament` is passed. Jev's
    request carries the Choice and the two calibration Nouls the spec asks for, while the LLM
    answers one question; TypeSafe documents that questions in one request run in parallel and
    cannot see one another's answers, so the Nouls are not scaffolding for the Choice, and this
    asymmetry is named in the write-up.
12. **First measured costs (2026-09-20, practice seed 1000, `docs/COSTS.md`):** the LLM costs
    0.00059 USD per request at 806 ms (survived 199 rows); Jev about 0.00003 USD per request at
    159 ms (survived 23 rows), an estimate from one console reading (29,457 tokens for 0.0011 USD,
    blended, no reading before the run). A 20-seed tournament costs at most about 3.56 USD for the
    LLM and about 0.20 USD for Jev. Neither player jumped and both died stepping sideways into a
    gap; the prompts stay as written, because tuning them on a track is what the seed rule forbids.

13. **Replay viewer (phase 4):** `python -m bakeoff view <run_dir>...` writes one self-contained HTML
    file, so a replay opens from disk, works offline and can be sent to someone. Python
    (`bakeoff/replay.py`) merges the run directories and applies the rules of the game (landing
    tiles, complete or cut off, scoreboard); the JavaScript only draws (`docs/REPLAY_DATA.md`). Players
    are lined up by row, not by decision, so every column shows the same stretch of track and a jump
    takes two ticks. The tiles a player was shown are drawn brighter. The same (player, seed) in two
    run directories is an error. When the players did not all play the same seeds, the scoreboard
    says its means are not a fair comparison. The fly's four numbers, the looming formula and the
    known weaknesses are on the page, with what is ours labelled as ours.

14. **Why Jev fell after 23 rows (spike 02, 2026-09-20, branch `spike/jev-questions`,
    `spikes/02-jev-questions/REPORT.md`; 200 capped requests on practice seed 1000, about 0.014 USD).** Not a
    bug. Jev reads the track almost perfectly (pointed yes/no questions: 1 wrong in 800), but the one-shot
    Choice carries no information about which actions are fatal: on the 55 dangerous states it landed on a
    gap in 29%, always staying in 33%, the LLM in 2%. From the rules alone Jev cannot map an action to its
    landing tile (it missed 16 of 16 jump landings). A confidence gate does not help. TypeSafe's own docs
    call the broad question the anti-pattern. This lifts decision 12's freeze on Jev's questions.
15. **The Jev in the demo is `jev_composed`:** four pointed per-action Nouls in one request, code picks the
    action with the lowest P(gap), ties in the solver's order. The wording and the rule are ours and are
    labelled as ours, like the fly's thresholds; frozen on practice seeds before any tournament seed. The
    one-shot `jev` stays as a player for comparison. **First recorded track (2026-09-21, practice seed 1000,
    `runs/20260921-120903`, 232 requests, `docs/COSTS.md`):** 247 rows (one-shot `jev` 23, the LLM 199), which is
    the ceiling of the rule on this track: it died where all four landing tiles were gaps one step ahead, as
    perfect answers would have. 1 answer in 928 was on the wrong side of 0.5. On safe rows its four answers
    differ by a hundredth, so ties are rare and it wanders sideways instead of running straight; never fatally.
    The rule stays as specified and the write-up names the wandering.
16. **The demo player is the main tool** (design: `docs/superpowers/specs/2026-09-20-demo-player-design.md`).
    Everything built so far is restyled to the user's brand (`~/Documents/PROJECTS/BRAND/brand.css`:
    near-black, concrete greys, one rationed blue, Hanken Grotesk, JetBrains Mono labels; BLAME! and Zima
    Blue as seasoning) and arranged around it.
17. **Staging:** one tunnel, three runners, fixed camera; everyone starts on the same tile and overlapping
    sprites are drawn translucent and fanned. **Blue is the cursor:** it marks the mind in focus and the
    tiles that mind was shown, nothing else. Figures are pixel sprites: a fruit fly with red eyes, an orange
    critter for the LLM (our own rendition, not official artwork), and for Jev "the visor", whose slit
    shows how sure it is that its move is safe.
18. **"Live" means both:** recorded runs play for free from one offline file, and `bakeoff live` runs the
    three minds in real time on the user's Mac, streams them into the same page and records a normal run
    directory. This reverses the first spec's non-goal "no real-time play" for that one local mode.
    Phases: 5a `jev_composed`, 5b the player, 5c go live; the tournament and write-up become phase 6.
    **First real go-live (2026-09-21, fresh practice seed 1001, `runs/20260921-132459`, `docs/COSTS.md`):**
    completed in six and a half minutes, watched in a browser. Composed Jev 241 rows, the fly 212, the LLM 95;
    no provider error. The fly's live run is move for move its batch run on the same seed of 2026-09-19
    (`runs/20260919-151934`, also 212 rows), so the live loop plays exactly what the runner plays. Because the
    fly's episode on seed 1001 now exists in both directories, `view` takes only one of the two at a time.
19. **Budget pre-authorized for the session that builds phase 5** (practice seeds 1000 and up only, through
    the cache and hard caps): up to 1,000 Jev requests in total (about 0.04 USD) and up to 300 Claude Haiku
    requests in total (about 0.18 USD, for one real go-live test on a fresh practice seed). Anything beyond
    that, and any tournament seed, needs a new go-ahead. **Used (2026-09-21):** 460 Jev requests (232 for
    track 1000, 228 live on track 1001) and 92 Claude Haiku requests (0.054 USD); nothing on a seed below
    1000. What is left of this authorization ended with that session.
20. **All eight updates in `docs/UPDATES.md` come before phase 6** (2026-09-21): a trained or better fly, two more
    Jev variants with the LLM fed the same signals, the number of rows of vision, one live log tab per mind, any
    seed live, a faster difficulty ramp, a benchmark for time, cost and performance, and the analysis moved to its
    own tab. Worked on branch `phase6-updates`, starting with the game (vision and ramp).
21. **Game v2** (2026-09-21, design `docs/superpowers/specs/2026-09-21-game-v2-design.md`, measured on practice
    seeds 1000–1199 with free players only): the faster ramp's job is to separate the players sooner; the track is
    150 rows and reaches full gap density by row 100 (perfect play still finishes 97%; the fly's stand-in brain
    averages 68 rows instead of 124, random 24). Vision stays 6 rows × 3 lanes either side: perfect play gains
    nothing from more on either ramp (v2, seeds 1000–1199: 97% of tracks finish with 6 rows, 98.5% with 8, 99%
    with 10), and only the LLM and the one-shot Jev are given the whole view in words; the fly weighs rows 1–2
    almost entirely and the composed Jev asks only about landing tiles.
22. **Vision is a setting of the game** (`--lookahead`, `--window`), and a changed vision renames the game
    (`v2+look3`), so an experiment can compare players at other depths without ever mixing scoreboards.
23. **Named game versions** (approach A): `v1` stays playable and is tile for tile the game of phases 1 to 5 (a test
    pins it); `v2` is the default. Every run records its rules in `meta.json`; a run from before versions reads as
    v1; `view` refuses to mix games. The fly's frozen numbers were fixed on v1 tracks and are not retuned for v2;
    the page says so.
24. **Built as update 1** (plan `docs/superpowers/plans/2026-09-21-update1-game-v2.md`). Amended while prototyping:
    `--max-rows` stays (a shorter track is a prefix of the same game, so it keeps its version).
25. **The players update (items 1 and 2 of `docs/UPDATES.md`, 2026-09-21).** Measured first, for free, on v2 practice
    seeds 1000–1199 with perfect answers: the composed Jev's one-step rule averages 112 rows (26% finish), a two-step
    rule 140 (74%), the solver 149 (97%). The fly's input is two eye rates of 11 levels each, so a trained readout on
    it could only learn a 121-entry table. The user chose: **the fly** gets richer input first (`fly_rich`,
    untrained, calibrated once on practice seeds), then a trained readout of ours on the same wiring
    (`fly_trained`); **three new Jev variants**: `jev_choice` (one Choice whose wording names each move's landing
    tile), `jev_two_step` (landing plus safe-follow-up questions) and `jev_reader` (Jev reads every visible tile, code
    plans over its answers); **an LLM twin for every question set** (composed Jev and the three new ones: Claude
    Haiku answers the same questions, the same rule picks), so the model is the only difference. Built as update 2a
    (the Jev family and twins), then 2b (the fly).
26. **Budget for update 2 (2026-09-21):** Claude Haiku up to **5.00 USD** in total, on v2 practice seeds 1000 and up
    only. Jev spend is not a concern to the user ("jev isn't costing me anything"); its requests stay capped and cached
    as always. Paid runs start with one capped track. **Split (controller's ruling after run 1):** the four Jev
    players and the four cheaper LLM twins on seeds 1000–1004, `llm_reader` (about 1 USD a track) on 1000 and 1001
    only.
27. **The LLM stays Claude Haiku** for update 2a (the user, 2026-09-21); a **GLM Flash** twin (Zhipu's free tier,
    through an OpenAI-compatible client) comes later as another model, and is one of the players the page will let
    the user select (items 9 and 10 of `docs/UPDATES.md`). OpenAI's GPT-5.6 Luna was considered (about 4 to 5 times
    cheaper than Haiku); not chosen for now.
28. **This file is the log only** (the user, 2026-09-21): numbered decisions, only ever added to. Where things
    stand, the resume list, the open items and what the write-up must carry moved to `docs/NEXT.md`, which is
    rewritten as the state changes.
29. **Update 2b is `fly_rich` only** (the user, 2026-09-22): `fly_trained` is dropped for now. Aim: honest science,
    what the real wiring can do with better input. The input says where a threat is, not just which side: each eye's
    looming cells (LPLC2, LC4) are cut into bands, and each visible gap drives the band facing its lane with the
    frozen v1 formula; the tile-to-band mapping is ours and labelled. Readout and rule unchanged; only the two
    thresholds are chosen again, from one recording of the real brain on v2 practice seeds 1100–1299 (the solver's
    path plus random detours) by a rule fixed beforehand, then frozen; `fly_rich` then plays 1000–1019 once. A probe
    comes first: find an ordering of the cells that follows their view and check that the brain's output differs by
    band; if it does not, `fly_rich` is not built and that is the result. `fly` is never touched.
30. **Update 2b stops at the probe** (2026-09-22, spike 03, branch `spike/fly-bands`, `spikes/03-fly-bands/REPORT.md`).
    Ordered by the eye positions of their columnar inputs, each eye's looming cells respond by band only in strength
    (dorsal bands drive the Giant Fiber about 30% harder, one azimuth end turns about half as hard), never with a
    different action. The user chose a play test with a rule fixed beforehand; on v2 practice seeds 1100-1104 with
    the frozen v1 thresholds the band flies survived 21.6 and 29.6 rows against `fly`'s 58.2 and never jumped. So
    `fly_rich` is not built; `fly` stays the only fly, and the report is the result for the write-up.
31. **The benchmark (item 7)** (the user, 2026-09-22; design `docs/superpowers/specs/2026-09-22-benchmark-design.md`):
    one report that says both who is better with confidence (paired comparisons on shared seeds, bootstrap
    intervals, survival curves, seeds needed) and the cost/performance trade-off (USD and seconds per row). It reads
    recorded runs only and spends nothing. `python -m bakeoff bench` prints the tables and writes `bench.json` and
    its own offline page, `bench.html`, now; the Analysis tab of item 8 reuses it later.
32. **The benchmark's intervals are t intervals** (2026-09-22, final review of item 7; controller's ruling under the
    user's aim of honest science, decision 29). The spec's percentile bootstrap is too narrow at a handful of tracks:
    at 5 tracks it gave a verdict about 1 time in 7 with no real difference, and one such verdict had been quoted in
    `docs/COSTS.md`. Now: 95% Student t intervals (paired for pairs), none below 5 tracks; tracks needed is for an
    80% chance of a verdict; a note counts the pairs compared and the verdicts chance alone would give; runs of
    different lengths are refused. A test simulates the verdict rate with no difference (about 5%).
33. **The GLM Flash twins** (the user, 2026-09-22; item 10 of `docs/UPDATES.md`): a third model on all four question
    sets (`glm_composed`, `glm_choice`, `glm_two_step`, `glm_reader`), sent the same request as the Haiku twins
    (`ChatSetPlayer`), so the model is what differs. `glm-4.5-flash` through the OpenAI-compatible endpoint
    (`ZHIPU_API_KEY`, `GLM_BASE_URL` for a mainland account), called with the standard library: one HTTP request per
    decision, no retries, the same cache and cap as every paid player. The free tier is priced at 0, so it reads as
    free rather than unknown. First run capped at one practice track, then tracks 1001–1004 to match the others.
34. **GLM Flash is parked after one track** (the user, 2026-09-22). The four `glm_<set>` players work and track 1000
    is recorded (`docs/COSTS.md`), but Zhipu's free tier throttles: about one request in five got through, and the
    run of tracks 1001–1004 aborted on six refusals in a row. Item 10 is part done; pick it up when the quota
    recovers. The page work (items 4, 5, 8, 9) comes next, with GLM among the selectable players.
35. **The page runs the show** (the user, 2026-09-22; items 4, 5, 8, 9; design
    `docs/superpowers/specs/2026-09-22-page-control-design.md`). `bakeoff live` opens a lobby: the page picks the
    track and the runners, starts and cancels runs, and can set up another when one ends (the old flags stay, plus
    `--start`). The page may start paid runs after showing the worst-case cost and asking, but the command keeps the
    ceiling: `--max-requests` is the session's cap per paid player and `--tournament` is still needed below seed
    1000, and the server refuses anything beyond that. Each mind panel gains an expandable running log (item 4);
    the page splits into Run and Analysis, the latter holding the findings, the scoreboard and the benchmark's
    charts from `bench.json` (item 8); one player picker governs live runs and replays (item 9). Built as 3a (the
    server and the lobby) and 3b (the panels and the tabs), each with its own plan.

36. **Update 3b's two open questions** (the user, 2026-09-23). The Analysis tab draws the benchmark with the same
    code as the standalone page: `viewer/bench_app.js` becomes a renderer mounted into a container, used by both
    `bench.html` and the Analysis tab, so there is one drawing code and one set of tests. And a live run's numbers
    come from the server: when a run ends, it scores that run directory with `bakeoff/bench.py` and sends the
    numbers with the end event, so the Analysis tab fills in without a reload (the spec's "live runs show it once
    the run has ended").

37. **The level table stops toggling players** (the user, 2026-09-23; update 3b, spec section F). The new picker
    over the tunnel is the one control over who is in it: it shows and hides a replay's runners, and a player that
    did not run the track in view can never be turned on. The level table keeps only its track buttons, and picking
    a track returns to the Run tab, where the track is watched. Two controls over the same thing could disagree;
    one cannot.

38. **Two rows in one Players section** (the user, 2026-09-24; update 3b's review, Minor 8). Spec F reads as one
    control for both jobs; what is built keeps two, because they answer different questions at different moments:
    *Who runs next* (the lobby's ticks, live only, with each player's price, what is left of the cap and whether the
    track was played before) and *Who is in the tunnel* (the picker, which shows and hides the runners of whatever
    is on screen, live or replay). They now sit in one section, "Players", one labelled row under the other, in the
    same tile style, so they read as one control with two jobs; a saved replay file has no lobby and so shows one
    row only. Whoever is ticked to play is shown when the run starts, so nobody has to say it twice. A single
    button would have to mean "play" before a run and "show" during one, which is the misreading this avoids.

39. **Claude Haiku's players are `haiku*`, not `llm*`** (the user, 2026-09-24). With a second chat model in the
    bakeoff, `llm_composed` beside `glm_composed` read as two unlike things when they are the same question set
    asked of two models. The players are now `haiku`, `haiku_composed`, `haiku_choice`, `haiku_two_step` and
    `haiku_reader`, and the page's tags say HAIKU. Nothing recorded changes: the response cache is keyed by
    provider, model, senses and questions, so every answer already paid for still replays (checked:
    `haiku_composed` replays practice track 1000 from 131 cache hits, 0 requests, the same 132 rows); the run
    directories keep their `llm*.jsonl` files; and `bakeoff/players/names.py` maps the old names to the new ones
    wherever a name is read — the command line, a `DIR:player,...` source, the lobby, and every record and
    `meta.json` that `load_steps`/`load_meta` return. So an old run and a new one merge as one player, and a saved
    command still works. The provider ids in `bakeoff/clients/` (`llm`, `jev`, `glm`) are part of the cache path
    and stay as they are.

40. **GLM Flash joins the one broad question, as `glm`** (the user, 2026-09-24). The lobby's grid had one empty
    cell: every question set was asked of all three models, but the one broad question ("which move?", asked once,
    with no pointed question under it) was asked only of Jev and Claude Haiku. `glm` fills it, built as the twin of
    `haiku`: the same briefing and the same one-action schema, `GlmClient` instead of Anthropic's, so the model is
    the only difference. Its one departure is reading the reply — GLM wraps its JSON in a markdown fence, which is
    stripped for the parse only, so the log still keeps the answer as it came. Free tier, so its price is 0, and it
    spends nothing until someone plays it with `--max-requests`.
41. **`fly2`, a second pure fly** (the user, 2026-09-24; research in `docs/research/2026-09-24-fly/`, design in
    `docs/superpowers/specs/2026-09-24-fly2-design.md`, branch `fly2`). The research found that the input is the
    bottleneck: the best table on `fly`'s two eye totals scores 66.7 rows on v2 held-out seeds, and the fly already
    scores 66.0. The user chose the following:
    - **Pure first:** the fly is improved within decision 2. A trained fly comes later as a separate, labelled player.
    - **Both flies selectable:** `fly` stays unchanged and `fly2` plays beside it.
    - **A rule picks the input:** it chooses among three candidate mappings (a straight-ahead channel, narrow eyes, a
      sideways LPLC4/LC22 channel), each measured on the real brain, with the rule fixed before any measurement,
      practice seeds 1000–1199 only, and the winner played once on 1200–1399.
    - **The readout and rule, ours and labelled:** turn from DNa02 + DNa01 + DNg13 (DNb01 dropped), the Giant Fiber
      for the jump, and dodge before jump.
    - **Controls reported with the result:** no brain, shuffled wiring, and `fly`.
    - **A probe first (spike 04):** if no candidate turns away from the gap's side, the update stops there.
42. **The probe passes; the turn readout is chosen per candidate** (the user, 2026-09-24; spike 04, branch
    `spike/fly2-probe`, `spikes/04-fly2-probe/REPORT.md`). With the centre driven at 500 Hz, every candidate still
    turns away from the side of an extra gap, so fly2 goes on to the surfaces. M3's sideways channel (LPLC4 + LC22)
    turns the fly away from its own side and drives no Giant Fiber, so M3 is admitted. The spec's DNa02 test gives
    a different answer for each candidate, and the user chose to apply it per candidate:
    - **M2:** DNa02 is within the trial noise in every uneven condition, so its turn is DNa01 + DNg13.
    - **M3:** DNa02 adds to the turn (above the noise at 300 and 500 Hz), so it keeps DNa02 + DNa01 + DNg13.
    - **M1:** DNa02 is above the noise for a left gap at 300 and 500 Hz and within it for every right gap. The test
      says "cancels" only when DNa02 is within the noise in the uneven conditions, and here it is not, so M1 keeps
      DNa02 + DNa01 + DNg13. This is the controller's reading of the test and the user may still reverse it.
43. **fly2 is M3, the sideways channel, frozen** (the user, 2026-09-25; `calibration/FLY2_REPORT.md`). The rule
    of decision 41, fixed before any surface was measured, picked M3 over M1 and M2 on v2 practice seeds 1000–1199.
    - **What M3 is:** gaps in the runner's own lane drive LPLC2 + LC4 of both eyes; gaps in side lanes drive
      LPLC4 + LC22 of that side's eye.
    - **Its read-out:** turn = right minus left of DNa02 + DNa01 + DNg13; jump = the Giant Fiber.
    - **Its numbers:** gain 250 Hz, falloff 2, turn threshold 40 Hz, jump threshold 175 Hz. They are frozen in
      `bakeoff/players/fly2.py`.

    On the stand-in brain, held-out seeds 1200–1399 (mean rows):
    - fly2: 82.3;
    - the same mapping and rule with no brain: 74.1;
    - M3 on shuffled wiring: 27.8;
    - `fly`: 66.0.

    The user accepted the result with what it says:
    - **Our part is large.** Our mapping and rule already reach 74 rows without a brain; the wiring adds about 8
      rows more.
    - **The shuffled control is weak evidence.** On shuffled wiring, the read-out neurons never fire, so it shows
      only that the real wiring routes these eye cells to them.
    - **Deaths are still mostly jumps into gaps:** 158 of 195 on held-out seeds.
    - **The turn threshold sits at the top of the grid** (40 Hz), so a higher one was never tried.
    - **The held-out seeds were not wholly unseen:** they had been used by the research that chose the three
      candidates.

44. **The question sets are renamed plain, guided, step1, step2 and map** (the user, 2026-09-25).

    | old player | new player |
    |---|---|
    | `jev`, `haiku`, `glm` (the one-shot) | `jev_plain`, `haiku_plain`, `glm_plain` |
    | `jev_choice`, `haiku_choice`, `glm_choice` | `jev_guided`, `haiku_guided`, `glm_guided` |
    | `jev_composed`, `haiku_composed`, `glm_composed` | `jev_step1`, `haiku_step1`, `glm_step1` |
    | `jev_two_step`, `haiku_two_step`, `glm_two_step` | `jev_step2`, `haiku_step2`, `glm_step2` |
    | `jev_reader`, `haiku_reader`, `glm_reader` | `jev_map`, `haiku_map`, `glm_map` |

    Nothing recorded changes: the response cache is keyed by provider, model, senses and questions, not by a name,
    so every answer already paid for still replays; the run directories keep their old file names and are read
    through `canonical()` in `bakeoff/players/names.py`, which maps every old name, the `llm*` ones of decision 39
    included, straight to its new one. The new names were chosen for the Brain Battle character select
    (`docs/FRONTEND.md`), where each set is a skin.

45. **Brain Battle is the front of `bakeoff live`** (the user, 2026-09-25; spec
    `docs/superpowers/specs/2026-09-25-brain-battle-design.md`, mock-ups and answers in `docs/FRONTEND.md`). Home,
    character select (skins are the players), track select, the race, results, and Records. The user approved the
    spec's seven open calls:
    - **Wrong moves** count the executed move, a fallback included; a death with no surviving move is "trapped".
    - **Records** keeps the newest complete episode of each (player, track), notes how many older ones it left out,
      and leaves tournament seeds out until phase 6.
    - **Results** open by themselves when the tunnel reaches its last row; a viewer scrubbing back gets a button.
    - **"What is ours"** keeps the whole current section under the mock-up's three paragraphs.
    - **The live page drops the lobby's grid and "Who runs next"** (amends decision 38 for the live page; "Who is in
      the tunnel" stays).
    - **Skin colours and tags** ("Jev · Step 1") reach `bakeoff view` too; its layout is otherwise unchanged.
    - **A results card's cost** is live requests × the page's price per request, labelled an estimate.

46. **Records after Brain Battle plan a** (the user, 2026-09-25, on the plan's final review):
    - **The leaderboard ranks on practice tracks 1000–1019 only**, the tracks the track select offers, so the flies'
      calibration and settle runs (1000–1199) do not swamp the question sets' five tracks. Each row keeps its track
      count; head to head still compares a pair on the tracks both played.
    - **fly2's rows are marked "tuned on these tracks"**, not removed: its thresholds were fixed on 1000–1199
      (`records_of` returns `tuned_on`). A clean test of fly2 uses tracks 1200 and up.
    - **The skins' `about` lines say what is ours** as reworded at the review: each question set ends "The question
      is ours." or "The questions and the rule (the planner) are ours.", and the flies name their input, read-out,
      rule and thresholds.
    - **One fly smoke covers plans a and b**, run once no other session holds a fly brain.

47. **fly2 is the better pure fly** (2026-09-25). On 100 fresh v2 seeds 1400–1499 (`runs/20260925-163957`), never used
    by either fly's calibration, fly2 scored 79.45 rows against fly's 66.02: +13.4 (95% interval 5.3 to 21.6), 63
    wins / 4 ties / 33 losses, `bakeoff bench` verdict "fly2 ahead". A third of fly2's deaths are dodges into a gap.
48. **fly3, the trained fly** (the user, 2026-09-25; design `docs/superpowers/specs/2026-09-25-fly3-design.md`). Track 2
    of decision 41, a separate player labelled *trained*; decision 2 still binds `fly` and `fly2`. The user chose:
    - **Purpose: science first, then the page.** It answers "does the fly's wiring help a learner play?"; fly3 is
      offered in the lobby and the tournament only if it beats its no-brain control.
    - **Input: per cell.** Each LPLC2/LC4 cell gets its own place on the eye and is driven by the gaps it would see
      (ours, labelled), not by summed channels.
    - **Learning: imitate the solver by DAgger** (supervised, NumPy), not reinforcement learning.
    - **Readout: linear over every descending neuron, sparse** (a softmax over the four moves, L1 + L2).
    - **Controls, all four** (the user left them to Claude): no brain (the same learner on the per-cell input),
      blind brain, shuffled wiring (retrained), and fly and fly2 on the same evaluation tracks.
    - **Seeds fixed beforehand:** training 1000–1399 only, evaluation 1400–1499 played once.
    - **A probe first (spike 05)**, on today's Brian2, which also decides the engine. Into it go five questions the
      user asked to be investigated: the "any safe move" target, weighting the rows where a wrong move kills, the
      input strength against how many DNs fire, early/late timing within the window, and noise averaging.
49. **fly3 stops at its probe** (the user accepted it on 2026-09-26; spike 05, branch `spike/fly3-probe`, local,
    `spikes/05-fly3-probe/REPORT.md`, DONE `stop C`). Part A passed (every looming cell gets a place on the eye: LPLC2
    from its lobula-plate layers by a published rule, LC4 through a map fitted on LPLC2) and part B passed (the DNs
    name a single gap's lane 80% of the time at the strongest gain). Part C, the play test on seeds 1300–1309: fly3 86.5 rows, the same learner on the input
    with no brain 112.5, the same readout on a blind brain 19.6. With the same learner the frozen wiring is a worse
    layer of features than the input it is given, so the answer to decision 48's question for this game is no. fly3
    is not built and stays off the page and out of the tournament. The one lever left untested is a stronger input
    (gains above 4000; about 1.5 h, judged against the same no-brain bar of 112.5), only if the user asks for it.

50. **Jev plays without a cap** (the user, 2026-09-26: "Jev right now is free for me. Still monitor cost, but allow
    it to play even with budget caps"). Every `jev_*` player (`bakeoff.players.UNCAPPED`) gets an `UncappedBudget`:
    its live requests are counted, recorded in `meta.json` (`"max": null`) and priced as before, but never stopped,
    in `run` and in `live`, whatever `--max-requests` says. Claude Haiku and GLM Flash keep their hard cap. Jev is
    still kept off the tournament seeds (below 1000) without `--tournament`: that rule keeps those seeds unseen, it
    is not about money. The track select still shows Jev's worst case (the whole track × its price) but does not ask
    to confirm a lineup whose only spending is Jev's. The fast tests hide every provider key (`tests/conftest.py`),
    since a cap of 0 no longer keeps a test from going live.
51. **Brain Battle is renamed Brain Run** (the user, 2026-09-26): the logo reads BRAIN RUN, the fighters are
    runners ("Choose your runners", "Ready to run"), and the home brain's glow pulses visibly. On screen only:
    code names, ids and the record of decisions 45–46 keep the old name.

52. **A player that stops drops out; the others play on** (the user, 2026-09-28). Before, one capped player reaching
    its cap, or one provider failing six times in a row, ended the run for everyone, flies and free players
    included. Now that player alone stops, in `run` (for the rest of its tracks) and in `live`; `meta.json` records
    it under `stopped` (`{status, reason, seed, row}`), the page is told ("… stopped: …; the others play on") and its
    card shows it stopped, and the command names it and exits 1. The run ends `budget_exhausted` or `aborted` only
    when every player has stopped. The error streak now counts per player. It makes GLM Flash's throttled free tier
    safe to put beside the others.

53. **Phase 6 is a study, not a tournament** (the user, 2026-09-28: "get rid of the whole tournament idea ... this
    should now turn into a research project where we're seeing what performs best at cost and speed"). Design:
    `docs/superpowers/specs/2026-09-28-study-design.md`. The user chose:
    - **Held-out seeds 100–199** (game v2); the free players play all 100, Claude Haiku's five skins the first 15
      (at most 23.85 USD, capped; the user buys about 25 USD of API credit), GLM Flash's five the first 15 only if
      its free tier fails under 2% of decisions over at least 5 practice tracks.
    - **Measured:** performance (rows, 95% interval), cost (USD per track and decision at listed price), speed
      (seconds per decision), reliability. **Verdict:** two trade-off charts (rows vs cost, rows vs speed) with
      their frontiers, plus named scores (rows per cent, rows per second) as extras, never the verdict.
    - **The page:** Records stays the historical log; a new **Charts** tab holds all the data; no practice and
      evaluation split. The numbers come from the benchmark (`bakeoff/bench.py`), extended.
    - **One Writeup page** is the report: drafted by Claude for now, to be rewritten in the user's own words.
    - `--tournament` is renamed `--held-out`.

54. **Claude Haiku's budget is 10 USD, not 25; `haiku_map` is left out** (the user, 2026-09-29: "25 is too much.
    Let's reduce to 10"). The five skins' worst case is 1.59 USD a track (150 rows, one request a row), and
    `haiku_map` alone is 61% of it. The user chose four skins on the planned 15 tracks over all five on 6:
    `haiku_plain`, `haiku_step1`, `haiku_guided` and `haiku_step2` on held-out tracks 100–114, `--max-requests 2250`
    each in total (track 100 first with 150, then 101–114 with 2100), worst case 9.23 USD. `haiku_map` plays no
    held-out track, so `jev_map` has no Claude Haiku twin in the study; the Writeup says so and why (the priciest
    skin, and its Jev twin is among the weakest players).

Where we are and what comes next: `docs/NEXT.md`.

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
