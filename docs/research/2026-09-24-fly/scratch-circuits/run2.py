import sys; sys.path.insert(0, ".superpowers/research/2026-09-24-fly/scratch-circuits")
from paths import *
INPUTS = ["LPLC2","LC4","LPLC1","LC6","LC9","LC11","LC12","LC15","LC16","LC17","LC18","LC21","LC22","LC25","LC26","LPLC4","LLPC1","LLPC2","LLPC3","LC10a","LC24","LC31a","HSE","HSN","HSS","VS1","VS2","VS3","VS4","VS5","VS6","H2","T4a","T4b","T5a","T5b"]
OUTS = ["DNp01","DNp02","DNp04","DNp11","DNp06","DNp03","DNp05","DNp07","DNp09","MDN","DNa01","DNa02","DNa03","DNa04","DNa05","DNa07","DNb01","DNb05","DNb06","DNg13","DNg11","DNp10","DNp37","DNp15","DNp35","DNb02","DNb03"]
isdn = sclass == "descending"
res = {}
for t in INPUTS:
    x = np.zeros(N); x[members(t, "left")] = 1.0  # left eye, unit drive per cell
    y1 = A @ x; y2 = A @ y1; y3 = A @ y2
    res[t] = (y1, y2, y3)
np.save(".superpowers/research/2026-09-24-fly/scratch-circuits/dummy.npy", 0)
def dn_val(y, t, s):
    m = members(t, s); return y[m].mean() if len(m) else np.nan
# Table: hop-2 and hop-3 influence (x1000), left-eye input -> ipsi(left)/contra(right) DN (soma side)
for hop in (1, 2, 3):
    rows = []
    for t in INPUTS:
        y = res[t][hop-1]; r = {"input(L eye)": t}
        for o in OUTS:
            L, Rr = dn_val(y, o, "left"), dn_val(y, o, "right")
            r[o] = f"{1000*L:+.1f}/{1000*Rr:+.1f}" if abs(L)+abs(Rr) >= 0.00005 else "."
        rows.append(r)
    df = pd.DataFrame(rows)
    print(f"\n### hop {hop}: influence x1000, L-eye set -> DN left/right (soma side)\n")
    print(df.to_markdown(index=False))
# unbiased: top 12 DN types by |hop2+hop3| for each input
print("\n### top DN types per input (hop2+hop3 summed, per-cell mean, x1000; L/R soma side)\n")
dnidx = np.where(isdn)[0]
for t in INPUTS:
    y = res[t][1] + res[t][2]
    df = pd.DataFrame({"t": ctype[dnidx], "s": side[dnidx], "v": y[dnidx]})
    g = df.groupby(["t","s"]).v.mean().unstack(fill_value=0)
    g["tot"] = g.abs().sum(axis=1)
    g = g.sort_values("tot", ascending=False).head(10)
    print(f"- **{t}**: " + ", ".join(f"{i} {1000*r.get('left',0):+.1f}/{1000*r.get('right',0):+.1f}" for i, r in g.iterrows()))
