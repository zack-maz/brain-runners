# Tunnel Run tournament: design

Date: 2026-09-19 · Status: design approved in chat by the user; implementation not started ·
Background: `docs/DECISIONS.md`, `docs/RESEARCH.md`, spike report on branch
`spike/fly-steering` (`spikes/01-fly-steering/REPORT.md`)

## Goal

A watchable tournament in which three very different minds play the same seeded runs of a
"Run"-style tunnel game (reference: https://www.coolmathgames.com/0-run):

- a **traditional LLM** (Claude Haiku 4.5, `claude-haiku-4-5-20251001`),
- **Jev**, TypeSafe's System One model (`jev-latest`), which returns typed probabilities,
- a **fruit fly brain**: the published whole-brain spiking model of the adult *Drosophila*
  connectome, **untrained**, pressing the buttons with its own innate escape wiring.

Output: replays showing the three runners side by side with each one's "mind" visible
(neurons firing, Jev's probabilities, the LLM's answer) and a scoreboard across tracks.

## Non-goals

- No training or fine-tuning of anything, and no learned readout on the fly. The fly's only
  tuning is two fixed thresholds (see "Fly player").
- No real-time play. The game is turn-based so slow API calls and the slow fly simulation
  cost nobody anything; replays are what people watch.
- No food-seeking game. The spike showed the pure fly cannot steer toward food in this model.
- No pixels. Contestants receive senses, not a screen (the fly model has no visual front end).

## The game

- **Track:** a ring of **12 lanes** (the tunnel unrolled: stepping past lane 11 wraps to lane 0,
  which is the original game's tunnel rotation). Rows of tiles scroll toward the runner; each
  tile is floor or gap.
- **Turn:** once per row the player picks one action: `left`, `right`, `jump`, `stay`.
  `left`/`right` move one lane (with wrap) and advance one row. `jump` stays in lane, clears
  the next row entirely and lands on the row after it. `stay` advances one row.
- **Death:** the runner falls if the tile it lands on is a gap. Score = rows survived.
  A run also ends at `max_rows` (default 300).
- **Seeds and difficulty:** tracks are generated from a seed; gap density and gap width rise
  with distance. The generator guarantees at least one survivable path, so every death is the
  player's fault. All contestants run identical tracks.
- **Look-ahead:** every contestant perceives the same next **6 rows**.

The engine is a pure module: no I/O, no randomness outside the seeded generator.

## Senses (one source of truth, two encodings)

From the engine state, `senses` computes for the next 6 rows the gaps relative to the runner.

1. **JSON senses** for Jev and the LLM (and logged for every player):
   ```json
   {
     "lane": 4, "lanes": 12, "rows_survived": 37,
     "ahead": [
       {"row": 1, "gaps_relative": [-1, 0]},
       {"row": 2, "gaps_relative": []},
       {"row": 3, "gaps_relative": [2, 3]}
     ],
     "actions": {"left": "move one lane left", "right": "move one lane right",
                 "jump": "clear the next row, land on the one after", "stay": "run straight"}
   }
   ```
   `gaps_relative` are lane offsets from the runner (negative = left), wrapped to −6…+5 and
   limited to the visible window of ±3 lanes.
2. **Looming rates** for the fly: two numbers, `left_hz` and `right_hz` (0–250 Hz). Each
   visible gap contributes intensity that grows as it gets closer (nearest row strongest).
   Gaps left of the runner's lane add to the left eye, gaps to the right add to the right eye,
   gaps in the runner's own lane add to both. The exact weighting is a small pure function,
   fixed before the tournament and shown in the viewer.

## Players

All implement one interface (carried over from `zack-maz/jev-testing` PR #1):
`reset(game, seed)`, `act(senses) -> Decision`, `observe(executed_action)`. `Decision` carries
`chosen_action`, `gated`, `invalid`, `error`, `questions`, `answers`, `latency_ms`, `usage`,
`cache_hit`, `info`.

1. **random**: uniform over the four actions. Floor for every metric.
2. **solver**: scripted search over the visible 6 rows for a surviving action sequence; takes
   the first action of the longest-surviving one. The reference player (the role the BabyAI
   bot had in the predecessor). Not a contestant.
3. **fly**: see below.
4. **jev**: one request per row: a Choice over the four actions (each with its one-line
   description), plus two speculative Nouls logged for calibration: "is there a gap directly
   ahead in the next row?" and "is the lane to the left safe next row?" (ground truth comes
   from the engine for free).
5. **llm**: Claude Haiku 4.5 receives the same JSON senses and must answer with one action via
   structured output. An unparseable or unknown answer is logged as `invalid`.

Fallback rule: when a paid player errors, is gated, or is invalid, the executed action is
`stay` (not the solver's move: in this game being rescued would hide exactly what we want to
see). Every record logs `chosen_action`, `executed_action` and `solver_action` separately.

### Fly player

Model: Shiu et al., "A Drosophila computational brain model reveals sensorimotor processing",
Nature 2024; https://github.com/philshiu/Drosophila_brain_model (MIT, Brian2), FlyWire **v783**
connectivity (138,639 neurons, 15.1 M synapses), default parameters, untrained. Neuron IDs by
cell type and side come from the public FlyWire annotations
(https://github.com/flyconnectome/flywire_annotations).

Per decision:
1. `restore()` the network to its clean stored state (0.04 s).
2. Poisson-stimulate the **looming detectors LPLC2 + LC4** of the left eye at `left_hz` and of
   the right eye at `right_hz` (LPLC2 108 L / 102 R, LC4 54 L / 50 R).
3. Simulate a **100 ms** window (about 0.6–0.7 s wall-clock on the user's M1, cython target).
4. Read firing rates:
   - **turn signal** = (DNa01 + DNb01, right) − (DNa01 + DNb01, left); above `+turn_threshold`
     → `right`, below `−turn_threshold` → `left`. These steering neurons fire on the side
     *opposite* a one-sided threat, which turns a fly away from it.
   - **jump signal** = Giant Fiber (DNp01) mean rate over both sides; above `jump_threshold`
     → `jump` (the Giant Fiber is the fly's real escape-jump neuron). Jump wins over a turn.
   - otherwise `stay`.
5. Log into `Decision.info`: the two input rates, every read-out rate, and the spike counts, so
   the viewer can draw the neurons firing.

The two thresholds are the fly's only tuning. They are set once on practice seeds that are not
in the tournament, committed, and displayed on screen.

What the spike measured (36 of 36 one-sided trials): steering neurons fired only on the side
opposite the stimulated eye, graded with intensity (DNa01 ipsi − contra −27 / −39 / −47 Hz at
50 / 150 / 250 Hz), cancelling when both eyes were stimulated; the Giant Fiber fired in every
threat trial, more on the threatened side and graded. DNa02 is inversely graded and is not
used for intensity.

Known weaknesses, to be stated in the viewer and write-up:
- The fly does not plan. It flees gaps reflexively and may dodge into another gap.
- Input is crude: whole-eye stimulation was what the spike tested; partial-field input was not.
- The wiring has a mild built-in left bias (left DNa02 responds more than right).
- The model has no spontaneous activity and no state between decisions, so trial-to-trial
  spread comes only from input noise.
- The ipsilateral-turn role of DNa01/DNa02/DNb01 comes from published steering studies, not
  from anything verified in this project.
- Giant Fiber rates of 100–200 Hz are not realistic (a real one fires about once per escape);
  it is used as a graded signal.

## Architecture

Python package `bakeoff/` in this repo, managed with `uv`, tests with `pytest`.

| Unit | Responsibility | Depends on |
| --- | --- | --- |
| `bakeoff/game/track.py` | Seeded track generator with a guaranteed survivable path (pure) | — |
| `bakeoff/game/engine.py` | Game state, `step(action)`, death and scoring (pure) | track |
| `bakeoff/senses.py` | Engine state → JSON senses and → `(left_hz, right_hz)` (pure) | engine |
| `bakeoff/players/base.py` | `Decision`, `Player` protocol | — |
| `bakeoff/players/random_player.py`, `solver.py` | Baselines | senses |
| `bakeoff/players/fly.py` | Thresholding of brain read-outs into actions | `fly/brain.py` |
| `bakeoff/fly/brain.py` | Build the network once, `restore()` + window per decision, rates by named neuron group | brian2, fly data |
| `bakeoff/fly/neurons.py` | Select FlyWire IDs by cell type and side from the annotations; report coverage | pandas |
| `scripts/fetch_fly_data.py` | Download the model repo and annotations into git-ignored `data/` | — |
| `bakeoff/players/jev.py`, `llm.py` | Paid players | `clients/` |
| `bakeoff/clients/` | Thin Jev and Anthropic clients sharing a disk cache (sha256 of provider, model, senses, questions) and a hard `--max-requests` cap; load keys from `.env` inside the program | typesafe-sdk, anthropic |
| `bakeoff/runner.py` | Players × seeds, streaming JSONL step log, `meta.json` with `schema_version`, `git_sha`, run arguments and final `status` | all above |
| `bakeoff/report.py` | Logs → scoreboard (reads files only) | — |
| `bakeoff/__main__.py` | `uv run python -m bakeoff run|report` | runner, report |
| `viewer/` | Static HTML replay reading a run's JSONL | — |

Carry over from `jev-testing` PR #1, adapting names: `Decision`/`Policy`, the runner's
streaming log and status handling, the report's complete-episodes-only rule, and the review
notes at the end of that repo's phase 1 plan (factory with options, fallback-rate column, run
arguments in `meta.json`, a `RunAborted` subclass for the request cap, guarded `close()`).

### Step record (contract for report and viewer)

`run_id, player, seed, row, lane, senses, looming{left_hz,right_hz}, questions, answers,
chosen_action, executed_action, solver_action, gated, invalid, error, ground_truth{gap_ahead,
left_safe}, alive, rows_survived, latency_ms, usage, cache_hit, info`; the full `track` is
logged once per run in the first record of each seed. `meta.json`: `schema_version`,
`git_sha`, `status` (`running → completed | aborted | budget_exhausted | interrupted`), run
arguments, package versions, model ids, fly thresholds.

## Report

Per player: mean and median rows survived, deaths by cause (ran into gap, jumped into gap,
dodged into gap), agreement with the solver, invalid/error/fallback rates, Noul calibration
(Brier) for Jev, requests, tokens, latency and measured cost per run. Only complete runs count
toward run metrics; interrupted ones are shown as `incomplete`.

## Budget

The fly is free (about 3.5 minutes per 300-row run; run one fly process at a time on the 8 GB
machine). Jev and the LLM cost one request per row survived, so a strong player costs up to
300 requests per track and a weak one dies early. Jev's price per request is unknown until the
first call: phase 3 starts with a single capped track. Cache makes re-runs and replays free.

## Testing

TDD with pytest. Engine, track generator, senses, solver, report and thresholding are pure and
tested directly. Jev and Anthropic are replaced by fakes; no test touches the network. Fly
brain tests are marked `slow` and skipped when `data/` is absent; the fly player's
thresholding is tested with a fake brain. One opt-in `live` test per provider.

## Phases (each gets its own plan)

1. Game engine, track generator, senses, `random` and `solver`, runner, report, CLI. No keys,
   no fly.
2. Fly player: data fetch script, brain wrapper (port of the spike's build-once/restore
   approach, rewritten properly rather than copied), neuron selection, threshold calibration
   on practice seeds, first fly-vs-baselines scoreboard.
3. Jev and LLM players with cache and request cap; first cost numbers from one capped track.
4. Replay viewer.
5. Tournament run and short write-up with the caveats above.

## Open items

- Jev pricing and per-request latency (measured in phase 3).
- The looming weighting function and the two fly thresholds (fixed in phase 2 on practice seeds).
- Whether partial-field looming stimulation (a subset of LPLC2/LC4 cells by position) improves
  the fly's play; out of scope unless phase 2 shows whole-eye input is too blunt.
- A recent community port of the model to Apple MLX claims a large speed-up (unverified); only
  worth testing if fly runs become the bottleneck.
