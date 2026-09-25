import pytest

from bakeoff.fly.calibrate2 import calibrate, fly2_on, main, report
from bakeoff.fly.channels import MAPPINGS
from bakeoff.fly.fly2_rule import grid
from bakeoff.fly.reading import Reading
from bakeoff.fly.surface import measure_mapping

TYPES = ("DNa01", "DNa02", "DNg13", "DNb01", "DNb05", "DNa04", "DNp01")


class CartoonBrain:
    """Steering fires opposite the louder side, the Giant Fiber with the centre (both eyes for M2).
    `flip` makes it steer toward the louder side instead: a brain that is worse than none."""

    window_ms, shuffle_seed = 100.0, None

    def __init__(self, flip=False, shuffle_seed=None):
        self.flip, self.shuffle_seed = flip, shuffle_seed

    def window_of(self, name, rates, noise_seed=None):
        counts = {f"{t}_{s}": 0 for t in TYPES for s in ("left", "right")}
        push = rates["left"] - rates["right"]
        if self.flip:
            push = -push
        counts["DNa01_right"], counts["DNa01_left"] = int(max(push, 0) // 50), int(max(-push, 0) // 50)
        centre = rates.get("centre", min(rates["left"], rates["right"]))
        counts["DNp01_left"] = counts["DNp01_right"] = int(centre // 20)
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


def surfaces(flip=False, names=("M1", "M2", "M3")):
    return {name: measure_mapping(CartoonBrain(flip), MAPPINGS[name], trials=1) for name in names}


SMALL = dict(practice_seeds=range(1000, 1004), held_out_seeds=range(1200, 1202), check_seeds=range(1000, 1002),
             grid=grid((250.0, 500.0), (2.0,), (0.0, 10.0), (100.0, 1000.0)),
             no_brain_grid=grid((250.0, 500.0), (2.0,), (0.0, 100.0), (500.0, 5000.0)))


def test_calibrate_scores_every_candidate_picks_one_winner_and_plays_the_controls():
    result = calibrate(surfaces(), **SMALL)
    assert set(result["scored"]) == {"M1", "M2", "M3"} and all(len(r) == 8 for r in result["scored"].values())
    best = max(r["mean_rows"] for rows in result["scored"].values() for r in rows)
    assert result["winner"]["mean_rows"] == best and result["winner"]["candidate"] in ("M1", "M2", "M3")
    assert set(result["held_out"]) >= {"mean_rows", "deaths"} and "shuffled" not in result
    assert result["no_brain"]["practice"]["turn_threshold_hz"] in (0.0, 100.0)
    assert [f["player"] for f in result["floors"]] == ["random", "always_jump", "solver"]
    assert result["missing"] == [] and calibrate(surfaces(), **SMALL) == result  # repeatable


def test_a_candidate_that_was_not_measured_is_named_and_left_out():
    result = calibrate(surfaces(names=("M2",)), **SMALL)
    assert result["missing"] == ["M1", "M3"] and result["winner"]["candidate"] == "M2"
    assert "Not measured, so not in the running: M1, M3." in report(result, SMALL["practice_seeds"],
                                                                     SMALL["held_out_seeds"], SMALL["check_seeds"])


def test_the_shuffled_control_must_be_shuffled_and_of_the_winners_mapping():
    measured = surfaces()
    winner = calibrate(measured, **SMALL)["winner"]["candidate"]
    with pytest.raises(ValueError, match="not measured on shuffled wiring"):
        calibrate(measured, shuffled=measured[winner], **SMALL)
    other = "M2" if winner != "M2" else "M1"
    wrong = measure_mapping(CartoonBrain(shuffle_seed=1), MAPPINGS[other], trials=1)
    with pytest.raises(ValueError, match=f"measured for '{other}', not '{winner}'"):
        calibrate(measured, shuffled=wrong, **SMALL)
    shuffled = measure_mapping(CartoonBrain(flip=True, shuffle_seed=1), MAPPINGS[winner], trials=1)
    result = calibrate(measured, shuffled=shuffled, **SMALL)
    assert result["shuffled"]["shuffle_seed"] == 1
    assert result["shuffled"]["practice"]["mean_rows"] <= result["winner"]["mean_rows"]


def test_the_report_says_whose_tuning_it_is_and_shows_the_controls():
    result = calibrate(surfaces(), **SMALL)
    text = report(result, SMALL["practice_seeds"], SMALL["held_out_seeds"], SMALL["check_seeds"])
    assert "OUR tuning, not the fly's biology" in text and "fixed before any surface was measured" in text
    assert f"## Winner: {result['winner']['candidate']}" in text and "## Controls" in text
    assert "| no brain |" in text and "The shuffled-wiring control is not measured yet." in text
    assert "--players fly,fly2 --seeds 2 --seed-start 1000" in text and "| deaths |" in text
    # Minor 8: the held-out seeds were not wholly unseen; the research that chose the candidates used them
    assert "were used earlier by the research that chose the three candidates" in text
    assert "the rule itself never looked at them" in text
    # Minor 7: what the shuffle keeps and loses, and that its control searches the whole grid
    assert "keeps each neuron's in- and out-degree by sign" in text
    assert "loses which neuron talks to which" in text
    assert "searches the whole grid, gain and falloff included" in text


def test_calibrate_refuses_any_seed_below_1000():
    with pytest.raises(ValueError, match="tournament seeds"):
        calibrate(surfaces(), **{**SMALL, "practice_seeds": range(900, 904)})
    with pytest.raises(ValueError, match="tournament seeds"):
        calibrate(surfaces(), **{**SMALL, "held_out_seeds": range(500, 502)})
    with pytest.raises(ValueError, match="tournament seeds"):
        calibrate(surfaces(), **{**SMALL, "check_seeds": range(0, 2)})


def test_a_candidate_surface_measured_on_shuffled_wiring_is_refused():
    shuffled_m1 = measure_mapping(CartoonBrain(shuffle_seed=1), MAPPINGS["M1"], trials=1)
    bad = {**surfaces(names=("M2", "M3")), "M1": shuffled_m1}
    with pytest.raises(ValueError, match="the surface for M1 was measured on shuffled wiring; "
                                          "it is a control, not a candidate"):
        calibrate(bad, **SMALL)


def test_fly2_on_refuses_a_surface_of_another_candidate():
    with pytest.raises(ValueError, match="measured for 'M1', not 'M3'"):
        fly2_on(surfaces(names=("M1",))["M1"], "M3")


@pytest.mark.parametrize("argv, message", [
    (["--surface", "M9=x.json", "out.md"], "NAME one of"),
    (["--surface", "M1", "out.md"], "NAME one of"),
])
def test_the_command_wants_name_equals_path(argv, message, capsys):
    with pytest.raises(SystemExit):
        main(argv)
    assert message in capsys.readouterr().err


def test_the_command_refuses_a_candidate_given_twice(tmp_path, capsys):
    import json

    path = tmp_path / "m1.json"
    path.write_text(json.dumps(surfaces(names=("M1",))["M1"]))
    with pytest.raises(SystemExit):
        main(["--surface", f"M1={path}", "--surface", f"M1={path}", str(tmp_path / "out.md")])
    assert "--surface M1 was given twice" in capsys.readouterr().err
