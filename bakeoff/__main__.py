"""uv run python -m bakeoff run|report"""

from __future__ import annotations

import argparse
import sys
import time

from bakeoff.game.track import MAX_ROWS
from bakeoff.players import REGISTRY, make_player
from bakeoff.report import format_table, load_steps, summarize
from bakeoff.runner import RunAborted, Runner


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
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "report":
        try:
            print(format_table(summarize(load_steps(args.run_dir))))
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 2
        return 0
    try:
        players = [make_player(name) for name in args.players.split(",")]
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
                "max_rows": args.max_rows}
    status = 0
    try:
        runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
    except FileExistsError:
        print(f"run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    except RunAborted as e:
        print(f"run {e.status}: {e}", file=sys.stderr)
        status = 1
    print(f"run directory: {run_dir}")
    print(format_table(summarize(load_steps(run_dir))))
    return status


if __name__ == "__main__":
    sys.exit(main())
