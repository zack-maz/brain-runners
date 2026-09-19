"""Q2: lateralized stimulation. usage: run_set.py <set> [n_trials] [dur_ms] [rates csv]
<set> is one of orn, sugar, loom (LPLC2+LC4), lplc2, lc4, jo_ce.
Saves every spike of every descending/motor neuron, per trial, to results/<set>.parquet."""
import sys, time, json
import numpy as np, pandas as pd
from flysim import *

name = sys.argv[1]
n_trials = int(sys.argv[2]) if len(sys.argv) > 2 else 6
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 500
rates = [float(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [50, 150, 250]

ann, comp, flyid2i = load_tables()
sets, cov = sensory_sets(ann)
sets['loom'] = {s: sets['lplc2'][s] + sets['lc4'][s] for s in ('left', 'right')}
L, R = sets[name]['left'], sets[name]['right']
stim = L + R
outs = output_index(ann)
out_idx = set(outs.idx)
fly = Fly(stim, target='cython')
np.random.seed(abs(hash(name)) % 2**31)

conds = [('none', 0, 0)]
for r in rates:
    conds += [(f'L{int(r)}', r, 0), (f'R{int(r)}', 0, r)]
conds += [('both150', 150, 150)]
rows, meta = [], []
t_all = time.time()
for cname, rl, rr in conds:
    nt = 2 if cname == 'none' else n_trials
    for k in range(nt):
        rv = np.r_[np.full(len(L), rl), np.full(len(R), rr)]
        counts, wall = fly.window(rv, dur)
        i = np.asarray(fly.mon.i); t = np.asarray(fly.mon.t / fly.ms)
        keep = np.isin(i, list(out_idx))
        rows.append(pd.DataFrame({'cond': cname, 'trial': k, 'idx': i[keep], 't_ms': t[keep]}))
        stim_rate = counts[stim].sum() / max(1, len(stim)) / (dur / 1000)
        meta.append({'cond': cname, 'trial': k, 'wall_s': wall, 'total_spikes': int(counts.sum()),
                     'active_neurons': int((counts > 0).sum()), 'mean_stim_neuron_hz': float(stim_rate)})
        print(name, cname, k, f'{wall:.1f}s', 'spikes', int(counts.sum()), 'active', int((counts > 0).sum()), flush=True)
pd.concat(rows).to_parquet(f'results/{name}.parquet')
json.dump({'set': name, 'n_left': len(L), 'n_right': len(R), 'dur_ms': dur, 'n_trials': n_trials,
           'rates': rates, 'coverage': {f'{k[0]}_{k[1]}': v for k, v in cov.items()},
           'wall_total_s': time.time() - t_all, 'trials': meta}, open(f'results/{name}.json', 'w'), indent=1)
