import pandas as pd
import pytest

from bakeoff.fly import data
from bakeoff.fly.channels import FLY_CELLS, MAPPINGS
from bakeoff.fly.neurons import load_selection, load_tables, select_channels, select_neurons

TYPES = ("LPLC2", "LC4", "DNa01", "DNb01", "DNp01", "DNa02", "DNg13", "DNb05", "DNa04")


def annotations(extra=()):
    rows = [(100 + 10 * t + s, cell_type, side)
            for t, cell_type in enumerate(TYPES) for s, side in enumerate(("left", "right"))]
    return pd.DataFrame(list(rows) + list(extra), columns=["root_id", "cell_type", "side"])


def test_a_neurons_model_index_is_its_position_in_the_model_id_list():
    model_ids = [999] + [int(r) for r in annotations()["root_id"]]  # 999 shifts every index by one
    selection = select_neurons(annotations(), model_ids)
    assert selection.inputs == {"left": (1, 3), "right": (2, 4)}  # LPLC2 then LC4 of that eye
    assert selection.readouts["DNa01_left"] == (5,) and selection.readouts["DNp01_right"] == (10,)
    assert selection.readouts["DNg13_left"] == (13,) and selection.readouts["DNa04_right"] == (18,)
    assert set(selection.readouts) == {f"{t}_{s}" for t in TYPES[2:] for s in ("left", "right")}


def test_an_annotated_cell_that_the_model_lacks_is_counted_but_not_used():
    extra = [(777, "LC4", "left")]
    model_ids = [int(r) for r in annotations()["root_id"]]
    selection = select_neurons(annotations(extra), model_ids)
    assert selection.coverage["LC4_left"] == {"annotated": 2, "in_model": 1}
    assert selection.coverage["LPLC2_right"] == {"annotated": 1, "in_model": 1}
    assert len(selection.inputs["left"]) == 2


def test_other_cell_types_and_center_cells_are_ignored():
    extra = [(778, "LC6", "left"), (779, "LC4", "center")]
    model_ids = [int(r) for r in annotations(extra)["root_id"]]
    selection = select_neurons(annotations(extra), model_ids)
    assert len(selection.inputs["left"]) == len(selection.inputs["right"]) == 2


def test_a_group_with_no_neuron_in_the_model_is_an_error():
    model_ids = [int(r) for r in annotations()["root_id"] if r != 120]  # 120 is the left DNa01
    with pytest.raises(ValueError, match="no left DNa01 neuron is in the model"):
        select_neurons(annotations(), model_ids)


def test_fly_as_channels_selects_exactly_its_eyes():
    model_ids = [999] + [int(r) for r in annotations()["root_id"]]
    assert select_channels(annotations(), model_ids, FLY_CELLS) == select_neurons(annotations(), model_ids).inputs


def test_channels_list_their_groups_in_the_order_given_and_a_missing_group_is_an_error():
    extra = [(900, "LPLC4", "left"), (901, "LC22", "left"), (902, "LC22", "left")]
    model_ids = [int(r) for r in annotations(extra)["root_id"]]
    cells = {"centre": (("LC4", "right"), ("LPLC2", "left")), "left": (("LPLC4", "left"), ("LC22", "left"))}
    assert select_channels(annotations(extra), model_ids, cells) == {"centre": (3, 0), "left": (18, 19, 20)}
    with pytest.raises(ValueError, match="no right LPLC4 neuron is in the model"):
        select_channels(annotations(extra), model_ids, {"right": (("LPLC4", "right"),)})


@pytest.mark.slow
def test_every_candidate_channel_has_its_cells_in_the_real_model():
    tables = load_tables(data.ANNOTATIONS, data.COMPLETENESS)
    m3 = select_channels(*tables, MAPPINGS["M3"].cells)
    assert (len(m3["centre"]), len(m3["left"]), len(m3["right"])) == (108 + 102 + 54 + 50, 56 + 43, 54 + 46)
    m1 = select_channels(*tables, MAPPINGS["M1"].cells)
    assert (len(m1["centre"]), len(m1["left"]), len(m1["right"])) == (210, 54, 50)


@pytest.mark.slow
def test_the_real_data_has_the_cell_counts_the_spec_quotes():
    selection = load_selection(data.ANNOTATIONS, data.COMPLETENESS)
    in_model = {name: c["in_model"] for name, c in selection.coverage.items()}
    assert in_model == {"LPLC2_left": 108, "LPLC2_right": 102, "LC4_left": 54, "LC4_right": 50,
                        **{f"{t}_{s}": 1 for t in TYPES[2:] for s in ("left", "right")}}
    assert all(c["annotated"] == c["in_model"] for c in selection.coverage.values())
    assert len(selection.inputs["left"]) == 162 and len(selection.inputs["right"]) == 152
