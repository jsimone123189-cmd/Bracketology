import numpy as np, collections
from bracketology import history, model, project
from bracketology.features import build_year
Y=sorted(history.SELECTION_SUNDAY); ps=[];err=collections.defaultdict(collections.Counter)
for h in Y:
    m=model.Model().fit(project.training_rows(exclude={h})); rows=model.prepare(build_year(h)); m.score(rows)
    f,_=model.choose_field(rows,h,project_autos=False); o=model.assign_lines(f,h)
    for r in rows:
        if not r['champ'] and r['net']<=120: ps.append((r['p_in'],r['in_field']))
    for r in o:
        if r['in_field']: err[(r['line']-1)//4][r['seed']-r['line']]+=1
ps=np.array(ps,float)
print('at-large calibration (held-out):')
for a,b in ((0,.05),(.05,.2),(.2,.4),(.4,.6),(.6,.8),(.8,.95),(.95,1.01)):
    q=(ps[:,0]>=a)&(ps[:,0]<b); print(a,b,int(q.sum()),round(ps[q,0].mean(),3) if q.sum() else None,round(ps[q,1].mean(),3) if q.sum() else None)
print('brier',round(((ps[:,0]-ps[:,1])**2).mean(),4))
for t,c in sorted(err.items()): n=sum(c.values()); print('lines',t*4+1,'-',t*4+4,n,{d:round(v/n,2) for d,v in sorted(c.items())})
