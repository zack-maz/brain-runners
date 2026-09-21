import hashlib
import json

from bakeoff.game.rules import V1, V2
from bakeoff.game.track import generate_track, start_lane, survivable


def fingerprint(track) -> str:
    return hashlib.sha256(json.dumps(track.to_json()).encode()).hexdigest()[:16]


def test_v1_tracks_are_the_tracks_phases_1_to_5_were_played_on():
    # taken from the generator before game versions existed: old runs must replay tile for tile
    assert {seed: fingerprint(generate_track(seed, V1)) for seed in (0, 7, 1000, 1001)} == {
        0: "06d01a25177a758b", 7: "1ec2d9f9eb2a5592", 1000: "58ce5671352ab3d7", 1001: "d84472fe66921e36"}
    assert fingerprint(generate_track(3, V1, max_rows=40)) == "0d4fd98fd7fc2540"


def test_the_default_game_is_v2():
    track = generate_track(0)
    assert track.rules == V2 and (track.max_rows, track.lanes) == (150, 12)
    assert len(track.gaps) == 150 + 6 + 2


def test_v2_reaches_full_density_by_row_100():
    early = late = 0
    for seed in range(1000, 1020):
        v1, v2 = generate_track(seed, V1), generate_track(seed)
        early += sum(len(v1.gaps[row]) for row in range(90, 110))
        late += sum(len(v2.gaps[row]) for row in range(90, 110))
    assert late > 1.5 * early


def test_a_track_carries_its_vision():
    track = generate_track(5, V2.variant(lookahead=3, window=2))
    assert (track.rules.lookahead, track.rules.window, track.rules.version) == (3, 2, "v2+look3+win2")
    assert len(track.gaps) == 150 + 3 + 2


def test_same_seed_same_track_and_different_seed_differs():
    assert generate_track(7) == generate_track(7)
    assert generate_track(7).gaps != generate_track(8).gaps


def test_a_shorter_track_is_a_prefix_of_the_same_seeds_longer_track():
    for seed in (0, 3, 7, 42):
        short = generate_track(seed, max_rows=50)
        assert short.gaps == generate_track(seed).gaps[:len(short.gaps)]


def test_a_shorter_track_keeps_its_version():
    assert generate_track(3, max_rows=40).rules == V2.variant(max_rows=40)
    assert generate_track(3, max_rows=40).rules.version == "v2"


def test_shape():
    for rules in (V1, V2):
        track = generate_track(0, rules)
        assert (track.seed, track.lanes, track.max_rows) == (0, 12, rules.max_rows)
        assert len(track.gaps) == rules.max_rows + rules.lookahead + 2
        assert all(0 <= lane < 12 for row in track.gaps for lane in row)
    assert all(list(row) == sorted(set(row)) for row in track.gaps)


def test_runway_is_all_floor_and_start_tile_is_floor():
    for seed in range(20):
        track = generate_track(seed)
        assert all(track.gaps[row] == () for row in range(track.rules.runway_rows + 1))
        assert not track.is_gap(0, start_lane())


def test_is_gap_wraps_lanes_and_is_false_past_the_end(make_track):
    track = make_track({2: [0, 11]})
    assert track.is_gap(2, 0) and track.is_gap(2, 11)
    assert track.is_gap(2, 12) and track.is_gap(2, -1)  # lane 12 is lane 0, lane -1 is lane 11
    assert not track.is_gap(2, 5)
    assert not track.is_gap(10_000, 0)


def test_every_generated_track_is_survivable():
    assert all(survivable(generate_track(seed)) for seed in range(100))
    assert all(survivable(generate_track(seed, V1)) for seed in range(30))
    assert survivable(generate_track(3, max_rows=40))


def test_survivable_detects_an_impossible_track(make_track):
    wall = list(range(12))
    assert survivable(make_track({5: wall}))  # one full row of gaps can be jumped
    assert not survivable(make_track({5: wall, 6: wall}))  # two in a row cannot


def test_gaps_get_denser_with_distance():
    first = last = 0
    for seed in range(20):
        track = generate_track(seed, V1)
        first += sum(len(track.gaps[row]) for row in range(0, 100))
        last += sum(len(track.gaps[row]) for row in range(200, 300))
    assert last > 2 * first


def test_to_json_round_trips_through_json():
    import json

    track = generate_track(1, max_rows=20)
    data = json.loads(json.dumps(track.to_json()))
    assert data["seed"] == 1 and data["lanes"] == 12 and data["max_rows"] == 20
    assert data["gaps"] == [list(row) for row in track.gaps]


def test_survivable_agrees_that_a_jump_past_the_finish_line_is_safe(make_track):
    wall = list(range(12))
    assert survivable(make_track({3: wall, 4: wall}, max_rows=3))  # jump from row 2 over the wall to row 4
    assert not survivable(make_track({2: wall, 3: wall, 4: wall}, max_rows=3))
