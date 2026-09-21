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

## Open

- Whether the tournament reuses seeds 0–19 or takes fresh seeds below 1000.
- Left from the PR #2 review for phase 3 or later (details in the PR comments): `meta.json` and the logged `looming`
  ignore per-player overrides of the fly constants; `calibrate.play` duplicates the game loop without the fallback
  rule; `fetch_fly_data` cannot repair an existing clone; `Network.restore` copies static synapse arrays every
  decision (measure before optimising).
- Left from the second PR #2 review: the fly data is hashed twice per CLI run (preflight, then
  `Brain`); `SurrogateBrain` raises a bare `KeyError` on a surface file missing a pin field. Done in
  phase 3: `preflight()` runs inside `Runner.run`. Declined: turning a brain exception into a `stay`
  fallback; phase 2 decided a simulator failure must end the run, because a silent `stay` would
  change the fly's score.
- Left from the final review of phase 5 (Minor): a crash in `live` (and in `run`) closes the run as `interrupted`,
  the same status as Ctrl-C; a status of its own would be the more honest record. A hard kill leaves `status:
  running` behind. `viewer/tunnel.js` knows that rows past the finish line never kill (drawing only, commented and
  tested); a `finish_row` in the track JSON would remove the one rule of the game that also lives in JavaScript.
  The live `episode` event carries the question sets known at that moment; a player that changed its questions
  mid-episode would show nothing under "What it was asked" for the later ones (no player does).

## Next step

A plain-language tour of everything built so far, from the idea down to the code: `docs/EXPLAINER.html`.

Phases 1 to 5 are built and on `main`. Phase 5 (5a the composed Jev, 5b the demo player, 5c go live) was PR #4,
merged on 2026-09-21 at the user's request. Plans:
`docs/superpowers/plans/2026-09-21-phase5a-jev-composed.md`, `...-phase5b-demo-player.md`, `...-phase5c-go-live.md`
(each ends with the rulings on its reviews).

To look at it: `uv run python -m bakeoff view runs/20260919-151934 runs/20260920-102919 runs/20260921-120903`
(practice track 1000: the fly, the LLM, the composed Jev) and `uv run python -m bakeoff view runs/20260921-132459`
(the live run on track 1001), then open the HTML file; or `uv run python -m bakeoff live --game v1 --seed 1001`
with the default cap of 0, which replays the paid answers of that run from the cache for free (the fly is
simulated again, about a minute to build and a second a row). All of these are game v1. Without `--game v1`,
`live` plays v2, where no paid answer is cached yet: with a cap of 0 a paid player stops at its first question.
A free v2 run of the yardsticks: `runs/20260921-155758` (seeds 1000–1019: solver 150, always-jump 39, random 24).

Before phase 6: the eight updates of `docs/UPDATES.md` (decision 20). Game v2 (items 3 and 6) is built
(decisions 21–24). Next: the players, items 1 (a better or trained fly) and 2 (two more Jev variants, the LLM fed the
same signals), brainstormed as their own spec; they will be the first paid runs on v2 and need a budget go-ahead.

Then phase 6, the tournament and the write-up. It starts by settling the first open item above (which seeds),
and it needs a new budget go-ahead: the tournament is the first paid use of seeds below 1000 (`--tournament`).
Things the write-up must carry from phase 5: the composed Jev's wording and rule are ours and it looks one
step ahead only; it wanders on safe rows because its four answers rarely tie; on both practice tracks it died
only where all four landing tiles were gaps; the one-shot Jev stays in for comparison; all of this is one or
two practice tracks, an impression and not a result.

## Prior art to reuse

`zack-maz/jev-testing`, PR #1 (`glassbox/`): policy interface (`Decision`, `Policy`),
episode runner with streaming JSONL step log and run status, summary report, and the
phase 1 review notes. Only its environment wrapper and state serializer are BabyAI-specific.
