"""docs/17: train on earlier seasons only; recency weights and nonlinear pairs."""
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); TEST = [2022, 2023, 2024, 2025, 2026]
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in TEST}
pct = lambda y, s: round(100 * sum(v < s for v in MS[y]) / len(MS[y]))
X = model._X
def fit_score(train, rows, w_of, nonlinear):
    wt = lambda r: w_of(r["year"])
    pool = [r for r in train if not r["champ"]]; Xs = X(pool, model.SELECT); y = np.array([r["in_field"] for r in pool], int); sw = np.array([wt(r) for r in pool])
    ss = StandardScaler().fit(Xs); lr = LogisticRegression(C=.3, max_iter=3000).fit(ss.transform(Xs), y, sample_weight=sw)
    gb = GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(Xs, y, sample_weight=sw)
    field = [r for r in train if r["in_field"]]; sd = StandardScaler().fit(X(field, model.SEED)); dX, dy, dw = [], [], []
    for yr in {r["year"] for r in field}:
        rs = [r for r in field if r["year"] == yr]; Z = sd.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = rs[i]["ov"] - rs[j]["ov"]
                if d and abs(d) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]; dw += [wt(rs[i])] * 2
    Xr = X(rows, model.SELECT); p = (lr.predict_proba(ss.transform(Xr))[:, 1] + gb.predict_proba(Xr)[:, 1]) / 2
    for r, a in zip(rows, p): r["p_in"] = float(a)
    if not nonlinear:
        rk = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int), sample_weight=np.array(dw))
        q = sd.transform(X(rows, model.SEED)) @ rk.coef_[0]
        for r, b in zip(rows, q): r["rank_score"] = float(b)
        return None
    return GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=.05, subsample=.8, random_state=0).fit(np.array(dX), np.array(dy, int), sample_weight=np.array(dw)), sd
out = {n: [] for n in ("control", "R1 recency", "R2 nonlinear", "R3 nonlinear+recency")}
for h in TEST:
    train = project.training_rows(exclude={y for y in Y if y >= h}); off = None
    for n, rec, nl in (("control", False, False), ("R1 recency", True, False), ("R2 nonlinear", False, True), ("R3 nonlinear+recency", True, True)):
        w_of = (lambda yr: 0.5 ** ((h - yr - 1) / 2)) if rec else (lambda yr: 1.0)
        rows = model.prepare(build_year(h)); res = fit_score(train, rows, w_of, nl)
        if nl:
            gbm, sd = res; f, _ = model.choose_field([dict(r, rank_score=0.0) for r in rows], h, project_autos=False)
            B = sd.transform(X(f, model.SEED))
            for i, r in enumerate(f): r["rank_score"] = float(gbm.predict_proba(np.array([B[i] - B[j] for j in range(len(f)) if j != i]))[:, 1].mean())
        else: f, _ = model.choose_field(rows, h, project_autos=False)
        o = model.assign_lines(f, h); off = {r["key"]: r["seed"] for r in rows if r["in_field"]}
        out[n].append(bm.score({r["key"]: r["line"] for r in o}, off)["score"])
    print(h, {n: v[-1] for n, v in out.items()}, flush=True)
base = np.array(out["control"])
for n, s in out.items():
    d = np.array(s) - base; ok = d.mean() >= 3 and (d > 0).sum() >= 4 and d.min() >= -5
    print(f"{n:<22}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} percentiles {[pct(y, v) for y, v in zip(TEST, s)]}")
