"""Records, for the Brain Battle records screen (docs/superpowers/specs/2026-09-25-brain-battle-design.md,
section F): the leaderboard and the pairs over the recorded practice tracks 1000 to 1019 of this game, and
the past runs. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here adds a statistic.

A live session replays tracks, so one (player, seed) can sit in several run directories, which `bench.load`
rightly refuses. Records takes each pair from the newest run that completed it and leaves the older copies
out, and says how many it left out.

It ranks on the track select's own practice tracks only (decision 46): the flies' calibration and settle runs
cover 1000 to 1199, and a mean over 120 tracks beside a mean over 5 is not the same comparison."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, benchmark, load
from bakeoff.fly.fly2_rule import PRACTICE_SEEDS  # cheap: no brian2 (bakeoff/fly/__init__.py imports nothing)
from bakeoff.game.rules import Rules
from bakeoff.report import load_meta, load_steps
from bakeoff.runner import ours_meta
from bakeoff.session import FIRST_PRACTICE_SEED, PRACTICE_TRACKS, RUN_ID

# the tracks Records ranks on: the track select's practice tracks
TRACKS = (FIRST_PRACTICE_SEED, FIRST_PRACTICE_SEED + PRACTICE_TRACKS - 1)

# fly2's frozen numbers were fitted on these seeds (calibration/FLY2_REPORT.md, decision 43): a leaderboard
# mean over them is in-sample for fly2 in a way it is not for anyone else, so `records_of` marks it.
TUNED_ON = {"fly2": [min(PRACTICE_SEEDS), max(PRACTICE_SEEDS)]}


def _run_key(name: str) -> tuple[str, int]:
    """(the timestamp, the counter or 0), so `-10` sorts after `-9` (ten runs started in one second, the
    tenth naming itself last)."""
    match = RUN_ID.fullmatch(name)
    suffix = match.group(1) or "" if match else ""
    return (name[: len(name) - len(suffix)] if suffix else name, int(suffix[1:]) if suffix else 0)


def _run_dirs(out_root: Path) -> list[Path]:
    """Every run directory, newest first: only a name shaped like a run id (`session.RUN_ID`) holding a
    meta.json is one; a renamed directory is not a run this page can offer to watch."""
    return sorted((d for d in out_root.iterdir() if d.is_dir() and RUN_ID.fullmatch(d.name) and (d / "meta.json").is_file()),
                  key=lambda d: _run_key(d.name), reverse=True)


def _same_game(meta: dict, rules: Rules) -> bool:
    try:
        recorded = Rules.from_json(meta["game"])
    except (KeyError, TypeError, ValueError):
        return False  # a run from before game versions, or a game block this code cannot read
    return recorded.same_game(rules) and recorded.max_rows == rules.max_rows


def pick(out_root: Path | str, rules: Rules) -> tuple[list[Source], int, list[str]]:
    """(the sources to score, how many older complete episodes were left out, the run ids that could not be
    read). Only the practice tracks in TRACKS, only runs of this game and length, only complete episodes."""
    taken: set[tuple[str, int]] = set()
    sources, left_out, unreadable = [], 0, []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir)
        if meta is None:
            unreadable.append(run_dir.name)  # meta.json exists (_run_dirs required it) but cannot be read
            continue
        if not _same_game(meta, rules):
            continue
        try:
            steps = load_steps(run_dir)
            last: dict[tuple[str, int], dict] = {}
            for s in steps:
                key = (s["player"], s["seed"])
                if TRACKS[0] <= s["seed"] <= TRACKS[1] and (key not in last or s["row"] > last[key]["row"]):
                    last[key] = s
            complete = [(key, step) for key, step in last.items() if step["finished"] or not step["alive"]]
        except Exception:
            # a record that parses but is not one of ours (a missing key, a value of the wrong shape): this
            # run cannot be scored, but it must not take the others down with it (nothing is committed yet)
            unreadable.append(run_dir.name)
            continue
        mine = set()
        for key, _ in complete:
            if key in taken:
                left_out += 1
            else:
                taken.add(key)
                mine.add(key)
        if mine:
            sources.append(Source(run_dir, episodes=frozenset(mine)))
    return sources, left_out, unreadable


def past_runs(out_root: Path | str, current: str | None = None) -> list[dict]:
    """Every run directory's meta.json, newest first. `current` is the run this session is playing: only it can
    be watched live, since the page cannot stream another process's run."""
    runs = []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir) or {}
        game, players, seeds = meta.get("game"), meta.get("players"), meta.get("seeds")
        runs.append({"run_id": run_dir.name, "status": meta.get("status"), "started_at": meta.get("started_at"),
                     "finished_at": meta.get("finished_at"), "seeds": seeds if isinstance(seeds, list) else [],
                     "players": players if isinstance(players, list) else [],
                     "game": game.get("version") if isinstance(game, dict) else None,
                     "current": run_dir.name == current})
    return runs


def records_of(out_root: Path | str, rules: Rules, current: str | None = None) -> dict:
    """{game, max_rows, tracks, bench (bench.benchmark's numbers, or None), why, left_out, unreadable, runs,
    tuned_on, ours}. Like `benchmark_of`, it answers with a reason instead of failing. `tracks` is the first and
    last track ranked; `tuned_on` names the seeds any frozen player's numbers were fitted on, so a leaderboard
    can mark them in-sample for that player; `ours` is what the "what is ours" panel is written from."""
    about = {"tracks": list(TRACKS), "tuned_on": TUNED_ON, "ours": ours_meta(rules)}
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "bench": None, "why": "no run has been recorded yet.",
                "left_out": 0, "unreadable": [], "runs": [], **about}
    sources, left_out, unreadable = pick(out_root, rules)
    numbers, why = None, None
    if not sources:
        why = f"no completed practice track ({TRACKS[0]} to {TRACKS[1]}) of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(sources))
        except (OSError, ValueError) as e:
            why = f"the records could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "bench": numbers, "why": why, "left_out": left_out,
            "unreadable": unreadable, "runs": past_runs(out_root, current), **about}
