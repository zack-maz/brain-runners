# Step record and `meta.json` (schema version 1)

The contract between the runner and everything that reads a run: the report and
`bakeoff/replay.py`, which turns run directories into the replay viewer's data
(`docs/REPLAY_DATA.md`; the viewer is JavaScript and cannot import Python, so the rules below are
applied once, in Python). The code that writes it is `bakeoff/runner.py`; the spec's "Step record"
section is the short version and points here.

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
| `looming` | `{left_hz, right_hz}` | floats, the fly's eye rates for these senses: each visible gap adds `gain_hz / row ** falloff` to its eye (own lane: both eyes), the sum is capped at `max_hz` and rounded to the nearest `step_hz` (so 11 levels, 0 to 250). Ours, not the fly's biology |
| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. Composed Jev: `{gap_left, gap_stay, gap_right, gap_jump}`, four Nouls. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON |
| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. Composed Jev: `{gap_left: {type, noul}, gap_stay, gap_right, gap_jump}`, each the probability that the action lands on a gap. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Null after an `error` |
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
| `usage` | object or null | `{input_tokens, output_tokens}` for paid players, as reported by the provider (also on a cache hit: what the original request used) |
| `cache_hit` | bool | the answer came from the response cache (no request, no cost) |
| `info` | object or null | player-specific extras: the fly's activity (below); `{model}` for paid players, the model id the provider reported; the composed Jev adds `rule` (`"lowest_gap_probability"`) and `order` (its tie-break, `["stay", "left", "right", "jump"]`) |
| `track` | object or null | the full track, present only in the first record of each seed, else null |

The fallback rule: when `gated`, `invalid`, `error` is set, or `chosen_action` is null, the
runner executes `stay`. It is never the solver's move.

### `senses`

`{lane, lanes, rows_survived, ahead, actions}`. `lane` and `rows_survived` are at decision time
(so `senses.lane == lane`). `lanes` is 12. `ahead` has 6 entries, `{row: 1..6, gaps_relative: [...]}`:
the gap lanes `row` rows ahead as offsets from the runner's lane, only within 3 lanes either side
(`-3..3`), lane wrap already applied. `actions` maps each action to a description.

### `info` of the fly

One object per decision, everything the viewer needs to draw the fly's "mind". Neuron-group keys
are `<cell type>_<side>`: `DNa01`, `DNb01` (steering), `DNp01` (Giant Fiber) and `DNa02` (logged
only, never decides), each `_left` and `_right`; every group is a single neuron.

| key | type | meaning |
| --- | --- | --- |
| `left_hz`, `right_hz` | float | Poisson rate given to the LPLC2 + LC4 looming detectors of each eye (equals `looming`) |
| `noise_seed` | int | seed of this decision's input noise, `crc32("fly:{seed}:{row}")`; the same seed repeats the window exactly |
| `rates_hz` | object | firing rate of each group over the window |
| `spike_counts` | object | spikes of each group in the window |
| `spike_times_ms` | object | spike times of each group, ms from the start of the window |
| `total_spikes` | int | spikes in the whole brain during the window |
| `turn_signal_hz` | float | (DNa01 + DNb01, right) − (DNa01 + DNb01, left); above `turn_threshold_hz` → `right`, below its negative → `left` |
| `jump_signal_hz` | float | Giant Fiber mean over both sides; above `jump_threshold_hz` → `jump`, which wins over a turn |
| `turn_threshold_hz`, `jump_threshold_hz` | float | the fly's only tuning (ours), as used for this decision |
| `wall_ms` | float | wall-clock time of the simulated window |

### Paid players

One request per row. `latency_ms` is set only for a live request; `cache_hit: true` means the answer
came from `.cache/responses` and cost nothing. A provider failure sets `error` (`"<ExceptionName>:
<message>"`), leaves `answers` null and executes `stay`. The LLM is `invalid` when its text is not
JSON with a string `action`, the action is unknown, or `stop_reason` is not `end_turn`; Jev is
`invalid` when its choice is missing or unknown. Jev is never `gated`. The two Nouls never influence
the move: they are scored against `ground_truth` (same key names) in the report.

The composed Jev (`jev_composed`) is asked four Nouls and no Choice; its move is the action with the
lowest Noul after rounding to two decimals, ties in the order of `info.order`. That rule and the
wording of the questions are ours. It is `invalid` when any of the four Nouls is missing or not a
finite number, and never `gated`. The report scores its Nouls (`brier_gap_left` and so on) against what
the record's `senses` show (`bakeoff.senses.lands_on_gap`), since that is what the questions ask;
`ground_truth` keeps its two keys.

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
| `game` | object | `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `looming: {gain_hz, falloff, step_hz, max_hz, provisional}` |
| `fly` | object | `turn_threshold_hz`, `jump_threshold_hz`, `window_ms`, `provisional` (true until calibrated), `model_commit`, `annotations_commit` |
| `models` | object | `{player: model id}` for paid players in the run, e.g. `{"jev": "jev-latest", "llm": "claude-haiku-4-5-20251001"}` |
| `requests` | object | `{player: {max, used}}` for paid players: the `--max-requests` cap and the live requests spent against it, failed ones included. Written at the start with `used: 0` and rewritten when the run ends, so a crashed run may show a stale count |
| `args` | object | the CLI arguments |
| `python` | string | interpreter version |
| `versions` | object | `brian2`, `cython`, `numpy`, `typesafe-sdk`, `anthropic`, `python-dotenv` versions or null |

Added in phase 2 without a version bump (additions only): `fly`, `game.looming.falloff`,
`game.looming.step_hz`, and the `cython` / `numpy` entries of `versions`. Runs made before phase 2
lack them, and their `looming` values were computed with the old weighting (`100 / row`, not
rounded), so a reader must treat these keys as optional and read the weighting from
`game.looming`, not assume it.

Added in phase 3 without a version bump (additions only): `models`, `requests`, `args.max_requests`,
`args.cache`, `args.tournament` and the `python-dotenv` entry of `versions`. Readers must treat them
as optional.

A run that is not `completed` may lack records for some players or seeds; compare `players` and
`seeds` with the files to see what is missing.
