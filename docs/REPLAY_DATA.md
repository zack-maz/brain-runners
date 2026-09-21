# Replay data (replay version 1)

The contract between `bakeoff/replay.py` (Python, which knows the rules of the game) and the
viewer in `viewer/` (JavaScript, which only draws). `uv run python -m bakeoff view <run_dir>...`
builds this object from one or more run directories and embeds it in one HTML file. The step
records it is built from are described in `docs/STEP_RECORD.md`.

## Top level

| key | type | meaning |
| --- | --- | --- |
| `replay_version` | int | 1. Bumped on any breaking change to this object |
| `runs` | object[] | one per run directory, in the order given: `run_id` plus these keys of its `meta.json`, null when absent: `status`, `git_sha`, `git_dirty`, `started_at`, `finished_at`, `players`, `seeds`, `game`, `fly`, `models`, `requests`. A directory without `meta.json` is named after the directory |
| `players` | string[] | players with at least one episode: `fly`, `jev_composed`, `llm` (the demo's three), then `jev`, then the others in the order the runs planned them |
| `seeds` | int[] | every seed with at least one episode, ascending |
| `tracks` | object | `{"<seed>": track}`, the step record's `track`. When runs played the same seed with different `max_rows`, the longest is kept (the shorter one is its prefix) |
| `episodes` | object[] | one per (player, seed), sorted by seed, then by `players` order |
| `scoreboard` | object | `columns`: `run_id` followed by the report's columns; `rows`: the report's rows, one per player per run, in `players` order; `same_seeds`: false when the scoreboard's rows do not all average the same seeds (the means count complete episodes only, so a seed on which a player was cut off, or a player that never started, makes it false), so their means are not a fair comparison and the viewer says so |

One (player, seed) may appear in only one of the run directories, and only once within a run
directory. Two versions of the same episode are an error (`ValueError`, exit 2 from the CLI),
never a silent pick.

## Episode

`player`, `seed`, `run_id`, `complete` (false for a run that was cut off: no death, no finish),
`finished`, `death_cause`, `rows_survived` (all three from the last record), `max_rows` of the run
that played it, `questions` and `frames`.

`questions` lists the distinct `questions` objects of the episode's records, normally one. A frame
points into it with `q`, so the briefing text is stored once and not once per row.

## Frame

A frame is a step record without `run_id`, `player`, `seed`, `senses`, `questions` and `track`,
plus three keys:

| key | type | meaning |
| --- | --- | --- |
| `ahead` | int[][] | the `gaps_relative` lists of `senses.ahead`, nearest row first: what the player was shown |
| `landing` | `[row, lane]` | the tile the executed move lands on, by the rules in `docs/STEP_RECORD.md` ("The landing tile"). For every frame but the last it is the next frame's `row` and `lane`; after a fatal move it is the gap the runner fell into |
| `q` | int or null | index into the episode's `questions`; null when nothing was asked |

Frames are sorted by `row`. A jump advances two rows, so rows are not consecutive.

## How the viewer uses it

Replay time is measured in rows and every player is on the same clock: at time `t` every runner
still alive is at row `t`, so the columns show the same stretch of track. The frame on screen is
the last one with `row <= t`; between `row` and `landing[0]` the runner moves from one to the
other (a jump takes two ticks). After the last frame's landing the episode is `dead`, `finished`
or, when `complete` is false, `cut`.

All text from a log (an LLM's answer, an error message, a question) is escaped before it is put
on the page, and the embedded JSON writes every `<` as `\u003c` so nothing in it can end its
`<script>` element. The page loads nothing from the network.
