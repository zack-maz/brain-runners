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

Where we are and what comes next: `docs/NEXT.md`.

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
