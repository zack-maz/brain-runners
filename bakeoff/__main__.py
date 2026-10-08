"""uv run python -m bakeoff run|report|view|live|bench"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
from bakeoff.game.rules import DEFAULT, RULES, Rules, resolve, rules_for
from bakeoff.live_server import EVENTS_PATH, HOST, serve
from bakeoff.players import PAID, REGISTRY, UNCAPPED, budget_of, make_player
from bakeoff.players.names import canonical
from bakeoff.report import format_table, load_meta, load_steps, summarize
from bakeoff.replay import build_replay, empty_replay
from bakeoff.runner import RunAborted, Runner
from bakeoff.session import FIRST_PRACTICE_SEED, LiveSession, LobbyError
from bakeoff.view import render_html
from bakeoff.writeup import STUDY as STUDY_JSON

CAPPED = tuple(name for name in PAID if name not in UNCAPPED)
UNCAPPED_HELP = (f"{', '.join(UNCAPPED)} play without a cap, counted and priced" if UNCAPPED
                 else "every paid player is capped, Jev included (decision 58)")
DEMO_PLAYERS = "fly,jev_step1,haiku_plain"  # the demo's three: what the character select offers first
DEMO_SEED = 1001
BOTS = ["solver", "random", "always_jump"]  # the demo's fallback when none of its three can play: free, no data


def _add_game_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game", choices=sorted(RULES), default=DEFAULT,
                        help=f"the game version (default {DEFAULT}); different versions never share a scoreboard")
    parser.add_argument("--lookahead", type=int,
                        help="rows a player is shown (default: the version's); renames the game")
    parser.add_argument("--window", type=int,
                        help="lanes a player is shown either side (default: the version's); renames the game")


def _rules(args) -> Rules:
    return rules_for(args.game).variant(lookahead=args.lookahead, window=args.window)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bakeoff")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run players over seeded tracks")
    run.add_argument("--players", default="random,solver", help=f"comma-separated; available: {sorted(REGISTRY)}")
    run.add_argument("--seeds", type=int, default=20, help="number of seeds (default 20)")
    run.add_argument("--seed-start", type=int, default=0,
                     help="first seed; practice seeds (1000 and up) must not overlap the held-out seeds")
    _add_game_arguments(run)
    run.add_argument("--max-rows", type=int, help="play a prefix of each track (default: the whole track)")
    run.add_argument("--out", default="runs")
    run.add_argument("--max-requests", type=int, default=0,
                     help=f"hard cap on live requests for EACH capped paid player ({', '.join(CAPPED)}); the default 0 "
                          "only replays the cache. Worst case a run spends this many requests per capped paid player. "
                          f"{UNCAPPED_HELP}")
    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    run.add_argument("--held-out", action="store_true",
                     help="allows live paid requests on seeds below 1000, the held-out seeds; for the study's runs only")
    report = sub.add_parser("report", help="summarize an existing run directory")
    report.add_argument("run_dir")
    view = sub.add_parser("view", help="write a replay of one or more run directories as one HTML file")
    view.add_argument("run_dirs", nargs="+", help="run directories; one (player, seed) may appear only once")
    view.add_argument("--output", default="replay.html", help="the file to write (default replay.html)")
    bench = sub.add_parser("bench", help="score recorded runs: who is better and how sure, time and cost per row; "
                                         "spends nothing")
    bench.add_argument("sources", nargs="+", metavar="RUN_DIR[:PLAYER,...]",
                       help="run directories, each optionally with the players to take from it")
    bench.add_argument("--output", default="bench.html",
                       help="the page to write (default bench.html); the numbers go next to it as .json")
    bench.add_argument("--pair", action="append", default=[], metavar="A,B",
                       help="show only these pairs in the terminal (repeatable); the page shows every pair")
    study = sub.add_parser("study-json", help="write the Writeup's figure numbers over the held-out tracks "
                                              "(docs/STUDY.json) from the recorded runs; spends nothing")
    study.add_argument("--out", default="runs", help="the run directories' root (default runs)")
    study.add_argument("--output", default=str(STUDY_JSON), help="the file to write (default docs/STUDY.json)")
    _add_game_arguments(study)
    live = sub.add_parser("live", help="play one track in real time and watch it in the browser (loopback only); "
                                       "the run is recorded like any other")
    live.add_argument("--players", help=f"comma-separated; available: {sorted(REGISTRY)}. Without it the page "
                                        f"opens on the Brain Runners home with the demo's three picked ({DEMO_PLAYERS})")
    live.add_argument("--seed", type=int, help=f"the track; practice seeds are 1000 and up (default {DEMO_SEED} in "
                                               "the track select, where the page may choose another)")
    _add_game_arguments(live)
    live.add_argument("--max-rows", type=int, help="play a prefix of the track (default: the whole track)")
    live.add_argument("--out", default="runs")
    live.add_argument("--max-requests", type=int, default=0,
                      help=f"hard cap on live requests for EACH capped paid player ({', '.join(CAPPED)}); the default 0 "
                           "only replays the cache, which makes a free live run of a track that was already played. "
                           f"{UNCAPPED_HELP}")
    live.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
    live.add_argument("--held-out", action="store_true",
                      help="allows live paid requests on seeds below 1000, the held-out seeds")
    live.add_argument("--start", action="store_true",
                      help="play at once with --players on --seed, as before; without it the page opens in the "
                           "Brain Runners home and starts the run when you say so")
    live.add_argument("--port", type=int, default=8000, help="the page is served on 127.0.0.1 only (default port 8000)")
    live.add_argument("--open", action="store_true", help="open the page in the browser once it is served")
    live.add_argument("--no-wait", action="store_true",
                      help="do not wait for a browser before the run, and do not keep serving after it")
    return parser


def _players(names: str, cache: DiskCache, max_requests: int, rules: Rules) -> list:
    # one budget per paid player: the providers bill separately, and one must not starve the other
    players = [make_player(name, cache=cache, budget=budget_of(name, max_requests)) if name in PAID
               else make_player(name) for name in (canonical(n.strip()) for n in names.split(","))]
    for p in players:  # a question set that cannot be asked on this vision is a usage error, before anyone plays
        if hasattr(p, "question_set"):
            p.question_set.build(rules)
    return players


def _spends_on_held_out_seeds(players: list, max_requests: int, first_seed: int, held_out: bool) -> bool:
    spends = any(p.name in UNCAPPED for p in players) or (max_requests > 0 and any(p.name in PAID for p in players))
    return spends and first_seed < FIRST_PRACTICE_SEED and not held_out


SEED_RULE = ("paid players may not spend requests on seeds below 1000 (held-out seeds); "
             "use {flag} 1000 or higher, or pass --held-out")

# the paid players' briefing (bakeoff/players/briefing.py) tells them they see 3 lanes either side; until
# that text follows the window, a different window would be a lie to a paid player, cache or not
WINDOW_RULE = ("paid players are told they see {chosen} lanes either side; --window {requested} is for "
               "free players only")


def _paid_window_mismatch(players: list, chosen_window: int, requested_window: int | None) -> bool:
    return requested_window is not None and requested_window != chosen_window and any(p.name in PAID for p in players)


def _live(args) -> int:
    """The page runs the show: the command sets the ceiling, binds the loopback port and keeps serving;
    Brain Runners in the browser picks the players and the track. `--start` plays at once, as before."""
    try:  # the session plays every run of this command, so --max-rows belongs to its rules
        rules = resolve(_rules(args), args.max_rows)
    except (KeyError, ValueError) as e:
        print(e.args[0] if isinstance(e, KeyError) else e, file=sys.stderr)
        return 2
    if args.no_wait and not args.start:
        print("--no-wait needs --start: without it the page starts the run and there is nothing to wait for",
              file=sys.stderr)
        return 2
    seed = DEMO_SEED if args.seed is None else args.seed
    names = [canonical(n.strip()) for n in (args.players or DEMO_PLAYERS).split(",")]
    run_args = {"command": "live", "game": args.game, "lookahead": args.lookahead, "window": args.window,
                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache,
                "held_out": args.held_out, "port": args.port}
    # a vision the paid players' briefing does not match: they may not play this session at all
    blocked = (WINDOW_RULE.format(chosen=RULES[args.game].window, requested=args.window)
               if args.window is not None and args.window != RULES[args.game].window else None)
    session = LiveSession(rules, out_root=args.out, cache_dir=args.cache, max_requests=args.max_requests,
                          held_out=args.held_out, args=run_args, paid_blocked=blocked, ready=(seed, names))
    if args.players is None:
        # the demo is a suggestion: leave out whoever could not play (the fly without its data, a paid player with
        # no requests to ask, as on a fresh clone), and run the bots if nobody is left
        names = [n for n in names if session.why_not(n, seed) is None
                 and (n not in PAID or n in UNCAPPED or args.max_requests > 0)] or BOTS
        session.ready_players = names
    try:
        session.check(seed, names)  # what the command line asks for, refused before anything is bound
    except LobbyError as e:
        print(e, file=sys.stderr)
        return 2
    try:
        server = serve(None, session, args.port)  # before anything is on disk: a busy port leaves nothing behind
    except OSError as e:
        print(f"cannot listen on {HOST}:{args.port}: {e}", file=sys.stderr)
        return 2
    try:
        try:
            server.page = render_html(empty_replay(rules), live=EVENTS_PATH, token=session.token,
                                      bench={"why": "The benchmark of this run comes when it ends."})
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        if not args.start:  # the charts take seconds to work out: start now, so Charts and the Writeup open at once
            threading.Thread(target=_warm_charts, args=(session,), daemon=True).start()
        url = f"http://{HOST}:{server.server_address[1]}/"
        print(f"watch: {url}", flush=True)
        if args.open:
            webbrowser.open(url)
        if args.start:
            return _play_now(session, seed, names, args)
        print(f"the page runs the show: pick a track and the players there (Ctrl-C to stop). "
              f"Ready: {','.join(names)} on track {seed}", flush=True)
        return _serve_until_interrupted(session)
    finally:
        _shutdown(server, session)


def _warm_charts(session) -> None:
    """Works the charts out before the page asks, unless a run has begun: its decisions are timed, and this would
    share the process with them."""
    for scope in ("held_out", "all", "study"):
        if session.run is not None:
            return
        try:
            session.study() if scope == "study" else session.charts(scope)
        except Exception as e:  # the page asks again and says why
            print(f"charts not worked out ahead ({scope}): {e}", file=sys.stderr)


def _play_now(session, seed: int, names: list[str], args) -> int:
    """`--start`: the command line's own run, played at once. Today's behaviour."""
    try:
        started = session.start(seed, names, wait_for_page=not args.no_wait)
    except LobbyError as e:
        print(e, file=sys.stderr)
        return 2
    except FileExistsError:
        print(f"run directory already exists: {session.out_root}", file=sys.stderr)
        return 2
    if not args.no_wait:
        print("waiting for a browser to open the page (Ctrl-C to give up)", flush=True)
    try:  # the run itself holds its first decision until the page is listening
        session.wait()
    except KeyboardInterrupt:
        started.run.stop()
        session.wait(30)
    run = started.run
    if run.status != "completed":
        print(f"run {run.status}" + (f": {run.error}" if run.error else ""), file=sys.stderr)
    stopped = _print_stopped((run.meta or {}).get("stopped"))
    _report_run(run)
    if not args.no_wait and run.status != "interrupted":
        print("still serving the page; pick another track there, or Ctrl-C to stop.", flush=True)
        _serve_until_interrupted(session, printed={run.run_id})
    return 0 if run.status == "completed" and not stopped else 1


def _print_stopped(stopped: dict | None) -> bool:
    """Says which players dropped out of a run and why (the others played on); True if any did."""
    for name, stop in (stopped or {}).items():
        print(f"{name} stopped ({stop['status']}): {stop['reason']}", file=sys.stderr)
    return bool(stopped)


def _serve_until_interrupted(session, printed: set | None = None) -> int:
    """Keeps serving while the page starts runs, reporting each one as it closes, until Ctrl-C."""
    printed = set() if printed is None else printed
    try:
        while True:
            for run in list(session.finished):
                if run.run_id not in printed:
                    printed.add(run.run_id)
                    if run.status != "completed":
                        print(f"run {run.status}" + (f": {run.error}" if run.error else ""), file=sys.stderr)
                    _print_stopped((run.meta or {}).get("stopped"))
                    _report_run(run)
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0


def _report_run(run) -> None:
    print(f"run directory: {run.run_dir}")
    _print_report(run.run_dir)
    print(f"replay it later: python -m bakeoff view {run.run_dir}", flush=True)


def _shutdown(server, session) -> None:
    if session.run is not None and session.run.status == "running":
        session.run.stop()
        session.wait(30)
    server.shutdown()
    server.server_close()


def _print_report(run_dir) -> None:
    meta = load_meta(run_dir)
    print(f"status: {meta.get('status', 'unknown') if meta else 'unknown'}")
    if meta and meta.get("game"):
        print(f"game: {Rules.from_json(meta['game']).version}")
    print(format_table(summarize(load_steps(run_dir), meta)))


def _bench(args) -> int:
    from bakeoff.bench import benchmark, format_tables, load as load_runs, parse_source  # numpy: only for bench

    try:
        pairs = [tuple(n.strip() for n in pair.split(",")) for pair in args.pair]
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("--pair takes two players: A,B")
        if any(pair[0] == pair[1] for pair in pairs):
            raise ValueError("--pair takes two different players: A,B")
        if Path(args.output).suffix != ".html":
            raise ValueError("--output must end in .html (the numbers go next to it as .json)")
        loaded = load_runs([parse_source(s) for s in args.sources])
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    if not loaded.episodes:
        print("no complete episode in " + ", ".join(args.sources), file=sys.stderr)
        return 2
    out = benchmark(loaded)
    names = {p["player"] for p in out["players"]}
    unknown = sorted({n for pair in pairs for n in pair} - names)
    if unknown:
        print(f"--pair names players that are not in the runs: {', '.join(unknown)}", file=sys.stderr)
        return 2
    page, numbers = Path(args.output), Path(args.output).with_suffix(".json")
    try:
        numbers.write_text(json.dumps(out, indent=1), encoding="utf-8")
        page.write_text(render_html(out, page_name="bench.html"), encoding="utf-8")
    except OSError as e:
        print(f"cannot write {e.filename}: {e.strerror}", file=sys.stderr)
        return 2
    print(format_tables(out, pairs or None))
    print(f"\nbench: {page} and {numbers}")
    return 0


def _study_json(args) -> int:
    """docs/STUDY.json: the held-out charts cut to what the Writeup's figures read, by the code the Writeup screen
    uses (bakeoff.writeup.study_of), so motg.dev/runners draws the same numbers as Brain Runners."""
    from bakeoff.writeup import study_charts, study_of

    try:
        rules = _rules(args)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    charts = study_charts(args.out, rules)
    study = study_of(charts)
    if study is None:
        print(f"no numbers over the held-out tracks: {charts['why']}", file=sys.stderr)
        return 2
    try:
        Path(args.output).write_text(json.dumps(study, indent=1) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"cannot write {e.filename}: {e.strerror}", file=sys.stderr)
        return 2
    print(f"study: {args.output} ({len(study['players'])} players, {len(study['pairs'])} pairs, "
          f"{charts['track_count']} tracks)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if getattr(args, "max_requests", 0) < 0:  # checked here: a lineup of Jev alone builds no capped budget to refuse it
        print(f"max_requests must not be negative: {args.max_requests}", file=sys.stderr)
        return 2
    if args.command == "bench":
        return _bench(args)
    if args.command == "study-json":
        return _study_json(args)
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
        from bakeoff.bench import benchmark_of  # numpy: only when a page wants the benchmark

        numbers, why = benchmark_of(args.run_dirs)
        if numbers is None:
            print(f"no benchmark: {why}", file=sys.stderr)
        output = Path(args.output)
        try:
            output.write_text(render_html(replay, bench=numbers if numbers else {"why": why}), encoding="utf-8")
        except OSError as e:
            print(f"cannot write {output}: {e}", file=sys.stderr)
            return 2
        print(f"replay: {output} ({len(replay['episodes'])} episodes, {output.stat().st_size / 1e6:.1f} MB)")
        return 0
    if args.command == "live":
        return _live(args)
    try:
        rules = _rules(args)
        players = _players(args.players, DiskCache(args.cache), args.max_requests, rules)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if _spends_on_held_out_seeds(players, args.max_requests, args.seed_start, args.held_out):
        print(SEED_RULE.format(flag="--seed-start"), file=sys.stderr)
        return 2
    if _paid_window_mismatch(players, RULES[args.game].window, args.window):
        print(WINDOW_RULE.format(chosen=RULES[args.game].window, requested=args.window), file=sys.stderr)
        return 2
    runner = Runner(args.out)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runner.out_root / run_id
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start, "game": args.game,
                "lookahead": args.lookahead, "window": args.window, "max_rows": args.max_rows,
                "max_requests": args.max_requests, "cache": args.cache, "held_out": args.held_out}
    status = 0
    try:
        runner.run(players, seeds, rules, max_rows=args.max_rows, run_id=run_id, args=run_args)
    except FileExistsError:
        print(f"run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    except RunAborted as e:
        print(f"run {e.status}: {e}", file=sys.stderr)
        status = 1
    meta_path = run_dir / "meta.json"
    if meta_path.exists() and _print_stopped(json.loads(meta_path.read_text()).get("stopped")):
        status = 1  # a player dropped out: the others played on, but the run is not whole
    print(f"run directory: {run_dir}")
    _print_report(run_dir)
    return status


if __name__ == "__main__":
    sys.exit(main())
