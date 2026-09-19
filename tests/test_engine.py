import pytest

from bakeoff.game.engine import ACTIONS, Game


def test_actions_and_start_state(make_track):
    game = Game(make_track({}))
    assert ACTIONS == ("left", "right", "jump", "stay")
    assert (game.row, game.lane, game.alive, game.rows_survived) == (0, 6, True, 0)
    assert not game.finished and not game.over and game.death_cause is None


def test_moves(make_track):
    game = Game(make_track({}))
    game.step("stay")
    assert (game.row, game.lane) == (1, 6)
    game.step("left")
    assert (game.row, game.lane) == (2, 5)
    game.step("right")
    assert (game.row, game.lane) == (3, 6)
    game.step("jump")
    assert (game.row, game.lane, game.rows_survived) == (5, 6, 5)


def test_lanes_wrap_around_the_tunnel(make_track):
    game = Game(make_track({}, max_rows=20))
    for _ in range(7):
        game.step("left")
    assert game.lane == 11  # 6 -> 0 -> wraps to 11
    game.step("right")
    assert game.lane == 0


def test_jump_clears_a_gap_in_the_next_row(make_track):
    game = Game(make_track({1: list(range(12))}))
    game.step("jump")
    assert game.alive and game.row == 2


@pytest.mark.parametrize("action, gap, cause, survived", [
    ("stay", (1, 6), "ran_into_gap", 0),
    ("left", (1, 5), "dodged_into_gap", 0),
    ("right", (1, 7), "dodged_into_gap", 0),
    ("jump", (2, 6), "jumped_into_gap", 1),  # a fatal jump still cleared the row it flew over
])
def test_death_causes(make_track, action, gap, cause, survived):
    game = Game(make_track({gap[0]: [gap[1]]}))
    game.step(action)
    assert not game.alive and game.over and not game.finished
    assert game.death_cause == cause and game.rows_survived == survived
    assert (game.row, game.lane) == (0, 6)  # the runner's last safe tile


def test_run_finishes_at_max_rows_and_score_is_capped(make_track):
    game = Game(make_track({}, max_rows=3))
    game.step("stay")
    game.step("stay")
    assert not game.over
    game.step("jump")  # lands on row 4, past max_rows
    assert game.finished and game.over and game.alive
    assert game.rows_survived == 3


def test_step_rejects_unknown_actions_and_finished_runs(make_track):
    game = Game(make_track({1: [6]}))
    with pytest.raises(ValueError, match="unknown action 'fly'"):
        game.step("fly")
    game.step("stay")
    with pytest.raises(RuntimeError, match="over"):
        game.step("stay")
