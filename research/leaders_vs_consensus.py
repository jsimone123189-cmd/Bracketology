"""Do the consistent nine follow the Matrix consensus, and are they right when they leave it? Diagnostic."""
import sys; sys.path.insert(0, "research")
import numpy as np, matrix_full
from scipy.stats import spearmanr
from bracketology import history
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]
for h in Y:
    R = {r["key"]: r for r in build_year(h)}; off = {k: r["seed"] for k, r in R.items() if r["in_field"]}
    cons = {key(t): a for t, (a, n) in bm.collect(h)["consensus"].items()}; subs = matrix_full.submissions(h)
    G = {g: {key(t): l for t, l in subs[g].items()} for g in GROUP if g in subs}
    agree, leave_right, leave_wrong, leave_same = [], 0, 0, 0
    for g, s in G.items():
        both = [k for k in s if k in cons]; agree.append(np.mean([s[k] == round(cons[k]) for k in both]))
        for k in both:
            c = round(cons[k])
            if s[k] != c and k in off:
                if s[k] == off[k]: leave_right += 1
                elif c == off[k]: leave_wrong += 1
                else: leave_same += 1
    gm = {k: np.mean([s[k] for s in G.values() if k in s]) for k in off if any(k in s for s in G.values())}
    rho = spearmanr([gm[k] for k in gm if k in cons], [cons[k] for k in gm if k in cons])[0]
    cons_exact = sum(1 for k in off if k in cons and round(cons[k]) == off[k])
    print(f"{h}: group mean vs consensus rank corr {rho:.3f}; members match the rounded consensus line on {np.mean(agree):.0%} of teams; when they leave it: right {leave_right}, consensus right {leave_wrong}, neither {leave_same}; consensus exact {cons_exact}")
