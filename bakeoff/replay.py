"""Run directories -> one replay object for the viewer. Reads files only.

The viewer is JavaScript and cannot import Python, so everything that needs the rules of the game
(where a move lands, which run is complete, the scoreboard) is worked out here and tested here.
The format is described in docs/REPLAY_DATA.md."""

from __future__ import annotations

from pathlib import Path

from bakeoff.report import COLUMNS, load_meta, load_steps, summarize

REPLAY_VERSION = 1
CONTESTANTS = ("fly", "jev", "llm")  # shown first, in this order; everyone else in order of appearance
# what a frame leaves out of its step record: the first three name the episode, the others are
# replaced by `ahead`, `q` and the replay's `tracks`
DROPPED = ("run_id", "player", "seed", "senses", "questions", "track")
META_KEYS = ("status", "git_sha", "git_dirty", "started_at", "finished_at", "players", "seeds", "game", "fly",
             "models", "requests")


def landing(row: int, lane: int, executed_action: str, lanes: int) -> list[int]:
    """The tile a move lands on (docs/STEP_RECORD.md, "The landing tile"). On a death the runner
    never reaches it; the viewer draws the fall there."""
    advance = 2 if executed_action == "jump" else 1
    shift = {"left": -1, "right": 1}.get(executed_action, 0)
    return [row + advance, (lane + shift) % lanes]


def _episode(player: str, seed: int, run_id: str, steps: list[dict]) -> tuple[dict, dict | None]:
    steps = sorted(steps, key=lambda s: s["row"])
    for prev, cur in zip(steps, steps[1:]):
        if cur["row"] <= prev["row"]:
            raise ValueError(f"{player} on seed {seed} appears more than once in {run_id}")
    track = next((s["track"] for s in steps if s.get("track")), None)
    lanes = track["lanes"] if track else steps[0]["senses"]["lanes"]
    questions: list[dict] = []
    frames = []
    for s in steps:
        frame = {k: v for k, v in s.items() if k not in DROPPED}
        frame["ahead"] = [entry["gaps_relative"] for entry in s["senses"]["ahead"]]
        frame["landing"] = landing(s["row"], s["lane"], s["executed_action"], lanes)
        frame["q"] = None
        if s.get("questions") is not None:
            if s["questions"] not in questions:
                questions.append(s["questions"])
            frame["q"] = questions.index(s["questions"])
        frames.append(frame)
    last = steps[-1]
    episode = {"player": player, "seed": seed, "run_id": run_id,
               # a run cut off mid-way (abort, budget stop, Ctrl-C) is incomplete, not a death
               "complete": bool(last["finished"] or not last["alive"]),
               "finished": last["finished"], "death_cause": last["death_cause"],
               "rows_survived": last["rows_survived"], "max_rows": track["max_rows"] if track else None,
               "questions": questions, "frames": frames}
    return episode, track


def build_replay(run_dirs: list[Path | str]) -> dict:
    """Merge one or more run directories (the fly and the paid players usually run separately).
    A player may appear in several runs, but one (player, seed) only once: two versions of the
    same episode would let the viewer show either, so that is an error, not a silent pick."""
    runs, episodes, tracks, scoreboard = [], [], {}, []
    owner: dict[tuple[str, int], str] = {}
    for run_dir in map(Path, run_dirs):
        steps = load_steps(run_dir)
        meta = load_meta(run_dir)
        run_id = (meta or {}).get("run_id") or run_dir.name
        runs.append({"run_id": run_id, **{k: (meta or {}).get(k) for k in META_KEYS}})
        grouped: dict[tuple[str, int], list[dict]] = {}
        for s in steps:
            grouped.setdefault((s["player"], s["seed"]), []).append(s)
        for (player, seed), group in grouped.items():
            if (player, seed) in owner:
                raise ValueError(f"{player} on seed {seed} is in both {owner[(player, seed)]} and {run_id}; "
                                 "pass only one of them")
            owner[(player, seed)] = run_id
            episode, track = _episode(player, seed, run_id, group)
            episodes.append(episode)
            # a run with a smaller max_rows plays a prefix of the same track: keep the longest
            if track and len(track["gaps"]) > len(tracks.get(str(seed), {}).get("gaps", ())):
                tracks[str(seed)] = track
        scoreboard += [{"run_id": run_id, **row} for row in summarize(steps, meta)]

    # the order the runs planned them in (the log files alone would give alphabetical order)
    planned = [p for run in runs for p in run["players"] or ()] + [e["player"] for e in episodes]
    seen = [p for p in dict.fromkeys(planned) if any(e["player"] == p for e in episodes)]
    players = [p for p in CONTESTANTS if p in seen] + [p for p in seen if p not in CONTESTANTS]
    episodes.sort(key=lambda e: (e["seed"], players.index(e["player"])))
    scoreboard.sort(key=lambda r: players.index(r["player"]) if r["player"] in players else len(players))
    seeds_of: dict[tuple[str, str], set[int]] = {}
    for e in episodes:
        seeds_of.setdefault((e["run_id"], e["player"]), set()).add(e["seed"])
    return {
        "replay_version": REPLAY_VERSION, "runs": runs, "players": players,
        "seeds": sorted({e["seed"] for e in episodes}), "tracks": tracks, "episodes": episodes,
        "scoreboard": {"columns": ["run_id", *COLUMNS], "rows": scoreboard,
                       # true only when every scoreboard row (one per run, player) covers the same seeds;
                       # means over different seeds are not a fair comparison, and the viewer says so
                       "same_seeds": len({frozenset(s) for s in seeds_of.values()}) <= 1},
    }
