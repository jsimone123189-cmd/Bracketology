import re,html,collections,statistics as st,numpy as np
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
from bracketology.features import build_year
from bracketology import backtest as B
h=open('data/raw/rankings.html',encoding='latin-1').read()
rows=[bm._cells(r) for r in re.findall(r'<tr[^>]*>(.*?)</tr>',h,re.S)]
for r in rows:
    j=' '.join(r)
    if re.search(r'Brad Evans|RFS Bracket Science',j): print([x for x in r if x][:12])
print('head',[r[:12] for r in rows if 'Rank' in ' '.join(r[:4])][:1])
Y=[2019,2021,2022,2023,2024,2025,2026]; ALL=[2016,2017,2018]+Y
M={y:bm.collect(y) for y in ALL}
def subs(y): return {n:{key(t):s for t,s in v.items()} for n,v in M[y]['submissions'].items() if len(v)>=60}
def score_of(y): return {n:int(v) for n,v in M[y]['reported'].get('SCORE',{}).items() if v.isdigit()}
def from_sites(y,names):
    S=subs(y); off={key(t):s for t,s in M[y]['official'].items()}; rows=build_year(y); champs={r['key'] for r in rows if r['champ']}; names=[n for n in names if n in S]
    if not names: return None,0
    votes=collections.defaultdict(list)
    for n in names:
        for t,s in S[n].items(): votes[t].append(s)
    tot=len(names)
    sc={t:(len(v)/tot,np.mean(v)) for t,v in votes.items()}
    atl=sorted((t for t in sc if t not in champs),key=lambda t:(-sc[t][0],sc[t][1]))
    field=[t for t in champs]+atl[:68-len(champs)]
    pred={t:int(min(16,max(1,round(sc[t][1])))) if t in sc else 16 for t in field}
    return bm.score(pred,off),len(names)
print('\nprior-track-record experts vs others (only earlier seasons used to pick them)')
res=collections.defaultdict(dict)
for i,y in enumerate(Y):
    prev=[p for p in ALL if p<y][-5:]
    hist=collections.defaultdict(list)
    for p in prev:
        s=score_of(p); med=st.median(s.values())
        for n,v in s.items():
            if n not in('MATRIX',''): hist[n].append(v-med)
    elig={n:np.mean(v) for n,v in hist.items() if len(v)>=2}
    top=sorted(elig,key=lambda n:-elig[n])
    for k in (1,5,10,25):
        r,_=from_sites(y,top[:k]); res[f'top {k} by past record'][y]=r
    r,_=from_sites(y,list(subs(y))); res['all sites'][y]=r
    r,_=from_sites(y,['RFS']); res['RFS alone'][y]=r
    r,_=from_sites(y,['BE']); res['BE alone'][y]=r
    r,_=from_sites(y,['RFS','BE']); res['RFS + BE'][y]=r
    res['actual MATRIX column'][y]={'score':score_of(y).get('MATRIX')}
for n,d in res.items():
    sc=[d[y]['score'] if d.get(y) and d[y]['score'] else None for y in Y]; v=[x for x in sc if x]
    print(f'{n:26}',sc,'mean',round(np.mean(v),1))
