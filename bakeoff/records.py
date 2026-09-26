"""Records, for the Brain Battle records screen (docs/superpowers/specs/2026-09-25-brain-battle-design.md,
section F): the leaderboard and the pairs over every recorded practice track of this game, and the past
runs. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here adds a statistic.

A live session replays tracks, so one (player, seed) can sit in several run directories, which `bench.load`
rightly refuses. Records takes each pair from the newest run that completed it and leaves the older copies
out, and says how many it left out."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, benchmark, load
from bakeoff.game.rules import Rules
from bakeoff.report import load_meta, load_steps
from bakeoff.session import FIRST_PRACTICE_SEED


def _run_dirs(out_root: Path) -> list[Path]:
    """Every run directory, newest first (run ids are timestamps)."""
    return sorted((d for d in out_root.iterdir() if d.is_dir() and (d / "meta.json").is_file()),
                  key=lambda d: d.name, reverse=True)


def _same_game(meta: dict, rules: Rules) -> bool:
    try:
        recorded = Rules.from_json(meta["game"])
    except (KeyError, TypeError, ValueError):
        return False  # a run from before game versions, or a game block this code cannot read
    return recorded.same_game(rules) and recorded.max_rows == rules.max_rows


def pick(out_root: Path | str, rules: Rules) -> tuple[list[Source], int, list[str]]:
    """(the sources to score, how many older complete episodes were left out, the run ids that could not be
    read). Only practice seeds, only runs of this game and length, only complete episodes."""
    taken: set[tuple[str, int]] = set()
    sources, left_out, unreadable = [], 0, []
    for run_dir in _run_dirs(Path(out_root)):
        meta = load_meta(run_dir) or {}
        if not _same_game(meta, rules):
            continue
        try:
            steps = load_steps(run_dir)
        except (OSError, ValueError):
            unreadable.append(run_dir.name)
            continue
        last: dict[tuple[str, int], dict] = {}
        for s in steps:
            key = (s["player"], s["seed"])
            if s["seed"] >= FIRST_PRACTICE_SEED and (key not in last or s["row"] > last[key]["row"]):
                last[key] = s
        mine = set()
        for key, step in last.items():
            if not (step["finished"] or not step["alive"]):
                continue  # stopped part way: not a result, and a newer or older complete one may stand in
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
        runs.append({"run_id": run_dir.name, "status": meta.get("status"), "started_at": meta.get("started_at"),
                     "finished_at": meta.get("finished_at"), "seeds": meta.get("seeds") or [],
                     "players": meta.get("players") or [], "game": (meta.get("game") or {}).get("version"),
                     "current": run_dir.name == current})
    return runs


def records_of(out_root: Path | str, rules: Rules, current: str | None = None) -> dict:
    """{game, max_rows, bench (bench.benchmark's numbers, or None), why, left_out, unreadable, runs}. Like
    `benchmark_of`, it answers with a reason instead of failing."""
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "bench": None, "why": "no run has been recorded yet.",
                "left_out": 0, "unreadable": [], "runs": []}
    sources, left_out, unreadable = pick(out_root, rules)
    numbers, why = None, None
    if not sources:
        why = f"no completed practice track of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(sources))
        except (OSError, ValueError) as e:
            why = f"the records could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "bench": numbers, "why": why, "left_out": left_out,
            "unreadable": unreadable, "runs": past_runs(out_root, current)}
