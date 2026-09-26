"""Spike 05, part C (throwaway, the one brain): DAgger on 1000-1019, six round-0 variants played on 1300-1309, rounds
1-2 with the winner, then fly3, no brain and blind brain on 1300-1309 (rules C1-C12 of REPORT.md).

Every phase's recording goes to data/spike05/partC/<phase>.npz and is skipped when it exists, so a crash resumes.
Results: spikes/05-fly3-probe/partC.json.
"""
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, MOVES, STORE, DNBrain, Retina, Standardizer, fit, load_fields, noise_seed, predict_proba  # noqa: E402

from bakeoff.game.engine import Game  # noqa: E402
from bakeoff.game.track import generate_track  # noqa: E402
from bakeoff.players.solver import solve, solve_depths  # noqa: E402
from bakeoff.senses import compute_senses  # noqa: E402

TRAIN = list(range(1000, 1020))
TEST = list(range(1300, 1310))
L2S, L1S = (0.001, 0.01, 0.1), (0.0, 0.001, 0.01)
VARIANTS = [("set", 1), ("single", 1), ("set", 3), ("single", 3), ("set", 10), ("single", 10)]  # simplest first
BUDGET_S = 3 * 3600
OUT = STORE / "partC"
OUT.mkdir(parents=True, exist_ok=True)
B = json.load(open(HERE / "partB.json"))
GAIN, HALVES, TWO = B["chosen_gain"], B["halves"]["adopted"], B["averaging"]["adopted"]
brain_s = {"windows": 0, "seconds": 0.0}

_brain = None
_retina = None


def brain():
    global _brain, _retina
    if _brain is None:
        _brain = DNBrain()
        _retina = Retina(_brain.fields_in_slot_order())
    return _brain


def retina():
    global _retina
    if _retina is None:
        # slot order without building the brain: the brain's input cells are fly's two eyes, each group sorted
        import pandas as pd

        from bakeoff.fly import data
        from bakeoff.fly.channels import FLY_CELLS
        from bakeoff.fly.neurons import load_tables, select_channels

        ch = select_channels(*load_tables(data.ANNOTATIONS, data.COMPLETENESS), FLY_CELLS)
        order = [i for c in ch.values() for i in c]
        by = {c["model_index"]: c for c in load_fields()}
        _retina = Retina([by[i] for i in order])
    return _retina


def sense(senses, phase, seed, row, blind=False):
    """-> dict of this decision's raw record: rates, DN early/late (summed over 1 or 2 windows), wall"""
    hz = retina().rates_of_senses(senses, GAIN)
    rec = {"rates": hz}
    if phase.startswith("nobrain"):
        return rec
    b = brain()
    drive = np.zeros_like(hz) if blind else hz
    seeds = [noise_seed(phase, seed, row)] + ([noise_seed(phase + ":b", seed, row)] if TWO else [])
    early = late = 0
    wall = 0.0
    for s in seeds:
        w = b.window(drive, s)
        early, late, wall = early + w["early"], late + w["late"], wall + w["wall_s"]
    n = len(seeds)
    rec.update(early=early / n, late=late / n, wall=wall)
    brain_s["windows"] += n
    brain_s["seconds"] += wall
    return rec


def feats(rec_or_arrays, nobrain):
    if nobrain:
        return np.log1p(np.atleast_2d(rec_or_arrays["rates"]))
    e, l = np.atleast_2d(rec_or_arrays["early"]), np.atleast_2d(rec_or_arrays["late"])
    return np.log1p(np.c_[e, l]) if HALVES else np.log1p(e + l)


