"""uv run python -m bakeoff run|report|view"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
from bakeoff.game.track import MAX_ROWS
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.replay import build_replay
from bakeoff.report import format_table, load_meta, load_steps, summarize
from bakeoff.runner import RunAborted, Runner
from bakeoff.view import render_html

# tournament seeds are below this and must not be paid for, or shape prompts, before the tournament
FIRST_PRACTICE_SEED = 1000


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakeoff")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run players over seeded tracks")
    run.add_argument("--players", default="random,solver", help=f"comma-separated; available: {sorted(REGISTRY)}")
    run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
    run.add_argument("--seed-start", type=int, default=0,
                     help="first seed; practice seeds must not overlap tournament seeds")
    run.add_argument("--max-rows", type=int, default=MAX_ROWS)
    run.add_argument("--out", default="runs")
    run.add_argument("--max-requests", type=int, default=0,
                     help="hard cap on live requests for EACH paid player (jev, llm); the default 0 only replays "
                          "the cache. Worst case a run spends this many requests per paid player")
    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    run.add_argument("--tournament", action="store_true",
                     help="allows live paid requests on seeds below 1000; for the phase 5 tournament only")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
    return parser


def _print_report(run_dir) -> None:
    meta = load_meta(run_dir)
    print(f"status: {meta.get('status', 'unknown') if meta else 'unknown'}")
    print(format_table(summarize(load_steps(run_dir), meta)))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "report":
        try:
            _print_report(args.run_dir)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 2
        return 0
    if args.command == "view":
        try:
            replay = build_replay(args.run_dirs)
        except (FileNotFoundError, ValueError) as e:
            print(e, file=sys.stderr)
            return 2
        if not replay["episodes"]:
            print("no step records in " + ", ".join(args.run_dirs), file=sys.stderr)
            return 2
        output = Path(args.output)
        try:
            output.write_text(render_html(replay), encoding="utf-8")
        except OSError as e:
            print(f"cannot write {output}: {e}", file=sys.stderr)
            return 2
        print(f"replay: {output} ({len(replay['episodes'])} episodes, {output.stat().st_size / 1e6:.1f} MB)")
        return 0
    cache = DiskCache(args.cache)
    try:
        # one budget per paid player: the providers bill separately, and one must not starve the other
        players = [make_player(name, cache=cache, budget=RequestBudget(args.max_requests)) if name in PAID
                   else make_player(name) for name in (n.strip() for n in args.players.split(","))]
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if (args.max_requests > 0 and any(name in PAID for name in (p.name for p in players))
            and args.seed_start < FIRST_PRACTICE_SEED and not args.tournament):
        print("paid players may not spend requests on seeds below 1000 (tournament seeds); "
              "use --seed-start 1000 or higher, or pass --tournament", file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
                "tournament": args.tournament}
    status = 0
    try:
        runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
    except FileExistsError:
        print(f"run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    except RunAborted as e:
        print(f"run {e.status}: {e}", file=sys.stderr)
        status = 1
    print(f"run directory: {run_dir}")
    _print_report(run_dir)
    return status


if __name__ == "__main__":
    sys.exit(main())
