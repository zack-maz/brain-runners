"""The real brain. Slow (one build of about half a minute, then about 0.7 s per window) and about
1 GB: run with `uv run pytest -m slow`, never while another fly process is running."""

import pytest

from bakeoff.players.fly import jump_signal_hz, turn_signal_hz

pytestmark = pytest.mark.slow  # the `brain` fixture is in conftest.py: one real brain per test session


def test_no_input_means_no_spikes_at_all(brain):
    reading = brain.window(0.0, 0.0, noise_seed=1)
    assert reading.total_spikes == 0 and set(reading.rates_hz.values()) == {0.0}


def test_the_same_noise_seed_repeats_the_window_exactly_and_another_does_not(brain):
    first, again, other = (brain.window(150.0, 0.0, noise_seed=s) for s in (1, 1, 2))
    assert (first.spike_counts, first.spike_times_ms, first.total_spikes) == (
        again.spike_counts, again.spike_times_ms, again.total_spikes)
    assert other.total_spikes != first.total_spikes


def test_a_threat_in_one_eye_fires_the_steering_neurons_of_the_other_side_only(brain):
    left_threat, right_threat = brain.window(150.0, 0.0, noise_seed=1), brain.window(0.0, 150.0, noise_seed=1)
    assert left_threat.spike_counts["DNa01_left"] == left_threat.spike_counts["DNb01_left"] == 0
    assert right_threat.spike_counts["DNa01_right"] == right_threat.spike_counts["DNb01_right"] == 0
    assert turn_signal_hz(left_threat.rates_hz) >= 40.0  # turn right, away from the left threat
    assert turn_signal_hz(right_threat.rates_hz) <= -40.0


def test_the_giant_fiber_is_graded_with_the_threat(brain):
    weak, strong = brain.window(50.0, 50.0, noise_seed=1), brain.window(250.0, 250.0, noise_seed=1)
    assert 0 < jump_signal_hz(weak.rates_hz) < jump_signal_hz(strong.rates_hz)
    assert abs(turn_signal_hz(strong.rates_hz)) <= 40.0  # both eyes: steering roughly cancels


def test_a_reading_names_every_read_out_group_and_times_lie_in_the_window(brain):
    reading = brain.window(150.0, 0.0, noise_seed=1)
    names = {f"{t}_{s}" for t in ("DNa01", "DNb01", "DNp01", "DNa02") for s in ("left", "right")}
    assert set(reading.rates_hz) == set(reading.spike_counts) == set(reading.spike_times_ms) == names
    assert reading.rates_hz["DNp01_left"] == reading.spike_counts["DNp01_left"] * 10.0  # one neuron, 100 ms
    assert all(0.0 <= t <= 100.0 for times in reading.spike_times_ms.values() for t in times)
    assert len(reading.spike_times_ms["DNp01_left"]) == reading.spike_counts["DNp01_left"]
