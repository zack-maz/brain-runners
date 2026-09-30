# Data formats

What a run leaves on disk, and what the page draws from it. The runner writes step records (the first part);
`bakeoff/replay.py` turns run directories into the replay data the viewer draws (the second part). Both are
contracts: change one only with its readers.

## Step record and `meta.json` (schema version 1)

The contract between the runner and everything that reads a run: the report and
`bakeoff/replay.py`, which turns run directories into the replay viewer's data
(the replay data, below; the viewer is JavaScript and cannot import Python, so the rules below are
applied once, in Python). The code that writes it is `bakeoff/runner.py`; the spec's "Step record"
section is the short version and points here.

### Files in a run directory

- `meta.json` — one object per run, rewritten when the run ends (see below).
- `<player>.jsonl` — one file per player. One JSON object per line, one line per decision
  (one row of the game). Lines of one seed are contiguous and seeds come in run order. A run
  killed mid-write may leave a truncated last line; readers skip it.

### Two moments in one record

A record is written after the move, so it mixes two moments.

**Moment of decision** (what the player saw and did not yet know): `row`, `lane`, `senses`,
`looming`, `ground_truth`, `solver_action`, `solver_depths`. (`questions`, `answers`,
`chosen_action`, `executed_action`, `gated`, `invalid`, `error` and the latency/usage keys
describe the decision itself.)

**Result of the move**: `alive`, `finished`, `death_cause`, `rows_survived`.

`row` and `lane` are where the runner stood *before* the move. To draw the state after the move,
use the next record's `row`/`lane`, or derive the landing tile as below.

### Step record keys

| key | type | meaning |
| --- | --- | --- |
| `run_id` | string | the run directory name, e.g. `20260919-101500` |
| `player` | string | player name; also the file name |
| `seed` | int | track seed; the track's identity |
| `row` | int | row the runner stands on at decision time (starts at 0) |
| `lane` | int | lane at decision time, `0 .. lanes-1` (starts at `lanes // 2`, i.e. 6) |
| `senses` | object | exactly what the player was shown, see below |
| `looming` | `{left_hz, right_hz}` | floats, the fly's eye rates for these senses: each visible gap adds `gain_hz / row ** falloff` to its eye (own lane: both eyes), the sum is capped at `max_hz` and rounded to the nearest `step_hz` (so 11 levels, 0 to 250). Ours, not the fly's biology |
| `questions` | object or null | what a paid player was asked, else null. Jev (`jev_plain`): `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. `jev_step1`: `{gap_left, gap_stay, gap_right, gap_jump}`, four Nouls. LLM (`haiku_plain`, `glm_plain`): `{system, schema, max_tokens}`; its user message is the `senses` as JSON. Question-set players (`jev_guided`, `jev_step2`, `jev_map`): the set's questions, in Jev's form. Their LLM twins (`llm_<set>`): `{system, schema, max_tokens, questions}`, `questions` being the same set |
| `answers` | object or null | Jev (`jev_plain`): `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. `jev_step1`: `{gap_left: {type, noul}, gap_stay, gap_right, gap_jump}`, each the probability that the action lands on a gap. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Question-set players: one entry per question id in Jev's form (`{noul}` or `{choice}`); an LLM twin's entries are read from its JSON, plus `text` and `stop_reason`. Null after an `error` |
| `chosen_action` | string or null | what the player asked for. May be an invalid string, or null if it gave none |
| `executed_action` | string | what the game ran: `left`, `right`, `jump` or `stay`. Equals `chosen_action` unless a fallback applied |
| `solver_action` | string | the reference solver's move on the same senses: the first action, in the order `stay, left, right, jump`, with the maximum depth |
| `solver_depths` | object | for each of `stay`, `left`, `right`, `jump`, the furthest visible row (1..6, the game's `lookahead`, 6 by default; decision 22) its best continuation reaches; 0 if the first move is not known-safe. Ties are normal |
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
| `info` | object or null | player-specific extras: the fly's activity (below); `{model}` for paid players, the model id the provider reported; `jev_step1` adds `rule` (`"lowest_gap_probability"`) and `order` (its tie-break, `["stay", "left", "right", "jump"]`) |
| `track` | object or null | the full track, present only in the first record of each seed, else null |

The fallback rule: when `gated`, `invalid`, `error` is set, or `chosen_action` is null, the
runner executes `stay`. It is never the solver's move.

#### `senses`

`{lane, lanes, rows_survived, ahead, actions}`. `lane` and `rows_survived` are at decision time
(so `senses.lane == lane`). `lanes` is 12, the tunnel's width (a separate `Rules` field, not changed by
vision experiments). `ahead` has 6 entries, `{row: 1..6, gaps_relative: [...]}`: the gap lanes `row` rows
ahead as offsets from the runner's lane, only within 3 lanes either side (`-3..3`), lane wrap already
applied. The 6 rows and the 3 lanes either side are the game's default `lookahead` and `window`
(`bakeoff/game/rules.py`); a run with a different vision (`--lookahead`, `--window`, decision 22) shows
more or fewer entries here. `actions` maps each action to a description.

