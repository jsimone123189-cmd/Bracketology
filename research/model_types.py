"""docs/16: M1 comparables, M2 nonlinear pairwise ranking, M3 blend. Field selection is v2.0's."""
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
def X(rows): return np.array([[float(r[f]) for f in model.SEED] for r in rows])
def matrix_scores(y): return sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX")
MS = {y: matrix_scores(y) for y in Y}; pct = lambda y, s: 100 * sum(v < s for v in MS[y]) / len(MS[y])
out = {n: [] for n in ("control", "M1 comparables", "M2 nonlinear pairs", "M3 blend")}
for h in Y:
    train = project.training_rows(exclude={h}); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    def place(score):            # lower score = better position
        order = sorted(f, key=lambda r: score[r["key"]]); return bm.score({r["key"]: slots[i] for i, r in enumerate(order)}, off)["score"]
    field_tr = [r for r in train if r["in_field"] and r.get("ov")]; sc = StandardScaler().fit(X(field_tr)); A = sc.transform(X(field_tr)); ov = np.array([r["ov"] for r in field_tr], float)
    B = sc.transform(X(f)); m1 = {}
    for r, b in zip(f, B):
        d = np.sqrt(((A - b) ** 2).sum(1)); idx = np.argsort(d)[:10]; w = 1 / (d[idx] + 1e-6); m1[r["key"]] = float((w * ov[idx]).sum() / w.sum())
    dX, dy = [], []
    for y in {r["year"] for r in field_tr}:
        rs = [r for r in field_tr if r["year"] == y]; Z = sc.transform(X(rs))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                dd = rs[i]["ov"] - rs[j]["ov"]
                if dd and abs(dd) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [dd < 0, dd > 0]
    gb = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=.05, subsample=.8, random_state=0).fit(np.array(dX), np.array(dy, int))
    m2 = {}
    for i, r in enumerate(f):
        diffs = np.array([B[i] - B[j] for j in range(len(f)) if j != i]); m2[r["key"]] = -float(gb.predict_proba(diffs)[:, 1].mean())
    v2 = {r["key"]: -r["rank_score"] for r in f}
    z = lambda d: {k: (v - np.mean(list(d.values()))) / np.std(list(d.values())) for k, v in d.items()}
    m3 = {k: .5 * z(v2)[k] + .5 * z(m1)[k] for k in v2}
    for n, s in (("control", v2), ("M1 comparables", m1), ("M2 nonlinear pairs", m2), ("M3 blend", m3)): out[n].append(place(s))
    print(h, {n: v[-1] for n, v in out.items()}, flush=True)
print("control reproduces:", out["control"] == CONTROL)
for n, s in out.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [round(pct(y, v)) for y, v in zip(Y, s)]
    print(f"{n:<20}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)}  percentiles {p} all>=75: {min(p) >= 75}")
