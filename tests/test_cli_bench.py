"""`bakeoff bench` from the command line, on free players only."""

import json

from bakeoff.__main__ import main


def free_run(tmp_path, players="solver,random", seeds="5"):
    assert main(["run", "--players", players, "--seeds", seeds, "--seed-start", "1000", "--max-rows", "40",
                 "--out", str(tmp_path / "runs")]) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    return run_dir


def test_bench_prints_the_tables_and_writes_the_page_and_the_numbers(tmp_path, capsys):
    run_dir = free_run(tmp_path)
    capsys.readouterr()
    page = tmp_path / "out" / "b.html"
    page.parent.mkdir()
    assert main(["bench", str(run_dir), "--output", str(page)]) == 0
    out = capsys.readouterr().out
    assert "| solver | 5 | 40.0 |" in out and "| solver | random | 5 |" in out and f"bench: {page}" in out
    numbers = json.loads(page.with_suffix(".json").read_text())
    assert [p["player"] for p in numbers["players"]] == ["solver", "random"] and numbers["max_rows"] == 40
    html = page.read_text()
    assert '"player":"solver"' in html and "<title>" in html


def test_bench_takes_players_from_a_directory_and_limits_the_pairs(tmp_path, capsys):
    run_dir = free_run(tmp_path, players="solver,random,always_jump")
    capsys.readouterr()
    assert main(["bench", f"{run_dir}:solver,random", "--pair", "random,solver", "--output",
                 str(tmp_path / "b.html")]) == 0
    out = capsys.readouterr().out
    assert "always_jump" not in out and "| solver | random |" in out


def test_bench_usage_errors(tmp_path, capsys):
    run_dir = free_run(tmp_path)
    capsys.readouterr()
    out = str(tmp_path / "b.html")
    assert main(["bench", f"{run_dir}:fly", "--output", out]) == 2
    assert "has no fly" in capsys.readouterr().err
    assert main(["bench", str(run_dir), str(run_dir), "--output", out]) == 2
    assert "is in both" in capsys.readouterr().err
    assert main(["bench", str(run_dir), "--pair", "solver", "--output", out]) == 2
    assert "--pair takes two players" in capsys.readouterr().err
    assert main(["bench", str(run_dir), "--pair", "solver,fly", "--output", out]) == 2
    assert "not in the runs: fly" in capsys.readouterr().err
    assert main(["bench", str(run_dir), "--pair", "solver,solver", "--output", out]) == 2
    assert "--pair takes two different players" in capsys.readouterr().err
    assert main(["bench", str(run_dir), "--output", str(tmp_path / "b.json")]) == 2
    assert "--output must end in .html" in capsys.readouterr().err
    assert main(["bench", str(tmp_path / "nope"), "--output", out]) == 2
    assert "no such run directory" in capsys.readouterr().err
    assert main(["bench", str(run_dir), "--output", str(tmp_path / "missing" / "b.html")]) == 2
    assert "cannot write" in capsys.readouterr().err
    assert not (tmp_path / "b.html").exists()
