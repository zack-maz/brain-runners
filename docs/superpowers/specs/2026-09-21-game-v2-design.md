# Game v2: named game versions, a shorter track, a faster ramp: design

Date: 2026-09-21 · Status: design approved in chat by the user (approach A, sections 1 and 2; "don't need my
approval here, just go" for the rest) · Updates 3 and 6 of `docs/UPDATES.md`, the first of the updates that come
before phase 6 (decision 20) · Extends `docs/superpowers/specs/2026-09-19-tunnel-run-design.md`, still binding where
this document is silent.

## Goal

Make the players separate sooner, on shorter and cheaper runs, while the game stays fair (perfect play almost
always finishes), and make the vision a setting of the game, so a later experiment can compare players at other
depths. Today's game stays playable and viewable, unchanged, as `v1`.

## What the numbers say

Measured on practice seeds 1000–1199 with free players only (throwaway probe scripts, not committed). The solver is
the reference player; it sees only what the contestants see. The fly is the stand-in brain built from the committed
`calibration/response_surface.json`, not the 1 GB simulation.

Vision on 300-row tracks, share of tracks the solver finishes:

| ramp reaches full density at | 1 row | 2 | 3 | 4 | 5 | 6 | 8 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| row 300 (today) | 0% | 60% | 85% | 92% | 96% | 98% | 98% | 98% |
| row 150 | 0% | 30% | 63% | 80% | 88% | 94% | 94% | 98% |
| row 100 | 0% | 28% | 53% | 72% | 86% | 90% | 96% | 97% |

Ramp on 150-row tracks, mean rows / share finished:

| ramp full at | solver, 6 rows | solver, 3 rows | fly (stand-in) | random |
| --- | --- | --- | --- | --- |
| 60 | 148.5 / 98% | 139.3 / 80% | 50.5 / 0% | 18.7 / 0% |
| 80 | 148.5 / 98% | 138.9 / 81% | 59.9 / 0% | 22.2 / 0% |
| **100** | **149.0 / 97%** | **143.9 / 86%** | **67.9 / 0%** | **23.9 / 0%** |
| 120 | 149.2 / 98% | 143.9 / 82% | 77.1 / 0% | 25.3 / 0% |
| 300 | 150.0 / 100% | 150.0 / 100% | 124.0 / 43% | 32.4 / 0% |

Six rows is where more vision stops helping perfect play on today's ramp. The contestants use far less: the fly's
looming weighting falls off with the cube of distance (rows 1–2 carry nearly all of it), the composed Jev asks only
about the tiles it would land on, and only the LLM reads all six rows. So vision stays 6 rows by 3 lanes either side
in v2, and becomes a setting for later experiments.

## Decisions taken in this design

1. The ramp's job is to separate the players sooner (user, 2026-09-21).
2. Vision becomes a setting of the game, not a constant (user).
3. The track gets shorter: 150 rows (user).
4. Approach A, named game versions, with v2 = 150 rows, full density at row 100, 6 rows × 3 lanes either side
   (user).

## Section 1: the game version (`bakeoff/game/rules.py`, new)

A frozen dataclass `Rules`, everything that defines a game:

| field | v1 | v2 |
| --- | --- | --- |
| `version` | `"v1"` | `"v2"` |
| `lanes` | 12 | 12 |
| `max_rows` | 300 | 150 |
| `lookahead` (rows seen) | 6 | 6 |
| `window` (lanes seen either side) | 3 | 3 |
| `runway_rows` | 4 | 4 |
| `start_gap_rate` | 0.04 | 0.04 |
| `end_gap_rate` | 0.16 | 0.16 |
| `difficulty_rows` | 300 | 100 |
| `max_gap_width` | 3 | 3 |

- `RULES = {"v1": V1, "v2": V2}`, `DEFAULT = "v2"`. `rules_for(version)` looks one up and names the known versions
  in its error.
- `Rules.variant(max_rows=None, lookahead=None, window=None)` returns a copy for tests and experiments. A changed
  vision shows in the version, e.g. `v2+look3`, `v2+look8+win4`; unchanged values leave the version alone. A
  different length keeps the version: within one version tracks are prefix-stable (the ramp does not depend on
  `max_rows`), so a shorter run plays the first rows of the same tracks, and `max_rows` is recorded beside it.
- `Rules` refuses a vision in which some action's landing tile is out of sight: `lookahead` at least 2 (a jump
  lands two rows on), `window` from 1 (a dodge lands one lane over) to 5 (half of 12 lanes, less the runner's own).
- `Rules.to_json()` / `Rules.from_json(d)`: the dict recorded in `meta.json`. `from_json` of a `game` block without
  `version` (every run before this change) gives v1 with that block's `max_rows`, `lookahead` and `window`.
- `generate_track(seed, rules)` replaces the module constants of `track.py`. The algorithm is unchanged: two
  independent random streams, the protected safe path, the same gap-rate and gap-width formulas with the numbers
  read from `rules`, track length `max_rows + lookahead + 2`.
- `Track` carries its `rules`. `compute_senses` and `survivable` read vision and length from the track, never from
  module globals, so vision can never disagree with the track it is played on. The solver works from the senses
  alone, so it takes the window as an argument (`solve_depths(senses, window)`); the runner passes the track's, and
  the `solver` player reads it from the game at `reset`. The senses themselves do not change shape, so paid answers
  cached for v1 still replay.
- A test pins v1: for a sample of seeds, the v1 track is identical tile for tile to the generator as it is before
  this change (expected gaps written into the test from the current code). Old runs therefore still replay exactly.
- `--max-rows` stays, as a prefix of the chosen version's tracks (default: the version's full length). Amended while
  prototyping: the approved text removed it, but within a version a shorter track is a prefix of the same game, not a
  different one, and it keeps the fast CLI tests fast.

