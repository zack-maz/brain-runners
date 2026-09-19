"""Summarise results/<set>.parquet. usage: analyze.py <set> [t_max_ms]
Rates are per cell type and side (sum of spikes over the type's neurons on that side / n neurons / s).
AI = (right - left) / (right + left) per trial; ipsi index flips sign so + means "more on the stimulated side"."""
import sys, json
import numpy as np, pandas as pd
from flysim import load_tables, output_index, OUTPUT_TYPES

name = sys.argv[1]
meta = json.load(open(f'results/{name}.json'))
dur = meta['dur_ms']; tmax = float(sys.argv[2]) if len(sys.argv) > 2 else dur
ann, comp, _ = load_tables()
outs = output_index(ann)
outs = outs[outs.side.isin(['left', 'right']) & outs.ctype.notna()]
sp = pd.read_parquet(f'results/{name}.parquet')
sp = sp[sp.t_ms <= tmax].merge(outs[['idx', 'ctype', 'side']], on='idx')
ncell = outs.groupby(['ctype', 'side']).size()
trials = pd.DataFrame(meta['trials'])[['cond', 'trial']]
cnt = sp.groupby(['cond', 'trial', 'ctype', 'side']).size().rename('n').reset_index()

def table(ctype):
    """per-trial left/right rate (Hz per neuron) for one cell type -> DataFrame cond,trial,L,R"""
    c = cnt[cnt.ctype == ctype].pivot_table(index=['cond', 'trial'], columns='side', values='n', fill_value=0)
    c = trials.merge(c.reset_index(), on=['cond', 'trial'], how='left').fillna(0)
    for s in ('left', 'right'):
        if s not in c: c[s] = 0.0
        c[s] = c[s] / ncell.get((ctype, s), 1) / (tmax / 1000)
    return c

print(f'## {name}: n_left={meta["n_left"]} n_right={meta["n_right"]} window={tmax:.0f} ms, trials/cond={meta["n_trials"]}')
print(f'mean wall per trial {np.mean([t["wall_s"] for t in meta["trials"]]):.1f}s; stim neurons fire ~'
      f'{np.mean([t["mean_stim_neuron_hz"] for t in meta["trials"] if t["cond"]=="both150"]):.0f} Hz in both150 (L+R avg)')
order = [c for c in dict.fromkeys(t['cond'] for t in meta['trials'])]
print('\n| type | ' + ' | '.join(order) + ' |'); print('|---|' + '---|' * len(order))
for ct in OUTPUT_TYPES:
    t = table(ct); cells = []
    for c in order:
        x = t[t.cond == c]
        cells.append(f'L {x.left.mean():.1f}±{x.left.std(ddof=0):.1f} R {x.right.mean():.1f}±{x.right.std(ddof=0):.1f}')
    print(f'| {ct} | ' + ' | '.join(cells) + ' |')

# data-driven scan: all DN/motor types with both sides; ipsi-contra under one-sided stim at the middle rate
mid = f'{int(sorted(meta["rates"])[len(meta["rates"])//2])}'
rows = []
for ct in sorted(set(ncell.index.get_level_values(0))):
    if (ct, 'left') not in ncell or (ct, 'right') not in ncell: continue
    t = table(ct)
    l, r = t[t.cond == 'L' + mid], t[t.cond == 'R' + mid]
    d = np.r_[(l.left - l.right).values, (r.right - r.left).values]  # ipsi - contra, per trial
    tot = np.r_[(l.left + l.right).values, (r.right + r.left).values]
    if tot.mean() < 1: continue
    b = t[t.cond == 'both150']
    rows.append({'type': ct, 'ipsi_minus_contra_hz': d.mean(), 'sd': d.std(ddof=0),
                 'ipsi_index': (d / np.where(tot == 0, np.nan, tot)).mean() if (tot > 0).any() else np.nan,
                 'frac_trials_same_sign': max((d > 0).mean(), (d < 0).mean()), 'mean_sum_hz': tot.mean(),
                 'both_L': b.left.mean(), 'both_R': b.right.mean()})
scan = pd.DataFrame(rows)
if len(scan):
    scan['z'] = scan.ipsi_minus_contra_hz / scan.sd.replace(0, np.nan)
    scan = scan.reindex(scan.ipsi_minus_contra_hz.abs().sort_values(ascending=False).index)
    print(f'\nTop lateralized DN/motor types at {mid} Hz one-sided stim (of {len(scan)} active types):')
    print(scan.head(15).round(2).to_string(index=False))
else:
    print('\nNo DN/motor type reached 1 Hz under one-sided stimulation.')
# gradedness for key types
print('\nGradedness (ipsi - contra Hz, mean±sd over L and R trials pooled):')
for ct in OUTPUT_TYPES + list(scan.head(4).type if len(scan) else []):
    t = table(ct); parts = []
    for r in sorted(meta['rates']):
        l, rr = t[t.cond == f'L{int(r)}'], t[t.cond == f'R{int(r)}']
        d = np.r_[(l.left - l.right).values, (rr.right - rr.left).values]
        parts.append(f'{int(r)}Hz: {d.mean():+.1f}±{d.std(ddof=0):.1f}')
    print(f'  {ct}: ' + ', '.join(parts))
