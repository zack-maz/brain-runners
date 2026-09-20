import json
import types
from pathlib import Path

import pytest

from bakeoff.fly.reading import Reading
from bakeoff.fly.surface import LEVELS_HZ, SurrogateBrain, load_surface, measure_surface

SURFACE_FILE = Path(__file__).resolve().parents[1] / "calibration" / "response_surface.json"


class CountingBrain:
    """Left DNa01 spikes once per 25 Hz in the right eye and vice versa; every other call adds a "noise" spike."""

    window_ms = 100.0

    def __init__(self):
        self.calls = []

    def window(self, left_hz, right_hz, noise_seed=None):
        self.calls.append((left_hz, right_hz, noise_seed))
        counts = {"DNa01_left": int(right_hz // 25) + len(self.calls) % 2, "DNa01_right": int(left_hz // 25)}
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


def test_the_levels_are_the_eleven_steps_from_0_to_250_hz():
    assert LEVELS_HZ == (0.0, 25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0)


def test_measure_surface_runs_every_input_pair_with_distinct_repeatable_noise():
    brain, ticks = CountingBrain(), []
    surface = measure_surface(brain, levels_hz=(0.0, 25.0), trials=3, progress=lambda done, total: ticks.append((done, total)))
    assert [(c["left_hz"], c["right_hz"]) for c in surface["cells"]] == [(0.0, 0.0), (0.0, 25.0), (25.0, 0.0), (25.0, 25.0)]
    assert all(len(c["spike_counts"]) == 3 for c in surface["cells"])
    assert len({seed for _, _, seed in brain.calls}) == 12
    assert ticks == [(1, 4), (2, 4), (3, 4), (4, 4)]
    assert (surface["schema"], surface["window_ms"], surface["trials"], surface["levels_hz"]) == (1, 100.0, 3, [0.0, 25.0])
    assert len(surface["model_commit"]) == 40 and len(surface["annotations_commit"]) == 40
    again = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=3)
    assert again == surface
    json.dumps(surface)


def test_measure_surface_refuses_a_read_out_group_with_more_than_one_neuron():
    brain = CountingBrain()
    brain.selection = types.SimpleNamespace(readouts={"DNa01_left": (1, 2), "DNa01_right": (3,)})
    with pytest.raises(ValueError, match="one neuron per read-out group"):
        measure_surface(brain, levels_hz=(0.0,), trials=1)
    assert brain.calls == []


def test_the_surrogate_replays_a_measured_trial_chosen_by_the_noise_seed(tmp_path):
    surface = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=4)
    path = tmp_path / "surface.json"
    path.write_text(json.dumps(surface))
    brain = SurrogateBrain(load_surface(path))
    reading = brain.window(25.0, 0.0, noise_seed=5)
    assert reading == brain.window(25.0, 0.0, noise_seed=5)
    assert reading.spike_counts["DNa01_right"] == 1 and reading.rates_hz["DNa01_right"] == 10.0  # 1 spike in 100 ms
    seen = {brain.window(0.0, 25.0, noise_seed=s).spike_counts["DNa01_left"] for s in range(40)}
    assert seen == {1, 2}  # both noise outcomes that were measured come back
    brain.close()


def test_the_surrogate_refuses_an_input_that_was_not_measured():
    brain = SurrogateBrain(measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=1))
    with pytest.raises(KeyError, match="was not measured"):
        brain.window(10.0, 0.0, noise_seed=1)


def test_the_surrogate_refuses_an_unknown_schema():
    with pytest.raises(ValueError, match="unknown response surface schema"):
        SurrogateBrain({"schema": 99})


@pytest.mark.parametrize("key, wrong", [
    ("model_commit", "0" * 40),
    ("annotations_commit", "0" * 40),
    ("window_ms", 999.0),
])
def test_the_surrogate_refuses_a_surface_measured_on_a_different_fly(key, wrong):
    surface = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=1)
    surface[key] = wrong
    with pytest.raises(ValueError, match="measured on a different fly"):
        SurrogateBrain(surface)


def test_an_unchanged_surface_still_loads():
    surface = measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=1)
    SurrogateBrain(surface)  # does not raise


@pytest.mark.slow
def test_the_committed_surface_is_what_the_brain_does_today(brain):
    """Guards the calibration against drift (a Brian2 upgrade, different data, a changed wrapper)."""
    assert all(len(members) == 1 for members in brain.selection.readouts.values())
    committed = load_surface(SURFACE_FILE)
    assert (committed["schema"], committed["trials"], committed["levels_hz"]) == (1, 8, list(LEVELS_HZ))
    assert len(committed["cells"]) == 121
    cells = {(c["left_hz"], c["right_hz"]): c["spike_counts"] for c in committed["cells"]}
    for cell in measure_surface(brain, levels_hz=(0.0, 150.0), trials=8)["cells"]:
        assert cell["spike_counts"] == cells[(cell["left_hz"], cell["right_hz"])]
