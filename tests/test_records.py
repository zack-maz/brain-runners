"""Records (bakeoff/records.py): which episodes count, and the past runs. Hand-made run directories only. What
they score to is the charts' (tests/test_charts.py)."""

import json

from bakeoff.game.rules import V1, V2
from bakeoff.records import past_runs, pick, records_of
from tests.test_bench import V2 as V2_BLOCK
from tests.test_bench import episode
from tests.test_replay import record, write_run


def test_each_player_and_track_counts_once_from_the_newest_run_that_completed_it(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3) + episode("fly", 1001, 5), {"game": V2_BLOCK})
    write_run(tmp_path, "20260922-100000", episode("fly", 1000, 9), {"game": V2_BLOCK})
    stopped = [record(player="fly", seed=1001, row=r) for r in range(4)]  # alive at its last record: not a result
    write_run(tmp_path, "20260923-100000", stopped, {"game": V2_BLOCK})
    sources, left_out, unreadable, _ = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [
        ("20260922-100000", [("fly", 1000)]), ("20260921-100000", [("fly", 1001)])]
    assert left_out == 1 and unreadable == []


def test_other_games_and_other_lengths_stay_out_and_tracks_narrow_the_seeds(tmp_path):
    write_run(tmp_path, "20260921-090000", episode("fly", 999, 3) + episode("fly", 1000, 4), {"game": V2_BLOCK})
    write_run(tmp_path, "20260921-090001", episode("fly", 1001, 4), {"game": V1.to_json()})
    write_run(tmp_path, "20260921-090002", episode("fly", 1002, 4), {"game": {**V2_BLOCK, "max_rows": 40}})
    write_run(tmp_path, "20260921-090003", episode("fly", 1003, 4), {})  # no game block: from before game versions
    sources, _, _, _ = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("20260921-090000", [("fly", 999), ("fly", 1000)])]
    sources, _, _, _ = pick(tmp_path, V2, tracks=(1000, 1019))
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("20260921-090000", [("fly", 1000)])]


def test_the_past_runs_newest_first_and_only_this_sessions_run_is_current(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3),
              {"game": V2_BLOCK, "status": "completed", "players": ["fly"], "seeds": [1000]})
    write_run(tmp_path, "20260925-100000", episode("jev", 1000, 3),  # an old name comes back as the new one
              {"game": V2_BLOCK, "status": "running", "players": ["jev"], "seeds": [1000]})
    runs = records_of(tmp_path, V2, current="20260921-100000")["runs"]
    assert [(r["run_id"], r["status"], r["players"], r["current"]) for r in runs] == [
        ("20260925-100000", "running", ["jev_plain"], False), ("20260921-100000", "completed", ["fly"], True)]
    assert runs[0]["game"] == "v2" and runs[0]["seeds"] == [1000]


def test_records_are_the_log_only_and_say_why_when_there_is_none(tmp_path):
    missing = records_of(tmp_path / "missing", V2)
    assert missing["why"] == "no run has been recorded yet." and missing["runs"] == []
    write_run(tmp_path, "20260921-090010", episode("fly", 999, 3), {"game": V2_BLOCK})
    out = records_of(tmp_path, V2)
    assert out["why"] is None and [r["run_id"] for r in out["runs"]] == ["20260921-090010"]
    assert "bench" not in out  # the numbers are the Charts screen's (decision 53)
    bad = write_run(tmp_path, "20260921-090011", episode("fly", 1000, 3), {"game": V2_BLOCK})
    (bad / "fly.jsonl").write_text("not json\n{}\n")  # broken before its last line
    assert pick(tmp_path, V2)[2] == ["20260921-090011"]


def test_a_keyless_record_is_unreadable_but_other_runs_still_score(tmp_path):
    write_run(tmp_path, "20260921-090020", episode("fly", 1000, 3), {"game": V2_BLOCK})
    bad = write_run(tmp_path, "20260921-090021", episode("fly", 1001, 3), {"game": V2_BLOCK})
    (bad / "fly.jsonl").write_text(json.dumps({"player": "fly", "seed": 1001}) + "\n")  # parses; no "row"
    sources, left_out, unreadable, _ = pick(tmp_path, V2)
    assert unreadable == ["20260921-090021"]
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("20260921-090020", [("fly", 1000)])]


def test_a_run_whose_meta_json_cannot_be_read_is_unreadable_not_silently_dropped(tmp_path):
    run_dir = tmp_path / "20260921-090022"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text("not json")
    (run_dir / "fly.jsonl").write_text(json.dumps({"player": "fly", "seed": 1000, "row": 0}) + "\n")
    sources, left_out, unreadable, _ = pick(tmp_path, V2)
    assert sources == [] and unreadable == ["20260921-090022"]


