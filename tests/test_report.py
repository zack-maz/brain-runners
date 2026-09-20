import json

import pytest

from bakeoff.players import make_player
from bakeoff.report import COLUMNS, format_table, load_meta, load_steps, summarize
from bakeoff.runner import Runner


def step(player="p", seed=0, row=0, chosen="stay", executed=None, solver="stay", alive=True,
         finished=False, death_cause=None, rows_survived=0, depths=None, **extra):
    record = {"player": player, "seed": seed, "row": row, "chosen_action": chosen,
              "executed_action": chosen if executed is None else executed, "solver_action": solver,
              "solver_depths": depths or {"stay": 0, "left": 0, "right": 0, "jump": 0, solver: 6},
              "alive": alive, "finished": finished, "death_cause": death_cause,
              "rows_survived": rows_survived, "gated": False, "invalid": False, "error": None,
              "latency_ms": None, "usage": None, "cache_hit": False}
    record.update(extra)
    return record


def test_rows_deaths_and_finishes():
    steps = [
        step(seed=0, row=0), step(seed=0, row=1, alive=False, death_cause="ran_into_gap", rows_survived=1),
        step(seed=1, row=0), step(seed=1, row=9, alive=False, death_cause="dodged_into_gap", rows_survived=9),
        step(seed=2, row=0), step(seed=2, row=19, finished=True, rows_survived=20),
    ]
    (row,) = summarize(steps)
    assert row["player"] == "p" and row["runs"] == 3 and row["incomplete"] == 0
    assert row["mean_rows"] == 10 and row["median_rows"] == 9 and row["finished"] == 1
    assert (row["ran_into_gap"], row["jumped_into_gap"], row["dodged_into_gap"]) == (1, 0, 1)


def test_a_run_cut_off_midway_is_incomplete_not_a_death():
    steps = [step(seed=0, row=0), step(seed=0, row=1, alive=False, death_cause="ran_into_gap", rows_survived=1),
             step(seed=1, row=0), step(seed=1, row=1, rows_survived=2)]
    (row,) = summarize(steps)
    assert row["runs"] == 1 and row["incomplete"] == 1 and row["mean_rows"] == 1


def test_solver_agreement_ignores_steps_without_a_choice():
    steps = [step(chosen="left", solver="left"), step(row=1, chosen="jump", solver="stay"),
             step(row=2, chosen=None, executed="stay", solver="stay", error="boom", alive=False)]
    (row,) = summarize(steps)
    assert row["solver_agreement"] == 0.5
    assert row["error_rate"] == pytest.approx(1 / 3)
    assert row["fallback_rate"] == pytest.approx(1 / 3)


def test_a_tied_best_choice_counts_as_agreement_even_if_it_is_not_the_solvers_pick():
    tied = {"stay": 6, "left": 6, "right": 0, "jump": 3}
    steps = [step(chosen="left", solver="stay", depths=tied), step(row=1, chosen="jump", solver="stay", depths=tied),
             step(row=2, chosen="teleport", solver="stay", depths=tied)]
    (row,) = summarize(steps)
    assert row["solver_agreement"] == pytest.approx(1 / 3)  # left ties stay; jump is worse; teleport is no key


def test_jump_share_is_the_share_of_executed_jumps():
    steps = [step(chosen="jump"), step(row=2, chosen="jump", executed="stay", gated=True),
             step(row=3, chosen="left"), step(row=4, chosen="jump", alive=False, death_cause="jumped_into_gap")]
    (row,) = summarize(steps)
    assert row["jump_share"] == 0.5
    assert COLUMNS[COLUMNS.index("dodged_into_gap") + 1] == "jump_share"


def test_invalid_rate_and_fallback_rate():
    steps = [step(chosen="teleport", executed="stay", invalid=True), step(row=1, alive=False)]
    (row,) = summarize(steps)
    assert row["invalid_rate"] == 0.5 and row["fallback_rate"] == 0.5