#### `info` of the fly

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

#### Paid players

One request per row. `latency_ms` is set only for a live request; `cache_hit: true` means the answer
came from `.cache/responses` and cost nothing. A provider failure sets `error` (`"<ExceptionName>:
<message>"`), leaves `answers` null and executes `stay`. The LLM is `invalid` when its text is not
JSON with a string `action`, the action is unknown, or `stop_reason` is not `end_turn`; Jev is
`invalid` when its choice is missing or unknown. Jev is never `gated`. The two Nouls never influence
the move: they are scored against `ground_truth` (same key names) in the report.

`jev_step1` is asked four Nouls and no Choice; its move is the action with the
lowest Noul after rounding to two decimals, ties in the order of `info.order`. That rule and the
wording of the questions are ours. It is `invalid` when any of the four Nouls is missing or not a
finite number, and never `gated`. The report scores its Nouls (`brier_gap_left` and so on) against what
the record's `senses` show (`bakeoff.senses.lands_on_gap`), since that is what the questions ask;
`ground_truth` keeps its two keys.

The question-set players (`bakeoff/players/question_sets.py`, `set_players.py`) ask one set each: `step1` (the
four Nouls above; Jev's own player is `jev_step1`), `guided` (one Choice whose options name each move's
landing tile), `step2` (the four landing Nouls plus `trapped_<action>`: would every move after this one land on a
gap?) and `map` (`tile_r<row>_<side>`, one Noul per visible tile, e.g. `tile_r2_l3`). `jev_<set>` asks Jev,
`haiku_<set>` asks Claude Haiku and `glm_<set>` GLM Flash the same questions in one structured request. Records
written before decision 44 carry the old names: `"player"` (`jev`, `jev_composed`, `llm_reader`, ...) is read as
the new name by `bakeoff.players.names.canonical()`, and `info.set` keeps the name the set had then (`composed`,
`choice`, `two_step`, `reader`), which nothing reads. The set's rule picks the move from the
answers and is named in `info.rule` (with `info.set` and `info.order`); every wording and every rule is ours. A
decision is `invalid` unless every answer is usable (a Noul a finite number from 0 to 1, the Choice one of the four
moves; for an LLM twin also JSON with `stop_reason` `end_turn`). The report's `brier_all` scores every Noul whose
truth the senses show (`bakeoff.senses.truth_of`).

### The landing tile

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

### `track`

Present only in the first record of each seed (null elsewhere): `{seed, lanes, max_rows, gaps}`.
`gaps[r]` is the sorted list of lane indices that are gaps in row `r`; the list has
`max_rows + lookahead + 2` entries (rows `0 .. max_rows + lookahead + 1`); rows 0 to `runway_rows` are always
empty; a row beyond the list is floor. Lanes wrap. Lookups: gap at (`r`, `l`) iff `r < gaps.length` and
`gaps[r]` contains `((l % lanes) + lanes) % lanes`.

