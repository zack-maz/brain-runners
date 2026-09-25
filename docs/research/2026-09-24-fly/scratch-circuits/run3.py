import sys; sys.path.insert(0, ".superpowers/research/2026-09-24-fly/scratch-circuits")
from paths import *
INPUTS = ["LPLC2","LC4","LPLC1","LC6","LC9","LC11","LC12","LC15","LC16","LC17","LC18","LC21","LC22","LPLC4","LLPC1","LLPC2","LLPC3","LC10a","HSS","HSE","VS2","H2","T4a","T4b","T5a","T5b"]
OUTS = ["DNp01","DNp04","DNp03","DNp35","DNp11","DNp06","DNp09","MDN","DNa01","DNa02","DNa03","DNa04","DNa05","DNa07","DNa15","DNb01","DNb05","DNg13","DNae002","DNg41"]
rows=[]
for t in INPUTS:
    x = np.zeros(N); x[members(t,"left")] = 1.0
    y1 = A@x; y2 = A@y1; y3 = A@y2; y = y1+y2+y3
    r = {"input (L eye)": f"{t} ({len(members(t,'left'))})"}
    for o in OUTS:
        L = y[members(o,"left")].mean(); R = y[members(o,"right")].mean()
        r[o] = f"{1000*L:+.0f}/{1000*R:+.0f}" if max(abs(L),abs(R))*1000 >= 0.5 else "."
    rows.append(r)
import sys as _s
# shortest excitatory path length (hops, edges >= 5 synapses, excitatory only) from each input set to each DN
keep = w >= 5
E = sp.csr_matrix((np.ones(keep.sum(), np.float32), (post[keep], pre[keep])), shape=(N, N))
def hops(src, maxh=4):
    d = np.full(N, 99); d[src] = 0; front = np.zeros(N, bool); front[src] = True
    for h in range(1, maxh+1):
        nxt = (E @ front.astype(np.float32)) > 0
        nxt = np.asarray(nxt).ravel() & (d == 99)
        d[nxt] = h; front = nxt
    return d
print("\n### min hops (excitatory edges >= 5 synapses) L-eye type -> DN ipsi/contra\n")
rows=[]
for t in INPUTS:
    d = hops(members(t,"left")); r={"input": t}
    for o in OUTS:
        r[o] = f"{d[members(o,'left')].min()}/{d[members(o,'right')].min()}".replace("99","-")
    rows.append(r)
print(pd.DataFrame(rows).to_markdown(index=False))
