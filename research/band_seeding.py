"""docs/30 Test 20: band-specific re-ranking (1-16, 17-40, 41-68) after v2.0's order."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
BANDS = [(1, 16), (17, 40), (41, 68)]; W = 4
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def band_models(train, sd):
    fld = [r for r in train if r["in_field"] and r.get("ov")]; out = []
    for a, b in BANDS:
        lo, hi = a - W, b + W; dX, dy = [], []
        for y in {r["year"] for r in fld}:
            rs = [r for r in fld if r["year"] == y and lo <= r["ov"] <= hi]; Z = sd.transform(model._X(rs, model.SEED))
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    d = rs[i]["ov"] - rs[j]["ov"]
                    if d and abs(d) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
        out.append(LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int)).coef_[0])
    return out
def rerank(f, sd, coefs):
    order = sorted(f, key=lambda r: -r["rank_score"]); new = []
    for (a, b), c in zip(BANDS, coefs):
        grp = order[a - 1:b]; s = sd.transform(model._X(grp, model.SEED)) @ c if grp else []
        new += [grp[i] for i in np.argsort(-np.array(s), kind="stable")]
    return new
# in-sample expressiveness check
allr = project.training_rows(); M = model.Model().fit(allr); C = band_models(allr, M.s_seed); ins = []
for y in Y:
    rs = [r for r in allr if r["year"] == y and r["in_field"]]; M.score(rs); slots = fieldformat.format_for(y).slots
    o = sorted(rs, key=lambda r: r["ov"]); tmp = [dict(r, rank_score=-r["ov"]) for r in o]  # band membership by true position for the ceiling
    nb = rerank(tmp, M.s_seed, C); ins.append(sum(slots[p] == r["seed"] for p, r in enumerate(nb)))
print("in-sample exact, band formulas (true band membership):", ins, np.mean(ins))
res = {"control": [], "T20 band formulas": []}; ex = {n: [] for n in res}
for h in Y:
    train = project.training_rows(exclude={h}); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    for n, o in (("control", sorted(f, key=lambda r: -r["rank_score"])), ("T20 band formulas", rerank(f, m.s_seed, band_models(train, m.s_seed)))):
        L = {r["key"]: slots[i] for i, r in enumerate(o)}; res[n].append(bm.score(L, off)["score"]); ex[n].append(sum(1 for k in L if k in off and L[k] == off[k]))
    print(h, {n: v[-1] for n, v in res.items()}, "exact", {n: v[-1] for n, v in ex.items()}, flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{n:<20}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} exact {np.mean(ex[n]):.1f} pct {[pct(y, v) for y, v in zip(Y, s)]}")
