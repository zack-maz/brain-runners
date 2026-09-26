"""Spike 05 (throwaway): the retina (R1-R3), a brain window that reads every DN, and the readout (B3, C6).

Everything here is ours except the brain. Rules: REPORT.md, "Rules fixed before measuring".
"""
from __future__ import annotations

import json
import time
import zlib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STORE = HERE.parents[1] / "data" / "spike05"  # git-ignored recordings
CAP_HZ = 500.0
GAINS = (500.0, 1000.0, 2000.0, 4000.0)
TILES = [(r, o) for r in range(1, 7) for o in range(-3, 4)]  # 42 visible tiles of v2
MOVES = ("stay", "left", "right", "jump")  # the solver's tie order


# ---------------------------------------------------------------- the retina (ours)
def tile_geometry(row: int, offset: int) -> tuple[float, float, float]:
    """(azimuth, elevation, angular radius) in degrees, R1."""
    az = np.degrees(np.arctan2(offset, row))
    el = -np.degrees(np.arctan2(1.0, row))
    rho = np.degrees(np.arctan(0.5 / np.sqrt(offset ** 2 + row ** 2 + 1.0)))
    return float(az), float(el), float(rho)


class Retina:
    def __init__(self, cells_in_slot_order: list[dict]):
        self.cells = cells_in_slot_order
        az = np.radians([c["az_deg"] for c in self.cells])
        el = np.radians([c["el_deg"] for c in self.cells])
        sig = np.array([c["sigma_deg"] for c in self.cells])
        # coverage of every cell by a gap in every tile: 42 x cells (R2)
        cov = np.zeros((len(TILES), len(self.cells)))
        for k, (r, o) in enumerate(TILES):
            ta, te, rho = tile_geometry(r, o)
            ta, te = np.radians(ta), np.radians(te)
            cosd = np.sin(te) * np.sin(el) + np.cos(te) * np.cos(el) * np.cos(az - ta)
            d = np.degrees(np.arccos(np.clip(cosd, -1, 1)))
            s = rho / 2
            cov[k] = s ** 2 / (s ** 2 + sig ** 2) * np.exp(-d ** 2 / (2 * (s ** 2 + sig ** 2)))
        self.coverage = cov
        self.tile_index = {t: k for k, t in enumerate(TILES)}

    def rates(self, gaps, gain: float) -> np.ndarray:
        """gaps: iterable of (row, offset) visible gaps -> Hz per cell (slot order)."""
        total = np.zeros(len(self.cells))
        for g in gaps:
            total += self.coverage[self.tile_index[g]]
        return np.minimum(CAP_HZ, gain * total)

    def rates_of_senses(self, senses: dict, gain: float) -> np.ndarray:
        return self.rates([(e["row"], o) for e in senses["ahead"] for o in e["gaps_relative"]], gain)


def load_fields() -> list[dict]:
    return json.load(open(HERE / "fields.json"))["cells"]