def play(phase, seeds, model=None, rescue=False, nobrain=False, blind=False):
    """model None: the solver drives (round 0). rescue: DAgger (C4). Otherwise a scoring play (C3)."""
    path = OUT / f"{phase}.npz"
    if path.exists():
        return dict(np.load(path, allow_pickle=True))
    cols = {k: [] for k in ("track", "row", "rates", "early", "late", "depths", "solver", "chosen", "executed",
                            "rescued", "decision_s", "window_s")}
    scores, rescues = [], []
    for seed in seeds:
        game = Game(generate_track(seed))
        window = game.track.rules.window
        first_fail = None
        n_rescue = 0
        while not game.over:
            t0 = time.perf_counter()
            senses = compute_senses(game)
            depths = solve_depths(senses, window)
            rec = sense(senses, phase, seed, senses["rows_survived"], blind)
            solver_move = solve(senses, window)
            if model is None:
                chosen = solver_move
            else:
                s, W = model
                chosen = MOVES[int(predict_proba(W, s(feats(rec, nobrain))).argmax())]
            executed, rescued = chosen, False
            if rescue:
                trial = copy.deepcopy(game)
                trial.step(chosen)
                if not trial.alive:
                    if first_fail is None:
                        first_fail = game.rows_survived
                    executed, rescued = solver_move, True
                    n_rescue += 1
            cols["track"].append(seed); cols["row"].append(game.row); cols["rates"].append(rec["rates"])
            if not nobrain:
                cols["early"].append(rec["early"]); cols["late"].append(rec["late"])
                cols["window_s"].append(rec["wall"])
            cols["depths"].append([depths[m] for m in MOVES]); cols["solver"].append(MOVES.index(solver_move))
            cols["chosen"].append(MOVES.index(chosen)); cols["executed"].append(MOVES.index(executed))
            cols["rescued"].append(rescued)
            game.step(executed)
            cols["decision_s"].append(time.perf_counter() - t0)
        scores.append(game.rows_survived if first_fail is None else first_fail)
        rescues.append(n_rescue)
        print(f"  {phase} track {seed}: {scores[-1]} rows (rescues {n_rescue}); brain so far "
              f"{brain_s['seconds'] / 60:.1f} min", flush=True)
    arrays = {k: np.array(v) for k, v in cols.items()}
    arrays["scores"] = np.array(scores)
    arrays["rescues"] = np.array(rescues)
    arrays["seeds"] = np.array(seeds)
    np.savez_compressed(path, **arrays)
    return arrays


def labels(rec, target, w):
    D = rec["depths"]
    best = D.max(1, keepdims=True)
    mask = (D == best) if target == "set" else np.eye(4, dtype=bool)[rec["solver"]]
    critical = (D.min(1) == 0) & (D.max(1) > 0)
    weights = np.where(critical, float(w), 1.0)
    return mask, weights, D == best


def cat(recs):
    return {k: np.concatenate([r[k] for r in recs]) for k in ("track", "rates", "early", "late", "depths", "solver")
            if all(k in r and len(r[k]) for r in recs)}


def fit_model(recs, target, w, nobrain):
    """C6 + C7: penalty by 5-fold CV grouped by track, then the fit on everything."""
    rec = cat(recs)
    X = feats(rec, nobrain)
    mask, weights, safe = labels(rec, target, w)
    tracks = np.unique(rec["track"])
    folds = [tracks[i::5] for i in range(5)]
    grid = []
    for l1 in L1S:
        for l2 in L2S:
            sc = []
            for f in folds:
                te = np.isin(rec["track"], f)
                s = Standardizer(X[~te])
                W = fit(s(X[~te]), mask[~te], weights[~te], l1=l1, l2=l2)
                hit = safe[te][np.arange(te.sum()), predict_proba(W, s(X[te])).argmax(1)]
                sc.append(float((hit * weights[te]).sum() / weights[te].sum()))
            grid.append({"l1": l1, "l2": l2, "score": float(np.mean(sc))})
    best = max(g["score"] for g in grid)
    pick = max((g for g in grid if g["score"] >= best - 0.005), key=lambda g: (g["l1"], g["l2"]))
    s = Standardizer(X)
    W = fit(s(X), mask, weights, l1=pick["l1"], l2=pick["l2"])
    return (s, W), {"penalty": pick, "grid": grid, "rows": int(len(X)), "features": int(s.keep.sum()),
                    "nonzero_weights": int((W[:-1] != 0).any(1).sum())}


def moves_of(rec):
    return {m: int((rec["chosen"] == i).sum()) for i, m in enumerate(MOVES)}


def summary(rec):
    sc = rec["scores"]
    return {"scores": sc.tolist(), "mean_rows": float(sc.mean()), "moves": moves_of(rec),
            "decisions": int(len(rec["chosen"])), "rescues": rec["rescues"].tolist()}


def top_dns(model, nobrain=False, k=20):
    if nobrain:
        return None
    meta = json.load(open(STORE / "partB_meta.json"))
    s, W = model
    full = np.zeros((len(s.keep), 4))
    full[s.keep] = W[:-1]
    per = np.abs(full).sum(1)
    n = len(meta["dn_type"])
    if HALVES:
        per = per[:n] + per[n:]
    order = np.argsort(-per)
    rank = {t: None for t in ("DNa02", "DNa01", "DNg13", "DNp01")}
    for pos, i in enumerate(order):
        t = meta["dn_type"][i].rsplit("_", 1)[0]
        if t in rank and rank[t] is None and per[i] > 0:
            rank[t] = pos + 1
    return {"top": [{"type": meta["dn_type"][i], "root_id": meta["dn_root"][i], "weight": round(float(per[i]), 4)}
                    for i in order[:k]], "first_rank_of": rank, "dns_with_weight": int((per > 0).sum())}


