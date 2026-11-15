"""docs/27 Test 14: location-weighted head-to-head and common opponents (RPI venue weights)."""
import collections, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; X = model._X
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
H2H = {}
for y in Y:
    day = history.SELECTION_SUNDAY[y]; c = collections.Counter(); seen = set()
    for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); di = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if di > day or (di, a, b) in seen: continue
        seen.add((di, a, b))
        if g["win"]: c[(a, b)] += {"A": 1.4, "N": 1.0, "H": 0.6}[g["loc"]]
    H2H[y] = c
h2h = lambda y, a, b: H2H[y][(a, b)] - H2H[y][(b, a)]
REC = {}
for y in Y:
    rec = collections.defaultdict(lambda: [0, 0])
    for (a, b), n in H2H[y].items(): rec[(a, b)][0] += n; rec[(b, a)][1] += (2.0 - n if n in (0.6, 1.4) else n)
    opp = collections.defaultdict(set)
    for (a, b) in rec: opp[a].add(b)
    REC[y] = (rec, opp)
_cc = {}
def common(y, a, b):
    if (y, a, b) in _cc: return _cc[(y, a, b)]
    rec, opp = REC[y]; cs = (opp[a] & opp[b]) - {a, b}
    v = float(np.mean([rec[(a, o)][0] / sum(rec[(a, o)]) - rec[(b, o)][0] / sum(rec[(b, o)]) for o in cs])) if cs else 0.0
    _cc[(y, a, b)] = v; _cc[(y, b, a)] = -v; return v
def pf(y, a, b, mode):
    return {"h2h": [h2h(y, a, b)], "both": [h2h(y, a, b), common(y, a, b)], "common": [common(y, a, b)], "none": []}[mode]
def train_pairs(field, sd, with_h2h):
    dX, dy = [], []
    for yr in {r["year"] for r in field}:
        rs = [r for r in field if r["year"] == yr]; Z = sd.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = rs[i]["ov"] - rs[j]["ov"]
                if d and abs(d) <= 16:
                    e = pf(yr, rs[i]["key"], rs[j]["key"], with_h2h)
                    dX += [np.r_[Z[i] - Z[j], e], np.r_[Z[j] - Z[i], [-x for x in e]]]; dy += [d < 0, d > 0]
    return np.array(dX), np.array(dy, int)
out = {n: [] for n in ("control", "Test 14 weighted h2h+common")}; ex = {n: [] for n in out}
for h in Y:
    train = project.training_rows(exclude={h}); m = model.Model().fit(train)
    rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    field_tr = [r for r in train if r["in_field"]]; sd = StandardScaler().fit(X(field_tr, model.SEED)); B = sd.transform(X(f, model.SEED))
    met = sum(1 for i in range(len(f)) for j in range(i + 1, len(f)) if h2h(h, f[i]["key"], f[j]["key"]) or H2H[h][(f[i]["key"], f[j]["key"])])
    def place(score): order = [f[i] for i in np.argsort(-np.array(score))]; return {r["key"]: slots[i] for i, r in enumerate(order)}
    lines = {"control": place([r["rank_score"] for r in f])}
    for n, w in (("Test 14 weighted h2h+common", "both"),):
        dX, dy = train_pairs(field_tr, sd, w); rk = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(dX, dy); coef = rk.coef_[0]
        sc = []
        for i in range(len(f)):
            Zd = np.array([np.r_[B[i] - B[j], pf(h, f[i]["key"], f[j]["key"], w)] for j in range(len(f)) if j != i])
            sc.append(float((1 / (1 + np.exp(-(Zd @ coef)))).mean()))
        lines[n] = place(sc)
        if h == Y[0]: print(f"   {n} pair coefficients (trained without 2019):", [round(float(x), 3) for x in coef[len(model.SEED):]])
    for n, L in lines.items():
        out[n].append(bm.score(L, off)["score"]); ex[n].append(sum(1 for k in L if k in off and L[k] == off[k]))
    print(h, {n: v[-1] for n, v in out.items()}, "exact", {n: v[-1] for n, v in ex.items()}, flush=True)
print("control reproduces:", out["control"] == CONTROL)
for n, s in out.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    print(f"{n:<32}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75} exact {np.mean(ex[n]):.1f}")
