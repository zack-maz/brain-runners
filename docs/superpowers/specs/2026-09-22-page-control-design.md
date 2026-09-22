# Items 4, 5, 8, 9: the page runs the show: design

Date: 2026-09-22 · Status: approved by the user in chat ("okay looks good") · Items 4, 5, 8 and 9 of
`docs/UPDATES.md` · Decision 35 of `docs/DECISIONS.md` · Builds on the demo player
(`docs/superpowers/specs/2026-09-20-demo-player-design.md`, binding) and the benchmark
(`docs/superpowers/specs/2026-09-22-benchmark-design.md`)

## Goal

The page stops being a viewer of what the command line chose. It picks the track and the runners, starts and
cancels a live run, shows each mind's full running log, and keeps the analysis out of the way of the race.

Built in two parts, each with its own plan: **3a** the server and the lobby (A, B, C below), **3b** the panels and
the tabs (D, E, F). A replay file opened from disk has no server and shows none of the controls.

## A. The control channel (`bakeoff/live_server.py`, `bakeoff/live.py`)

Loopback only, as today, and every request carries a token minted at startup and embedded in the page, so another
program on this machine cannot drive the run.

| route | what it does |
| --- | --- |
| `GET /state` | what can be run: the players (each with `paid`, its measured price per request, whether its answers for this track are already cached), the session's remaining cap, whether seeds below 1000 are allowed, the game version, and what is happening now (`lobby`, `running`, `finished`, with the run directory) |
| `POST /run` | `{seed, players}`: validate, then start. Refusals name the reason: unknown player, duplicate, a paid player with no cap left, a seed below 1000 without `--tournament`, a run already going |
| `POST /cancel` | stop the current run; it closes as a normal run directory with status `interrupted` |
| `GET /events` | unchanged: the frames of the run, Server-Sent Events |

`LiveRun` gains: it is built per run rather than per command, and the server owns a session that can hold one run
at a time. The records still come from `runner.play_row` and the frames from `replay.frame_of`; that stays.

## B. Money safety

The command sets the ceiling and nothing the page does can raise it:

- `--max-requests N` is the most the **session** may spend per paid player, not per run. The server keeps one
  budget per paid player for its lifetime, and `/state` reports what is left.
- A seed below 1000 is refused unless the command was started with `--tournament`.
- The page must show, before starting, the worst case of the run it is about to ask for: for each paid player,
  requests left of the track × its measured price (`docs/COSTS.md`), and "0 USD (free tier)" for GLM. The user
  confirms in the browser. The server refuses anything beyond the ceiling whatever the page sends.
- With the default cap of 0 the page may still start runs: paid players then replay what is cached and stop at
  their first uncached question, exactly as the command does today.

## C. The lobby (`viewer/`)

`bakeoff live` with no `--seed` and no `--players` opens the page with nothing chosen: a track number, the player
list (paid ones marked, with their estimate and whether the track is already cached), and a start button. When a
run ends the page returns to the lobby with the finished run still on screen, so another track can be set up
without restarting the command. `--seed`, `--players` and a new `--start` keep today's behaviour: chosen on the
command line, playing at once.

## D. A log in every mind panel (item 4)

Each panel in the mind strip gains an expander with that mind's running log, newest last, one line per row: the
row, what it was asked, what it answered, latency, cache hit, and any error in `--bad`. The fly's lines carry its
looming rates, its read-out signals and its spike counts. Nothing new is streamed: the log is built from the
frames the strip already receives, and every value from a log goes through `Minds.esc`. The expander is closed by
default, one panel at a time open, and keeps its scroll while the run continues.

## E. Two tabs (item 8)

- **Run**: the tunnel, the mind strip with its logs, the transport, the lobby controls.
- **Analysis**: the level table, the scoreboard, the findings, the "what is ours" notes, and the benchmark, drawn
  by `viewer/bench.js` from a `bench.json` written into the page by `bakeoff/view.py` (`bakeoff bench`'s numbers
  for the same run directories). Live runs show it once the run has ended.

The tabs are plain buttons over one page, no routing, no build step; the tab in focus is remembered while the page
is open. A replay file behaves the same, minus the controls.

## F. The player picker governs both (item 9)

One control lists the players. In a replay it shows and hides runners (what the level table does today); live it
chooses who runs. The demo's default three stay the default in a replay.

## Testing

Python: the routes (validation, refusals, the token, the ceiling, cancel), a session that runs twice, `--start`
and the flags' defaults, and that a paid run over the ceiling is refused. No test touches the network or a
provider: the live tests use free players, as today. JavaScript: the lobby's state machine, the estimate text, the
log lines' escaping, and the tab switch, in `viewer/tests/*.test.js` through `node --test`.

## Not in scope

No remote access (loopback only), no authentication beyond the local token, no editing of a recorded run from the
page, no new statistics (the Analysis tab shows what `bench.py` already computes).
