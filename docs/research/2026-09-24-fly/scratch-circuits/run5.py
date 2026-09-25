import sys; sys.path.insert(0, ".superpowers/research/2026-09-24-fly/scratch-circuits")
from paths import *
for t in ["DNg97","DNg100","DNp42","DNa10","MDN","DNp50","DNg55","DNa11"]:
    print(t, len(members(t,"left")), len(members(t,"right")))
INS = ["LC16","LC10d","LC10a","LPLC1","LC11","LC18","LC9","LPLC2","LC4","LPLC4","LPC1","LLPC1"]
OUTS = ["MDN","DNp42","DNa10","DNg97","DNg100","DNp09","DNa02","DNa01","DNg13","DNb06","DNp01","DNp11","DNp02"]
rows=[]
for t in INS:
    x=np.zeros(N); x[members(t,"left")]=1
    y1=A@x; y2=A@y1; y3=A@y2; y=y1+y2+y3
    r={"input (L eye)":t}
    for o in OUTS:
        L=y[members(o,"left")].mean(); Rr=y[members(o,"right")].mean()
        r[o]=f"{1000*L:+.1f}/{1000*Rr:+.1f}"
    rows.append(r)
print(pd.DataFrame(rows).to_markdown(index=False))
# raw direct synapses LC16 -> MDN ; LC10d -> DNa10
for a,b in [("LC16","MDN"),("LC10d","DNa10"),("LPLC1","DNp03"),("LC9","DNp09"),("LC11","DNp35")]:
    s = R[members(b)][:, members(a,"left")].toarray()
    print(a,"L ->",b, "per target:", s.sum(axis=1).astype(int).tolist(), "sides", side[members(b)].tolist())
