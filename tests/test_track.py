from bakeoff.game.track import (DIFFICULTY_ROWS, LANES, LOOKAHEAD, MAX_ROWS, RUNWAY_ROWS, generate_track,
                                start_lane, survivable)


def test_same_seed_same_track_and_different_seed_differs():
    assert generate_track(7) == generate_track(7)
    assert generate_track(7).gaps != generate_track(8).gaps


def test_a_shorter_track_is_a_prefix_of_the_same_seeds_longer_track():
    for seed in (0, 3, 7, 42):
        short = generate_track(seed, max_rows=50)
        assert short.gaps == generate_track(seed).gaps[:len(short.gaps)]


def test_difficulty_ramps_on_a_fixed_scale_not_on_max_rows():
    assert DIFFICULTY_ROWS == MAX_ROWS == 300


def test_shape_and_defaults():
    track = generate_track(0)
    assert (track.seed, track.lanes, track.max_rows) == (0, LANES, MAX_ROWS) == (0, 12, 300)
    assert len(track.gaps) == MAX_ROWS + LOOKAHEAD + 2
    assert all(0 <= lane < LANES for row in track.gaps for lane in row)
    assert all(list(row) == sorted(set(row)) for row in track.gaps)


def test_runway_is_all_floor_and_start_tile_is_floor():
    for seed in range(20):
        track = generate_track(seed)
        assert all(track.gaps[row] == () for row in range(RUNWAY_ROWS + 1))
        assert not track.is_gap(0, start_lane())


def test_is_gap_wraps_lanes_and_is_false_past_the_end(make_track):
    track = make_track({2: [0, 11]})
    assert track.is_gap(2, 0) and track.is_gap(2, 11)
    assert track.is_gap(2, 12) and track.is_gap(2, -1)  # lane 12 is lane 0, lane -1 is lane 11
    assert not track.is_gap(2, 5)
    assert not track.is_gap(10_000, 0)


def test_every_generated_track_is_survivable():
    assert all(survivable(generate_track(seed)) for seed in range(100))
    assert survivable(generate_track(3, max_rows=40))


def test_survivable_detects_an_impossible_track(make_track):
    wall = list(range(12))
    assert survivable(make_track({5: wall}))  # one full row of gaps can be jumped
    assert not survivable(make_track({5: wall, 6: wall}))  # two in a row cannot


def test_gaps_get_denser_with_distance():
    first = last = 0
    for seed in range(20):
        track = generate_track(seed)
        first += sum(len(track.gaps[row]) for row in range(0, 100))
        last += sum(len(track.gaps[row]) for row in range(200, 300))
    assert last > 2 * first


def test_to_json_round_trips_through_json():
    import json

    track = generate_track(1, max_rows=20)
    data = json.loads(json.dumps(track.to_json()))
    assert data["seed"] == 1 and data["lanes"] == 12 and data["max_rows"] == 20
    assert data["gaps"] == [list(row) for row in track.gaps]
