"""Pathway analysis (pandas/numpy/scipy only; no Brian2). Signed, input-normalised influence.
A[post, pre] = (signed synapse count) / (total synapses onto post). k-hop influence of an input set = A^k x."""
import sys, numpy as np, pandas as pd, scipy.sparse as sp
from collections import defaultdict
ROOT = "data/Drosophila_brain_model/"
con = pd.read_parquet(ROOT + "Connectivity_783.parquet")
ids = pd.read_csv(ROOT + "Completeness_783.csv", index_col=0).index.values
N = len(ids)
ann = pd.read_csv("data/neuron_annotations.tsv", sep="\t", usecols=["root_id", "cell_type", "side", "super_class"], low_memory=False)
ann = ann.set_index("root_id").reindex(ids)
ctype = ann.cell_type.fillna("?").values; side = ann.side.fillna("?").values; sclass = ann.super_class.fillna("?").values
pre = con.Presynaptic_Index.values; post = con.Postsynaptic_Index.values; w = con["Excitatory x Connectivity"].values.astype(float)
tot_in = np.bincount(post, weights=np.abs(w), minlength=N); tot_in[tot_in == 0] = 1
A = sp.csr_matrix((w / tot_in[post], (post, pre)), shape=(N, N))
R = sp.csr_matrix((w, (post, pre)), shape=(N, N))  # raw signed synapses
def members(t, s=None):
    m = (ctype == t) & ((side == s) if s else True)
    return np.where(m)[0]
