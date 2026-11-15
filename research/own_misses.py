"""docs/28: Test 17 (residual correction learned from v2.0's own held-out misses) and Test 18 (three-model ensemble)."""
import collections, numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; X = model._X
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))

# ---- head-to-head and common opponents (docs/23, unchanged) ----
H2H = {}
for y in Y:
    day = history.SELECTION_SUNDAY[y]; c = collections.Counter(); seen = set()
    for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); di = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if di > day or (di, a, b) in seen: continue
        seen.add((di, a, b))
        if g["win"]: c[(a, b)] += 1
    H2H[y] = c
REC = {}
for y in Y:
    rec = collections.defaultdict(lambda: [0, 0])
    for (a, b), n in H2H[y].items(): rec[(a, b)][0] += n; rec[(b, a)][1] += n
    opp = collections.defaultdict(set)
    for (a, b) in rec: opp[a].add(b)
    REC[y] = (rec, opp)
_cc = {}
def common(y, a, b):
    if (y, a, b) in _cc: return _cc[(y, a, b)]
    rec, opp = REC[y]; cs = (opp[a] & opp[b]) - {a, b}
    v = float(np.mean([rec[(a, o)][0] / sum(rec[(a, o)]) - rec[(b, o)][0] / sum(rec[(b, o)]) for o in cs])) if cs else 0.0
    _cc[(y, a, b)] = v; _cc[(y, b, a)] = -v; return v
pf = lambda y, a, b: [H2H[y][(a, b)] - H2H[y][(b, a)], common(y, a, b)]

def pairs(field_tr, sd, extra):
    dX, dy = [], []
    for yr in {r["year"] for r in field_tr}:
        rs = [r for r in field_tr if r["year"] == yr]; Z = sd.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = rs[i]["ov"] - rs[j]["ov"]
                if d and abs(d) <= 16:
                    e = pf(yr, rs[i]["key"], rs[j]["key"]) if extra else []
                    dX += [np.r_[Z[i] - Z[j], e], np.r_[Z[j] - Z[i], [-x for x in e]]]; dy += [d < 0, d > 0]
    return np.array(dX), np.array(dy, int)

def v2_run(h, exclude):
    train = project.training_rows(exclude=exclude); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False)
    return train, rows, f

RF = list(model.SEED) + ["champ", "is_power"]
def rfeat(r, pos): return [float(r[k]) for k in RF] + [pos]

res = {n: [] for n in ("control", "T17 full correction", "T17 half (reported)", "T18 ensemble")}; ex = {n: [] for n in res}
for h in Y:
    # step 1: v2.0's held-out misses on the other seasons, never touching h
    RX, Ry = [], []
    for s in Y:
        if s == h: continue
        _, rows_s, f_s = v2_run(s, {h, s})
        order = sorted(f_s, key=lambda r: -r["rank_score"])
        for p, r in enumerate(order, 1):
            if r["in_field"] and r.get("ov"): RX.append(rfeat(r, p)); Ry.append(r["ov"] - p)
    gbr = GradientBoostingRegressor(n_estimators=100, max_depth=2, learning_rate=.05, subsample=.8, min_samples_leaf=10, random_state=0).fit(np.array(RX), np.array(Ry))
    # outer: v2.0 on the six other seasons
    train, rows, f = v2_run(h, {h})
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    def place(score):  # higher = better
        order = [f[i] for i in np.argsort(-np.array(score), kind="stable")]; return {r["key"]: slots[i] for i, r in enumerate(order)}
    v2 = np.array([r["rank_score"] for r in f]); pos = np.empty(len(f)); pos[np.argsort(-v2, kind="stable")] = np.arange(1, len(f) + 1)
    corr = gbr.predict(np.array([rfeat(r, p) for r, p in zip(f, pos)]))
    L = {"control": place(v2), "T17 full correction": place(-(pos + corr)), "T17 half (reported)": place(-(pos + .5 * corr))}
    # Test 18 components
    field_tr = [r for r in train if r["in_field"] and r.get("ov")]; sd = StandardScaler().fit(X(field_tr, model.SEED)); B = sd.transform(X(f, model.SEED))
    dX, dy = pairs(field_tr, sd, True); coef = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(dX, dy).coef_[0]
    hc = np.array([float((1 / (1 + np.exp(-(np.array([np.r_[B[i] - B[j], pf(h, f[i]["key"], f[j]["key"])] for j in range(len(f)) if j != i]) @ coef)))).mean()) for i in range(len(f))])
    dX, dy = pairs(field_tr, sd, False)
    gb = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=.05, subsample=.8, random_state=0).fit(dX, dy)
    nl = np.array([float(gb.predict_proba(np.array([B[i] - B[j] for j in range(len(f)) if j != i]))[:, 1].mean()) for i in range(len(f))])
    z = lambda a: (a - a.mean()) / a.std()
    L["T18 ensemble"] = place((z(v2) + z(hc) + z(nl)) / 3)
    for n, l in L.items():
        res[n].append(bm.score(l, off)["score"]); ex[n].append(sum(1 for k in l if k in off and l[k] == off[k]))
    print(h, {n: v[-1] for n, v in res.items()}, "exact", {n: v[-1] for n, v in ex.items()}, f"| residual model n={len(Ry)} mean |corr| {np.abs(corr).mean():.2f}", flush=True)

print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    print(f"{n:<24}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75} exact {np.mean(ex[n]):.1f}")
