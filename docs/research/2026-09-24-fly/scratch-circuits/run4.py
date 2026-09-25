import sys; sys.path.insert(0, ".superpowers/research/2026-09-24-fly/scratch-circuits")
from paths import *
vpn = sorted(set(ctype[(sclass=="visual_projection") & (side=="left")]))
gf = members("DNp01")
def infl(t, s="left"):
    x = np.zeros(N); x[members(t, s)] = 1.0
    y1 = A@x; y2 = A@y1; y3 = A@y2
    return y1, y2, y3
rows=[]
for t in vpn:
    n = len(members(t,"left"))
    if n < 3: continue
    y1,y2,y3 = infl(t); y = y1+y2+y3
    def m(o,s): return y[members(o,s)].mean()
    rows.append({"type": t, "n(L)": n, "GF hop1": 1000*y1[gf].mean(), "GF hop1-3": 1000*y[gf].mean(),
                 "DNa02 R-L": 1000*(m("DNa02","right")-m("DNa02","left")), "DNa01 R-L": 1000*(m("DNa01","right")-m("DNa01","left")),
                 "DNb01 R-L": 1000*(m("DNb01","right")-m("DNb01","left")), "DNp09": 1000*(m("DNp09","left")+m("DNp09","right"))/2,
                 "MDN": 1000*y[members("MDN")].mean()})
df = pd.DataFrame(rows).round(1)
print("### most GF-inhibiting VPN types (left eye, signed influence x1000, hop 1-3)\n")
print(df.sort_values("GF hop1-3").head(15).to_markdown(index=False))
print("\n### most GF-exciting\n"); print(df.sort_values("GF hop1-3", ascending=False).head(10).to_markdown(index=False))
print("\n### strongest steering asymmetry (|DNa02 R-L|+|DNa01 R-L|+|DNb01 R-L|)\n")
df["steer"] = df[["DNa02 R-L","DNa01 R-L","DNb01 R-L"]].abs().sum(axis=1)
print(df.sort_values("steer", ascending=False).head(15).to_markdown(index=False))
print("\n### DNp09 / MDN drivers\n"); print(df.sort_values("DNp09", ascending=False).head(6).to_markdown(index=False)); print(df.sort_values("MDN", ascending=False).head(6).to_markdown(index=False))
# direct inputs to GF (raw signed synapses, whole brain), top 15 by |syn|, with type and side
col = R[gf].toarray().sum(axis=0)
idx = np.argsort(-np.abs(col))[:20]
print("\n### top direct presynaptic partners of both GFs (Shiu signed synapse counts)\n")
print(pd.DataFrame({"pre": ctype[idx], "side": side[idx], "class": sclass[idx], "signed syn": col[idx].astype(int)}).to_markdown(index=False))
