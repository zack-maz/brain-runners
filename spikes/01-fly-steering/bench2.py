"""Warm short-window cost (cython) with a looming stimulus, restore vs continuous."""
import json, time
import numpy as np
from flysim import *
ann, comp, _ = load_tables(); sets, _ = sensory_sets(ann)
L = sets['lplc2']['left'] + sets['lc4']['left']; R = sets['lplc2']['right'] + sets['lc4']['right']
fly = Fly(L + R, target='cython')
rv = np.r_[np.full(len(L), 150.0), np.zeros(len(R))]
fly.window(rv, 50)  # warm-up
res = {}
for dur in (20, 50, 100, 200):
    w = [fly.window(rv, dur)[1] for _ in range(5)]
    res[f'restore_{dur}ms'] = [round(np.mean(w), 3), round(np.std(w), 3)]
fly.net.restore('clean')
w = [fly.window(rv if k % 2 else rv[::-1].copy(), 100, fresh=False)[1] for k in range(6)]
res['continuous_100ms'] = [round(np.mean(w), 3), round(np.std(w), 3)]
print(json.dumps(res)); json.dump(res, open('results/bench2_cython.json', 'w'), indent=1)
