import pytest

from bakeoff.fly.channels import FLY_CELLS, MAPPINGS, MAX_HZ, rates, to_level


def senses(*rows):
    """rows: one list of gap offsets per visible row, nearest first."""
    return {"ahead": [{"row": i + 1, "gaps_relative": list(gaps)} for i, gaps in enumerate(rows)]}


def test_each_candidate_has_the_channels_and_levels_the_spec_gives():
    assert MAPPINGS["M1"].channels == MAPPINGS["M3"].channels == ("centre", "left", "right")
    assert MAPPINGS["M2"].channels == ("left", "right")
    assert MAPPINGS["M1"].levels_hz == (0.0, 100.0, 200.0, 300.0, 400.0, 500.0)
    assert len(MAPPINGS["M2"].levels_hz) == 11 and MAPPINGS["M2"].levels_hz[-1] == MAX_HZ == 500.0


def test_the_turn_read_out_is_per_candidate_as_decision_42_says():
    assert MAPPINGS["M1"].turn_types == MAPPINGS["M3"].turn_types == ("DNa02", "DNa01", "DNg13")
    assert MAPPINGS["M2"].turn_types == ("DNa01", "DNg13")


def test_m1_a_gap_straight_ahead_drives_the_centre_and_side_gaps_their_side():
    assert rates(senses([0]), MAPPINGS["M1"], 250.0, 3.0) == {"centre": 300.0, "left": 0.0, "right": 0.0}
    assert rates(senses([-3, 2]), MAPPINGS["M1"], 250.0, 3.0) == {"centre": 0.0, "left": 300.0, "right": 300.0}
    assert MAPPINGS["M1"].cells["centre"] == (("LPLC2", "left"), ("LPLC2", "right"))


def test_m2_sees_only_its_own_lane_and_the_next_one_and_the_centre_drives_both_eyes():
    assert rates(senses([0]), MAPPINGS["M2"], 250.0, 3.0) == {"left": 250.0, "right": 250.0}
    assert rates(senses([-2, -1, 3]), MAPPINGS["M2"], 250.0, 3.0) == {"left": 250.0, "right": 0.0}
    assert MAPPINGS["M2"].cells == FLY_CELLS


def test_m3_drives_the_sideways_cells_from_side_gaps():
    assert rates(senses([], [1]), MAPPINGS["M3"], 500.0, 2.0) == {"centre": 0.0, "left": 0.0, "right": 100.0}
    assert MAPPINGS["M3"].cells["left"] == (("LPLC4", "left"), ("LC22", "left"))


def test_farther_rows_add_less_and_the_sum_is_capped_at_500_hz():
    near_and_far = rates(senses([0], [0]), MAPPINGS["M1"], 250.0, 2.0)  # 250 + 62.5
    assert near_and_far["centre"] == 300.0
    assert rates(senses([0], [0], [0]), MAPPINGS["M1"], 500.0, 2.0)["centre"] == 500.0  # 500 + 125 + 55 capped


@pytest.mark.parametrize("hz,step,level", [(49.9, 100.0, 0.0), (50.0, 100.0, 100.0), (149.0, 100.0, 100.0),
                                           (74.9, 50.0, 50.0), (75.0, 50.0, 100.0), (9999.0, 50.0, 500.0)])
def test_rates_are_rounded_to_the_nearest_level(hz, step, level):
    assert to_level(hz, step) == level


def test_every_rate_a_candidate_can_produce_is_one_of_its_levels():
    for mapping in MAPPINGS.values():
        for gain in (100.0, 250.0, 500.0):
            for falloff in (2.0, 3.0, 4.0):
                for gaps in ([0], [-1, 0, 1], [-3, -2, -1, 0, 1, 2, 3]):
                    out = rates(senses(gaps, gaps, gaps, gaps, gaps, gaps), mapping, gain, falloff)
                    assert set(out.values()) <= set(mapping.levels_hz)
