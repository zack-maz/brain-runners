import json

import pytest

from bakeoff.players import make_player
from bakeoff.replay import build_replay, landing
from bakeoff.report import COLUMNS
from bakeoff.runner import Runner


def record(player="p", seed=0, row=0, lane=6, executed="stay", alive=True, finished=False, death_cause=None,
           track=None, **extra):
    """A hand-made step record with every key the runner writes."""
    senses = {"lane": lane, "lanes": 12, "rows_survived": row,
              "ahead": [{"row": r, "gaps_relative": [r] if r < 3 else []} for r in range(1, 7)], "actions": {}}
    rec = {"run_id": "r", "player": player, "seed": seed, "row": row, "lane": lane, "senses": senses,
           "looming": {"left_hz": 0.0, "right_hz": 25.0}, "questions": None, "answers": None,
           "chosen_action": executed, "executed_action": executed, "solver_action": "stay",
           "solver_depths": {"stay": 6, "left": 6, "right": 6, "jump": 6}, "gated": False, "invalid": False,
           "error": None, "ground_truth": {"gap_ahead": False, "left_safe": True}, "alive": alive,
           "finished": finished, "death_cause": death_cause, "rows_survived": row + 1, "latency_ms": None,
           "usage": None, "cache_hit": False, "info": None, "track": track}
    rec.update(extra)
    return rec


def write_run(root, run_id, records, meta=None):
    run_dir = root / run_id
    run_dir.mkdir()
    by_player = {}
    for rec in records:
        by_player.setdefault(rec["player"], []).append(rec)
    for player, recs in by_player.items():
        (run_dir / f"{player}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    if meta is not None:
        (run_dir / "meta.json").write_text(json.dumps({"run_id": run_id, **meta}))
    return run_dir


DIED = {"alive": False, "death_cause": "ran_into_gap"}  # a complete episode: the report's means count it
TRACK = {"seed": 0, "lanes": 12, "max_rows": 10, "gaps": [[] for _ in range(18)]}


def test_landing_follows_the_step_record_rules():
    assert landing(4, 6, "stay", 12) == [5, 6]
    assert landing(4, 6, "jump", 12) == [6, 6]
    assert landing(4, 0, "left", 12) == [5, 11]  # lanes wrap
    assert landing(4, 11, "right", 12) == [5, 0]


def test_every_landing_matches_the_engine(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("random"), make_player("always_jump"), make_player("solver")],
                                   range(3), max_rows=40, run_id="real")
    replay = build_replay([run_dir])
    assert len(replay["episodes"]) == 9
    for episode in replay["episodes"]:
        gaps = replay["tracks"][str(episode["seed"])]["gaps"]
        frames = episode["frames"]
        for frame, following in zip(frames, frames[1:]):
            assert frame["landing"] == [following["row"], following["lane"]]
        row, lane = frames[-1]["landing"]
        # mirroring the engine's own condition (Game.step): a landing past max_rows can never kill
        would_kill = row <= episode["max_rows"] and row < len(gaps) and lane in gaps[row]
        assert would_kill == (not frames[-1]["alive"])
        assert episode["complete"] and episode["max_rows"] == 40
        assert episode["rows_survived"] == frames[-1]["rows_survived"]


def test_a_frame_is_the_record_without_the_bulky_keys(tmp_path):
    run_dir = write_run(tmp_path, "a", [record(track=TRACK), record(row=1, executed="left")])
    (episode,) = build_replay([run_dir])["episodes"]
    first, second = episode["frames"]
    for dropped in ("run_id", "player", "seed", "senses", "questions", "track"):
        assert dropped not in first
    assert first["ahead"] == [[1], [2], [], [], [], []]
    assert first["looming"] == {"left_hz": 0.0, "right_hz": 25.0} and first["q"] is None
    assert second["landing"] == [2, 5] and second["solver_depths"]["jump"] == 6
    assert (episode["player"], episode["seed"], episode["run_id"]) == ("p", 0, "a")


def test_questions_are_stored_once_per_episode(tmp_path):
    ask, other = {"system": "rules"}, {"system": "edited rules"}
    run_dir = write_run(tmp_path, "a", [record(track=TRACK, questions=ask), record(row=1, questions=ask),
                                        record(row=2, questions=other), record(row=3)])
    (episode,) = build_replay([run_dir])["episodes"]
    assert episode["questions"] == [ask, other]
    assert [f["q"] for f in episode["frames"]] == [0, 0, 1, None]