def test_requests_latency_and_tokens_count_only_live_calls():
    steps = [
        step(latency_ms=100.0, usage={"input_tokens": 10, "output_tokens": 2}),
        step(row=1, latency_ms=300.0, usage={"input_tokens": 30, "output_tokens": 4}),
        step(row=2, latency_ms=1.0, usage={"input_tokens": 99, "output_tokens": 99}, cache_hit=True, alive=False),
    ]
    (row,) = summarize(steps)
    assert row["requests"] == 2 and row["mean_latency_ms"] == 200.0
    assert row["input_tokens"] == 40 and row["output_tokens"] == 6


def test_players_are_separate_rows_sorted_by_name():
    rows = summarize([step(player="solver", alive=False), step(player="random", alive=False)])
    assert [r["player"] for r in rows] == ["random", "solver"]


def test_format_table_has_every_column_and_dashes_for_none():
    table = format_table(summarize([step(alive=False, death_cause="ran_into_gap")]))
    header, rule, body = table.splitlines()
    assert header == "| " + " | ".join(COLUMNS) + " |"
    assert " - " in body and "0.00" in body


def test_load_steps_reads_a_real_run(tmp_path):
    run_dir = Runner(tmp_path).run([make_player("solver"), make_player("random")], range(2), max_rows=30, run_id="t")
    steps = load_steps(run_dir)
    assert {s["player"] for s in steps} == {"solver", "random"}
    rows = {r["player"]: r for r in summarize(steps)}
    assert rows["solver"]["runs"] == 2 and rows["solver"]["solver_agreement"] == 1.0


def test_load_steps_tolerates_a_truncated_last_line_only(tmp_path):
    good = json.dumps(step())
    (tmp_path / "p.jsonl").write_text(good + "\n" + good[:20])
    assert len(load_steps(tmp_path)) == 1
    (tmp_path / "p.jsonl").write_text(good[:20] + "\n" + good + "\n")
    with pytest.raises(json.JSONDecodeError):
        load_steps(tmp_path)


def test_load_steps_rejects_a_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such run directory"):
        load_steps(tmp_path / "nope")


def test_columns_put_missing_right_after_incomplete():
    assert COLUMNS[COLUMNS.index("incomplete") + 1] == "missing"


def test_missing_counts_seeds_with_no_record_and_is_none_without_meta():
    steps = [step(seed=0, alive=False, death_cause="ran_into_gap"), step(seed=1, row=0)]
    meta = {"players": ["p"], "seeds": [0, 1, 2, 3]}
    (row,) = summarize(steps, meta)
    assert row["missing"] == 2 and row["incomplete"] == 1 and row["runs"] == 1
    assert summarize(steps)[0]["missing"] is None


def test_a_player_that_never_started_still_gets_a_row():
    meta = {"players": ["p", "late"], "seeds": [0, 1]}
    rows = summarize([step(alive=False, death_cause="ran_into_gap")], meta)
    late = next(r for r in rows if r["player"] == "late")
    assert late["runs"] == 0 and late["missing"] == 2 and late["incomplete"] == 0
    assert late["mean_rows"] is None and late["solver_agreement"] is None and late["fallback_rate"] is None
    assert "| late |" in format_table(rows)


def test_load_meta_returns_none_when_absent_or_unparseable(tmp_path):
    assert load_meta(tmp_path) is None
    (tmp_path / "meta.json").write_text("{not json")
    assert load_meta(tmp_path) is None
    (tmp_path / "meta.json").write_text(json.dumps({"status": "completed"}))
    assert load_meta(tmp_path) == {"status": "completed"}


def test_a_gated_stay_is_a_fallback_even_though_executed_equals_chosen():
    # M2
    steps = [step(chosen="stay", gated=True), step(row=1, chosen="stay"), step(row=2, chosen=None, executed="stay")]
    (row,) = summarize(steps)
    assert row["fallback_rate"] == pytest.approx(2 / 3)
