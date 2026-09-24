import sys; sys.path.insert(0, ".superpowers/research/2026-09-24-fly/scratch-circuits")
from paths import *
INPUTS = ["LPLC2","LC4","LPLC1","LC6","LC9","LC11","LC12","LC15","LC16","LC17","LC18","LC21","LC22","LC25","LC26","LPLC4","LLPC1","LLPC2","LLPC3","LC10a","LC24","LC31a","HSE","HSN","HSS","VS1","VS2","VS3","VS4","VS5","VS6","H2","T4a","T4b","T5a","T5b","R1-6","R7","R8"]
OUTS = ["DNp01","DNp02","DNp04","DNp11","DNp06","DNp03","DNp05","DNp07","DNp09","MDN","DNa01","DNa02","DNa03","DNa04","DNa05","DNa07","DNb01","DNb05","DNb06","DNg13","DNg11","DNp10","DNp37","DNp15","DNp35","DNb02","DNb03"]
print("## counts (annotated in annotations.tsv / present in model)")
annfull = pd.read_csv("data/neuron_annotations.tsv", sep="\t", usecols=["root_id","cell_type","side"], low_memory=False)
inmodel = set(ids.tolist())
rows=[]
for t in INPUTS+OUTS:
    r={"type":t}
    for s in ["left","right"]:
        sub=annfull[(annfull.cell_type==t)&(annfull.side==s)]
        r[s]=f"{len(sub)}/{sum(int(x) in inmodel for x in sub.root_id)}"
    rows.append(r)
print(pd.DataFrame(rows).to_markdown(index=False))
