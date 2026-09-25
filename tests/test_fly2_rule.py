import pytest

from bakeoff.fly.fly2_rule import (GRID, HELD_OUT_SEEDS, NO_BRAIN_GRID, PRACTICE_SEEDS, grid, pick_winner)


def test_the_grids_are_the_ones_the_spec_fixes():
    assert len(GRID) == 3 * 3 * 4 * 9 and len(NO_BRAIN_GRID) == 3 * 3 * 4 * 15
    assert GRID[0] == {"gain_hz": 100.0, "falloff": 2.0, "turn_threshold_hz": 0.0, "jump_threshold_hz": 100.0}
    assert GRID[-1] == {"gain_hz": 500.0, "falloff": 4.0, "turn_threshold_hz": 40.0, "jump_threshold_hz": 300.0}
    assert GRID[1]["jump_threshold_hz"] == 125.0  # the jump threshold is the innermost loop
    assert NO_BRAIN_GRID[-1]["jump_threshold_hz"] == 1500.0 and NO_BRAIN_GRID[-1]["turn_threshold_hz"] == 200.0
    assert min(PRACTICE_SEEDS) == 1000 and min(HELD_OUT_SEEDS) == 1200 and max(HELD_OUT_SEEDS) == 1399


def test_the_highest_mean_rows_wins_across_candidates():
    scored = {"M1": [{"mean_rows": 70.0}], "M2": [{"mean_rows": 90.0}, {"mean_rows": 80.0}], "M3": [{"mean_rows": 85.0}]}
    assert pick_winner(scored) == {"candidate": "M2", "mean_rows": 90.0}


def test_a_tie_goes_to_the_candidate_listed_first_then_to_grid_order():
    scored = {"M3": [{"mean_rows": 90.0, "i": 0}], "M2": [{"mean_rows": 80.0, "i": 0}, {"mean_rows": 90.0, "i": 1}]}
    assert pick_winner(scored) == {"candidate": "M2", "mean_rows": 90.0, "i": 1}
    scored = {"M1": [{"mean_rows": 5.0, "i": 0}, {"mean_rows": 9.0, "i": 1}, {"mean_rows": 9.0, "i": 2}]}
    assert pick_winner(scored)["i"] == 1


def test_an_unknown_candidate_or_nothing_scored_is_an_error():
    with pytest.raises(ValueError, match="unknown candidates"):
        pick_winner({"M4": [{"mean_rows": 1.0}]})
    with pytest.raises(ValueError, match="nothing was scored"):
        pick_winner({"M1": []})


def test_grid_takes_other_values_in_the_same_nesting_order():
    assert grid((1.0,), (2.0,), (3.0, 4.0), (5.0,)) == [
        {"gain_hz": 1.0, "falloff": 2.0, "turn_threshold_hz": 3.0, "jump_threshold_hz": 5.0},
        {"gain_hz": 1.0, "falloff": 2.0, "turn_threshold_hz": 4.0, "jump_threshold_hz": 5.0}]
