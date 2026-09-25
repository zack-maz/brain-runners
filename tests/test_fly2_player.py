import pytest

from bakeoff.errors import PreflightError
from bakeoff.fly import shared
from bakeoff.fly.reading import Reading
from bakeoff.game.engine import Game
from bakeoff.players import fly2, make_player
from bakeoff.players.fly2 import Fly2Player, NoBrainPlayer, choose, no_brain_signals, noise_seed, turn_signal_hz
from bakeoff.runner import Runner
from bakeoff.senses import compute_senses

TYPES = ("DNa01", "DNa02", "DNg13", "DNb01", "DNb05", "DNa04", "DNp01")
QUIET = {f"{t}_{s}": 0.0 for t in TYPES for s in ("left", "right")}


def rates(**changed):
    return {**QUIET, **changed}


class FakeBrain:
    window_ms = 100.0

    def __init__(self, rates_hz=QUIET):
        self.rates_hz, self.calls, self.closed = rates_hz, [], False

    def window_of(self, name, channel_hz, noise_seed=None):
        self.calls.append((name, dict(channel_hz), noise_seed))
        return Reading(rates_hz=self.rates_hz, spike_counts={k: int(v / 10) for k, v in self.rates_hz.items()},
                       spike_times_ms={k: [] for k in self.rates_hz}, total_spikes=9, wall_ms=2.0)

    def close(self):
        self.closed = True


def test_the_turn_is_right_minus_left_of_the_mappings_own_steering_neurons():
    r = rates(DNa02_right=30.0, DNa01_left=10.0, DNg13_right=5.0, DNb01_right=99.0)
    assert turn_signal_hz(r, ("DNa02", "DNa01", "DNg13")) == 25.0
    assert turn_signal_hz(r, ("DNa01", "DNg13")) == -5.0  # DNa02 left out; DNb01 is never read


@pytest.mark.parametrize("turn, jump, expected", [
    (0.0, 0.0, ("stay", "stay")),
    (25.0, 0.0, ("right", "dodge")),
    (-25.0, 0.0, ("left", "dodge")),
    (20.0, 500.0, ("jump", "jump")),  # the threshold itself is not a turn
    (-21.0, 500.0, ("left", "dodge")),  # dodge before jump
    (0.0, 150.0, ("stay", "stay")),  # the jump threshold itself is not a jump
    (0.0, 151.0, ("jump", "jump")),
])
def test_the_rule_dodges_before_it_jumps(turn, jump, expected):
    assert choose(turn, jump, turn_threshold_hz=20.0, jump_threshold_hz=150.0) == expected


def test_a_zero_turn_threshold_turns_on_any_difference_and_never_on_none():
    assert choose(0.0, 0.0, 0.0, 100.0) == ("stay", "stay")
    assert choose(10.0, 0.0, 0.0, 100.0) == ("right", "dodge")


def test_the_no_brain_control_turns_away_from_the_louder_side_and_jumps_on_the_sum():
    assert no_brain_signals({"centre": 300.0, "left": 200.0, "right": 0.0}) == (200.0, 500.0)
    assert no_brain_signals({"left": 50.0, "right": 150.0}) == (-100.0, 200.0)
    control = NoBrainPlayer(mapping="M1", gain_hz=250.0, falloff=3.0, turn_threshold_hz=50.0, jump_threshold_hz=100.0)
    senses = {"ahead": [{"row": 1, "gaps_relative": [-1]}], "rows_survived": 0}
    decision = control.act(senses)
    assert decision.chosen_action == "right" and decision.info["branch"] == "dodge"


def test_act_feeds_the_mappings_channels_and_logs_what_is_ours(make_track):
    brain = FakeBrain(rates(DNg13_left=40.0, DNp01_left=300.0, DNp01_right=300.0))
    player = Fly2Player(brain_factory=lambda name: brain, mapping="M3", gain_hz=500.0, falloff=2.0,
                        turn_threshold_hz=20.0, jump_threshold_hz=200.0)
    game = Game(make_track({1: [6]}))
    player.reset(game, seed=1234)
    decision = player.act(compute_senses(game))
    assert brain.calls == [("M3", {"centre": 500.0, "left": 0.0, "right": 0.0}, noise_seed(1234, 0))]
    assert decision.chosen_action == "left" and decision.info["branch"] == "dodge"  # the turn wins over the jump
    info = decision.info
    assert info["mapping"] == "M3" and info["turn_types"] == ["DNa02", "DNa01", "DNg13"]
    assert (info["turn_signal_hz"], info["jump_signal_hz"], info["total_spikes"]) == (-40.0, 300.0, 9)
    assert (info["turn_threshold_hz"], info["jump_threshold_hz"], info["channels_hz"]) == (20.0, 200.0, {
        "centre": 500.0, "left": 0.0, "right": 0.0})
    player.close()
    assert brain.closed


def test_noise_seeds_are_fly2s_own_and_stable():
    assert noise_seed(3, 7) == noise_seed(3, 7) != noise_seed(3, 8)
    from bakeoff.players.fly import noise_seed as fly_noise_seed

    assert noise_seed(3, 7) != fly_noise_seed(3, 7)


def test_a_real_fly2_registers_its_input_for_the_shared_brain_and_a_stand_in_does_not():
    shared._wanted.clear()
    Fly2Player(brain_factory=lambda name: FakeBrain())
    assert shared._wanted == {}
    make_player("fly2")
    assert shared._wanted == {fly2.MAPPING: fly2.MAPPINGS[fly2.MAPPING].cells}
    shared._wanted.clear()


def test_an_uncalibrated_fly2_is_refused_before_the_run_directory_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(fly2, "CALIBRATED", False)
    with pytest.raises(PreflightError, match="fly2: fly2 is not calibrated yet"):
        Runner(out_root=tmp_path).run([make_player("fly2")], seeds=[1000], run_id="r")
    assert not (tmp_path / "r").exists()
    shared._wanted.clear()


def test_the_committed_constants_are_the_calibration_winner():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "calibration" / "FLY2_REPORT.md").read_text()
    heading = text.split("## Winner: ")[1]
    assert heading.startswith(fly2.MAPPING + ",")
    row = heading.split("\n\n")[2].splitlines()[2]
    winner = tuple(float(cell) for cell in row.strip("| ").split(" | ")[:4])
    assert winner == (fly2.GAIN_HZ, fly2.FALLOFF, fly2.TURN_THRESHOLD_HZ, fly2.JUMP_THRESHOLD_HZ)
    assert fly2.CALIBRATED and fly2.CONTROLS["seeds"] == "1200-1399" and fly2.CONTROLS["practice_seeds"] == "1000-1199"
    assert fly2.CONTROLS["candidates"] == 3 - ("Not measured, so not in the running" in text)  # none missing expected
    # every control number on the page is the report's, not a copy that can drift (final review, I3)
    table = text.split("## Controls\n\n")[1].split("\n\n")[1].splitlines()[2:]
    keys = {"fly2 (winner)": "fly2", "no brain": "no_brain", "shuffled wiring": "shuffled", "fly (frozen": "fly"}
    seen = set()
    for line in table:
        player, _practice, held_out = [cell.strip() for cell in line.strip("|").split("|")]
        key = next(k for prefix, k in keys.items() if player.startswith(prefix))
        assert f"{fly2.CONTROLS[key]:.2f}" == held_out, key
        seen.add(key)
    assert seen == {"fly2", "no_brain", "shuffled", "fly"}