# ---------------------------------------------------------------- the brain
class DNBrain:
    """One real brain (the project's Brain, fly's two-eye input = every LPLC2 + LC4 cell), driven cell by cell,
    reading every descending neuron. One per process."""

    def __init__(self):
        import pandas as pd

        from bakeoff.fly import data
        from bakeoff.fly.brain import Brain
        from bakeoff.fly.channels import FLY_CELLS

        self.brain = Brain(inputs={"fly3": FLY_CELLS})
        self.b2 = self.brain._b2
        self.group, _, self.cells, _ = self.brain._groups["fly3"]
        ann = pd.read_csv(data.ANNOTATIONS, sep="\t", usecols=["root_id", "cell_type", "side", "super_class"])
        model_ids = pd.read_csv(data.COMPLETENESS, index_col=0).index
        index_of = {int(r): i for i, r in enumerate(model_ids)}
        dn = ann[ann.super_class == "descending"].drop_duplicates("root_id")
        self.dn_annotated = len(dn)
        dn = dn[dn.root_id.isin(index_of)]
        self.dn_index = np.array([index_of[int(r)] for r in dn.root_id])
        self.dn_type = [f"{t}_{s}" for t, s in zip(dn.cell_type.fillna("?"), dn.side.fillna("?"))]
        self.dn_root = [int(r) for r in dn.root_id]
        n = len(model_ids)
        self.dn_slot = np.full(n, -1)
        self.dn_slot[self.dn_index] = np.arange(len(self.dn_index))
        self.in_slot = np.full(n, -1)
        self.in_slot[self.cells] = np.arange(len(self.cells))

    def fields_in_slot_order(self) -> list[dict]:
        by_index = {c["model_index"]: c for c in load_fields()}
        return [by_index[int(i)] for i in self.cells]

    def window(self, rates_hz: np.ndarray, seed: int) -> dict:
        b2, net = self.b2, self.brain._net
        t0 = time.perf_counter()
        net.restore("clean")
        b2.seed(seed)
        self.group.rates = np.asarray(rates_hz, float) * b2.Hz
        net.run(self.brain.window_ms * b2.ms)
        who = np.asarray(self.brain._monitor.i)
        when = np.asarray(self.brain._monitor.t / b2.ms) - self.brain._t0_ms
        dn = self.dn_slot[who]
        m = dn >= 0
        k = len(self.dn_index)
        early = np.bincount(dn[m & (when < 50)], minlength=k)
        late = np.bincount(dn[m & (when >= 50)], minlength=k)
        inp = self.in_slot[who]
        return {"early": early.astype(np.int16), "late": late.astype(np.int16),
                "inputs": np.bincount(inp[inp >= 0], minlength=len(self.cells)).astype(np.int16),
                "total": int(len(who)), "wall_s": time.perf_counter() - t0}


def noise_seed(phase: str, seed: int, row: int) -> int:
    return zlib.crc32(f"fly3probe:{phase}:{seed}:{row}".encode())


# ---------------------------------------------------------------- the readout (ours)
class Standardizer:
    def __init__(self, X: np.ndarray):
        self.mean = X.mean(0)
        self.sd = X.std(0)
        self.keep = self.sd > 0

    def __call__(self, X: np.ndarray) -> np.ndarray:
        return (X[:, self.keep] - self.mean[self.keep]) / self.sd[self.keep]


def softmax(Z):
    Z = Z - Z.max(1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(1, keepdims=True)


def fit(X, mask, weights=None, l1=0.0, l2=0.0, iters=3000, tol=1e-7):
    """Multinomial logistic readout with a set-valued target: minimise
    -sum_i w_i log sum_{a in S_i} p_i(a) / sum w + l1 |W|_1 + l2/2 |W|^2 (bias free), by FISTA from zero.
    X: n x d (already standardised), mask: n x K bool (the target set; one-hot for a single target)."""
    n, d = X.shape
    K = mask.shape[1]
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    Xb = np.c_[X, np.ones(n)]
    L = 0.5 * np.linalg.norm(Xb * np.sqrt(w)[:, None], 2) ** 2 + l2  # Lipschitz bound of the smooth part
    step = 1.0 / L
    W = np.zeros((d + 1, K))
    Y, t, prev = W.copy(), 1.0, np.inf
    pen = np.r_[np.ones(d), 0.0][:, None]
    for _ in range(iters):
        P = softmax(Xb @ Y)
        Q = np.where(mask, P, 0.0)
        Q /= Q.sum(1, keepdims=True)
        G = Xb.T @ ((P - Q) * w[:, None]) + l2 * Y * pen
        Wn = Y - step * G
        if l1 > 0:
            thr = step * l1 * pen
            Wn = np.sign(Wn) * np.maximum(np.abs(Wn) - thr, 0.0)
        tn = (1 + np.sqrt(1 + 4 * t * t)) / 2
        Y = Wn + (t - 1) / tn * (Wn - W)
        W, t = Wn, tn
        if _ % 25 == 0:
            obj = objective(Xb, mask, w, W, l1, l2, pen)
            if abs(prev - obj) < tol * max(1.0, abs(obj)):
                break
            prev = obj
    return W


def objective(Xb, mask, w, W, l1, l2, pen):
    P = softmax(Xb @ W)
    ps = np.where(mask, P, 0.0).sum(1)
    return float(-(w * np.log(np.maximum(ps, 1e-300))).sum() + l1 * np.abs(W * pen).sum()
                 + l2 / 2 * ((W * pen) ** 2).sum())


def predict_proba(W, X):
    return softmax(np.c_[X, np.ones(len(X))] @ W)
