"""Spike 05, part B analysis (throwaway, no brain): the readouts of B3-B8 on data/spike05/partB_*.npz.
Writes spikes/05-fly3-probe/partB.json."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GAINS, HERE, STORE, TILES, Standardizer, fit, predict_proba  # noqa: E402

LAMBDAS = (0.001, 0.01, 0.1, 1.0)
FOLDS = [(2 * k, 2 * k + 1) for k in range(4)]
LANE = np.array([o + 3 for r, o in TILES])
ROW = np.array([r - 1 for r, o in TILES])


def features(d, kind):
    if kind == "dn_whole":
        return np.log1p(d["early"] + d["late"].astype(float))
    if kind == "dn_halves":
        return np.log1p(np.c_[d["early"], d["late"]].astype(float))
    if kind == "input_rates":
        return np.log1p(d["rates"])
    if kind == "input_counts":
        return np.log1p(d["inputs"].astype(float))
    raise KeyError(kind)


def train(X, y, K, lam):
    s = Standardizer(X)
    return s, fit(s(X), np.eye(K, dtype=bool)[y], l2=lam)


def acc(model, X, y):
    s, W = model
    return float((predict_proba(W, s(X)).argmax(1) == y).mean())


def choose_lambda(X, y, rep, K):
    """inner leave-one-repeat-out on the training repeats; ties within 0.005 to the larger lambda"""
    scores = []
    for lam in LAMBDAS:
        scores.append(np.mean([acc(train(X[rep != r], y[rep != r], K, lam), X[rep == r], y[rep == r])
                               for r in np.unique(rep)]))
    best = max(scores)
    return max(l for l, s in zip(LAMBDAS, scores) if s >= best - 0.005), scores


def cv(X, y, rep, K, averaged=None):
    """outer 4-fold CV by repeats. averaged: (Xmean_by_fold) callable -> also score the mean of the 2 held-out."""
    out, out_avg, lams = [], [], []
    for held in FOLDS:
        tr = ~np.isin(rep, held)
        lam, _ = choose_lambda(X[tr], y[tr], rep[tr], K)
        m = train(X[tr], y[tr], K, lam)
        te = np.isin(rep, held)
        out.append(acc(m, X[te], y[te]))
        lams.append(lam)
        if averaged is not None:
            Xa, ya = averaged(held)
            out_avg.append(acc(m, Xa, ya))
    res = {"mean": float(np.mean(out)), "sd": float(np.std(out, ddof=1)), "folds": out, "lambdas": lams}
    if averaged is not None:
        res["averaged"] = {"mean": float(np.mean(out_avg)), "sd": float(np.std(out_avg, ddof=1)), "folds": out_avg}
    return res


results = {"chance": {"lane": 1 / 7, "row": 1 / 6}, "gains": {}}
meta = json.load(open(STORE / "partB_meta.json"))
results["dn_annotated"], results["dn_in_model"] = meta["dn_annotated"], meta["dn_in_model"]
data = {}
for gain in GAINS:
    d = dict(np.load(STORE / f"partB_{int(gain)}.npz"))
    data[gain] = d
    fit_rows = d["cond"] < len(TILES)
    E = d["early"] + d["late"].astype(int)
    blank = ~fit_rows
    g = {"window_s_mean": float(d["wall_s"].mean()),
         "dns_fired_any": int((E.sum(0) > 0).sum()),
         "dns_fired_in_half_the_windows": int(((E > 0).mean(0) >= 0.5).sum()),
         "dn_spikes_per_window_mean": float(E[fit_rows].sum(1).mean()),
         "dns_fired_blank": int((E[blank].sum(0) > 0).sum()),
         "input_hz_max": float(d["rates"].max()),
         "fits": {}}
    rep = d["rep"][fit_rows]
    cond = d["cond"][fit_rows]
    for kind in ("dn_whole", "dn_halves", "input_rates", "input_counts"):
        X = features(d, kind)[fit_rows]
        g["fits"][kind] = {}
        for target, labels, K in (("lane", LANE, 7), ("row", ROW, 6)):
            y = labels[cond]
            g["fits"][kind][target] = cv(X, y, rep, K)
            print(gain, kind, target, round(g["fits"][kind][target]["mean"], 3),
                  round(g["fits"][kind][target]["sd"], 3), flush=True)
    results["gains"][str(int(gain))] = g

# B5: the gain
lane_acc = {g: results["gains"][str(int(g))]["fits"]["dn_whole"]["lane"]["mean"] for g in GAINS}
best = max(lane_acc.values())
chosen = min(g for g in GAINS if lane_acc[g] >= best - 0.01)
results["chosen_gain"] = chosen
f = results["gains"][str(int(chosen))]["fits"]
# B6: halves
diff = f["dn_halves"]["lane"]["mean"] - f["dn_whole"]["lane"]["mean"]
spread = max(f["dn_halves"]["lane"]["sd"], f["dn_whole"]["lane"]["sd"])
halves = diff > spread
results["halves"] = {"diff": diff, "spread": spread, "adopted": bool(halves)}
kind = "dn_halves" if halves else "dn_whole"
# B7: averaging, at the chosen gain and features
d = data[chosen]
fit_rows = d["cond"] < len(TILES)
rep, cond = d["rep"][fit_rows], d["cond"][fit_rows]
early, late = d["early"][fit_rows].astype(float), d["late"][fit_rows].astype(float)


def averaged(held):
    Xs, ys = [], []
    for c in range(len(TILES)):
        m = (cond == c) & np.isin(rep, held)
        e, l = early[m].mean(0), late[m].mean(0)
        Xs.append(np.log1p(np.r_[e, l]) if halves else np.log1p(e + l))
        ys.append(LANE[c])
    return np.array(Xs), np.array(ys)


X = features(d, kind)[fit_rows]
avg = cv(X, LANE[cond], rep, 7, averaged=averaged)
gain_avg = avg["averaged"]["mean"] - avg["mean"]
results["averaging"] = {"single": avg["mean"], "mean_of_two": avg["averaged"]["mean"], "gain": gain_avg,
                        "adopted": bool(gain_avg >= 0.10), "detail": avg}
# B8: pass
a = f[kind]["lane"]
passed = a["mean"] >= 0.30 and (a["mean"] - 1 / 7) > 3 * a["sd"]
results["pass"] = {"features": kind, "lane_acc": a["mean"], "lane_sd": a["sd"], "passed": bool(passed)}
print(json.dumps({k: results[k] for k in ("chosen_gain", "halves", "pass")}, indent=1))
print("averaging", results["averaging"]["single"], results["averaging"]["mean_of_two"])
json.dump(results, open(HERE / "partB.json", "w"), indent=1)
