"""Train seeding on the committee's published 1-68 order instead of 16 coarse lines."""
import json, sys
sys.path.insert(0, "research")
from common import *
from sklearn.ensemble import GradientBoostingClassifier as GC, GradientBoostingRegressor as GR
from sklearn.linear_model import LogisticRegression as LR, Ridge
from sklearn.preprocessing import StandardScaler as SS
D = load(); F = Z + ["is_power"]
SC = json.load(open("data/history/scurve.json"))
for y in Y:
    seq = SC[str(y)]; off = truth(D[y])
    if off[seq[-1]] <= 2: seq = [seq[-1]] + seq[:-1]           # list header pushed the #1 team to the end in one article
    lines = [off[k] for k in seq]
    print(y, "line-order drops", sum(b < a for a, b in zip(lines, lines[1:])), "max", max([a - b for a, b in zip(lines, lines[1:])] + [0]), seq[:2], flush=True)
    pos = {k: i + 1 for i, k in enumerate(seq)}
    for r in D[y]: r["ov"] = pos.get(r["key"])

def sel(pool, te, seed=0):
    Xp, yp = A(pool, F), np.array([r["in_field"] for r in pool], int); sc = SS().fit(Xp); Xt = A(te, F)
    return (LR(C=.3, max_iter=3000).fit(sc.transform(Xp), yp).predict_proba(sc.transform(Xt))[:, 1]
            + GC(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=seed).fit(Xp, yp).predict_proba(Xt)[:, 1]) / 2
def reg(tf, te, target, seed=0, alpha=10, gbm=True, depth=2):
    Xf, yf = A(tf, F), np.array([r[target] for r in tf], float); s = SS().fit(Xf); Xt = A(te, F)
    p = Ridge(alpha=alpha).fit(s.transform(Xf), yf).predict(s.transform(Xt))
    if not gbm: return p
    g = GR(n_estimators=150, max_depth=depth, learning_rate=.05, subsample=.8, random_state=seed).fit(Xf, yf).predict(Xt)
    return (p + g) / 2
def pair(tf, te, target, win, C=.1):
    s = SS().fit(A(tf, F)); dX, dy = [], []
    by = {}
    for r in tf: by.setdefault(r["year"], []).append(r)
    for rows in by.values():
        X = s.transform(A(rows, F))
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                d = rows[i][target] - rows[j][target]
                if d != 0 and abs(d) <= win:
                    dX += [X[i] - X[j], X[j] - X[i]]; dy += [d < 0, d > 0]
    m = LR(C=C, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int))
    return -(s.transform(A(te, F)) @ m.coef_[0])
def run(fn):
    out = {}
    for h in Y:
        tr = [r for y in Y if y != h for r in D[y]]; te = D[h]; tf = [r for r in tr if r["in_field"]]
        for r, p, m in zip(te, sel([r for r in tr if not r["champ"]], te), fn(tf, te)): r["_p"], r["_m"] = float(p), float(m)
        out[h] = B.bm_score(B.slot(sorted(B.pick_field(te, "_p"), key=lambda r: r["_m"])), truth(te))
    return out
base = run(lambda a, b: reg(a, b, "seed")); summarize("BASE, target = 16 seed lines", base)
summarize("target = official 1-68, ridge + boosting", run(lambda a, b: reg(a, b, "ov")), base)
summarize("target = official 1-68, ridge only", run(lambda a, b: reg(a, b, "ov", gbm=False)), base)
summarize("target = lines, ridge only", run(lambda a, b: reg(a, b, "seed", gbm=False)), base)
for w in (8, 16, 30): summarize(f"pairwise on official order, within {w} spots", run(lambda a, b, w=w: pair(a, b, "ov", w)), base)
for s in (1, 2): summarize(f"1-68 target, random seed {s}", run(lambda a, b, s=s: reg(a, b, "ov", seed=s)), base)
