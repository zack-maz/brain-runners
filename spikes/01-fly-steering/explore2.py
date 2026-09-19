import pandas as pd, json, re, pickle
D='../../data/'
ann=pd.read_csv(D+'neuron_annotations.tsv',sep='\t',low_memory=False)
comp=pd.read_csv(D+'Drosophila_brain_model/Completeness_783.csv',index_col=0)
print(comp.head(3)); print(comp.columns.tolist())
con=pd.read_parquet(D+'Drosophila_brain_model/Connectivity_783.parquet')
print(con.shape, con.columns.tolist()); print(con.head(3))
sugar630=[720575940624963786,720575940630233916,720575940637568838,720575940638202345,720575940617000768,720575940630797113,720575940632889389,720575940621754367,720575940621502051,720575940640649691,720575940639332736,720575940616885538,720575940639198653,720575940620900446,720575940617937543,720575940632425919,720575940633143833,720575940612670570,720575940628853239,720575940629176663,720575940611875570]
s=ann[ann.root_id.isin(sugar630)]
print('sugar630 IDs still valid in 783 annotations:',len(s),'in model',sum(i in comp.index for i in sugar630))
print(s[['root_id','cell_type','side','nerve','cell_sub_class']].to_string())
nb=json.load(open(D+'Drosophila_brain_model/figures.ipynb'))
src='\n'.join(''.join(c['source']) for c in nb['cells'])
print(len(src)); 
for m in re.finditer(r'(?i)(sugar|783|pickle|JO|left|right)[^\n]{0,100}',src): print(m.group(0)[:140])
p=pickle.load(open(D+'Drosophila_brain_model/sez_neurons.pickle','rb')); print(type(p), list(p.items())[:5] if isinstance(p,dict) else p[:5])
print(ann[ann.cell_class=='gustatory'].cell_sub_class.value_counts())
