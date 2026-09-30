import json
import types
from pathlib import Path

import pytest

from bakeoff.fly.reading import Reading
from bakeoff.fly.channels import MAPPINGS, Mapping
from bakeoff.fly.surface import LEVELS_HZ, SurrogateBrain, load_surface, main, measure_mapping, measure_surface

SURFACE_FILE = Path(__file__).resolve().parents[1] / "docs" / "calibration" / "response_surface.json"


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
        committed_trials = cells[(cell["left_hz"], cell["right_hz"])]
        # the brain now reads more neurons than the surface was measured with: compare the ones it holds
        assert [{k: trial[k] for k in old} for trial, old in zip(cell["spike_counts"], committed_trials)] == committed_trials


class ChannelBrain:
    """window_of: DNa01_left spikes once per 100 Hz of `right`, DNg13_right once per 100 Hz of `left`."""

    window_ms, shuffle_seed = 100.0, None

    def __init__(self):
        self.calls = []

    def window_of(self, name, rates, noise_seed=None):
        self.calls.append((name, dict(rates), noise_seed))
        counts = {"DNa01_left": int(rates["right"] // 100) + len(self.calls) % 2, "DNg13_right": int(rates["left"] // 100)}
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


SMALL = Mapping(name="M1", summary="test", cells={"centre": (), "left": (), "right": ()},
                sees={"centre": (0,), "left": (-1,), "right": (1,)}, step_hz=250.0, turn_types=("DNa01",))


def test_measure_mapping_runs_every_combination_of_its_channels_with_repeatable_noise():
    brain, ticks = ChannelBrain(), []
    surface = measure_mapping(brain, SMALL, trials=2, progress=lambda done, total: ticks.append((done, total)))
    assert len(surface["cells"]) == 27 and ticks[-1] == (27, 27)
    assert surface["cells"][1]["rates_hz"] == {"centre": 0.0, "left": 0.0, "right": 250.0}  # last channel fastest
    assert (surface["schema"], surface["input"], surface["channels"]) == (2, "M1", ["centre", "left", "right"])
    assert surface["levels_hz"]["left"] == [0.0, 250.0, 500.0] and surface["shuffle_seed"] is None
    assert {name for name, _, _ in brain.calls} == {"M1"} and len({seed for _, _, seed in brain.calls}) == 54
    assert measure_mapping(ChannelBrain(), SMALL, trials=2) == surface
    json.dumps(surface)


def test_the_surrogate_answers_a_schema_2_surface_by_channel():
    brain = SurrogateBrain(measure_mapping(ChannelBrain(), SMALL, trials=2))
    reading = brain.window_of("M1", {"centre": 0.0, "left": 500.0, "right": 250.0}, noise_seed=3)
    assert reading.spike_counts["DNg13_right"] == 5 and reading.rates_hz["DNg13_right"] == 50.0
    assert reading.spike_counts["DNa01_left"] in (2, 3)
    with pytest.raises(ValueError, match="use window_of"):
        brain.window(0.0, 0.0)


def test_the_surrogate_names_the_channel_and_level_it_lacks():
    brain = SurrogateBrain(measure_mapping(ChannelBrain(), SMALL, trials=1))
    with pytest.raises(KeyError, match=r"left at 100.0 Hz was not measured; its levels are \[0.0, 250.0, 500.0\]"):
        brain.window_of("M1", {"centre": 0.0, "left": 100.0, "right": 0.0})
    with pytest.raises(KeyError, match="measured for input 'M1', not 'M3'"):
        brain.window_of("M3", {"centre": 0.0, "left": 0.0, "right": 0.0})
    with pytest.raises(ValueError, match="has channels"):
        brain.window_of("M1", {"left": 0.0, "right": 0.0})


def test_a_schema_1_surface_still_answers_both_ways():
    brain = SurrogateBrain(measure_surface(CountingBrain(), levels_hz=(0.0, 25.0), trials=1))
    assert brain.window_of("fly", {"left": 25.0, "right": 0.0}, 1) == brain.window(25.0, 0.0, 1)


def test_the_command_refuses_an_unknown_mapping_and_a_shuffled_fly(capsys):
    with pytest.raises(SystemExit):
        main(["--mapping", "M9", "out.json"])
    assert "unknown mapping 'M9'" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--shuffle-seed", "1", "out.json"])
    assert "for a fly2 mapping only" in capsys.readouterr().err


@pytest.mark.slow
def test_a_small_real_surface_of_each_candidate_has_one_neuron_per_group(brain):
    for mapping in MAPPINGS.values():
        one = measure_mapping(brain, Mapping(name=mapping.name, summary="", cells=mapping.cells, sees=mapping.sees,
                                             step_hz=500.0, turn_types=mapping.turn_types), trials=1)
        assert len(one["cells"]) == 2 ** len(mapping.channels)
        silent = one["cells"][0]
        assert set(silent["rates_hz"].values()) == {0.0} and set(silent["spike_counts"][0].values()) == {0}


@pytest.mark.slow
def test_the_committed_fly2_surface_is_what_the_brain_does_today(brain):
    from bakeoff.fly.surface import _channels_seed
    from bakeoff.players import fly2

    committed = load_surface(SURFACE_FILE.parent / f"fly2_surface_{fly2.MAPPING}.json")
    for cell in committed["cells"][-6:]:  # the loudest inputs
        combo = tuple(cell["rates_hz"][ch] for ch in committed["channels"])
        counts = [brain.window_of(fly2.MAPPING, cell["rates_hz"],
                                  noise_seed=_channels_seed(fly2.MAPPING, combo, t)).spike_counts
                  for t in range(committed["trials"])]
        assert [{k: c[k] for k in old} for c, old in zip(counts, cell["spike_counts"])] == cell["spike_counts"]
