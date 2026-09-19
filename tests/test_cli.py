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
    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30}

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
