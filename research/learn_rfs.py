"""docs/32: reproduce RFS Bracket Science's lines from free stats (Part 1) and seed with its style (Test 22)."""
import sys; sys.path.insert(0, "research")
import numpy as np, matrix_full
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; X = model._X
RFS = {y: {key(t): l for t, l in matrix_full.submissions(y)["RFS"].items()} for y in Y}
ALL = {y: {r["key"]: r for r in (lambda rs: (model.attach_overall(rs, y), rs)[1])(model.prepare(build_year(y)))} for y in Y}
for y in Y: print(y, "RFS teams", len(RFS[y]), "found in our rows", sum(k in ALL[y] for k in RFS[y]))
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def rfs_rows(y): return [ALL[y][k] for k in RFS[y] if k in ALL[y]]
def rfs_pairs(years, sd):
    dX, dy = [], []
    for y in years:
        rs = rfs_rows(y); Z = sd.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = RFS[y][rs[i]["key"]] - RFS[y][rs[j]["key"]]
                if d and abs(d) <= 4: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
    return dX, dy
def com_pairs(train, sd):
    dX, dy = [], []; fld = [r for r in train if r["in_field"]]
    for y in {r["year"] for r in fld}:
        rs = [r for r in fld if r["year"] == y]; Z = sd.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = rs[i]["ov"] - rs[j]["ov"]
                if d and abs(d) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
    return dX, dy
LR = lambda dX, dy: LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int)).coef_[0]
def reproduce(y, sd, scorefn):
    rs = rfs_rows(y); s = scorefn(sd.transform(X(rs, model.SEED))); slots = fieldformat.format_for(y).slots
    o = np.argsort(-np.array(s), kind="stable"); return np.mean([slots[p] == RFS[y][rs[i]["key"]] for p, i in enumerate(o)])
# ceiling
sdA = StandardScaler().fit(X([r for y in Y for r in rfs_rows(y)], model.SEED)); cA = LR(*rfs_pairs(Y, sdA))
ceil = [reproduce(y, sdA, lambda Z: Z @ cA) for y in Y]
lin, nl = [], []; res = {n: [] for n in ("control", "T22a RFS order", "T22b committee+RFS")}
for h in Y:
    tr = [y for y in Y if y != h]; sd = StandardScaler().fit(X([r for y in tr for r in rfs_rows(y)], model.SEED))
    dX, dy = rfs_pairs(tr, sd); c = LR(dX, dy); lin.append(reproduce(h, sd, lambda Z: Z @ c))
    gb = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=.05, subsample=.8, random_state=0).fit(np.array(dX), np.array(dy, int))
    nl.append(reproduce(h, sd, lambda Z: [gb.predict_proba(np.array([Z[i] - Z[j] for j in range(len(Z)) if j != i]))[:, 1].mean() for i in range(len(Z))]))
    # Test 22 on v2.0's field, judged against the committee
    train = project.training_rows(exclude={h}); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    sdf = StandardScaler().fit(X([r for r in train if r["in_field"]], model.SEED)); Bf = sdf.transform(X(f, model.SEED))
    rX, ry = rfs_pairs(tr, sdf); cX, cy = com_pairs(train, sdf)
    for n, coef in (("control", None), ("T22a RFS order", LR(rX, ry)), ("T22b committee+RFS", LR(rX + cX, ry + cy))):
        sc = np.array([r["rank_score"] for r in f]) if coef is None else Bf @ coef
        L = {r["key"]: slots[i] for i, r in enumerate([f[i] for i in np.argsort(-sc, kind="stable")])}; res[n].append(bm.score(L, off)["score"])
    print(h, f"reproduce RFS exact: linear {lin[-1]:.0%} nonlinear {nl[-1]:.0%} ceiling {ceil[Y.index(h)]:.0%}", {n: v[-1] for n, v in res.items()}, flush=True)
best = max((np.mean(lin), "linear", lin), (np.mean(nl), "nonlinear", nl))
print(f"Part 1: linear mean {np.mean(lin):.0%} min {min(lin):.0%}; nonlinear mean {np.mean(nl):.0%} min {min(nl):.0%}; ceiling mean {np.mean(ceil):.0%}")
print("CRACKED:", any(np.mean(v) >= .85 and min(v) >= .75 for v in (lin, nl)))
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{n:<22}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {[pct(y, v) for y, v in zip(Y, s)]}")
