# Step record and `meta.json` (schema version 1)

The contract between the runner (Python) and the phase 4 replay viewer (JavaScript, which cannot
import Python). The code that writes it is `bakeoff/runner.py`; the spec's "Step record" section
is the short version and points here.

## Files in a run directory

- `meta.json` — one object per run, rewritten when the run ends (see below).
- `<player>.jsonl` — one file per player. One JSON object per line, one line per decision
  (one row of the game). Lines of one seed are contiguous and seeds come in run order. A run
  killed mid-write may leave a truncated last line; readers skip it.

## Two moments in one record

A record is written after the move, so it mixes two moments.

**Moment of decision** (what the player saw and did not yet know): `row`, `lane`, `senses`,
`looming`, `ground_truth`, `solver_action`, `solver_depths`. (`questions`, `answers`,
`chosen_action`, `executed_action`, `gated`, `invalid`, `error` and the latency/usage keys
describe the decision itself.)

**Result of the move**: `alive`, `finished`, `death_cause`, `rows_survived`.

`row` and `lane` are where the runner stood *before* the move. To draw the state after the move,
use the next record's `row`/`lane`, or derive the landing tile as below.

## Step record keys

| key | type | meaning |
| --- | --- | --- |
| `run_id` | string | the run directory name, e.g. `20260919-101500` |
| `player` | string | player name; also the file name |
| `seed` | int | track seed; the track's identity |
| `row` | int | row the runner stands on at decision time (starts at 0) |
| `lane` | int | lane at decision time, `0 .. lanes-1` (starts at `lanes // 2`, i.e. 6) |
| `senses` | object | exactly what the player was shown, see below |
| `looming` | `{left_hz, right_hz}` | floats, the same senses as the fly's eye rates, capped at `max_hz`. Provisional and ours, not the fly's biology |
| `questions` | object or null | questions put to the player (Jev / LLM), else null |
| `answers` | object or null | the player's answers, else null |
| `chosen_action` | string or null | what the player asked for. May be an invalid string, or null if it gave none |
| `executed_action` | string | what the game ran: `left`, `right`, `jump` or `stay`. Equals `chosen_action` unless a fallback applied |
| `solver_action` | string | the reference solver's move on the same senses: the first action, in the order `stay, left, right, jump`, with the maximum depth |
| `solver_depths` | object | for each of `stay`, `left`, `right`, `jump`, the furthest visible row (1..6) its best continuation reaches; 0 if the first move is not known-safe. Ties are normal |
| `gated` | bool | the player was blocked by a threshold and produced no move (fallback applies) |
| `invalid` | bool | the chosen action was not one of the four (fallback applies) |
| `error` | string or null | player error text (API failure etc.); the fallback applies |
| `ground_truth` | `{gap_ahead, left_safe}` | bools at decision time: is (`row+1`, `lane`) a gap; is (`row+1`, `lane-1`) safe |
| `alive` | bool | after the move: false if the runner died |
| `finished` | bool | after the move: true if the runner reached the finish line alive |
| `death_cause` | string or null | `ran_into_gap` (executed `stay`), `jumped_into_gap`, `dodged_into_gap` (executed `left` or `right`); null if alive |
| `rows_survived` | int | after the move, the rows cleared, capped at `max_rows`. A fatal jump still counts the row it flew over |
| `latency_ms` | float or null | wall time of a live call; null for players with no call |
| `usage` | object or null | `{input_tokens, output_tokens}` for paid players |
| `cache_hit` | bool | the answer came from the response cache (no request, no cost) |
| `info` | object or null | player-specific extras (e.g. fly activity), free-form |
| `track` | object or null | the full track, present only in the first record of each seed, else null |

The fallback rule: when `gated`, `invalid`, `error` is set, or `chosen_action` is null, the
runner executes `stay`. It is never the solver's move.

### `senses`

`{lane, lanes, rows_survived, ahead, actions}`. `lane` and `rows_survived` are at decision time
(so `senses.lane == lane`). `lanes` is 12. `ahead` has 6 entries, `{row: 1..6, gaps_relative: [...]}`:
the gap lanes `row` rows ahead as offsets from the runner's lane, only within 3 lanes either side
(`-3..3`), lane wrap already applied. `actions` maps each action to a description.

## The landing tile

Given `row`, `lane` and `executed_action` (`lanes` from `track.lanes`):

- rows advanced: 2 for `jump`, otherwise 1;
- lane after: `lane - 1` for `left`, `lane + 1` for `right`, else `lane`, then wrapped into
  `0 .. lanes-1` (`((l % lanes) + lanes) % lanes` in JavaScript; lane 0 going left lands on lane 11);
- landing = (`row + advance`, lane after).

A `jump` flies over row `row + 1` and never checks it; only the landing tile can kill. The
landing tile is a gap exactly when the record says `alive: false`. **On death the runner never
reaches that tile**: it stays on (`row`, `lane`), and no further record follows; draw the death
at the landing tile. A landing row past `max_rows` (a jump from `max_rows - 1`) is past the finish
line and cannot kill. `finished` is true when the runner's row after the move is `>= max_rows`.

## `track`

Present only in the first record of each seed (null elsewhere): `{seed, lanes, max_rows, gaps}`.
`gaps[r]` is the sorted list of lane indices that are gaps in row `r`; the list has
`max_rows + 8` entries (rows `0 .. max_rows + 7`); rows 0 to 4 are always empty; a row beyond
the list is floor. Lanes wrap. Lookups: gap at (`r`, `l`) iff `r < gaps.length` and
`gaps[r]` contains `((l % lanes) + lanes) % lanes`.

A track's identity is its seed: the difficulty ramp is fixed at 300 rows, so a run with a smaller
`max_rows` plays the first rows of the same track (its `gaps` is a prefix of the 300-row
`gaps`). All players on a seed see the same track.

## `meta.json`

| key | type | meaning |
| --- | --- | --- |
| `schema_version` | int | 1. Bumped on any breaking change to this file or the step record |
| `run_id` | string | as above |
| `git_sha` | string or null | commit of the code that ran |
| `git_dirty` | bool or null | uncommitted changes when the run started |
| `started_at`, `finished_at` | string | UTC ISO 8601; `finished_at` is null while running |
| `status` | string | `running`, then `completed`, `aborted`, `budget_exhausted` or `interrupted` |
| `players` | string[] | the players planned for this run, in order |
| `seeds` | int[] | the seeds planned for this run |
| `game` | object | `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `looming: {gain_hz, max_hz, provisional}` |
| `args` | object | the CLI arguments |
| `python` | string | interpreter version |
| `versions` | object | `brian2`, `typesafe-sdk`, `anthropic` versions or null |

A run that is not `completed` may lack records for some players or seeds; compare `players` and
`seeds` with the files to see what is missing.
