"""Charts (bakeoff/charts.py): every recorded track of this game, scored once per player and track. Hand-made run
directories only."""

from bakeoff.charts import HELD_OUT, TUNED_ON, charts_of
from bakeoff.fly.fly2_rule import PRACTICE_SEEDS
from bakeoff.game.rules import V1, V2
from tests.test_bench import V2 as V2_BLOCK
from tests.test_bench import episode
from tests.test_replay import record, write_run


def test_each_player_and_track_counts_once_from_the_newest_run_that_completed_it(tmp_path):
    write_run(tmp_path, "20260921-100000", episode("fly", 1000, 3) + episode("fly", 1001, 5), {"game": V2_BLOCK})
    write_run(tmp_path, "20260922-100000", episode("fly", 1000, 9), {"game": V2_BLOCK})
    stopped = [record(player="fly", seed=1001, row=r) for r in range(4)]  # alive at its last record: not a result
    write_run(tmp_path, "20260923-100000", stopped, {"game": V2_BLOCK})
    out = charts_of(tmp_path, V2)
    (fly,) = out["bench"]["players"]
    assert fly["seeds"] == 2 and fly["mean_rows"] == 7  # 9 on track 1000 (the newer run) and 5 on track 1001
    assert out["left_out"] == 1 and out["unreadable"] == []


def test_charts_take_every_track_of_this_game_held_out_and_practice_alike(tmp_path):
    """decision 53: all the data. Tracks below 1000 and past the track select's twenty are counted."""
    write_run(tmp_path, "20260928-090000", episode("fly", 100, 4) + episode("fly", 1019, 6) + episode("fly", 1199, 8),
              {"game": V2_BLOCK})
    write_run(tmp_path, "20260928-090001", episode("fly", 101, 50), {"game": V1.to_json()})  # another game: out
    out = charts_of(tmp_path, V2)
    (fly,) = out["bench"]["players"]
    assert fly["seeds"] == 3 and fly["mean_rows"] == 6
    assert out["tracks"] == [100, 1199] and out["held_out"] == [100, 199] and list(HELD_OUT) == [100, 199]


def test_charts_count_the_tracks_fly2_was_tuned_on(tmp_path):
    assert TUNED_ON == {"fly2": [min(PRACTICE_SEEDS), max(PRACTICE_SEEDS)]}
    write_run(tmp_path, "20260928-090010", episode("fly2", 100, 4) + episode("fly2", 1000, 4) + episode("fly2", 1001, 4)
              + episode("fly", 1000, 4), {"game": V2_BLOCK})
    out = charts_of(tmp_path, V2)
    assert out["tuned_on"] == TUNED_ON and out["tuned_tracks"] == {"fly2": 2}  # not the held-out track 100
    (tmp_path / "x").mkdir()
    write_run(tmp_path / "x", "20260928-090011", episode("fly2", 150, 4), {"game": V2_BLOCK})
    assert charts_of(tmp_path / "x", V2)["tuned_tracks"] == {}


def test_charts_say_why_instead_of_failing(tmp_path):
    missing = charts_of(tmp_path / "missing", V2)
    assert missing["bench"] is None and missing["why"] == "no run has been recorded yet." and missing["tracks"] is None
    write_run(tmp_path, "20260928-090020", [record(player="fly", seed=100, row=0)], {"game": V2_BLOCK})  # still alive
    out = charts_of(tmp_path, V2)
    assert out["bench"] is None and out["why"] == "no completed track of game v2 has been recorded yet."
    bad = write_run(tmp_path, "20260928-090021", episode("fly", 1000, 3), {"game": V2_BLOCK})
    (bad / "fly.jsonl").write_text("not json\n{}\n")  # broken before its last line
    assert charts_of(tmp_path, V2)["unreadable"] == ["20260928-090021"]


def test_a_practice_track_does_not_change_a_held_out_number(tmp_path):
    """The Writeup's Method says held-out tracks 100-199, so it cites the held-out scope: seed 1000 is left out."""
    write_run(tmp_path, "20260928-090030", episode("fly", 100, 4) + episode("fly", 101, 6), {"game": V2_BLOCK})
    held_out = charts_of(tmp_path, V2, tracks=HELD_OUT)
    write_run(tmp_path, "20260928-090031", episode("fly", 1000, 150, finished=True), {"game": V2_BLOCK})
    again = charts_of(tmp_path, V2, tracks=HELD_OUT)
    assert again["bench"]["players"] == held_out["bench"]["players"] and again["bench"]["players"][0]["mean_rows"] == 5
    assert again["scope"] == "held_out" and again["tracks"] == [100, 101] and again["track_count"] == 2
    every = charts_of(tmp_path, V2)
    assert every["scope"] == "all" and every["bench"]["players"][0]["mean_rows"] == 160 / 3 and every["track_count"] == 3
    (tmp_path / "x").mkdir()
    write_run(tmp_path / "x", "20260928-090032", episode("fly", 1000, 4), {"game": V2_BLOCK})
    assert charts_of(tmp_path / "x", V2, tracks=HELD_OUT)["why"] == (
        "no completed track 100–199 of game v2 has been recorded yet.")


def test_a_stopped_episode_counts_in_failed_and_stopped_but_in_no_other_number(tmp_path):
    """decision 52: a player that stops leaves the others playing; its unfinished track's failed decisions still
    count, or a provider that made it quit would look reliable."""
    write_run(tmp_path, "20260928-090040", episode("glm_plain", 1001, 4), {"game": V2_BLOCK, "status": "completed"})
    failing = [record(player="glm_plain", seed=1002, row=r, error="429") for r in range(4)]
    write_run(tmp_path, "20260928-090041", failing, {"game": V2_BLOCK, "status": "completed", "stopped": {
        "glm_plain": {"status": "provider_failing", "reason": "6 errors in a row", "seed": 1002, "row": 3}}})
    crashed = [record(player="glm_plain", seed=1003, row=r, error="500") for r in range(4)]  # cut short, not stopped
    write_run(tmp_path, "20260928-090042", crashed, {"game": V2_BLOCK, "status": "crashed"})
    out = charts_of(tmp_path, V2)
    (glm,) = out["bench"]["players"]
    assert glm["seeds"] == 1 and glm["mean_rows"] == 4 and glm["stopped"] == 1
    assert glm["failed_rate"] == 4 / 8  # 0 of the finished track's 4 decisions, all 4 of the stopped one's; none
    # of the crashed run's, which no stop names
    assert out["bench"]["incomplete"] == [{"player": "glm_plain", "seed": 1002, "run_id": "20260928-090041", "rows": 4}]
    assert out["tracks"] == [1001, 1001] and out["track_count"] == 1  # a stopped track is not a scored one


def test_charts_may_keep_some_players_only_as_if_no_other_had_played(tmp_path):
    write_run(tmp_path, "20260928-090020", episode("fly", 100, 4) + episode("glm_plain", 100, 9)
              + episode("glm_plain", 101, 9), {"game": V2_BLOCK})
    out = charts_of(tmp_path, V2, HELD_OUT, keep=lambda p: not p.startswith("glm_"))
    assert [p["player"] for p in out["bench"]["players"]] == ["fly"] and out["track_count"] == 1
    assert charts_of(tmp_path, V2, HELD_OUT, keep=lambda p: False)["bench"] is None
