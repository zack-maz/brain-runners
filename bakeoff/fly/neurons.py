"""Pick the fly's input and read-out neurons by cell type and side from the FlyWire annotations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

SIDES = ("left", "right")
INPUT_TYPES = ("LPLC2", "LC4")  # looming detectors of each eye
READOUT_TYPES = ("DNa01", "DNb01", "DNp01")  # steering, steering, Giant Fiber: these decide for fly
# read and logged for every fly; fly never decides on them. fly2 turns on DNa02 + DNa01 + DNg13 or on
# DNa01 + DNg13 (decision 42); DNb05 and DNa04 are shown only.
LOGGED_ONLY_TYPES = ("DNa02", "DNg13", "DNb05", "DNa04")


@dataclass(frozen=True)
class Selection:
    inputs: dict[str, tuple[int, ...]]  # side -> model indices of that eye's LPLC2 + LC4 cells
    readouts: dict[str, tuple[int, ...]]  # "DNa01_left" -> model indices
    coverage: dict[str, dict[str, int]]  # "LPLC2_left" -> {"annotated": 108, "in_model": 108}


def _indices(annotations: pd.DataFrame, index_of: dict[int, int], cell_type: str, side: str,
             coverage: dict[str, dict[str, int]]) -> tuple[int, ...]:
    rows = annotations[(annotations["cell_type"] == cell_type) & (annotations["side"] == side)]
    found = tuple(sorted(index_of[int(r)] for r in rows["root_id"] if int(r) in index_of))
    coverage[f"{cell_type}_{side}"] = {"annotated": len(rows), "in_model": len(found)}
    if not found:
        raise ValueError(f"no {side} {cell_type} neuron is in the model")
    return found


def select_neurons(annotations: pd.DataFrame, model_ids: Sequence[int]) -> Selection:
    """`model_ids` are the FlyWire root ids in the model's order: a neuron's model index is its
    position there. A cell that is annotated but absent from the model is counted, not used."""
    index_of = {int(root_id): i for i, root_id in enumerate(model_ids)}
    coverage: dict[str, dict[str, int]] = {}

    def indices(cell_type: str, side: str) -> tuple[int, ...]:
        return _indices(annotations, index_of, cell_type, side, coverage)

    inputs = {side: tuple(i for t in INPUT_TYPES for i in indices(t, side)) for side in SIDES}
    readouts = {f"{t}_{side}": indices(t, side) for t in READOUT_TYPES + LOGGED_ONLY_TYPES for side in SIDES}
    return Selection(inputs=inputs, readouts=readouts, coverage=coverage)


def select_channels(annotations: pd.DataFrame, model_ids: Sequence[int],
                    cells: Mapping[str, Sequence[tuple[str, str]]]) -> dict[str, tuple[int, ...]]:
    """channel -> the model indices of its (cell type, side) groups, each group sorted, in the order given.
    fly's channels (bakeoff/fly/channels.py:FLY_CELLS) give exactly `select_neurons(...).inputs`."""
    index_of = {int(root_id): i for i, root_id in enumerate(model_ids)}
    coverage: dict[str, dict[str, int]] = {}
    return {channel: tuple(i for cell_type, side in groups
                           for i in _indices(annotations, index_of, cell_type, side, coverage))
            for channel, groups in cells.items()}


def load_tables(annotations_path: Path, completeness_path: Path) -> tuple[pd.DataFrame, pd.Index]:
    """The annotations (root id, cell type, side) and the model's root ids in model order."""
    annotations = pd.read_csv(annotations_path, sep="\t", usecols=["root_id", "cell_type", "side"])
    return annotations, pd.read_csv(completeness_path, index_col=0).index


def load_selection(annotations_path: Path, completeness_path: Path) -> Selection:
    return select_neurons(*load_tables(annotations_path, completeness_path))
