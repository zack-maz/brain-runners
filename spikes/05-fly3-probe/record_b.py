"""Spike 05, part B recording (throwaway, the one brain): single gaps in each of the 42 tiles and a blank, 8 noise
repeats, 4 gains (B1). Saves every DN's early/late counts and the input cells' counts to data/spike05/partB_<gain>.npz.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import GAINS, STORE, TILES, DNBrain, Retina  # noqa: E402

REPEATS = 8
CONDITIONS = TILES + [None]  # None = blank
STORE.mkdir(parents=True, exist_ok=True)

t0 = time.perf_counter()
brain = DNBrain()
build_s = time.perf_counter() - t0
retina = Retina(brain.fields_in_slot_order())
meta = {"dn_annotated": brain.dn_annotated, "dn_in_model": len(brain.dn_index), "dn_type": brain.dn_type,
        "dn_root": brain.dn_root, "cells": [int(i) for i in brain.cells], "build_s": build_s, "tiles": TILES}
json.dump(meta, open(STORE / "partB_meta.json", "w"))
print(f"brain built in {build_s:.0f} s; {len(brain.dn_index)} of {brain.dn_annotated} DNs in the model", flush=True)
for gi, gain in enumerate(GAINS):
    out = STORE / f"partB_{int(gain)}.npz"
    if out.exists():
        continue
    early, late, inputs, rates, seeds, walls, cond, rep = [], [], [], [], [], [], [], []
    for ci, tile in enumerate(CONDITIONS):
        hz = retina.rates([] if tile is None else [tile], gain)
        for k in range(REPEATS):
            seed = 50_000 + 10_000 * gi + 100 * ci + k
            w = brain.window(hz, seed)
            early.append(w["early"]); late.append(w["late"]); inputs.append(w["inputs"])
            rates.append(hz); seeds.append(seed); walls.append(w["wall_s"]); cond.append(ci); rep.append(k)
    np.savez_compressed(out, early=np.array(early), late=np.array(late), inputs=np.array(inputs),
                        rates=np.array(rates), seeds=np.array(seeds), wall_s=np.array(walls),
                        cond=np.array(cond), rep=np.array(rep))
    E = np.array(early) + np.array(late)
    print(f"gain {gain:.0f}: {len(cond)} windows, {np.mean(walls):.3f} s each; DNs that fired at all "
          f"{int((E.sum(0) > 0).sum())}; mean DN spikes/window {E.sum(1).mean():.1f}", flush=True)
print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)
