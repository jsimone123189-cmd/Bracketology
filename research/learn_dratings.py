"""docs/21: seed model trained on dRatings' (DII) historical lines, alone (T8a) and with committee pairs (T8b)."""
import sys; sys.path.insert(0, "research")
import numpy as np, matrix_full
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; X = model._X
DII = {y: {key(t): l for t, l in matrix_full.submissions(y)["DII"].items()} for y in Y}
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def pairs(field, sd, use_committee, use_dii):
    dX, dy = [], []
    for yr in {r["year"] for r in field}:
        rs = [r for r in field if r["year"] == yr]; Z = sd.transform(X(rs, model.SEED)); D = DII[yr]
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                if use_committee:
                    d = rs[i]["ov"] - rs[j]["ov"]
                    if d and abs(d) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
                if use_dii and rs[i]["key"] in D and rs[j]["key"] in D:
                    d = D[rs[i]["key"]] - D[rs[j]["key"]]
                    if d and abs(d) <= 4: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
    return np.array(dX), np.array(dy, int)
out = {n: [] for n in ("control", "T8a dRatings order", "T8b committee+dRatings")}; ex = {n: [] for n in out}; match = []
for h in Y:
    train = project.training_rows(exclude={h}); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    field_tr = [r for r in train if r["in_field"]]; sd = StandardScaler().fit(X(field_tr, model.SEED)); Bf = sd.transform(X(f, model.SEED))
    for n, uc, ud in (("control", True, False), ("T8a dRatings order", False, True), ("T8b committee+dRatings", True, True)):
        dX, dy = pairs(field_tr, sd, uc, ud); rk = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(dX, dy)
        sc = Bf @ rk.coef_[0]; order = [f[i] for i in np.argsort(-sc)]; L = {r["key"]: slots[i] for i, r in enumerate(order)}
        out[n].append(bm.score(L, off)["score"]); both = [k for k in L if k in off]
        ex[n].append((sum(L[k] == off[k] for k in both), sum(L[k] == off[k] for k in both if off[k] <= 4), sum(L[k] == off[k] for k in both if 5 <= off[k] <= 8)))
        if n == "T8a dRatings order": match.append(np.mean([L[k] == DII[h][k] for k in L if k in DII[h]]))
    print(h, {n: v[-1] for n, v in out.items()}, "exact (all, 1-4, 5-8)", {n: v[-1] for n, v in ex.items()}, f"T8a matches dRatings' line {match[-1]:.0%}", flush=True)
print("control reproduces:", out["control"] == CONTROL)
for n, s in out.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    e = np.array(ex[n]).mean(0)
    print(f"{n:<24}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75} exact {e.round(1)}")
