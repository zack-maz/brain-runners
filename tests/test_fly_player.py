import subprocess
import sys
from pathlib import Path

import pytest

from bakeoff.fly.reading import Reading
from bakeoff.game.engine import Game
from bakeoff.players.fly import FlyPlayer, choose, jump_signal_hz, noise_seed, turn_signal_hz
from bakeoff.senses import compute_senses

QUIET = {"DNa01_left": 0.0, "DNa01_right": 0.0, "DNb01_left": 0.0, "DNb01_right": 0.0,
         "DNp01_left": 0.0, "DNp01_right": 0.0, "DNa02_left": 0.0, "DNa02_right": 0.0}


def rates(**changed):
    return {**QUIET, **changed}


class FakeBrain:
    def __init__(self, rates_hz=QUIET):
        self.rates_hz, self.calls, self.closed = rates_hz, [], False

    def window(self, left_hz, right_hz, noise_seed=None):
        self.calls.append((left_hz, right_hz, noise_seed))
        return Reading(rates_hz=self.rates_hz, spike_counts={k: int(v / 10) for k, v in self.rates_hz.items()},
                       spike_times_ms={k: [] for k in self.rates_hz}, total_spikes=7, wall_ms=1.5)

    def close(self):
        self.closed = True


def test_turn_signal_is_right_steering_minus_left_steering():
    assert turn_signal_hz(rates(DNa01_right=40.0, DNb01_right=50.0)) == 90.0
    assert turn_signal_hz(rates(DNa01_left=30.0, DNb01_left=30.0, DNb01_right=10.0)) == -50.0
    assert turn_signal_hz(rates(DNa02_left=200.0)) == 0.0  # DNa02 is logged, never used


def test_jump_signal_is_the_giant_fiber_mean_over_both_sides():
    assert jump_signal_hz(rates(DNp01_left=170.0, DNp01_right=100.0)) == 135.0


@pytest.mark.parametrize("changed, action", [
    ({}, "stay"),
    ({"DNa01_right": 30.0}, "right"),
    ({"DNb01_left": 30.0}, "left"),
    ({"DNa01_right": 20.0}, "stay"),  # the threshold itself is not enough
    ({"DNa01_left": 20.0}, "stay"),
    ({"DNp01_left": 160.0, "DNp01_right": 160.0}, "jump"),
    ({"DNp01_left": 150.0, "DNp01_right": 150.0}, "stay"),
    ({"DNp01_left": 200.0, "DNp01_right": 200.0, "DNa01_right": 90.0}, "jump"),  # jump wins over a turn
])
def test_choose_applies_the_two_thresholds(changed, action):
    assert choose(rates(**changed), turn_threshold_hz=20.0, jump_threshold_hz=150.0) == action


def test_noise_seed_depends_on_track_seed_and_row_and_is_stable_across_processes():
    assert noise_seed(3, 7) == noise_seed(3, 7) == 3662795588
    assert len({noise_seed(s, r) for s in range(5) for r in range(5)}) == 25


def test_listing_the_players_does_not_import_the_simulator():
    # In a fresh interpreter: the slow tests may already have imported brian2 into this one.
    code = ("import sys, bakeoff.__main__; from bakeoff.players import make_player; make_player('fly'); "
            "assert not {'brian2', 'pandas', 'numpy'} & set(sys.modules)")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).resolve().parents[1])


def test_the_brain_is_built_on_the_first_reset_and_only_once(make_track):
    built = []
    player = FlyPlayer(brain_factory=lambda: built.append(FakeBrain()) or built[-1])
    assert built == []
    player.reset(Game(make_track({})), 0)
    player.reset(Game(make_track({})), 1)
    assert len(built) == 1


def test_act_feeds_the_looming_rates_to_the_brain_and_logs_what_it_read(make_track):
    brain = FakeBrain(rates(DNa01_right=40.0, DNb01_right=50.0, DNp01_left=100.0))
    player = FlyPlayer(brain_factory=lambda: brain, turn_threshold_hz=20.0, jump_threshold_hz=150.0,
                       gain_hz=100.0, falloff=1.0)
    game = Game(make_track({1: [5]}))  # one gap, next row, one lane to the left
    player.reset(game, 3)
    decision = player.act(compute_senses(game))
    assert brain.calls == [(100.0, 0.0, noise_seed(3, 0))]
    assert decision.chosen_action == "right" and not decision.needs_fallback
    assert decision.latency_ms is None  # not an API call: the report must not count it as a request
    assert decision.info == {
        "left_hz": 100.0, "right_hz": 0.0, "noise_seed": noise_seed(3, 0),
        "rates_hz": brain.rates_hz, "spike_counts": {k: int(v / 10) for k, v in brain.rates_hz.items()},
        "spike_times_ms": {k: [] for k in brain.rates_hz}, "total_spikes": 7,
        "turn_signal_hz": 90.0, "jump_signal_hz": 50.0,
        "turn_threshold_hz": 20.0, "jump_threshold_hz": 150.0, "wall_ms": 1.5}


def test_the_noise_seed_follows_the_row(make_track):
    brain = FakeBrain()
    player = FlyPlayer(brain_factory=lambda: brain)
    game = Game(make_track({}))
    player.reset(game, 9)
    player.act(compute_senses(game))
    game.step("stay")
    player.act(compute_senses(game))
    assert [call[2] for call in brain.calls] == [noise_seed(9, 0), noise_seed(9, 1)]


def test_senses_rows_survived_matches_the_game_row_at_decision_time(make_track):
    brain = FakeBrain()
    player = FlyPlayer(brain_factory=lambda: brain)
    game = Game(make_track({}, max_rows=10))
    player.reset(game, 0)
    for action in ["stay", "jump", "left", "stay", "left"]:
        senses = compute_senses(game)
        assert senses["rows_survived"] == game.row
        player.act(senses)
        game.step(action)


def test_preflight_checks_the_fly_data_when_using_the_real_brain(monkeypatch):
    from bakeoff.fly import data

    monkeypatch.setattr(data, "problems", lambda **kwargs: ["missing: /x/model.py"])
    with pytest.raises(FileNotFoundError, match="missing: /x/model.py"):
        FlyPlayer().preflight()


def test_preflight_is_a_no_op_with_an_injected_brain_factory(monkeypatch):
    from bakeoff.fly import data

    monkeypatch.setattr(data, "problems", lambda **kwargs: ["missing: /x/model.py"])
    FlyPlayer(brain_factory=lambda: FakeBrain()).preflight()  # no data needed, must not raise


def test_close_releases_the_brain_and_is_safe_to_repeat(make_track):
    brain = FakeBrain()
    player = FlyPlayer(brain_factory=lambda: brain)
    player.close()  # never built: nothing to do
    player.reset(Game(make_track({})), 0)
    player.close()
    player.close()
    assert brain.closed