def test_past_runs_tolerates_a_game_that_is_not_an_object_and_players_or_seeds_that_are_not_lists(tmp_path):
    write_run(tmp_path, "20260921-090023", episode("fly", 1000, 3),
              {"game": "x", "players": "fly", "seeds": 1000})
    (runs_entry,) = past_runs(tmp_path)
    assert runs_entry["game"] is None and runs_entry["players"] == [] and runs_entry["seeds"] == []


def test_run_directories_sort_newest_first_and_skip_names_that_are_not_run_ids(tmp_path):
    write_run(tmp_path, "20260925-100000-9", episode("fly", 1000, 3), {"game": V2_BLOCK})
    write_run(tmp_path, "20260925-100000-10", episode("fly", 1000, 3), {"game": V2_BLOCK})
    write_run(tmp_path, "renamed", episode("fly", 1000, 3), {"game": V2_BLOCK})
    runs = past_runs(tmp_path)
    assert [r["run_id"] for r in runs] == ["20260925-100000-10", "20260925-100000-9"]


def test_records_carry_what_the_what_is_ours_panel_is_written_from(tmp_path):
    from bakeoff.runner import ours_meta

    for out in (records_of(tmp_path / "missing", V2), records_of(tmp_path, V2)):
        assert out["ours"] == ours_meta(V2)
        assert set(out["ours"]) == {"game", "fly", "fly2"} and out["ours"]["game"]["looming"]["falloff"] is not None


def stop(player, seed, row, status="provider_failing"):
    """meta.json's `stopped`, as runner.py and live.py record a player that dropped out (errors.RunAborted.stopped)."""
    return {player: {"status": status, "reason": "6 errors in a row", "seed": seed, "row": row}}


def test_a_stopped_episode_no_run_completed_is_picked_apart_so_its_failures_count(tmp_path):
    """decision 52: a player that stops leaves an episode neither dead nor finished, and meta.json's `stopped` names
    it. The newest such copy of a (player, seed) no run completed is picked as a stopped one; a completed copy
    anywhere wins."""
    write_run(tmp_path, "20260921-100000", episode("glm_plain", 1001, 5), {"game": V2_BLOCK})
    old = [record(player="glm_plain", seed=1002, row=r) for r in range(2)]
    write_run(tmp_path, "20260922-100000", old, {"game": V2_BLOCK, "status": "completed",
                                                 "stopped": stop("glm_plain", 1002, 1)})
    new = [record(player="glm_plain", seed=1002, row=r) for r in range(3)]
    write_run(tmp_path, "20260923-100000", new, {"game": V2_BLOCK, "status": "completed",
                                                 "stopped": stop("glm_plain", 1002, 2)})
    redone = [record(player="glm_plain", seed=1001, row=r) for r in range(2)]  # 1001 was completed: not stopped
    write_run(tmp_path, "20260924-100000", redone, {"game": V2_BLOCK, "status": "completed",
                                                    "stopped": stop("glm_plain", 1001, 1)})
    sources, left_out, _, stopped = pick(tmp_path, V2)
    assert [(s.run_dir.name, sorted(s.episodes)) for s in sources] == [("20260921-100000", [("glm_plain", 1001)])]
    assert [(s.run_dir.name, sorted(s.episodes)) for s in stopped] == [("20260923-100000", [("glm_plain", 1002)])]
    assert left_out == 0
    assert pick(tmp_path, V2, tracks=(1001, 1001))[3] == []


def test_an_episode_cut_short_without_a_stop_is_not_stopped(tmp_path):
    """Only meta.json's `stopped` makes an unfinished episode a stopped one: an interrupted or crashed run, a run
    still going, an old whole-run abort (`stopped: null`) or another player's or seed's stop leave it out."""
    cut = lambda player, seed: [record(player=player, seed=seed, row=r) for r in range(3)]  # noqa: E731
    write_run(tmp_path, "20260925-100000", cut("glm_plain", 1001), {"game": V2_BLOCK, "status": "interrupted"})
    write_run(tmp_path, "20260925-100001", cut("glm_plain", 1002), {"game": V2_BLOCK, "status": "crashed"})
    write_run(tmp_path, "20260925-100002", cut("glm_plain", 1003), {"game": V2_BLOCK, "status": "running"})
    write_run(tmp_path, "20260925-100003", cut("glm_plain", 1004),
              {"game": V2_BLOCK, "status": "budget_exhausted", "stopped": None})
    write_run(tmp_path, "20260925-100004", cut("glm_plain", 1005) + cut("glm_map", 1006),
              {"game": V2_BLOCK, "status": "completed", "stopped": stop("glm_plain", 1006, 2)})
    assert pick(tmp_path, V2)[3] == []
