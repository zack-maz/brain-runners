import pandas as pd
D='../../data/'
ann=pd.read_csv(D+'neuron_annotations.tsv',sep='\t',low_memory=False)
comp=pd.read_csv(D+'Drosophila_brain_model/Completeness_783.csv',index_col=0)
print('model neurons',len(comp),'annotations',len(ann),'overlap',ann.root_id.isin(comp.index).sum())
comp630=pd.read_csv(D+'Drosophila_brain_model/2023_03_23_completeness_630_final.csv',index_col=0)
print('v630 overlap',ann.root_id.isin(comp630.index).sum(),'of',len(comp630))
print(ann.super_class.value_counts())
print(ann[ann.super_class=='sensory'].cell_class.value_counts())
for ct in ['DNa01','DNa02','DNa03','DNb01','DNb02','DNg13','DNae003','DNp01','DNp02','DNp04','DNp11','MDN','DNp09','DNp15','LPLC2','LC4','DNa11','DNg34']:
    s=ann[(ann.cell_type==ct)|(ann.hemibrain_type==ct)]
    print(ct, s.side.value_counts().to_dict(), 'in model', s.root_id.isin(comp.index).sum(),'/',len(s))
g=ann[ann.cell_class=='gustatory']
print(g.groupby(['cell_type','side']).size().unstack(fill_value=0).head(40))
m=ann[ann.cell_class=='mechanosensory']
print(m.groupby(['cell_type','side']).size().unstack(fill_value=0).head(60))
o=ann[ann.cell_class=='olfactory']
print(o.groupby(['cell_type','side']).size().unstack(fill_value=0).to_string())
