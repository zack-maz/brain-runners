"""Records (bakeoff/records.py): which episodes count, and the past runs. Hand-made run directories only."""

from bakeoff.game.rules import V1, V2
from bakeoff.records import pick, records_of
from tests.test_bench import V2 as V2_BLOCK
from tests.test_bench import episode
from tests.test_replay import record, write_run


def test_each_player_and_track_counts_once_from_the_newest_run_that_completed_it(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3) + episode("fly", 1001, 5), {"game": V2_BLOCK})
    write_run(tmp_path, "20260922-100000", episode("fly", 1000, 9), {"game": V2_BLOCK})
    stopped = [record(player="fly", seed=1001, row=r) for r in range(4)]  # alive at its last record: not a result
    write_run(tmp_path, "20260923-100000", stopped, {"game": V2_BLOCK})
    sources, left_out, unreadable = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [
        ("20260922-100000", [("fly", 1000)]), ("20260921-100000", [("fly", 1001)])]
    assert left_out == 1 and unreadable == []
    (fly,) = records_of(tmp_path, V2)["bench"]["players"]
    assert fly["seeds"] == 2 and fly["mean_rows"] == 7  # 9 on track 1000 (the newer run) and 5 on track 1001


def test_tournament_seeds_other_games_and_other_lengths_stay_out(tmp_path):
    write_run(tmp_path, "a", episode("fly", 999, 3) + episode("fly", 1000, 4), {"game": V2_BLOCK})
    write_run(tmp_path, "b", episode("fly", 1001, 4), {"game": V1.to_json()})
    write_run(tmp_path, "c", episode("fly", 1002, 4), {"game": {**V2_BLOCK, "max_rows": 40}})
    write_run(tmp_path, "d", episode("fly", 1003, 4), {})  # no game block: from before game versions
    sources, _, _ = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("a", [("fly", 1000)])]


def test_the_past_runs_newest_first_and_only_this_sessions_run_is_current(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3),
              {"game": V2_BLOCK, "status": "completed", "players": ["fly"], "seeds": [1000]})
    write_run(tmp_path, "20260925-100000", episode("jev", 1000, 3),  # an old name comes back as the new one
              {"game": V2_BLOCK, "status": "running", "players": ["jev"], "seeds": [1000]})
    runs = records_of(tmp_path, V2, current="20260921-100000")["runs"]
    assert [(r["run_id"], r["status"], r["players"], r["current"]) for r in runs] == [
        ("20260925-100000", "running", ["jev_plain"], False), ("20260921-100000", "completed", ["fly"], True)]
    assert runs[0]["game"] == "v2" and runs[0]["seeds"] == [1000]


def test_records_say_why_instead_of_failing(tmp_path):
    assert records_of(tmp_path / "missing", V2)["why"] == "no run has been recorded yet."
    write_run(tmp_path, "a", episode("fly", 999, 3), {"game": V2_BLOCK})
    out = records_of(tmp_path, V2)
    assert out["bench"] is None and out["why"] == "no completed practice track of game v2 has been recorded yet."
    bad = write_run(tmp_path, "b", episode("fly", 1000, 3), {"game": V2_BLOCK})
    (bad / "fly.jsonl").write_text("not json\n{}\n")  # broken before its last line
    assert records_of(tmp_path, V2)["unreadable"] == ["b"]
