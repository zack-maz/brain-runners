import json

from bakeoff.game.engine import Game
from bakeoff.senses import MAX_HZ, compute_senses, ground_truth, looming_rates


def test_senses_shape_matches_the_spec(make_track):
    game = Game(make_track({1: [5, 6], 3: [8, 9]}))
    senses = compute_senses(game)
    assert senses["lane"] == 6 and senses["lanes"] == 12 and senses["rows_survived"] == 0
    assert senses["ahead"] == [
        {"row": 1, "gaps_relative": [-1, 0]}, {"row": 2, "gaps_relative": []},
        {"row": 3, "gaps_relative": [2, 3]}, {"row": 4, "gaps_relative": []},
        {"row": 5, "gaps_relative": []}, {"row": 6, "gaps_relative": []},
    ]
    assert set(senses["actions"]) == {"left", "right", "jump", "stay"}
    json.dumps(senses)


def test_gaps_beyond_three_lanes_are_not_visible(make_track):
    senses = compute_senses(Game(make_track({1: [2, 3, 9, 10]})))
    assert senses["ahead"][0]["gaps_relative"] == [-3, 3]


def test_offsets_wrap_around_the_tunnel(make_track):
    game = Game(make_track({8: [11, 1]}, max_rows=20))
    for _ in range(6):
        game.step("left")  # now at row 6, lane 0
    assert (game.row, game.lane) == (6, 0)
    assert compute_senses(game)["ahead"][1] == {"row": 2, "gaps_relative": [-1, 1]}


def test_senses_follow_the_runner(make_track):
    game = Game(make_track({3: [6]}))
    game.step("stay")
    senses = compute_senses(game)
    assert senses["rows_survived"] == 1
    assert senses["ahead"][1] == {"row": 2, "gaps_relative": [0]}


def test_no_gaps_means_no_looming(make_track):
    assert looming_rates(compute_senses(Game(make_track({})))) == (0.0, 0.0)


def test_left_gap_drives_left_eye_only_and_right_gap_right_eye_only(make_track):
    left, right = looming_rates(compute_senses(Game(make_track({1: [5]}))))
    assert left > 0 and right == 0
    left, right = looming_rates(compute_senses(Game(make_track({1: [7]}))))
    assert left == 0 and right > 0


def test_gap_in_own_lane_drives_both_eyes_equally(make_track):
    left, right = looming_rates(compute_senses(Game(make_track({1: [6]}))))
    assert left == right > 0


def test_nearer_gaps_loom_larger(make_track):
    near, _ = looming_rates(compute_senses(Game(make_track({1: [5]}))))
    far, _ = looming_rates(compute_senses(Game(make_track({4: [5]}))))
    assert near > far > 0


def test_rates_are_capped_at_250_hz(make_track):
    everything = {row: list(range(12)) for row in range(1, 7)}
    assert looming_rates(compute_senses(Game(make_track(everything)))) == (MAX_HZ, MAX_HZ) == (250.0, 250.0)


def test_ground_truth(make_track):
    assert ground_truth(Game(make_track({1: [6]}))) == {"gap_ahead": True, "left_safe": True}
    assert ground_truth(Game(make_track({1: [5]}))) == {"gap_ahead": False, "left_safe": False}
