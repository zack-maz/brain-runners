import json
import time

from bakeoff.__main__ import main
from bakeoff.players import REGISTRY
from bakeoff.players.base import Decision


def test_run_then_report(tmp_path, capsys):
    assert main(["run", "--players", "solver,random", "--seeds", "2", "--max-rows", "30", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "run directory:" in out and "| solver |" in out and "| random |" in out
    (run_dir,) = tmp_path.iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [0, 1]
    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30,
                            "max_requests": 0, "cache": ".cache/responses"}
    assert meta["models"] == {} and meta["requests"] == {}

    assert main(["report", str(run_dir)]) == 0
    assert "| solver |" in capsys.readouterr().out


def test_seed_start_offsets_the_seeds(tmp_path):
    assert main(["run", "--players", "solver", "--seeds", "2", "--seed-start", "1000", "--max-rows", "20",
                 "--out", str(tmp_path)]) == 0
    (run_dir,) = tmp_path.iterdir()
    assert json.loads((run_dir / "meta.json").read_text())["seeds"] == [1000, 1001]


def test_unknown_player_is_a_usage_error(tmp_path, capsys):
    assert main(["run", "--players", "nope", "--out", str(tmp_path)]) == 2
    assert "unknown player 'nope'" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_report_on_a_missing_directory_is_a_usage_error(tmp_path, capsys):
    assert main(["report", str(tmp_path / "nope")]) == 2
    assert "no such run directory" in capsys.readouterr().err


def test_run_directory_collision_is_a_usage_error(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(time, "strftime", lambda fmt: "same")
    args = ["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path)]
    assert main(args) == 0
    assert main(args) == 2
    assert "already exists" in capsys.readouterr().err


def test_an_aborted_run_exits_1_and_still_prints_the_directory_status_and_table(tmp_path, capsys, monkeypatch):
    class Boom:
        name = "boom"

        def reset(self, game, seed): pass
        def act(self, senses): return Decision(None, error="boom")
        def observe(self, executed_action): pass

    monkeypatch.setitem(REGISTRY, "boom", Boom)
    assert main(["run", "--players", "boom", "--seeds", "3", "--out", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "consecutive player errors" in captured.err
    assert "run directory:" in captured.out and "status: aborted" in captured.out
    assert "| boom |" in captured.out
    (run_dir,) = tmp_path.iterdir()
    assert main(["report", str(run_dir)]) == 0
    assert "status: aborted" in capsys.readouterr().out


def test_report_says_status_unknown_without_a_meta_file(tmp_path, capsys):
    assert main(["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path)]) == 0
    (run_dir,) = tmp_path.iterdir()
    (run_dir / "meta.json").unlink()
    capsys.readouterr()
    assert main(["report", str(run_dir)]) == 0
    assert "status: unknown" in capsys.readouterr().out


def test_missing_fly_data_is_a_usage_error_before_the_run_directory_exists(tmp_path, capsys, monkeypatch):
    from bakeoff.fly import data

    monkeypatch.setattr(data, "problems", lambda **kwargs: ["missing: /x/model.py"])
    assert main(["run", "--players", "fly,solver", "--seeds", "1", "--out", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "fly data unusable" in err and "missing: /x/model.py" in err
    assert list(tmp_path.iterdir()) == []


def test_duplicate_players_are_a_usage_error(tmp_path, capsys):
    assert main(["run", "--players", "solver,solver", "--out", str(tmp_path)]) == 2
    assert "duplicate player names: ['solver']" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_spaces_around_player_names_are_ignored(tmp_path, capsys):
    assert main(["run", "--players", "random, solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "| random |" in out and "| solver |" in out


def fake_paid(monkeypatch, action="stay"):
    """Put a JevPlayer with a fake SDK in the registry; returns the list of SDKs the CLI built."""
    from bakeoff.players.jev import JevPlayer
    from tests.fakes import FakeTypeSafe, jev_reply

    sdks = []

    def factory(cache, budget):
        sdks.append(FakeTypeSafe(jev_reply(action)))
        return JevPlayer(cache=cache, budget=budget, sdk=sdks[-1])

    monkeypatch.setitem(REGISTRY, "jev", factory)
    return sdks


def paid_args(tmp_path, *extra):
    return ["run", "--players", "jev", "--seeds", "1", "--seed-start", "1000", "--max-rows", "12",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]


def test_without_max_requests_a_paid_player_cannot_spend_anything(tmp_path, capsys, monkeypatch):
    sdks = fake_paid(monkeypatch)
    assert main(paid_args(tmp_path)) == 1
    assert "run budget_exhausted: request cap of 0 reached" in capsys.readouterr().err
    assert sdks[0].calls == []
    (run_dir,) = (tmp_path / "runs").iterdir()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "budget_exhausted" and meta["requests"] == {"jev": {"max": 0, "used": 0}}
    assert meta["models"] == {"jev": "jev-latest"}


def test_the_cap_stops_the_run_and_the_next_run_continues_from_the_cache(tmp_path, capsys, monkeypatch):
    sdks = fake_paid(monkeypatch, action="jump")  # always_jump survives the 12 rows of seed 1000
    assert main(paid_args(tmp_path, "--max-requests", "2")) == 1
    assert len(sdks[0].calls) == 2
    time.sleep(1.1)  # run ids have one-second resolution
    assert main(paid_args(tmp_path, "--max-requests", "50")) == 0
    first, second = sorted((tmp_path / "runs").iterdir())
    assert json.loads((first / "meta.json").read_text())["requests"] == {"jev": {"max": 2, "used": 2}}
    steps = [json.loads(line) for line in (second / "jev.jsonl").read_text().splitlines()]
    assert [s["cache_hit"] for s in steps[:2]] == [True, True] and not any(s["cache_hit"] for s in steps[2:])
    meta = json.loads((second / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["requests"]["jev"]["used"] == len(steps) - 2
    time.sleep(1.1)
    assert main(paid_args(tmp_path)) == 0  # a full replay needs no budget at all
    assert len(sdks[2].calls) == 0


def test_a_missing_key_is_a_usage_error_before_the_run_directory_exists(tmp_path, capsys, monkeypatch):
    import bakeoff.clients.core as core

    def no_key(name):
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    args = ["run", "--players", "solver,llm", "--seeds", "1", "--max-requests", "3",
            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache")]
    assert main(args) == 2
    assert "llm: ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_a_negative_cap_is_a_usage_error(tmp_path, capsys):
    assert main(paid_args(tmp_path, "--max-requests", "-1")) == 2
    assert "must not be negative" in capsys.readouterr().err