A track's identity is its seed and its game version (`meta.json` `game`): the same seed is a different track
in another version. Within a version the difficulty ramp is fixed (`difficulty_rows`), so a run with a
smaller `max_rows` plays the first rows of the same track (its `gaps` is a prefix of the full track's).
All players on a seed see the same track.

### `meta.json`

| key | type | meaning |
| --- | --- | --- |
| `schema_version` | int | 1. Bumped on any breaking change to this file or the step record |
| `run_id` | string | as above |
| `git_sha` | string or null | commit of the code that ran |
| `git_dirty` | bool or null | uncommitted changes when the run started |
| `started_at`, `finished_at` | string | UTC ISO 8601; `finished_at` is null while running |
| `status` | string | `running`, then `completed`, `aborted`, `budget_exhausted` or `interrupted`; `aborted` or `budget_exhausted` only when every player stopped (decision 52) |
| `stopped` | object, optional | the players that dropped out while the others played on: `{player: {status, reason, seed, row}}`, `status` being `budget_exhausted` (its cap) or `aborted` (six provider errors in a row); absent when nobody stopped |
| `players` | string[] | the players planned for this run, in order |
| `seeds` | int[] | the seeds planned for this run |
| `game` | object | the game's rules (`bakeoff/game/rules.py`): `version` (`v1`, `v2`, or a vision variant such as `v2+look3`), `lanes`, `max_rows`, `lookahead`, `window` (visible lanes each side), `runway_rows`, `start_gap_rate`, `end_gap_rate`, `difficulty_rows`, `max_gap_width`; and `looming: {gain_hz, falloff, step_hz, max_hz, provisional}`. Runs from before game versions have only `lanes`, `max_rows`, `lookahead`, `window` and `looming`, and were played on v1 |
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

## Replay data (replay version 1)

The contract between `bakeoff/replay.py` (Python, which knows the rules of the game) and the
viewer in `viewer/` (JavaScript, which only draws). `uv run python -m bakeoff view <run_dir>...`
builds this object from one or more run directories and embeds it in one HTML file. The step
records it is built from are described above.

### Top level

| key | type | meaning |
| --- | --- | --- |
| `replay_version` | int | 1. Bumped on any breaking change to this object |
| `game` | object or null | the game every run in the replay played (`Rules.to_json()`: `version`, `lanes`, `max_rows`, `lookahead`, `window`, the ramp), null when no run has a `meta.json`. Runs of different games are an error (`ValueError`, exit 2): a seed is a different track in another game. Runs that differ only in `max_rows` are the same game. A `game` block without `version` is v1 |
| `runs` | object[] | one per run directory, in the order given: `run_id` plus these keys of its `meta.json`, null when absent: `status`, `git_sha`, `git_dirty`, `started_at`, `finished_at`, `players`, `seeds`, `game`, `fly`, `models`, `requests`. A directory without `meta.json` is named after the directory |
| `players` | string[] | players with at least one episode, ordered by `CONTESTANTS` in `bakeoff/replay.py`: `fly`, `jev_step1`, `haiku_plain` (the demo's three), then `jev_plain`, `glm_plain`, `fly2`, `jev_guided`, `haiku_guided`, `haiku_step1`, `jev_step2`, `haiku_step2`, `jev_map`, `haiku_map`, `glm_step1`, `glm_guided`, `glm_step2`, `glm_map` (runs recorded under the old names, `llm*` and `jev_composed` and the like, are read as these, decision 44); any player not in that list follows, in the order the runs planned them |
| `seeds` | int[] | every seed with at least one episode, ascending |
| `tracks` | object | `{"<seed>": track}`, the step record's `track`. When runs played the same seed with different `max_rows`, the longest is kept (the shorter one is its prefix) |
| `episodes` | object[] | one per (player, seed), sorted by seed, then by `players` order |
| `scoreboard` | object | `columns`: `run_id` followed by the report's columns; `rows`: the report's rows, one per player per run, in `players` order; `same_seeds`: false when the scoreboard's rows do not all average the same seeds (the means count complete episodes only, so a seed on which a player was cut off, or a player that never started, makes it false), so their means are not a fair comparison and the viewer says so |

One (player, seed) may appear in only one of the run directories, and only once within a run
directory. Two versions of the same episode are an error (`ValueError`, exit 2 from the CLI),
never a silent pick.

### Episode

`player`, `seed`, `run_id`, `complete` (false for a run that was cut off: no death, no finish),
`finished`, `death_cause`, `rows_survived` (all three from the last record), `max_rows` of the run
that played it, `questions` and `frames`.

`questions` lists the distinct `questions` objects of the episode's records, normally one. A frame
points into it with `q`, so the briefing text is stored once and not once per row.

### Frame

A frame is a step record without `run_id`, `player`, `seed`, `senses`, `questions` and `track`,
plus three keys:

| key | type | meaning |
| --- | --- | --- |
| `ahead` | int[][] | the `gaps_relative` lists of `senses.ahead`, nearest row first: what the player was shown |
| `landing` | `[row, lane]` | the tile the executed move lands on, by the rules above ("The landing tile"). For every frame but the last it is the next frame's `row` and `lane`; after a fatal move it is the gap the runner fell into |
| `q` | int or null | index into the episode's `questions`; null when nothing was asked |

Frames are sorted by `row`. A jump advances two rows, so rows are not consecutive.

### How the viewer uses it

The page never reads this object directly: `viewer/feed.js` hands it over as calls (`onMeta` with `game`, then
`onEpisode` and `onFrame` per episode), the same calls a live run makes, so the two cannot drift apart.

### The live stream

`bakeoff live` serves the page with an empty replay (`episodes: []`, the run's entry in `runs`) and
`<body data-live="/events">`, and streams Server-Sent Events from `/events`, built by the same functions as
this object (`bakeoff.replay.frame_of`, `summary_of`):

| event | data |
| --- | --- |
| `episode` | `{episode, track}`: an episode as above without `frames` (`complete` false, `rows_survived` 0), sent once, just before the player's first frame |
| `frame` | `{player, seed, frame, summary}`: one frame as above; `summary` is `{complete, finished, death_cause, rows_survived}` after it |
| `end` | `{status, runs, scoreboard}`: the run's final status and the replay's `runs` and `scoreboard` |
| `error` | `{message}`: why the run stopped early (a request cap, a provider that kept failing) |

A page that connects late or reconnects gets the whole history again; `viewer/feed.js` drops what it
already has. After `end` the page closes the stream.

Replay time is measured in rows and every player is on the same clock: at time `t` every runner
still alive is at row `t`, so they all run the same stretch of one tunnel. The frame on screen is
the last one with `row <= t`; between `row` and `landing[0]` the runner moves from one to the
other (a jump takes two ticks). After the last frame's landing the episode is `dead`, `finished`
or, when `complete` is false, `cut`.

All text from a log (an LLM's answer, an error message, a question) is escaped before it is put
on the page, and the embedded JSON writes every `<` as `\u003c` so nothing in it can end its
`<script>` element. The page loads nothing from the network.
