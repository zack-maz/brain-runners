"""Shared helpers for spike 01. Reuses create_model/default_params from the Shiu repo.

Stimulation differs from the repo's poi() in mechanics only: instead of one PoissonInput
object per neuron (fixed rate, very slow with hundreds of objects) we use ONE PoissonGroup
wired one-to-one onto the sensory neurons with the same kick (w_syn * f_poi = 68.75 mV,
refractory 0 for stimulated neurons), so rates can be changed between windows without
rebuilding. bench.py checks the two give the same downstream rates.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / 'data' / 'Drosophila_brain_model'
sys.path.insert(0, str(REPO))
PATH_COMP = REPO / 'Completeness_783.csv'
PATH_CON = REPO / 'Connectivity_783.parquet'
PATH_ANN = ROOT / 'data' / 'neuron_annotations.tsv'

ATTRACTIVE_ORN = ['ORN_DM1', 'ORN_VA2', 'ORN_DM4', 'ORN_DM2']  # vinegar/food-odour attraction glomeruli
JO_WIND = None  # filled by prefix JO-C / JO-E

OUTPUT_TYPES = ['DNa01', 'DNa02', 'DNa03', 'DNb01', 'DNb02', 'DNg13', 'DNae003', 'DNp09',
                'MDN', 'DNp01', 'DNp02', 'DNp04', 'DNp11']  # DNp01 = Giant Fiber


def load_tables():
    ann = pd.read_csv(PATH_ANN, sep='\t', low_memory=False)
    comp = pd.read_csv(PATH_COMP, index_col=0)
    flyid2i = {j: i for i, j in enumerate(comp.index)}
    ann['idx'] = ann.root_id.map(flyid2i)
    return ann, comp, flyid2i


def sensory_sets(ann):
    """dict name -> {'left': [root ids], 'right': [...]} plus coverage info."""
    sel = {
        'orn': ann.cell_type.isin(ATTRACTIVE_ORN),
        'sugar': (ann.cell_class == 'gustatory') & (ann.cell_sub_class == 'sugar/water'),
        'lplc2': ann.cell_type == 'LPLC2',
        'lc4': ann.cell_type == 'LC4',
        'jo_ce': ann.cell_type.fillna('').str.match(r'JO-(C|E)'),
    }
    out, cov = {}, {}
    for k, m in sel.items():
        out[k] = {}
        for side in ('left', 'right'):
            s = ann[m & (ann.side == side)]
            out[k][side] = s.idx.dropna().astype(int).tolist()
            cov[(k, side)] = (int(s.idx.notna().sum()), len(s))
    return out, cov


def output_index(ann, types=None):
    """DataFrame of descending + motor neurons present in the model with idx, cell_type, side."""
    d = ann[ann.super_class.isin(['descending', 'motor']) & ann.idx.notna()].copy()
    d['idx'] = d.idx.astype(int)
    d['ctype'] = d.cell_type.fillna(d.hemibrain_type)
    return d[['root_id', 'idx', 'ctype', 'side', 'super_class', 'top_nt']]


class Fly:
    def __init__(self, stim_idx, target='numpy'):
        from brian2 import PoissonGroup, Synapses, Network, Hz, ms, mV, prefs
        from model import create_model, default_params
        prefs.codegen.target = target
        self.Hz, self.ms = Hz, ms
        self.params = dict(default_params)
        t0 = time.time()
        self.neu, self.syn, self.mon = create_model(PATH_COMP, PATH_CON, self.params)
        self.stim_idx = np.asarray(stim_idx, dtype=int)
        self.pg = PoissonGroup(len(self.stim_idx), rates=np.zeros(len(self.stim_idx)) * Hz, name='stim_pg')
        kick = self.params['w_syn'] * self.params['f_poi']
        self.stim_syn = Synapses(self.pg, self.neu, on_pre='v_post += %r*mV' % float(kick / mV), name='stim_syn')
        self.stim_syn.connect(i=np.arange(len(self.stim_idx)), j=self.stim_idx)
        self.neu.rfc[self.stim_idx] = 0 * ms  # as in repo poi(): no refractory for Poisson targets
        self.net = Network(self.neu, self.syn, self.mon, self.pg, self.stim_syn)
        self.t_build = time.time() - t0
        t0 = time.time()
        self.net.run(0.1 * ms)  # force codegen/compile + first-step setup
        self.t_first = time.time() - t0
        self.net.store('clean')
        self.N = len(self.neu)

    def set_rates(self, rate_by_pos):
        self.pg.rates = np.asarray(rate_by_pos, dtype=float) * self.Hz

    def window(self, rate_by_pos, dur_ms, fresh=True):
        """Run one window; returns (spike counts per neuron in this window, wall seconds)."""
        t0 = time.time()
        if fresh:
            self.net.restore('clean')
            n_before = 0
        else:
            n_before = self.mon.num_spikes
        self.set_rates(rate_by_pos)
        self.net.run(dur_ms * self.ms)
        i = np.asarray(self.mon.i[n_before:])
        counts = np.bincount(i, minlength=self.N)
        return counts, time.time() - t0
