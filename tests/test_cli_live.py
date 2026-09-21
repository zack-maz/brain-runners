"""`bakeoff live` from the command line, with free players only. `--no-wait` neither waits for a
browser before the run nor keeps serving after it."""

import json
import socket

from bakeoff.__main__ import _parser, main


def live_args(tmp_path, *extra, players="solver,random"):
    return ["live", "--players", players, "--max-rows", "30", "--port", "0", "--no-wait",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]


def test_the_defaults_are_the_demos_three_on_a_practice_seed_with_no_budget():
    args = _parser().parse_args(["live"])
    assert (args.players, args.seed, args.max_requests, args.port, args.tournament) == ("fly,jev_composed,llm", 1001, 0, 8000, False)


def test_a_live_run_leaves_a_normal_run_directory_and_prints_where_to_watch(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001")) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "status: completed" in out and "| solver |" in out
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["command"] == "live" and meta["args"]["max_requests"] == 0
    assert main(["view", str(run_dir), "--output", str(tmp_path / "replay.html")]) == 0  # and it replays afterwards


def test_a_paid_cap_on_a_tournament_seed_is_refused_before_anything_exists(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "7", "--max-requests", "5", players="solver,jev_composed")) == 2
    assert "paid players may not spend requests on seeds below 1000" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_without_a_cap_a_paid_player_can_only_replay_the_cache(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", players="solver,jev_composed")) == 1
    captured = capsys.readouterr()
    assert "run budget_exhausted: request cap of 0 reached" in captured.err
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert json.loads((run_dir / "meta.json").read_text())["requests"] == {"jev_composed": {"max": 0, "used": 0}}


def test_a_live_run_plays_the_chosen_game(tmp_path):
    assert main(live_args(tmp_path, "--game", "v1", "--window", "2")) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["game"]["version"] == "v1+win2" and meta["args"]["game"] == "v1" and meta["args"]["window"] == 2


def test_usage_errors(tmp_path, capsys):
    assert main(live_args(tmp_path, players="solver,nobody")) == 2
    assert "unknown player 'nobody'" in capsys.readouterr().err
    assert main(live_args(tmp_path, players="solver,solver")) == 2
    assert "duplicate player names" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--window", "9")) == 2
    assert "window must be 1 to 5 lanes" in capsys.readouterr().err
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        args = [a if a != "0" else str(taken.getsockname()[1]) for a in live_args(tmp_path)]
        assert main(args) == 2
        assert "cannot listen on 127.0.0.1:" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()