## Section 2: how the version flows through the code

- CLI: `run` and `live` take `--game` (default `v2`; `v1` stays playable) and `--lookahead N`, `--window N`, which
  apply `variant`; an impossible vision is a usage error (exit 2) before anything is written. `meta.json` `args`
  records all three.
- The record: the `game` block of `meta.json` becomes `rules.to_json()` plus the looming block it carries today.
  `schema_version` stays 1: the step record does not change and old runs still open.
- The runner and `live` take a `Rules` instead of `max_rows`; tracks come from `generate_track(seed, rules)`. Records
  still come from `runner.play_row` and frames from `replay.frame_of`.
- Replay and view: `build_replay` refuses runs whose games (read through `Rules.from_json`, so an old run compares as
  v1) differ in anything but length, with an error naming both runs and both versions. A run without `meta.json`
  has nothing to compare and is let through. The replay object gets a top-level `game` (the first recorded run's
  rules; null when no run has a meta), handed to the page by `Feed` in `onMeta`, and the live page's empty replay
  carries it too. Tracks stay keyed by seed, safe because one replay holds one game; the "keep the longest prefix"
  rule stays for runs of different lengths.
- Viewer: `minds.js`'s hard-coded "six rows" (comment and aria label) reads the lookahead from the data. The page
  shows the version next to the track number (e.g. "track 1001 · v2").
- Seeds: unchanged rule. Practice seeds are 1000 and up, no paid request below 1000 without `--tournament`. A seed
  names a different track in each version. The paid-answer cache is keyed by the senses, so identical senses may
  reuse an answer, which is correct.

## Section 3: the players and the honesty surface

- The fly's looming weighting and thresholds stay frozen (`calibration/REPORT.md`). `bakeoff/fly/calibrate.py` is
  pinned to v1: the frozen numbers were fixed on v1 tracks and must stay reproducible exactly as they were. The
  write-up and the page say the fly was calibrated on v1 and never retuned for v2.
- The composed Jev, the one-shot Jev, the LLM and the baselines need no change: they read the senses, which now
  come from the track's rules. The LLM's prompt lists however many rows the senses carry.
- Nothing in this work spends money. v2 has no paid runs yet; the first one is a later step that needs the user's
  budget go-ahead (the runbook in `DECISIONS.md` says so).

## Testing

TDD, fast tests only, no network. New `tests/test_rules.py` (presets, `with_vision` naming, JSON round trip,
old-block fallback to v1). `tests/test_track.py`: the v1 pin, v2 length and ramp, survivability of v2 tracks on a
seed sample. Senses and solver follow the track's lookahead and window. Runner and live record the rules. CLI:
`--game`, `--lookahead`, `--window`, unknown version error, `--max-rows` gone. Replay: mixed versions refused, an old
meta without `version` reads as v1. Viewer JS test: the senses label uses the lookahead. `uv run pytest` green;
no slow test needed (the fly brain is untouched).

## Docs to update

`CLAUDE.md` status line, `docs/DECISIONS.md` (decisions 21–24 from this design, next step),
`docs/UPDATES.md` (items 3 and 6 designed), `docs/REPLAY_DATA.md` (top-level `game`), `docs/EXPLAINER.html` (the
game section: 150 rows, the ramp, versions).

## Non-goals

- No new players, no change to any player's logic, no retuning of the fly.
- No paid run, no rerun of old runs; v1 runs stay as they are and open under v1.
- No tournament; no seed decision for it.