def test_a_run_cut_off_midway_is_incomplete_not_a_death(tmp_path):
    run_dir = write_run(tmp_path, "a", [
        record(seed=0, track=TRACK), record(seed=0, row=1, alive=False, death_cause="ran_into_gap"),
        record(seed=1, track=TRACK), record(seed=1, row=1)])
    dead, cut = build_replay([run_dir])["episodes"]
    assert dead["complete"] and dead["death_cause"] == "ran_into_gap"
    assert not cut["complete"] and cut["death_cause"] is None


def test_runs_are_merged_with_the_contestants_first(tmp_path):
    a = write_run(tmp_path, "a", [record("solver", track=TRACK, **DIED), record("llm", track=TRACK, **DIED)],
                  meta={"status": "completed", "players": ["solver", "llm"], "seeds": [0],
                        "models": {"llm": "claude-haiku-4-5-20251001"}})
    b = write_run(tmp_path, "b", [record("fly", seed=0, track=TRACK, **DIED),
                                  record("fly", seed=1, track=TRACK, **DIED)],
                  meta={"status": "interrupted", "players": ["fly"], "seeds": [0, 1],
                        "fly": {"turn_threshold_hz": 0.0, "jump_threshold_hz": 200.0}})
    replay = build_replay([a, b])
    assert replay["replay_version"] == 1
    assert replay["players"] == ["fly", "llm", "solver"] and replay["seeds"] == [0, 1]
    assert [(e["seed"], e["player"]) for e in replay["episodes"]] == [(0, "fly"), (0, "llm"), (0, "solver"), (1, "fly")]
    assert [r["run_id"] for r in replay["runs"]] == ["a", "b"]
    assert replay["runs"][1]["status"] == "interrupted" and replay["runs"][1]["fly"]["jump_threshold_hz"] == 200.0
    assert replay["runs"][0]["fly"] is None  # a run from before phase 2 has no fly block
    board = replay["scoreboard"]
    assert board["columns"] == ["run_id", *COLUMNS]
    assert [(r["player"], r["run_id"]) for r in board["rows"]] == [("fly", "b"), ("llm", "a"), ("solver", "a")]
    assert board["same_seeds"] is False  # the fly played a seed the others did not


def test_the_demos_three_come_first_then_the_one_shot_jev(tmp_path):
    run_dir = write_run(tmp_path, "a", [record(p, track=TRACK) for p in ("jev", "llm", "solver", "jev_composed", "fly")],
                        meta={"players": ["jev", "llm", "solver", "jev_composed", "fly"], "seeds": [0]})
    assert build_replay([run_dir])["players"] == ["fly", "jev_composed", "llm", "jev", "solver"]


def test_other_players_keep_the_order_the_run_planned(tmp_path):
    run_dir = write_run(tmp_path, "a", [record("solver", track=TRACK), record("always_jump", track=TRACK),
                                        record("fly", track=TRACK)],
                        meta={"players": ["solver", "never_started", "fly", "always_jump"], "seeds": [0]})
    assert build_replay([run_dir])["players"] == ["fly", "solver", "always_jump"]


def test_same_seeds_is_true_when_everyone_played_the_same_tracks(tmp_path):
    run_dir = write_run(tmp_path, "a", [record("fly", track=TRACK, **DIED), record("llm", track=TRACK, **DIED)])
    assert build_replay([run_dir])["scoreboard"]["same_seeds"] is True


def test_same_seeds_is_false_when_one_player_is_split_across_runs(tmp_path):
    a = write_run(tmp_path, "a", [record("fly", seed=0, track=TRACK, **DIED)])
    b = write_run(tmp_path, "b", [record("fly", seed=1, track=TRACK, **DIED)])
    c = write_run(tmp_path, "c", [record("jev", seed=0, track=TRACK, **DIED),
                                  record("jev", seed=1, track=TRACK, **DIED)])
    assert build_replay([a, b, c])["scoreboard"]["same_seeds"] is False


def test_same_seeds_counts_only_the_episodes_behind_the_means(tmp_path):
    # the report's means are over complete episodes; the llm was cut off on seed 1 (a budget stop)
    run_dir = write_run(tmp_path, "a", [record("fly", seed=0, track=TRACK, **DIED),
                                        record("fly", seed=1, track=TRACK, **DIED),
                                        record("llm", seed=0, track=TRACK, **DIED), record("llm", seed=1, track=TRACK)],
                        meta={"players": ["fly", "llm"], "seeds": [0, 1], "status": "budget_exhausted"})
    replay = build_replay([run_dir])
    rows = replay["scoreboard"]["rows"]
    assert [(r["player"], r["runs"], r["incomplete"]) for r in rows] == [("fly", 2, 0), ("llm", 1, 1)]
    assert replay["scoreboard"]["same_seeds"] is False


