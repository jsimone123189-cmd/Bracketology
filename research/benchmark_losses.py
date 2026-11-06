"""Field vs seed losses for T-Rank and the 15 entrants nearest the median score, on the same rubric. Benchmarks only."""
import statistics as st, numpy as np
from bracketology import history
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
def parts(sub, off):
    miss = sum(t not in sub for t in off); one = sum(t in sub and abs(sub[t] - s) == 1 for t, s in off.items()); two = sum(t in sub and abs(sub[t] - s) >= 2 for t, s in off.items())
    return np.array([6 * miss, 2 * one, 3 * two])
T, M = [], []
for y in sorted(history.SELECTION_SUNDAY):
    m = bm.collect(y); O = {key(t): s for t, s in m["official"].items()}
    T.append(parts({key(t): s for t, s in m["submissions"]["T-Rank"].items()}, O))
    sc = {n: int(v) for n, v in m["reported"]["SCORE"].items() if v.isdigit() and n not in ("MATRIX", "") and n in m["submissions"]}
    med = st.median(sc.values()); near = sorted(sc, key=lambda n: abs(sc[n] - med))[:15]
    M.append(np.mean([parts({key(t): s for t, s in m["submissions"][n].items()}, O) for n in near], axis=0))
for lab, a in (("T-Rank", T), ("median entrants", M)):
    a = np.array(a); print(lab, "lost per season: field %.1f, one line off %.1f, two+ off %.1f, total %.1f" % (*a.mean(0), a.sum(1).mean()), "| field by season", a[:, 0].round(1).tolist())
