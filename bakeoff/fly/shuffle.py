"""The shuffled-wiring control (fly2 spec, step 4): the same neurons and synapses, wired at random.

Each connection keeps its presynaptic neuron, its synapse count and its sign; its postsynaptic neuron is drawn
by permuting the targets among the connections of the same sign. So every neuron keeps its out-degree, its
in-degree and how many of each are excitatory or inhibitory, while which neuron talks to which is lost. (A
neuron's summed input weight is not kept: the counts travel with the presynaptic side. A permutation can
also make a self-connection or repeat a pair; the model allows both.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def shuffled_connectivity(connectivity: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = connectivity.copy()
    post_index = out["Postsynaptic_Index"].to_numpy().copy()
    post_id = out["Postsynaptic_ID"].to_numpy().copy()
    sign = out["Excitatory"].to_numpy()
    for value in np.unique(sign):
        rows = np.flatnonzero(sign == value)
        order = rows[rng.permutation(len(rows))]
        post_index[rows], post_id[rows] = post_index[order], post_id[order]
    out["Postsynaptic_Index"], out["Postsynaptic_ID"] = post_index, post_id
    return out
