"""uv run python -m bakeoff run|report|view|live"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
from bakeoff.game.track import MAX_ROWS
from bakeoff.live import LiveRun
from bakeoff.live_server import EVENTS_PATH, HOST, serve
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
                     help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only replays "
                          "the cache. Worst case a run spends this many requests per paid player")
    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    run.add_argument("--tournament", action="store_true",
                     help="allows live paid requests on seeds below 1000; for the phase 5 tournament only")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
    live = sub.add_parser("live", help="play one track in real time and watch it in the browser (loopback only); "
                                       "the run is recorded like any other")
    live.add_argument("--players", default="fly,jev_composed,llm", help=f"comma-separated; available: {sorted(REGISTRY)}")
    live.add_argument("--seed", type=int, default=1001, help="the track; practice seeds are 1000 and up")
    live.add_argument("--max-rows", type=int, default=MAX_ROWS)
    live.add_argument("--out", default="runs")
    live.add_argument("--max-requests", type=int, default=0,
                      help=f"hard cap on live requests for EACH paid player ({', '.join(PAID)}); the default 0 only "
                           "replays the cache, which makes a free live run of a track that was already played")
    live.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    live.add_argument("--tournament", action="store_true", help="allows live paid requests on seeds below 1000")
    live.add_argument("--port", type=int, default=8000, help="the page is served on 127.0.0.1 only (default port 8000)")
    live.add_argument("--no-wait", action="store_true",
                      help="do not wait for a browser before the run, and do not keep serving after it")
    return parser


def _players(names: str, cache: DiskCache, max_requests: int) -> list:
    # one budget per paid player: the providers bill separately, and one must not starve the other
    return [make_player(name, cache=cache, budget=RequestBudget(max_requests)) if name in PAID
            else make_player(name) for name in (n.strip() for n in names.split(","))]


def _spends_on_tournament_seeds(players: list, max_requests: int, first_seed: int, tournament: bool) -> bool:
    return (max_requests > 0 and any(p.name in PAID for p in players)
            and first_seed < FIRST_PRACTICE_SEED and not tournament)


SEED_RULE = ("paid players may not spend requests on seeds below 1000 (tournament seeds); "
             "use {flag} 1000 or higher, or pass --tournament")


def _live(args) -> int:
    try:
        players = _players(args.players, DiskCache(args.cache), args.max_requests)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_tournament_seeds(players, args.max_requests, args.seed, args.tournament):
        print(SEED_RULE.format(flag="--seed"), file=sys.stderr)
        return 2
    run_args = {"command": "live", "players": args.players, "seed": args.seed, "max_rows": args.max_rows,
                "max_requests": args.max_requests, "cache": args.cache, "tournament": args.tournament, "port": args.port}
    try:
        live = LiveRun(players, args.seed, out_root=args.out, max_rows=args.max_rows, args=run_args)
        server = serve(None, live.broadcast, args.port)  # before anything is on disk: a busy port leaves nothing behind
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    except OSError as e:
        print(f"cannot listen on {HOST}:{args.port}: {e}", file=sys.stderr)
        return 2
    try:
        try:
            server.page = render_html(live.prepare(), live=EVENTS_PATH)
        except FileExistsError:
            print(f"run directory already exists: {live.run_dir}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        print(f"watch: http://{HOST}:{server.server_address[1]}/", flush=True)
        try:
            if not args.no_wait:
                print("waiting for a browser to open the page (Ctrl-C to give up)", flush=True)
                live.broadcast.wait_for_listener()
        except KeyboardInterrupt:
            live.cancel()
            print("run interrupted before it began", file=sys.stderr)
            return 1
        live.run()
        if live.status != "completed":
            print(f"run {live.status}" + (f": {live.error}" if live.error else ""), file=sys.stderr)
        print(f"run directory: {live.run_dir}")
        _print_report(live.run_dir)
        if not args.no_wait and live.status != "interrupted":
            print(f"still serving the page; Ctrl-C to stop. Replay it later: python -m bakeoff view {live.run_dir}", flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
        return 0 if live.status == "completed" else 1
    finally:
        server.shutdown()
        server.server_close()


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
    if args.command == "live":
        return _live(args)
    try:
        players = _players(args.players, DiskCache(args.cache), args.max_requests)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_tournament_seeds(players, args.max_requests, args.seed_start, args.tournament):
        print(SEED_RULE.format(flag="--seed-start"), file=sys.stderr)
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
