"""Compartment-resolved paths from the FlyWire viewer's split edgelist (read-only). Direct and 2-hop, input type (left) -> DN."""
import numpy as np, pandas as pd, pyarrow.feather as f, pyarrow.compute as pc, pyarrow as pa
FW = "/Users/zackmaz/Documents/PROJECTS/LEARN/flywire/brain/"
ann = pd.read_csv(FW + "data/raw/neuron_annotations.tsv", sep="\t", usecols=["root_id","cell_type","side","super_class"], low_memory=False)
ann["rid"] = ann.root_id.astype(str)
t_of = dict(zip(ann.rid, ann.cell_type.fillna("?"))); s_of = dict(zip(ann.rid, ann.side.fillna("?")))
IN = ["LPLC2","LC4","LPLC1","LC6","LC9","LC11","LC12","LC15","LC16","LC17","LC18","LC21","LC22","LPLC4","LLPC1","LLPC3","LC10a","HSS","VS2","H2"]
DN = ["DNp01","DNp02","DNp04","DNp11","DNp06","DNp03","DNp05","DNp09","MDN","DNa01","DNa02","DNa03","DNa04","DNa05","DNa07","DNa08","DNb01","DNb05","DNb06","DNg13","DNg11","DNae004","DNae002","DNg41","DNb03","DNp15","DNp35","DNg82","DNa15","DNg71","aSP22","DNp37"]
in_ids = pa.array(ann[ann.cell_type.isin(IN) & (ann.side=="left")].rid.tolist())
dn_ids = pa.array(ann[ann.cell_type.isin(DN)].rid.tolist())
t = f.read_table(FW + "data/raw/fafb_783_split_edgelist.feather", columns=["pre","post","post_label","count"], memory_map=True)
# edges onto DNs (any pre), and edges from inputs (any post)
onto = t.filter(pc.is_in(t["post"], value_set=dn_ids)).to_pandas()
frm = t.filter(pc.is_in(t["pre"], value_set=in_ids)).to_pandas()
del t
for d in (onto, frm):
    d["pre_t"] = d.pre.map(t_of); d["pre_s"] = d.pre.map(s_of); d["post_t"] = d.post.map(t_of); d["post_s"] = d.post.map(s_of)
dend = {"dendrite","primary_dendrite"}
# Direct
dct = frm[frm.post_t.isin(DN)].copy()
dct["dend"] = dct.post_label.isin(dend)
g = dct.groupby(["pre_t","post_t","post_s"]).agg(syn=("count","sum")).reset_index()
gd = dct[dct.dend].groupby(["pre_t","post_t","post_s"])["count"].sum().rename("dend_syn").reset_index()
g = g.merge(gd, how="left").fillna(0)
g = g[g.syn >= 10].sort_values("syn", ascending=False)
g["onto dendrite"] = (100*g.dend_syn/g.syn).round().astype(int).astype(str) + "%"
g["DN side"] = np.where(g.post_s=="left","ipsi","contra")
print("### direct: left-eye type -> DN (>= 10 synapses; post compartment)\n")
print(g[["pre_t","post_t","DN side","syn","onto dendrite"]].rename(columns={"pre_t":"input (L)","post_t":"DN"}).to_markdown(index=False))
# 2-hop: input -> mid -> DN, with mid->DN counted only onto DN dendrite; weight = syn(in->mid) * syn(mid->DN dend) / total input of mid
tot_in_mid = None
mids = set(frm.post) & set(onto.pre)
t = f.read_table(FW + "data/raw/fafb_783_split_edgelist.feather", columns=["post","count"], memory_map=True)
tm = t.filter(pc.is_in(t["post"], value_set=pa.array(list(mids)))).to_pandas(); del t
totin = tm.groupby("post")["count"].sum()
a = frm.groupby(["pre_t","post"])["count"].sum().rename("c1").reset_index().rename(columns={"post":"mid"})
b = onto[onto.post_label.isin(dend)].groupby(["pre","post_t","post_s"])["count"].sum().rename("c2").reset_index().rename(columns={"pre":"mid"})
p = a.merge(b, on="mid")
p["w"] = p.c1 / p.mid.map(totin) * p.c2
p["mid_t"] = p.mid.map(t_of); p["mid_s"] = p.mid.map(s_of)
p["DN side"] = np.where(p.post_s=="left","ipsi","contra")
agg = p.groupby(["pre_t","post_t","DN side"]).w.sum().reset_index()
top_mid = p.groupby(["pre_t","post_t","DN side","mid_t"]).w.sum().reset_index().sort_values("w", ascending=False).groupby(["pre_t","post_t","DN side"]).head(2)
tm2 = top_mid.groupby(["pre_t","post_t","DN side"]).mid_t.apply(lambda s: ", ".join(s)).rename("via (top 2)")
agg = agg.merge(tm2.reset_index()).sort_values("w", ascending=False)
agg = agg[agg.w >= 1.0]
agg["w"] = agg.w.round(1)
print("\n### 2-hop onto DN dendrites: sum over mids of syn(in->mid)/in(mid) * syn(mid->DN dendrite), >= 1\n")
print(agg.rename(columns={"pre_t":"input (L)","post_t":"DN","w":"2-hop weight"}).head(70).to_markdown(index=False))
