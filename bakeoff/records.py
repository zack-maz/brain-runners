"""Records, for the Brain Runners records screen: the historical log of past runs (decision 53), and which recorded
episodes a score may count (`pick`), which the Charts screen (bakeoff/charts.py) scores. Reads files only, spends
nothing.

A live session replays tracks, so one (player, seed) can sit in several run directories, which `bench.load`
rightly refuses. `pick` takes each pair from the newest run that completed it and leaves the older copies
out, and says how many it left out."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source
from bakeoff.game.rules import Rules
from bakeoff.report import load_meta, load_steps
from bakeoff.runner import ours_meta
from bakeoff.session import RUN_ID


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


def pick(out_root: Path | str, rules: Rules,
         tracks: tuple[int, int] | None = None) -> tuple[list[Source], int, list[str], list[Source]]:
    """(the sources to score, how many older complete episodes were left out, the run ids that could not be
    read, the stopped episodes). Only runs of this game and length, and only the seeds in `tracks` (first and
    last, inclusive) when it is given. The sources hold complete episodes only. A stopped episode is one its player
    dropped out of (decision 52): unfinished, and named by its run's meta.json `stopped` (that player, that seed).
    The newest such copy of each (player, seed) no run completed is taken. Its decisions count in the failed rate
    and nowhere else (bakeoff/bench.py). Any other episode cut short (an interrupted or crashed run, a run still
    going, an old whole-run abort) is in no number."""
    taken: set[tuple[str, int]] = set()
    sources, left_out, unreadable = [], 0, []
    unfinished: list[tuple[Path, tuple[str, int]]] = []  # newest run first, like the sources
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
                wanted = tracks is None or tracks[0] <= s["seed"] <= tracks[1]
                if wanted and (key not in last or s["row"] > last[key]["row"]):
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
        stops = meta.get("stopped") if isinstance(meta.get("stopped"), dict) else {}
        named = {(player, stop.get("seed")) for player, stop in stops.items() if isinstance(stop, dict)}
        done = {key for key, _ in complete}
        unfinished += [(run_dir, key) for key in last if key not in done and key in named]
    stopped_by_run: dict[Path, set[tuple[str, int]]] = {}
    for run_dir, key in unfinished:  # newest first: the first copy of a pair is the newest
        if key not in taken:
            taken.add(key)
            stopped_by_run.setdefault(run_dir, set()).add(key)
    stopped = [Source(run_dir, episodes=frozenset(keys)) for run_dir, keys in stopped_by_run.items()]
    return sources, left_out, unreadable, stopped


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
    """{game, max_rows, why, runs, ours}: the past runs, and what the "what is ours" panel is written from. The
    numbers are the Charts screen's (bakeoff/charts.py)."""
    out_root = Path(out_root)
    return {"game": rules.version, "max_rows": rules.max_rows,
            "why": None if out_root.is_dir() else "no run has been recorded yet.",
            "runs": past_runs(out_root, current) if out_root.is_dir() else [], "ours": ours_meta(rules)}
