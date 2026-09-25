"""FlyWire viewer data (read-only): neuropils per type, flow rank, modules. Source: ~/Documents/PROJECTS/LEARN/flywire/brain."""
import json, numpy as np, pandas as pd, pyarrow.parquet as pq
FW = "/Users/zackmaz/Documents/PROJECTS/LEARN/flywire/brain/"
ann = pd.read_csv(FW + "data/raw/neuron_annotations.tsv", sep="\t", usecols=["root_id","cell_type","side","super_class"], low_memory=False)
N = len(ann)
rank = np.frombuffer(open(FW + "public/data/flow_rank.bin","rb").read(), np.uint8)
gm = json.load(open(FW + "public/data/groupings.json")); gb = open(FW + "public/data/groupings.bin","rb").read()
lab = {g["id"]: (np.frombuffer(gb, np.uint8 if g["bytes"]==1 else np.uint16, N, g["offset"]), g["values"]) for g in gm}
ann["rank"] = rank
for k in ("infomap","leiden_fine","leiden_coarse"):
    code, vals = lab[k]; ann[k] = [vals[c] for c in code]
npc = pq.read_table(FW + "data/raw/neuron_neuropil_counts.parquet").to_pandas()
npc["root_id"] = npc.root_id.astype(np.int64)
TYPES = ["LPLC2","LC4","LPLC1","LC6","LC9","LC11","LC12","LC15","LC16","LC17","LC18","LC21","LC22","LC26","LPLC4","LLPC1","LLPC2","LLPC3","LC10a","HSS","VS2","H2",
         "DNp01","DNp02","DNp04","DNp11","DNp06","DNp03","DNp05","DNp09","MDN","DNa01","DNa02","DNa03","DNa04","DNa05","DNa07","DNa08","DNb01","DNb05","DNb06","DNg13","DNg11","DNae004","DNae002","DNg41","DNb03","DNp15","DNp35","DNp37","DNg82","DNa15","aSP22","DNg71"]
rows = []
for t in TYPES:
    sub = ann[(ann.cell_type == t) & (ann.side == "left")]
    ids = set(sub.root_id)
    c = npc[npc.root_id.isin(ids)]
    def top(role):
        g = c[c.role == role].groupby(["neuropil","side"]).n.sum().sort_values(ascending=False)
        tot = g.sum()
        return ", ".join(f"{np_}_{s[0].upper()} {100*v/tot:.0f}%" for (np_, s), v in g.head(3).items())
    rows.append({"type (left)": t, "n": len(sub), "flow step (median)": int(np.median(sub["rank"])),
                 "infomap module": sub.infomap.mode().iat[0], "leiden_fine": sub.leiden_fine.mode().iat[0],
                 "input neuropils": top("in"), "output neuropils": top("out")})
print(pd.DataFrame(rows).to_markdown(index=False))
