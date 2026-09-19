"""Check that flysim's PoissonGroup stimulation matches the repo's own poi() (numpy, 3 trials x 400 ms,
right sugar GRNs at 150 Hz). Compares a few strongly driven DN types and MN9."""
import numpy as np
from flysim import *
from brian2 import Network, ms, prefs
prefs.codegen.target = 'numpy'
from model import create_model, poi, default_params
ann, comp, flyid2i = load_tables(); sets, _ = sensory_sets(ann); outs = output_index(ann)
R = sets['sugar']['right']
probe = {ct: outs[(outs.ctype == ct) & (outs.side == 'right')].idx.tolist() for ct in ['DNg35', 'DNge031', 'DNg60', 'DNp58']}
probe['MN9_any'] = [flyid2i[720575940660219265]] if 720575940660219265 in flyid2i else []
def summarize(counts): return {k: round(float(counts[v].sum() / max(1, len(v)) / 0.4), 1) for k, v in probe.items()}
for k in range(3):
    neu, syn, mon = create_model(PATH_COMP, PATH_CON, default_params)
    p, neu = poi(neu, R, [], default_params)
    net = Network(neu, syn, mon, *p); net.run(400 * ms)
    print('repo poi()  ', summarize(np.bincount(np.asarray(mon.i), minlength=len(neu))), flush=True)
fly = Fly(sets['sugar']['left'] + R, target='numpy')
rv = np.r_[np.zeros(len(sets['sugar']['left'])), np.full(len(R), 150.0)]
for k in range(3):
    print('PoissonGroup', summarize(fly.window(rv, 400)[0]), flush=True)
