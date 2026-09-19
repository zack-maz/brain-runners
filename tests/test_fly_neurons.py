import pandas as pd
import pytest

from bakeoff.fly import data
from bakeoff.fly.neurons import load_selection, select_neurons

TYPES = ("LPLC2", "LC4", "DNa01", "DNb01", "DNp01", "DNa02")


def annotations(extra=()):
    rows = [(100 + 10 * t + s, cell_type, side)
            for t, cell_type in enumerate(TYPES) for s, side in enumerate(("left", "right"))]
    return pd.DataFrame(list(rows) + list(extra), columns=["root_id", "cell_type", "side"])


def test_a_neurons_model_index_is_its_position_in_the_model_id_list():
    model_ids = [999] + [int(r) for r in annotations()["root_id"]]  # 999 shifts every index by one
    selection = select_neurons(annotations(), model_ids)
    assert selection.inputs == {"left": (1, 3), "right": (2, 4)}  # LPLC2 then LC4 of that eye
    assert selection.readouts["DNa01_left"] == (5,) and selection.readouts["DNp01_right"] == (10,)
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


@pytest.mark.slow
def test_the_real_data_has_the_cell_counts_the_spec_quotes():
    selection = load_selection(data.ANNOTATIONS, data.COMPLETENESS)
    in_model = {name: c["in_model"] for name, c in selection.coverage.items()}
    assert in_model == {"LPLC2_left": 108, "LPLC2_right": 102, "LC4_left": 54, "LC4_right": 50,
                        **{f"{t}_{s}": 1 for t in TYPES[2:] for s in ("left", "right")}}
    assert all(c["annotated"] == c["in_model"] for c in selection.coverage.values())
    assert len(selection.inputs["left"]) == 162 and len(selection.inputs["right"]) == 152