results = {"gain": GAIN, "halves": HALVES, "two_windows": TWO}
t_start = time.perf_counter()

# round 0 (solver's path) and the six variants
r0 = play("r0", TRAIN)
results["round0"] = {"rows": int(len(r0["chosen"])), "window_s_mean": float(r0["window_s"].mean()),
                     "decision_s_mean": float(r0["decision_s"].mean())}
print("round 0:", results["round0"], flush=True)
variants = {}
for target, w in VARIANTS:
    name = f"{target}_w{w}"
    model, info = fit_model([r0], target, w, nobrain=False)
    rec = play(f"var_{name}", TEST, model)
    variants[name] = {"fit": info, **summary(rec), "window_s_mean": float(rec["window_s"].mean())}
    print(name, variants[name]["mean_rows"], info["penalty"], flush=True)
results["variants"] = variants
best = max(v["mean_rows"] for v in variants.values())
winner = next(f"{t}_w{w}" for t, w in VARIANTS if variants[f"{t}_w{w}"]["mean_rows"] >= best - 1.0)
target, w = winner.split("_w")[0], int(winner.split("_w")[1])
results["winner"] = winner
print("winner", winner, flush=True)


def dagger(nobrain):
    tag = "nobrain" if nobrain else "fly3"
    recs = [r0] if not nobrain else [{k: r0[k] for k in ("track", "rates", "depths", "solver")}]
    model, info = fit_model(recs, target, w, nobrain)
    rounds = [{"round": 0, "fit": info}]
    for k in (1, 2):
        if not nobrain and k == 2:
            done = [np.load(p)["window_s"] for p in OUT.glob("*.npz") if not p.name.startswith("nobrain")]
            used = float(sum(d.sum() for d in done))
            per = used / max(1, sum(len(d) for d in done))  # per decision (both windows if two)
            remaining = (len(TRAIN) * 150 + 2 * len(TEST) * 150) * per
            if not (OUT / f"{tag}_r2.npz").exists() and used + remaining > BUDGET_S:
                rounds.append({"round": 2, "skipped": f"brain time {used / 60:.0f} min + estimate "
                                                      f"{remaining / 60:.0f} min > 180 min"})
                break
        rec = play(f"{tag}_r{k}" if nobrain else f"r{k}", TRAIN, model, rescue=True, nobrain=nobrain)
        recs.append(rec)
        model, info = fit_model(recs, target, w, nobrain)
        rounds.append({"round": k, "rows_until_first_rescue": rec["scores"].tolist(),
                       "mean_rows_until_first_rescue": float(rec["scores"].mean()),
                       "rescues": rec["rescues"].tolist(), "moves": moves_of(rec), "fit": info})
        print(tag, "round", k, rounds[-1]["mean_rows_until_first_rescue"], flush=True)
    return model, rounds


fly3_model, results["fly3_rounds"] = dagger(nobrain=False)
nb_model, results["nobrain_rounds"] = dagger(nobrain=True)
fly3 = play("final_fly3", TEST, fly3_model)
nob = play("nobrain_final", TEST, nb_model, nobrain=True)
blind = play("final_blind", TEST, fly3_model, blind=True)
results["final"] = {"fly3": summary(fly3), "no_brain": summary(nob), "blind_brain": summary(blind)}
diff = fly3["scores"] - blind["scores"]
se = float(diff.std(ddof=1) / np.sqrt(len(diff)))
margin = max(10.0, 2 * se)
c_pass = bool(fly3["scores"].mean() >= nob["scores"].mean() and blind["scores"].mean() <= fly3["scores"].mean() - margin)
results["pass"] = {"fly3_mean": float(fly3["scores"].mean()), "no_brain_mean": float(nob["scores"].mean()),
                   "blind_mean": float(blind["scores"].mean()), "blind_margin_needed": margin, "se_diff": se,
                   "passed": c_pass}
results["top_dns"] = top_dns(fly3_model)
all_windows = np.concatenate([r["window_s"] for r in (r0, fly3)])
all_decisions = np.concatenate([r["decision_s"] for r in (r0, fly3)])
results["timing"] = {"window_s_mean": float(all_windows.mean()), "decision_s_mean": float(all_decisions.mean()),
                     "brain_minutes_this_process": brain_s["seconds"] / 60,
                     "wall_minutes_this_process": (time.perf_counter() - t_start) / 60}
print(json.dumps(results["pass"], indent=1), flush=True)
json.dump(results, open(HERE / "partC.json", "w"), indent=1, default=float)
