import re,html,statistics as st,openpyxl,collections
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
from bracketology import history
h=open('data/raw/rankings.html',encoding='latin-1').read()
for pat in ('science','evans','brad','miya'):
    for m in list(re.finditer(pat,h,re.I))[:6]:
        print(pat,'::',re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',h[max(0,m.start()-160):m.start()+160])))[:200], '| href', re.findall(r'href="([^"]+)"',h[max(0,m.start()-200):m.start()+200])[:1])
print()
Y=sorted(history.SELECTION_SUNDAY)
print('site scores by year (rank of field)')
for y in Y:
    d=bm.collect(y); S={n:int(v) for n,v in d['reported']['SCORE'].items() if v.isdigit()}; v=sorted(S.values(),reverse=True)
    print(y,'n',len(v),'median',int(st.median(v)),'best',v[0],{n:(S[n],1+sum(x>S[n] for x in v)) for n in ('RFS','BE','Brad','T-Rank','MATRIX') if n in S})
d=bm.collect(2026); off={key(t):s for t,s in d['official'].items()}
sub={n:{key(t):s for t,s in v.items()} for n,v in d['submissions'].items()}; jay=sub['Jay']
# Sheet-order lines among Jay's 61 teams
f=openpyxl.load_workbook('v1/Bracketology_V1_original.xlsx')['Sheet1']
A={'uva':'virginia','stmary':"saintmarysca",'sdsu':'sandiegostate','vatech':'virginiatech','ndst':'northdakotastate','kennesaw':'kennesawstate'}
def k(t):
    x=key(re.sub(r'\s+\d+\*?$','',t.replace('*','').strip())); return A.get(x,x)
order=[k(f.cell(r,1).value) for r in range(2,80) if f.cell(r,1).value and k(f.cell(r,1).value) in jay]
lines=sorted(jay[t] for t in order); sheet={t:lines[i] for i,t in enumerate(order)}
moves=[t for t in order if jay[t]!=sheet[t]]
cons={key(t):v[0] for t,v in d['consensus'].items()}
print('\nmoves',len(moves))
tow=collections.Counter(); right=0;helped=0;hurt=0
pts=lambda p,o:3 if p==o else 1 if abs(p-o)==1 else 0
print('team sheet->jay official RFS consensus_avg')
for t in moves:
    rf=sub['RFS'].get(t) if 'RFS' in sub else None; c=cons.get(t); o=off[t]
    d0=pts(sheet[t],o); d1=pts(jay[t],o)
    helped+=d1>d0; hurt+=d1<d0
    tw_c=abs(jay[t]-c)<abs(sheet[t]-c); tow['consensus']+=tw_c
    if rf: tow['RFS']+=abs(jay[t]-rf)<abs(sheet[t]-rf)
    print(f'{t:20} {sheet[t]:2}->{jay[t]:2} off {o:2} RFS {rf} cons {c:.2f} pts {d0}->{d1} toward_cons {tw_c}')
print('toward',dict(tow),'of',len(moves),'| helped',helped,'hurt',hurt,'same',len(moves)-helped-hurt)
# similarity of Jay to each site
sim=sorted(((sum(jay[t]==v.get(t) for t in jay),n,d['reported']['SCORE'].get(n)) for n,v in sub.items() if len(v)>=60 and n!='Jay'),reverse=True)[:8]
print('closest sites to Jay (teams same seed of 68):',sim)
