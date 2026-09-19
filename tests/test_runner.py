import json
from datetime import datetime, timedelta

import pytest

from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.runner import BudgetExhausted, RunAborted, Runner

KEYS = {"run_id", "player", "seed", "row", "lane", "senses", "looming", "questions", "answers",
        "chosen_action", "executed_action", "solver_action", "solver_depths", "gated", "invalid", "error",
        "ground_truth", "alive", "finished", "death_cause", "rows_survived", "latency_ms",
        "usage", "cache_hit", "info", "track"}


class Scripted:
    """Returns the same Decision every row."""

    def __init__(self, decision, name="scripted"):
        self.decision, self.name, self.observed = decision, name, []

    def reset(self, game, seed): pass
    def act(self, senses): return self.decision
    def observe(self, executed_action): self.observed.append(executed_action)


def test_solver_run_records(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert all(set(r) == KEYS for r in records)
    assert records[0]["row"] == 0 and records[0]["lane"] == 6
    assert [r["row"] for r in records] == sorted({r["row"] for r in records})
    assert all(r["chosen_action"] == r["executed_action"] == r["solver_action"] for r in records)
    assert all(r["alive"] for r in records)
    assert records[-1]["finished"] and not any(r["finished"] for r in records[:-1])
    assert records[-1]["rows_survived"] == 40
    assert set(records[0]["looming"]) == {"left_hz", "right_hz"}
    assert set(records[0]["ground_truth"]) == {"gap_ahead", "left_safe"}
    json.dumps(records)


def test_solver_action_is_the_first_maximum_of_the_logged_depths(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("random"), seed=3, run_id="r", max_rows=40)
    for r in records:
        depths = r["solver_depths"]
        assert list(depths) == ["stay", "left", "right", "jump"]
        assert r["solver_action"] == max(depths, key=depths.get)


def test_track_is_logged_once_per_seed(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert records[0]["track"]["seed"] == 3 and records[0]["track"]["max_rows"] == 40
    assert all(r["track"] is None for r in records[1:])


def test_senses_are_logged_as_seen_before_the_move(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40)
    assert records[0]["senses"]["rows_survived"] == 0
    assert records[1]["senses"]["lane"] == records[1]["lane"]


def test_sink_is_called_as_each_record_is_produced(tmp_path):
    seen: list[dict] = []
    records = Runner(tmp_path).run_seed(make_player("solver"), seed=3, run_id="r", max_rows=40, sink=seen.append)
    assert seen == records


@pytest.mark.parametrize("decision", [
    Decision("left", gated=True), Decision("left", invalid=True), Decision(None), Decision("teleport"),
])
def test_fallback_is_stay_never_the_solver(tmp_path, decision):
    player = Scripted(decision)
    records = Runner(tmp_path).run_seed(player, seed=1, run_id="r", max_rows=40)  # always-stay dies on seed 1
    assert all(r["executed_action"] == "stay" for r in records)
    assert all(r["chosen_action"] == decision.chosen_action for r in records)
    assert player.observed == ["stay"] * len(records)
    assert not records[-1]["alive"] and records[-1]["death_cause"] == "ran_into_gap"


def test_an_unknown_action_is_recorded_as_invalid(tmp_path):
    records = Runner(tmp_path).run_seed(Scripted(Decision("teleport")), seed=3, run_id="r", max_rows=40)
    assert all(r["invalid"] for r in records)


def test_a_dying_run_ends_with_alive_false_and_a_cause(tmp_path):
    records = Runner(tmp_path).run_seed(make_player("random"), seed=0, run_id="r")
    assert not records[-1]["alive"] and records[-1]["death_cause"] is not None
    assert all(r["alive"] and r["death_cause"] is None for r in records[:-1])


def test_run_writes_one_jsonl_per_player_and_meta(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], range(2), max_rows=40,
                                   run_id="t1", args={"players": "solver,random"})
    assert run_dir == tmp_path / "t1"
    lines = (run_dir / "solver.jsonl").read_text().splitlines()
    assert {json.loads(line)["seed"] for line in lines} == {0, 1}
    assert (run_dir / "random.jsonl").exists()
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["players"] == ["solver", "random"] and meta["seeds"] == [0, 1]
    assert meta["game"] == {"lanes": 12, "max_rows": 40, "lookahead": 6, "window": 3,
                            "looming": {"gain_hz": 250.0, "falloff": 3.0, "step_hz": 25.0, "max_hz": 250.0,
                                        "provisional": False}}
    assert meta["fly"] == {"turn_threshold_hz": 0.0, "jump_threshold_hz": 200.0, "window_ms": 100.0,
                           "provisional": False, "model_commit": "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960",
                           "annotations_commit": "17fc57722002e1a7d38cdd0c89ac382bf92718da"}
    assert meta["args"] == {"players": "solver,random"}
    assert meta["status"] == "completed" and meta["schema_version"] == 1
    assert "git_sha" in meta and {"anthropic", "brian2", "numpy"} <= set(meta["versions"])


def test_every_player_gets_the_same_track(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], [5], max_rows=40, run_id="t")
    first = [json.loads((run_dir / f"{name}.jsonl").read_text().splitlines()[0]) for name in ("solver", "random")]
    assert first[0]["track"] == first[1]["track"]


