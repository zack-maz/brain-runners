"""Spike 05, part A (throwaway): a place on the eye for every LPLC2 / LC4 cell, by the rules A1-A5 of REPORT.md.

No brain. Writes spikes/05-fly3-probe/fields.json. Rules are in the report; this only carries them out.
"""
import json

import numpy as np
import pandas as pd

from bakeoff.fly import data

OUT = "spikes/05-fly3-probe/fields.json"
VOXEL_UM = np.array([0.004, 0.004, 0.040])
LAYERS = {"a": ("T4a", "T5a"), "b": ("T4b", "T5b"), "c": ("T4c", "T5c"), "d": ("T4d", "T5d")}
SHARED = ("T2", "T2a", "Tm2", "Tm3", "Tm4", "TmY3")
SIGMA = {"LPLC2": 20.0, "LC4": 15.0}
AZ_RANGE, EL_RANGE = (-10.0, 160.0), (-60.0, 60.0)
BOOT = 200
rng = np.random.default_rng(5)

a = pd.read_csv(data.ANNOTATIONS, sep="\t", low_memory=False,
                usecols=["root_id", "cell_type", "side", "pos_x", "pos_y", "pos_z"])
a = a.drop_duplicates("root_id").set_index("root_id")
pos_um = a[["pos_x", "pos_y", "pos_z"]].to_numpy(float) * VOXEL_UM
a[["x", "y", "z"]] = pos_um
model_ids = pd.read_csv(data.COMPLETENESS, index_col=0).index
index_of = {int(r): i for i, r in enumerate(model_ids)}
c = pd.read_parquet(data.CONNECTIVITY, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
per_side = a.groupby(["cell_type", "side"]).size()


def edges(cells, types):
    e = c[c.Postsynaptic_ID.isin(cells) & c.Presynaptic_ID.isin(a.index)]
    e = e.assign(ptype=a.loc[e.Presynaptic_ID, "cell_type"].to_numpy())
    e = e[e.ptype.isin(types)]
    return e.assign(x=a.loc[e.Presynaptic_ID, "x"].to_numpy(), y=a.loc[e.Presynaptic_ID, "y"].to_numpy(),
                    z=a.loc[e.Presynaptic_ID, "z"].to_numpy())


def centres(e):
    """post root id -> (weighted centre xyz, synapses, the partner table for the bootstrap)"""
    out = {}
    for post, g in e.groupby("Postsynaptic_ID"):
        w = g.Connectivity.to_numpy(float)
        p = g[["x", "y", "z"]].to_numpy()
        out[int(post)] = ((p * w[:, None]).sum(0) / w.sum(), w.sum(), p, w)
    return out


def boot(p, w):
    """BOOT resampled centres of one cell: partners drawn with replacement, each with its synapse count."""
    k = rng.integers(0, len(w), size=(BOOT, len(w)))
    ww = w[k]
    return (p[k] * ww[..., None]).sum(1) / ww.sum(1, keepdims=True)


def unit(v):
    return v / np.linalg.norm(v)


result = {"cells": [], "eyes": {}}
for side in ("left", "right"):
    columnar = {t for (t, s), n in per_side.items() if s == side and n >= 300}
    lplc2 = a[(a.cell_type == "LPLC2") & (a.side == side)].index
    lc4 = a[(a.cell_type == "LC4") & (a.side == side)].index
    own = centres(edges(lplc2, columnar))
    ids = sorted(own)
    C = np.array([own[r][0] for r in ids])
    mean = C.mean(0)
    E = np.linalg.svd(C - mean, full_matrices=False)[2][:2].T  # 3x2 plane of the LPLC2 centres

    # A2: the layer rule
    layer = {k: centres(edges(lplc2, set(ts))) for k, ts in LAYERS.items()}
    pop = {k: a[a.cell_type.isin(ts) & (a.side == side)][["x", "y", "z"]].to_numpy().mean(0)
           for k, ts in LAYERS.items()}
    vp, vd = [], []
    for r in ids:
        if r in layer["a"] and r in layer["b"]:
            vp.append(E.T @ ((layer["a"][r][0] - layer["b"][r][0]) - (pop["a"] - pop["b"])))
        if r in layer["c"] and r in layer["d"]:
            vd.append(E.T @ ((layer["c"][r][0] - layer["d"][r][0]) - (pop["c"] - pop["d"])))
    vp, vd = np.array(vp), np.array(vd)
    P, D = vp.mean(0), vd.mean(0)
    frac_p = float((vp @ P > 0).mean())
    frac_d = float((vd @ D > 0).mean())
    angle = float(np.degrees(np.arccos(P @ D / np.linalg.norm(P) / np.linalg.norm(D))))
    accepted = frac_p >= 0.7 and frac_d >= 0.7 and 45 <= angle <= 135
    if accepted:
        Ph = unit(P)
        Dh = unit(D - (D @ Ph) * Ph)
        U3, V3 = -(E @ Ph), E @ Dh  # 3D directions: anterior, dorsal
        orientation = "layer rule (Klapoetke 2017), the fly's"
    else:
        V3 = unit(E @ (E.T @ np.array([0, -1.0, 0])))
        U3 = unit(np.cross(np.cross(E[:, 0], E[:, 1]), V3))
        if U3[2] > 0:
            U3 = -U3
        orientation = "OURS: -y dorsal, -z anterior"

    def uv_own(p):  # centre(s) -> (u, v)
        q = np.atleast_2d(p) - mean
        return np.stack([q @ U3, q @ V3], -1)

    uv = {r: uv_own(own[r][0])[0] for r in ids}
    boot_uv = {r: uv_own(boot(own[r][2], own[r][3])) for r in ids}

    # A3: LC4 through the shared frame, the map fitted on LPLC2
    sh_l = centres(edges(lplc2, set(SHARED)))
    sh_c = centres(edges(lc4, set(SHARED)))
    fit_ids = [r for r in ids if r in sh_l and sh_l[r][1] >= 20]
    X = np.c_[np.array([sh_l[r][0] for r in fit_ids]), np.ones(len(fit_ids))]
    Y = np.array([uv[r] for r in fit_ids])
    M = np.linalg.lstsq(X, Y, rcond=None)[0]
    r2 = 1 - ((Y - X @ M) ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)
    lc4_ids = sorted(sh_c)
    lc4_accepted = bool((r2 >= 0.5).all())
    if lc4_accepted:
        for r in lc4_ids:
            uv[r] = np.r_[sh_c[r][0], 1] @ M
            bb = boot(sh_c[r][2], sh_c[r][3])
            boot_uv[r] = np.c_[bb, np.ones(len(bb))] @ M
        lc4_source = f"shared frame {SHARED}, linear map fitted on this eye's LPLC2 (R2 u {r2[0]:.2f}, v {r2[1]:.2f})"
    else:
        CC = np.array([sh_c[r][0] for r in lc4_ids])
        m2 = CC.mean(0)
        pcs = np.linalg.svd(CC - m2, full_matrices=False)[2][:2]
        dors = pcs[np.argmax(np.abs(pcs @ [0, -1.0, 0]))]
        dors = dors * np.sign(dors @ [0, -1.0, 0])
        ant = pcs[1] if np.allclose(dors, pcs[0]) or np.allclose(dors, -pcs[0]) else pcs[0]
        ant = ant * np.sign(ant @ [0, 0, -1.0])
        for r in lc4_ids:
            uv[r] = np.array([(sh_c[r][0] - m2) @ ant, (sh_c[r][0] - m2) @ dors])
            bb = boot(sh_c[r][2], sh_c[r][3]) - m2
            boot_uv[r] = np.stack([bb @ ant, bb @ dors], -1)
        lc4_source = f"OURS: own-frame principal axes, signed by -y and -z (shared-frame map R2 {r2.round(2).tolist()} < 0.5)"

    # A4: degrees
    all_ids = ids + lc4_ids
    UV = np.array([uv[r] for r in all_ids])
    lo, hi = np.percentile(UV, 2.5, 0), np.percentile(UV, 97.5, 0)
    to_deg = lambda q: np.stack([AZ_RANGE[0] + (q[..., 0] - lo[0]) / (hi[0] - lo[0]) * (AZ_RANGE[1] - AZ_RANGE[0]),
                                 EL_RANGE[0] + (q[..., 1] - lo[1]) / (hi[1] - lo[1]) * (EL_RANGE[1] - EL_RANGE[0])], -1)
    sign = 1 if side == "right" else -1
    deg = {r: to_deg(uv[r]) for r in all_ids}
    se = {r: to_deg(boot_uv[r]).std(0) for r in all_ids}
    DEG = np.array([deg[r] for r in all_ids])
    SE = np.array([se[r] for r in all_ids])
    spread = np.percentile(DEG, 95, 0) - np.percentile(DEG, 5, 0)
    n_dist = spread / (2 * np.median(SE, 0))
    sig = np.array([SIGMA["LPLC2"]] * len(ids) + [SIGMA["LC4"]] * len(lc4_ids))
    result["eyes"][side] = {
        "cells": {"LPLC2": len(lplc2), "LPLC2_placed": len(ids), "LC4": len(lc4), "LC4_placed": len(lc4_ids)},
        "orientation": orientation, "orientation_accepted": bool(accepted),
        "layer_test": {"cells_ab": len(vp), "cells_cd": len(vd), "frac_post_agree": round(frac_p, 3),
                       "frac_dors_agree": round(frac_d, 3), "angle_P_D_deg": round(angle, 1),
                       "posterior_dir_xyz": np.round(-U3, 3).tolist(), "dorsal_dir_xyz": np.round(V3, 3).tolist()},
        "lc4_map": {"fit_cells": len(fit_ids), "r2_u": round(float(r2[0]), 3), "r2_v": round(float(r2[1]), 3),
                    "accepted": lc4_accepted, "source": lc4_source},
        "spread_P5_P95_deg": {"az": round(float(spread[0]), 1), "el": round(float(spread[1]), 1)},
        "median_boot_se_deg": {"az": round(float(np.median(SE[:, 0])), 2), "el": round(float(np.median(SE[:, 1])), 2)},
        "distinguishable_positions": {"az": round(float(n_dist[0]), 1), "el": round(float(n_dist[1]), 1)},
        "nonoverlapping_fields_info": {"az": round(float(spread[0] / (2 * np.median(sig))), 1),
                                       "el": round(float(spread[1] / (2 * np.median(sig))), 1)},
    }
    for r in all_ids:
        t = "LPLC2" if r in own else "LC4"
        result["cells"].append({
            "model_index": index_of[r], "root_id": r, "type": t, "side": side,
            "az_deg": round(float(sign * deg[r][0]), 2), "el_deg": round(float(deg[r][1]), 2),
            "se_deg": [round(float(x), 2) for x in se[r]], "sigma_deg": SIGMA[t],
            "source": (f"own-frame centre (columnar inputs), axes: {orientation}" if t == "LPLC2" else lc4_source),
        })
    print(side, json.dumps(result["eyes"][side], indent=1))

stop = any(v < 3 for e in result["eyes"].values() for v in e["distinguishable_positions"].values())
result["stop_A"] = stop
result["ours"] = [
    "the linear map from column position to degrees: azimuth -10..160 and elevation -60..60 over each eye's P2.5..P97.5 (A4)",
    "the field shape and width: Gaussian, sigma 20 deg LPLC2, 15 deg LC4 (R2)",
    "the eye's position: the left eye's cells at negative game azimuth, the right eye's at positive",
    "the orientation of any eye whose layer test failed, and LC4's if its shared-frame map failed (see eyes.*)",
]
result["sources"] = {
    "annotations": f"{data.ANNOTATIONS_URL} sha256 {data.SHA256['neuron_annotations.tsv']}",
    "connectivity": f"{data.MODEL_REPO_URL} @ {data.MODEL_REPO_COMMIT}, Connectivity_783.parquet sha256 "
                    f"{data.SHA256['Drosophila_brain_model/Connectivity_783.parquet']}",
    "layer_rule": "Klapoetke et al. 2017, Nature 551:237, LPLC2 dendrites extend outward along each layer's preferred direction",
}
print("cells", len(result["cells"]), "stop_A", stop)
json.dump(result, open(OUT, "w"), indent=1)
