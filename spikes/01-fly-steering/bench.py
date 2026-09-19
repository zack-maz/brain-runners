"""Q1: speed. usage: bench.py [numpy|cython]"""
import sys, time, json
import numpy as np
from flysim import *

target = sys.argv[1] if len(sys.argv) > 1 else 'numpy'
ann, comp, flyid2i = load_tables()
sets, cov = sensory_sets(ann)
stim = sets['sugar']['left'] + sets['sugar']['right']
nL = len(sets['sugar']['left'])
res = {'target': target, 'n_neurons': len(comp)}
fly = Fly(stim, target=target)
res['build_s'] = fly.t_build; res['first_run_compile_s'] = fly.t_first
rates = np.zeros(len(stim)); rates[:nL] = 150.0
t0 = time.time(); fly.net.restore('clean'); res['restore_s'] = time.time() - t0
for dur in (50, 100, 200, 1000):
    c, w = fly.window(rates, dur)
    res[f'win_{dur}ms_wall_s'] = w; res[f'win_{dur}ms_total_spikes'] = int(c.sum())
    print(dur, 'ms ->', round(w, 2), 's wall, spikes', int(c.sum()), flush=True)
# continuous run, changing rates every 100 ms without restore
fly.net.restore('clean'); ws = []
for k in range(5):
    r = np.zeros(len(stim)); r[:nL] = 150.0 if k % 2 == 0 else 0.0
    c, w = fly.window(r, 100, fresh=False); ws.append(w)
res['continuous_100ms_walls_s'] = ws
print(json.dumps(res, indent=1))
json.dump(res, open(f'results/bench_{target}.json', 'w'), indent=1)