def test_run_aborts_after_too_many_consecutive_errors_and_keeps_the_lines(tmp_path):
    with pytest.raises(RunAborted, match=r"^6 consecutive"):
        Runner(tmp_path).run([Scripted(Decision(None, error="boom"), name="errs")], range(10), run_id="t2")
    lines = [json.loads(line) for line in (tmp_path / "t2" / "errs.jsonl").read_text().splitlines()]
    assert len(lines) == 6 and all(r["executed_action"] == "stay" for r in lines)
    assert json.loads((tmp_path / "t2" / "meta.json").read_text())["status"] == "aborted"


def test_error_streak_resets_after_a_good_step(tmp_path):
    class FlakyThenGood(Scripted):
        calls = 0

        def act(self, senses):
            self.calls += 1
            return Decision("stay") if self.calls % 6 == 0 else Decision(None, error="boom")

    Runner(tmp_path).run([FlakyThenGood(None, name="flaky")], range(3), run_id="t3")  # must not raise


def test_budget_exhausted_is_recorded_in_meta(tmp_path):
    class Broke(Scripted):
        def act(self, senses): raise BudgetExhausted("request cap of 0 reached")

    with pytest.raises(BudgetExhausted):
        Runner(tmp_path).run([Broke(None, name="broke")], range(1), run_id="t4")
    assert json.loads((tmp_path / "t4" / "meta.json").read_text())["status"] == "budget_exhausted"


def test_any_other_exception_marks_the_run_interrupted(tmp_path):
    class Boom(Scripted):
        def reset(self, game, seed): raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        Runner(tmp_path).run([Boom(None, name="boom")], range(1), run_id="t5")
    assert json.loads((tmp_path / "t5" / "meta.json").read_text())["status"] == "interrupted"


def test_close_is_called_and_a_failing_close_does_not_mask_the_real_error(tmp_path):
    class Closing(Scripted):
        closed = False

        def close(self):
            self.closed = True
            raise OSError("close failed")

    ok = Closing(Decision("stay"), name="ok")
    Runner(tmp_path).run([ok], range(1), max_rows=20, run_id="t6")
    assert ok.closed

    class BoomClosing(Closing):
        def reset(self, game, seed): raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        Runner(tmp_path).run([BoomClosing(None, name="boom")], range(1), run_id="t7")


def test_second_run_with_the_same_run_id_raises(tmp_path):
    Runner(tmp_path).run([make_player("solver")], range(1), max_rows=20, run_id="dup")
    with pytest.raises(FileExistsError):
        Runner(tmp_path).run([make_player("solver")], range(1), max_rows=20, run_id="dup")


def test_duplicate_player_names_raise_before_the_run_directory_is_created(tmp_path):
    with pytest.raises(ValueError, match=r"duplicate player names: \['solver'\]"):
        Runner(tmp_path).run([make_player("solver"), make_player("random"), make_player("solver")], range(1),
                             max_rows=20, run_id="d")
    assert list(tmp_path.iterdir()) == []


def test_meta_records_the_code_version_and_when_the_run_started_and_finished(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # git_sha must not depend on where the CLI was started
    Runner(tmp_path).run([make_player("solver")], range(1), max_rows=20, run_id="m")
    meta = json.loads((tmp_path / "m" / "meta.json").read_text())
    assert isinstance(meta["git_sha"], str) and len(meta["git_sha"]) == 40
    assert isinstance(meta["git_dirty"], bool)
    started, finished = (datetime.fromisoformat(meta[k]) for k in ("started_at", "finished_at"))
    assert started.utcoffset() == timedelta(0) and started <= finished


def test_finished_at_is_written_even_when_the_run_aborts(tmp_path):
    with pytest.raises(RunAborted):
        Runner(tmp_path).run([Scripted(Decision(None, error="boom"), name="errs")], range(10), run_id="a")
    meta = json.loads((tmp_path / "a" / "meta.json").read_text())
    assert meta["status"] == "aborted" and meta["finished_at"] is not None