def test_same_seeds_is_false_when_a_scoreboard_row_has_no_complete_episode(tmp_path):
    run_dir = write_run(tmp_path, "a", [record("fly", track=TRACK, **DIED), record("llm", track=TRACK)],
                        meta={"players": ["fly", "llm", "jev"], "seeds": [0]})
    assert build_replay([run_dir])["scoreboard"]["same_seeds"] is False


def test_the_replay_reads_the_schema_the_runner_writes():
    import bakeoff.replay
    import bakeoff.runner

    assert bakeoff.replay.SCHEMA_VERSION == bakeoff.runner.SCHEMA_VERSION


def test_a_run_with_another_schema_version_is_an_error(tmp_path):
    run_dir = write_run(tmp_path, "a", [record(track=TRACK)], meta={"schema_version": 2})
    with pytest.raises(ValueError, match="a has schema_version 2; this viewer reads 1"):
        build_replay([run_dir])


def test_the_same_episode_in_two_runs_is_an_error(tmp_path):
    a = write_run(tmp_path, "a", [record("jev", track=TRACK)])
    b = write_run(tmp_path, "b", [record("jev", track=TRACK)])
    with pytest.raises(ValueError, match="jev on seed 0 is in both a and b"):
        build_replay([a, b])


def test_the_same_row_twice_in_one_run_is_an_error(tmp_path):
    run_dir = write_run(tmp_path, "a", [record(track=TRACK), record(row=0)])
    with pytest.raises(ValueError, match="p on seed 0 appears more than once in a"):
        build_replay([run_dir])


def test_the_longest_track_of_a_seed_is_kept(tmp_path):
    short = {**TRACK, "max_rows": 4, "gaps": [[] for _ in range(12)]}
    a = write_run(tmp_path, "a", [record("fly", track=short)])
    b = write_run(tmp_path, "b", [record("llm", track=TRACK)])
    replay = build_replay([a, b])
    assert len(replay["tracks"]["0"]["gaps"]) == 18
    assert [e["max_rows"] for e in replay["episodes"]] == [4, 10]


def test_a_replay_shows_one_game(tmp_path):
    from bakeoff.game.rules import V1, V2

    a = write_run(tmp_path, "a", [record("fly", track=TRACK)], meta={"game": V2.to_json()})
    b = write_run(tmp_path, "b", [record("llm", track=TRACK)], meta={"game": {**V2.to_json(), "max_rows": 40}})
    c = write_run(tmp_path, "c", [record("jev", track=TRACK)], meta={"game": V1.to_json()})
    d = write_run(tmp_path, "d", [record("solver", track=TRACK)])  # no meta: nothing to compare
    assert build_replay([a, b, d])["game"] == V2.to_json()  # a shorter run of the same game is a prefix
    with pytest.raises(ValueError, match="a is game v2 but c is game v1; a replay shows one game"):
        build_replay([a, c])


def test_a_run_from_before_game_versions_is_v1(tmp_path):
    from bakeoff.game.rules import V1

    old = {"lanes": 12, "max_rows": 300, "lookahead": 6, "window": 3, "looming": {"gain_hz": 250.0}}
    a = write_run(tmp_path, "a", [record("fly", track=TRACK)], meta={"game": old})
    b = write_run(tmp_path, "b", [record("llm", track=TRACK)], meta={"game": V1.to_json()})
    assert build_replay([a, b])["game"] == V1.to_json()
    assert build_replay([write_run(tmp_path, "c", [record(track=TRACK)])])["game"] is None


def test_a_run_without_meta_is_named_after_its_directory(tmp_path):
    run_dir = write_run(tmp_path, "nometa", [record(track=TRACK)])
    (run,) = build_replay([run_dir])["runs"]
    assert run["run_id"] == "nometa" and run["status"] is None


def test_a_missing_run_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such run directory"):
        build_replay([tmp_path / "nope"])


def test_frame_of_and_summary_of_are_the_pieces_the_replay_is_built_from(tmp_path):
    from bakeoff.replay import frame_of, summary_of

    questions_a = {"action": {"type": "choice"}}
    steps = [record(row=0, track=TRACK, questions=questions_a), record(row=1, questions=questions_a, **DIED)]
    run_dir = write_run(tmp_path, "a", steps)
    (episode,) = build_replay([run_dir])["episodes"]
    questions: list[dict] = []
    assert [frame_of(s, 12, questions) for s in steps] == episode["frames"]
    assert questions == episode["questions"] == [questions_a]
    assert summary_of(steps[-1]) == {k: episode[k] for k in ("complete", "finished", "death_cause", "rows_survived")}
    assert summary_of(steps[0])["complete"] is False
