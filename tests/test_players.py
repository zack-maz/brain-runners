import pytest

from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players import REGISTRY, make_player
from bakeoff.players.base import Decision
from bakeoff.players.solver import solve, solve_depths
from bakeoff.senses import compute_senses


def play(track, player, seed=0):
    game = Game(track)
    player.reset(game, seed)
    while not game.over:
        decision = player.act(compute_senses(game))
        game.step(decision.chosen_action)
        player.observe(decision.chosen_action)
    return game


def test_decision_defaults_and_fallback_rule():
    decision = Decision("left")
    assert not decision.needs_fallback
    assert (decision.gated, decision.invalid, decision.error, decision.cache_hit) == (False, False, None, False)
    assert Decision("left", gated=True).needs_fallback
    assert Decision("left", invalid=True).needs_fallback
    assert Decision(None, error="boom").needs_fallback
    assert Decision(None).needs_fallback


def test_factory_knows_the_baselines_and_rejects_unknown_names():
    assert set(REGISTRY) == {"random", "always_jump", "solver"}
    assert all(make_player(name).name == name for name in REGISTRY)
    with pytest.raises(KeyError, match="unknown player 'nope'"):
        make_player("nope")


def test_factory_passes_options_to_the_constructor(monkeypatch):
    class NeedsOptions:
        name = "needs_options"

        def __init__(self, cap):
            self.cap = cap

    monkeypatch.setitem(REGISTRY, "needs_options", NeedsOptions)
    assert make_player("needs_options", cap=3).cap == 3


def test_random_player_is_reproducible_per_seed_and_uses_every_action(make_track):
    def choices(seed):
        player = make_player("random")
        player.reset(Game(make_track({})), seed)
        return [player.act({}).chosen_action for _ in range(200)]

    assert choices(1) == choices(1)
    assert choices(1) != choices(2)
    assert set(choices(1)) == set(ACTIONS)


def test_random_player_stream_is_not_the_tracks_integer_seed(make_track):
    import random

    player = make_player("random")
    player.reset(Game(make_track({})), 5)
    mine = [player.act({}).chosen_action for _ in range(50)]
    track_stream = random.Random(5)
    assert mine != [track_stream.choice(ACTIONS) for _ in range(50)]


def test_always_jump_is_the_floor_for_a_jump_heavy_player():
    # Measured over seeds 0-199: always-jump averages 45.5 rows, random 30.8.
    jump_rows = [play(generate_track(seed), make_player("always_jump"), seed).rows_survived for seed in range(50)]
    random_rows = [play(generate_track(seed), make_player("random"), seed).rows_survived for seed in range(50)]
    assert sum(jump_rows) > sum(random_rows)
    assert max(jump_rows) < 300


def test_solver_runs_straight_on_open_floor(make_track):
    assert solve(compute_senses(Game(make_track({})))) == "stay"


def test_solve_depths_reports_the_furthest_row_each_first_move_reaches(make_track):
    open_floor = solve_depths(compute_senses(Game(make_track({}))))
    assert list(open_floor) == ["stay", "left", "right", "jump"]
    assert set(open_floor.values()) == {6}
    depths = solve_depths(compute_senses(Game(make_track({1: [6]}))))
    assert depths["stay"] == 0  # the first move is not known-safe
    assert depths["left"] == depths["right"] == depths["jump"] == 6


def test_solve_depths_stops_where_the_visible_floor_ends(make_track):
    wall = list(range(12))
    depths = solve_depths(compute_senses(Game(make_track({3: wall, 4: wall}))))
    assert depths == {"stay": 2, "left": 2, "right": 2, "jump": 2}


def test_solve_is_the_first_action_with_the_maximum_depth(make_track):
    senses = compute_senses(Game(make_track({1: [6]})))
    assert solve(senses) == "left"  # left, right and jump tie at 6; left comes first


def test_solver_dodges_a_gap_ahead(make_track):
    assert solve(compute_senses(Game(make_track({1: [6]})))) == "left"
    assert solve(compute_senses(Game(make_track({1: [5, 6]})))) == "right"


def test_solver_jumps_when_dodging_is_impossible(make_track):
    assert solve(compute_senses(Game(make_track({1: [5, 6, 7]})))) == "jump"


def test_solver_looks_further_than_one_row(make_track):
    # Staying is safe now but runs into a wall of gaps at row 2 whose only hole is two lanes left.
    wall = [lane for lane in range(12) if lane != 4]
    track = make_track({2: wall, 3: wall})
    assert solve(compute_senses(Game(track))) == "left"


def test_solver_does_not_trust_tiles_it_cannot_see(make_track):
    # Left is tried before right, and going left survives rows 1-3, but from there the only way
    # on is a lane 4 to the left, outside the visible window. Unseen tiles count as gaps, so the
    # solver goes right, where it can see floor all the way.
    track = make_track({1: [6], 2: [5, 6], 3: [4, 5, 6], 4: [3, 4, 5, 6], 5: [3, 4, 5, 6]})
    assert solve(compute_senses(Game(track))) == "right"


def test_solver_returns_stay_when_nothing_survives(make_track):
    wall = list(range(12))
    assert solve(compute_senses(Game(make_track({1: wall, 2: wall})))) == "stay"


def test_solver_beats_random_by_a_wide_margin():
    solver_rows = [play(generate_track(seed), make_player("solver"), seed).rows_survived for seed in range(10)]
    random_rows = [play(generate_track(seed), make_player("random"), seed).rows_survived for seed in range(10)]
    assert min(solver_rows) >= 200
    assert sum(random_rows) / 10 < 80
