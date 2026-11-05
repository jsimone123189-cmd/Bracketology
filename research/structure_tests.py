"""Structural changes: more training seasons, bubble-only selection pool, separate seeding groups, direct ranking, monotonic boosting."""
import numpy as np, sys
sys.path.insert(0, "research")
from common import *
from sklearn.ensemble import GradientBoostingClassifier as GC, GradientBoostingRegressor as GR, HistGradientBoostingRegressor as HR
from sklearn.linear_model import LogisticRegression as LR, Ridge
from sklearn.preprocessing import StandardScaler as SS
D = load(old=OLD)
F = Z + ["is_power"]

def sel(pool, te, f, seed=0):
    Xp, yp = A(pool, f), np.array([r["in_field"] for r in pool], int); sc = SS().fit(Xp); Xt = A(te, f)
    return (LR(C=.3, max_iter=3000).fit(sc.transform(Xp), yp).predict_proba(sc.transform(Xt))[:, 1]
            + GC(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=seed).fit(Xp, yp).predict_proba(Xt)[:, 1]) / 2

def seed_reg(tf, te, f, seed=0):
    Xf, yf = A(tf, f), np.array([r["seed"] for r in tf], float); s2 = SS().fit(Xf); Xt = A(te, f)
    return (Ridge(alpha=10).fit(s2.transform(Xf), yf).predict(s2.transform(Xt))
            + GR(n_estimators=150, max_depth=2, learning_rate=.05, subsample=.8, random_state=seed).fit(Xf, yf).predict(Xt)) / 2

def seed_split(tf, te, f):
    out = np.zeros(len(te)); mid = [r for r in tf if not r["champ"] or r["is_power"] or r["seed"] <= 11]; low = [r for r in tf if r["champ"] and not r["is_power"] and r["seed"] >= 10]
    a, b = seed_reg(mid, te, f), seed_reg(low, te, [x for x in f if x != "is_power"])
    for i, r in enumerate(te):
        out[i] = b[i] if (r["champ"] and not r["is_power"] and a[i] >= 10.5) else a[i]
    return out

def seed_pair(tf, te, f):
    by = {}
    for r in tf: by.setdefault(r["year"], []).append(r)
    X0 = A(tf, f); s = SS().fit(X0); dX, dy = [], []
    for rows in by.values():
        Xr = s.transform(A(rows, f))
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                if rows[i]["seed"] != rows[j]["seed"] and abs(rows[i]["seed"] - rows[j]["seed"]) <= 4:
                    sgn = 1 if rows[i]["seed"] < rows[j]["seed"] else -1
                    dX += [Xr[i] - Xr[j], Xr[j] - Xr[i]]; dy += [sgn > 0, sgn < 0]
    m = LR(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int))
    return -(s.transform(A(te, f)) @ m.coef_[0])

def seed_mono(tf, te, f):
    sign = {"z_net_log": 1, "z_wab": -1, "z_sor": -1, "z_rating": -1, "z_q1a_w": -1, "z_cq1_w": -1, "z_cq3_l": 1, "z_cq4_l": 1, "z_win_pct": -1, "rk_wab": 1, "rk_sor": 1, "rk_rating": 1}
    cst = [sign.get(x, 0) for x in f]; Xf, yf = A(tf, f), np.array([r["seed"] for r in tf], float); s2 = SS().fit(Xf); Xt = A(te, f)
    return (Ridge(alpha=10).fit(s2.transform(Xf), yf).predict(s2.transform(Xt))
            + HR(max_iter=150, max_depth=2, learning_rate=.05, monotonic_cst=cst, random_state=0).fit(Xf, yf).predict(Xt)) / 2

def run(f=F, seed_fn=seed_reg, net_cap=None, extra=(), seed_extra=()):
    out = {}
    for h in Y:
        tr_sel = [r for y in list(Y) + list(extra) if y != h for r in D[y] if not r["champ"] and (net_cap is None or r["net"] <= net_cap)]
        tf = [r for y in list(Y) + list(seed_extra) if y != h for r in D[y] if r["in_field"]]
        te = D[h]
        for r, p, m in zip(te, sel(tr_sel, te, f), seed_fn(tf, te, f)): r["_p"], r["_m"] = float(p), float(m)
        out[h] = B.bm_score(B.slot(sorted(B.pick_field(te, "_p"), key=lambda r: r["_m"])), truth(te))
    return out

base = run(); summarize("BASE (Z + is_power)", base)
print("-- bubble-focused selection training")
for c in (150, 100, 75, 60): summarize(f"train selection only on NET<={c}", run(net_cap=c), base)
print("-- seeding structure")
summarize("separate auto-bid low-major seeding", run(seed_fn=seed_split), base)
summarize("direct pairwise ranking", run(seed_fn=seed_pair), base)
summarize("monotonic boosting", run(seed_fn=seed_mono), base)
print("-- more training seasons (own rating stands in for NET)")
summarize("+2014-18 for selection and seeding", run(extra=OLD, seed_extra=OLD), base)
summarize("+2016-18 for selection and seeding", run(extra=(2016, 2017, 2018), seed_extra=(2016, 2017, 2018)), base)
summarize("+2014-18 for seeding only", run(seed_extra=OLD), base)
summarize("+2014-18 for selection only", run(extra=OLD), base)
print("-- features")
summarize("+ conference tournament wins", run(f=F + ["ct_wins"]), base)
summarize("+ Q1+Q2 wins and Q1 win rate", run(f=F + ["q12_w", "q1_rate"]), base)
