import json
import time

from bakeoff.__main__ import main


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
