"""`bakeoff live` from the command line, with free players only. `--start` plays the command line's own
run; `--no-wait` neither waits for a browser before it nor keeps serving after it. Without `--start` the
command opens the lobby and serves until Ctrl-C, which is covered in tests/test_session.py and
tests/test_live_server.py rather than by blocking here."""

import json
import socket

import pytest

from bakeoff.__main__ import DEMO_PLAYERS, DEMO_SEED, _parser, main


def live_args(tmp_path, *extra, players="solver,random"):
    return ["live", "--players", players, "--max-rows", "30", "--port", "0", "--no-wait", "--start",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]


def test_by_default_the_page_runs_the_show_with_the_demos_three_ready_and_no_budget():
    args = _parser().parse_args(["live"])
    assert (args.players, args.seed, args.start) == (None, None, False)  # the lobby chooses
    assert (args.max_requests, args.port, args.held_out) == (0, 8000, False)
    assert (DEMO_PLAYERS, DEMO_SEED) == ("fly,jev_step1,haiku_plain", 1001)  # what it offers first


def test_the_lobby_serves_until_it_is_interrupted_and_reports_the_runs_the_page_played(tmp_path, capsys, monkeypatch):
    """No --start: the command binds the port, says where to watch and hands over to the page."""
    lobby = []
    monkeypatch.setattr("bakeoff.__main__._serve_until_interrupted",
                        lambda session, printed=None: lobby.append(session) or 0)
    assert main(["live", "--port", "0", "--max-rows", "12", "--out", str(tmp_path / "runs"),
                 "--cache", str(tmp_path / "cache")]) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "the page runs the show" in out
    assert "on track 1001" in out  # who is ready: test_without_players_the_demo_keeps_only_who_can_really_play
    assert lobby and lobby[0].status == "lobby" and not (tmp_path / "runs").exists()


def test_no_wait_without_start_is_a_usage_error(tmp_path, capsys):
    assert main(["live", "--port", "0", "--no-wait", "--out", str(tmp_path / "runs")]) == 2
    assert "--no-wait needs --start" in capsys.readouterr().err


def test_a_live_run_leaves_a_normal_run_directory_and_prints_where_to_watch(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001")) == 0
    out = capsys.readouterr().out
    assert "watch: http://127.0.0.1:" in out and "status: completed" in out and "| solver |" in out
    assert "replay it later: python -m bakeoff view " in out
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["command"] == "live" and meta["args"]["max_requests"] == 0
    assert main(["view", str(run_dir), "--output", str(tmp_path / "replay.html")]) == 0  # and it replays afterwards


def test_a_paid_player_on_a_held_out_seed_is_refused_before_anything_exists(tmp_path, capsys):
    """Live, the rule is stricter than `run`'s: a paid player may not play a seed below 1000 at all
    without --held-out, cap or no cap. The page may start a run at any moment, so the seed is settled
    once, when the session is built, not per request."""
    assert main(live_args(tmp_path, "--seed", "7", "--max-requests", "5", players="solver,jev_step1")) == 2
    assert "paid players may not play seeds below 1000" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--seed", "7", players="solver,jev_step1")) == 2
    assert "paid players may not play seeds below 1000" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--seed", "7", players="solver,random")) == 0  # free players, nothing at stake
    assert not any((tmp_path / "runs").glob("*/jev_step1.jsonl"))


def test_without_a_cap_a_paid_player_can_only_replay_the_cache(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", players="solver,haiku_step1")) == 1
    captured = capsys.readouterr()
    assert "haiku_step1 stopped (budget_exhausted): request cap of 0 reached" in captured.err
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed"  # the solver played on
    assert meta["requests"] == {"haiku_step1": {"max": 0, "used": 0}}


def test_a_live_run_plays_the_chosen_game_for_the_chosen_length(tmp_path):
    assert main(live_args(tmp_path, "--game", "v1", "--window", "2")) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["game"]["version"] == "v1+win2" and meta["args"]["game"] == "v1" and meta["args"]["window"] == 2
    assert meta["game"]["max_rows"] == 30  # --max-rows belongs to the session's rules, so every run is a prefix
    assert max(json.loads(line)["row"] for line in (run_dir / "solver.jsonl").read_text().splitlines()) < 30


def test_a_paid_player_with_a_different_window_is_refused_before_anything_exists(tmp_path, capsys):
    assert main(live_args(tmp_path, "--window", "2", players="solver,jev_step1")) == 2
    assert ("paid players are told they see 3 lanes either side; --window 2 is for free players only"
            in capsys.readouterr().err)
    assert not (tmp_path / "runs").exists()


def test_a_paid_player_with_the_same_window_explicit_is_not_refused_by_this_check(tmp_path, capsys):
    assert main(live_args(tmp_path, "--seed", "1001", "--window", "3", players="solver,haiku_step1")) == 1
    assert "haiku_step1 stopped (budget_exhausted): request cap of 0 reached" in capsys.readouterr().err


def test_usage_errors(tmp_path, capsys):
    assert main(live_args(tmp_path, players="solver,nobody")) == 2
    assert "unknown player 'nobody'" in capsys.readouterr().err
    assert main(live_args(tmp_path, players="solver,solver")) == 2
    assert "duplicate player names" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--window", "9")) == 2
    assert "window must be 1 to 5 lanes" in capsys.readouterr().err
    assert main(live_args(tmp_path, "--lookahead", "3", players="solver,jev_step2")) == 2
    assert "the step2 questions need 4 rows" in capsys.readouterr().err
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        args = [a if a != "0" else str(taken.getsockname()[1]) for a in live_args(tmp_path)]
        assert main(args) == 2
        assert "cannot listen on 127.0.0.1:" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("fly_problems, max_requests, ready", [
    (["data/model missing"], "0", "solver,random,always_jump"),  # a fresh clone: no fly data, no cap
    ([], "0", "fly"),                                           # the fly is there, the paid players cannot ask
    ([], "5", "fly,jev_step1,haiku_plain"),                     # the whole demo
])
def test_without_players_the_demo_keeps_only_who_can_really_play(tmp_path, capsys, monkeypatch, fly_problems,
                                                                   max_requests, ready):
    """No --players: the demo lineup is a suggestion, so a runner that could not play is left out rather than the
    command refusing to start; with nobody left, the three bots run."""
    monkeypatch.setattr("bakeoff.fly.data.problems", lambda *a, **k: fly_problems)
    monkeypatch.setattr("bakeoff.__main__._serve_until_interrupted", lambda session, printed=None: 0)
    assert main(["live", "--port", "0", "--max-rows", "12", "--max-requests", max_requests,
                 "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache")]) == 0
    assert f"Ready: {ready} on track 1001" in capsys.readouterr().out


def test_players_named_on_the_command_line_are_still_refused_if_they_cannot_play(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("bakeoff.fly.data.problems", lambda *a, **k: ["data/model missing"])
    assert main(["live", "--port", "0", "--players", "fly,solver", "--out", str(tmp_path / "runs"),
                 "--cache", str(tmp_path / "cache")]) == 2
    assert "fetch_fly_data" in capsys.readouterr().err
