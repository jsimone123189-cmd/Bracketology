"""docs/20: Test 7, Bradley-Terry results rating in both models."""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from bracketology import history, model, project
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; _c = {}
def bt_rows(y):
    if y in _c: return [dict(r) for r in _c[y]]
    rows = raw_build(y); day = history.SELECTION_SUNDAY[y]; idx = {r["key"]: i for i, r in enumerate(rows)}; n = len(rows)
    R, C, V, yv, seen = [], [], [], [], set()
    for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); di = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if a not in idx or b not in idx or di > day: continue
        gid = (di, min(a, b), max(a, b))
        if gid in seen: continue
        seen.add(gid); r = len(yv); h = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]
        R += [r, r, r]; C += [idx[a], idx[b], n]; V += [1.0, -1.0, h]; yv.append(int(bool(g["win"])))
    X = csr_matrix((V, (R, C)), shape=(len(yv), n + 1))
    lr = LogisticRegression(C=1.0, fit_intercept=False, max_iter=5000).fit(X, np.array(yv))
    for r in rows: r["bt"] = float(lr.coef_[0][idx[r["key"]]])
    _c[y] = rows; return [dict(r) for r in rows]
project.build_year = bt_rows; model.BASE = model.BASE + ["bt"]; SEL, SEED = list(model.SELECT), list(model.SEED)
for y in Y:
    t = [r for r in bt_rows(y) if r["net"] <= 100]; print(f"  {y} BT vs NET rank corr (NET top 100): {spearmanr([-r['bt'] for r in t], [r['net'] for r in t])[0]:.3f}", flush=True)
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def loso(sel, seed):
    model.SELECT, model.SEED = sel, seed; s = []
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(bt_rows(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
        s.append(bm.score({r["key"]: r["line"] for r in o}, {r["key"]: r["seed"] for r in rows if r["in_field"]})["score"])
    return s
cs = loso(SEL, SEED); print("control", cs, "reproduces:", cs == CONTROL, flush=True)
s = loso(SEL + ["z_bt"], SEED + ["z_bt"]); d = np.array(s) - np.array(cs); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
print(f"Test 7 BT {s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} percentiles {p} all>=75 {min(p) >= 75}")
