import json

from bakeoff.game.engine import Game
from bakeoff.senses import (LANDS, LOOMING_STEP_HZ, MAX_HZ, compute_senses, ground_truth, lands_on_gap,
                            looming_rates)


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
    near, _ = looming_rates(compute_senses(Game(make_track({1: [5]}))), gain_hz=100.0, falloff=1.0)
    far, _ = looming_rates(compute_senses(Game(make_track({4: [5]}))), gain_hz=100.0, falloff=1.0)
    assert (near, far) == (100.0, 25.0)


def test_falloff_is_the_power_of_the_distance(make_track):
    senses = compute_senses(Game(make_track({2: [5]})))
    assert looming_rates(senses, gain_hz=200.0, falloff=1.0) == (100.0, 0.0)
    assert looming_rates(senses, gain_hz=200.0, falloff=2.0) == (50.0, 0.0)
    assert looming_rates(senses, gain_hz=200.0, falloff=3.0) == (25.0, 0.0)


def test_gaps_in_one_eye_add_up(make_track):
    senses = compute_senses(Game(make_track({1: [4, 5], 2: [7]})))
    assert looming_rates(senses, gain_hz=100.0, falloff=1.0) == (200.0, 50.0)


def test_rates_are_rounded_to_the_nearest_input_level(make_track):
    assert LOOMING_STEP_HZ == 25.0
    senses = compute_senses(Game(make_track({3: [5], 6: [7]})))
    assert looming_rates(senses, gain_hz=100.0, falloff=1.0) == (25.0, 25.0)  # 33.3 and 16.7
    assert looming_rates(senses, gain_hz=70.0, falloff=1.0) == (25.0, 0.0)  # 23.3 and 11.7
    assert looming_rates(senses, gain_hz=112.5, falloff=1.0) == (50.0, 25.0)  # 37.5 rounds up, 18.75 up


def test_rates_are_capped_at_250_hz(make_track):
    everything = {row: list(range(12)) for row in range(1, 7)}
    assert looming_rates(compute_senses(Game(make_track(everything)))) == (MAX_HZ, MAX_HZ) == (250.0, 250.0)


def test_ground_truth(make_track):
    assert ground_truth(Game(make_track({1: [6]}))) == {"gap_ahead": True, "left_safe": True}
    assert ground_truth(Game(make_track({1: [5]}))) == {"gap_ahead": False, "left_safe": False}


def test_lands_on_gap_reads_each_actions_landing_tile_from_the_senses(make_track):
    senses = compute_senses(Game(make_track({1: [5], 2: [6]})))  # row 1: a gap to the left; row 2: a gap ahead
    assert {a: lands_on_gap(senses, a) for a in LANDS} == {"left": True, "stay": False, "right": False, "jump": True}


def test_lands_on_gap_agrees_with_the_engine_up_to_the_finish_line():
    from bakeoff.game.track import generate_track

    checked = 0
    for action, (ahead, _) in LANDS.items():
        game = Game(generate_track(1000, max_rows=60))
        while not game.over:
            senses = compute_senses(game)
            if game.row + ahead + 1 <= game.track.max_rows:  # past the finish line a gap no longer kills
                probe = Game(game.track)
                probe.row, probe.lane = game.row, game.lane
                probe.step(action)
                assert (not probe.alive) == lands_on_gap(senses, action)
                checked += 1
            game.step(next(a for a in ("stay", "left", "right", "jump") if not lands_on_gap(senses, a)))
    assert checked > 200


def test_the_senses_follow_the_games_vision(make_track):
    senses = compute_senses(Game(make_track({1: [3, 4], 2: [9]}, lookahead=3, window=2)))
    assert [e["row"] for e in senses["ahead"]] == [1, 2, 3]
    assert senses["ahead"][0]["gaps_relative"] == [-2] and senses["ahead"][1]["gaps_relative"] == []


def test_truth_of_reads_every_question_set_noul_from_the_senses(make_track):
    from bakeoff.senses import parse_tile_id, tile_id, trapped, truth_of

    # runner in lane 6: a gap ahead; a dead end after stepping left (row 2 lanes 4, 5, 6 and row 3 lane 5)
    senses = compute_senses(Game(make_track({1: [6], 2: [4, 5, 6], 3: [5]})))
    assert truth_of(senses, "gap_stay") is True and truth_of(senses, "gap_left") is False
    assert trapped(senses, "left") and truth_of(senses, "trapped_left") is True
    assert truth_of(senses, "trapped_right") is False
    assert truth_of(senses, "tile_r1_c") is True and truth_of(senses, "tile_r2_l2") is True
    assert truth_of(senses, "tile_r2_r1") is False
    assert truth_of(senses, "tile_r9_c") is None and truth_of(senses, "gap_ahead") is None
    assert truth_of(senses, "tile_r1_l0") is None and truth_of(senses, "nonsense") is None
    assert [tile_id(2, o) for o in (-3, 0, 1)] == ["tile_r2_l3", "tile_r2_c", "tile_r2_r1"]
    assert parse_tile_id("tile_r2_l3") == (2, -3) and parse_tile_id("tile_r4_r1") == (4, 1)


def test_truth_of_a_follow_up_beyond_the_view_is_unknown(make_track):
    from bakeoff.senses import truth_of

    senses = compute_senses(Game(make_track({}, lookahead=3)))
    assert truth_of(senses, "trapped_stay") is False  # rows 2 and 3 are in view
    assert truth_of(senses, "trapped_jump") is None  # would need row 4
