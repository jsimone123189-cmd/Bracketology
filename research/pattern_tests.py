"""Patterns found in research/big_misses.py. Test list fixed before running. Same bar: +3 mean, better in 5+ of 7, no season below -5.
Because the ideas came from these seasons, field ideas also get an independent check on 2014-18 (own rating stands in for NET there)."""
import collections, itertools, sys
import numpy as np
sys.path.insert(0, "research")
from sklearn.ensemble import GradientBoostingClassifier as GB
from sklearn.linear_model import LogisticRegression as LR
from sklearn.preprocessing import StandardScaler as SS
from bracketology import fieldformat, history, model
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
import common
Y = sorted(history.SELECTION_SUNDAY); REF = [335, 326, 347, 344, 329, 363, 356]; OLD = common.OLD
def extra(rows, day, y):
    net = {r["key"]: r["net"] for r in rows}; F = collections.defaultdict(lambda: collections.defaultdict(list))
    for g in torvik.collect_games(y)["rows"]:
        m, d, yy = g["date"].split("/"); iso = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if iso > day or g["type"] not in (0, 1, 2): continue
        a, b = key(g["team"]), key(g["opp"])
        if a in net and b in net: F[a]["t%d" % g["type"]].append((net[b], g["win"]))
    for r in rows:
        f = F[r["key"]]; nc, cf = f["t0"], f["t1"]
        r["conf_pct"] = sum(w for _, w in cf) / max(1, len(cf)); r["conf_sub500"] = float(r["conf_pct"] < .5); r["nc_opp"] = float(np.mean([n for n, _ in nc])) if nc else 200.
        r["q1_rate"] = r["cq1_w"] / max(1, r["cq1_w"] + r["cq1_l"]); r["many_q1l"] = float(r["cq1_l"] >= 10)
        r["nonpower_atl"] = float(not r["is_power"] and not r["champ"]); r["champ_f"] = float(r["champ"])
    ref = [r for r in rows if r["net"] <= 120]
    for n in ("conf_pct", "nc_opp", "q1_rate"):
        v = np.array([r[n] for r in ref]); mu, s = v.mean(), v.std() + 1e-9
        for r in rows: r["z_" + n] = (r[n] - mu) / s
    for r in rows: r["conf_x_power"] = r["z_conf_pct"] * r["is_power"]
    return rows
def pac12(rows):
    """Copy of the season with the Pac-12 counted as a power league, as it was through 2023-24."""
    out = [dict(r) for r in rows]
    for r in out:
        if r["lg"] in ("P12", "pac12", "P10") and r["year"] <= 2024: r["is_power"] = 1.0
    return extra(model.prepare(out), history.SELECTION_SUNDAY.get(r["year"], OLD.get(r["year"])), r["year"])
D = {y: extra(model.attach_overall(model.prepare(build_year(y)), y), history.SELECTION_SUNDAY[y], y) for y in Y}
DP = {y: pac12(D[y]) for y in Y}
def X(rows, f): return np.array([[float(r[x]) for x in f] for r in rows])
def fitsel(pool, f):
    pool = [r for r in pool if not r["champ"]]; A, b = X(pool, f), np.array([r["in_field"] for r in pool], int); sc = SS().fit(A)
    lr = LR(C=.3, max_iter=3000).fit(sc.transform(A), b); gb = GB(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(A, b)
    return lambda rows: (lr.predict_proba(sc.transform(X(rows, f)))[:, 1] + gb.predict_proba(X(rows, f))[:, 1]) / 2
def pair(train, test, f, win=16, C=.1):
    fld = [r for r in train if r["in_field"]]; sc = SS().fit(X(fld, f)); A, b = [], []; by = {}
    for r in fld: by.setdefault(r["year"], []).append(r)
    for rs in by.values():
        Z = sc.transform(X(rs, f))
        for i, j in itertools.combinations(range(len(rs)), 2):
            d = rs[i]["ov"] - rs[j]["ov"]
            if d and abs(d) <= win: A += [Z[i] - Z[j], Z[j] - Z[i]]; b += [d < 0, d > 0]
    m = LR(C=C, max_iter=3000, fit_intercept=False).fit(np.array(A), np.array(b, int))
    return sc.transform(X(test, f)) @ m.coef_[0]
def run(fs=model.SELECT, fd=model.SEED, data=D):
    out = []
    for h in Y:
        train = [r for y in Y if y != h for r in data[y]]; rows = data[h]; p = fitsel(train, fs)(rows)
        autos = [r for r in rows if r["champ"]]; pool = sorted((x for x in zip(rows, p) if not x[0]["champ"]), key=lambda x: -x[1])
        fl = autos + [r for r, _ in pool[:68 - len(autos)]]; q = pair(train, fl, fd); o = np.argsort(-q, kind="stable")
        line = {fl[i]["key"]: l for i, l in zip(o, fieldformat.slot_lines(h))}; true = {r["key"]: r["seed"] for r in rows if r["in_field"]}
        s = bm.score(line, true); big = sum(k in line and abs(line[k] - v) >= 2 for k, v in true.items())
        out.append((s["score"], s["picked"], big))
    return out
def flip(d):
    d = np.array(d, float); return sum(abs((d * np.array(s)).mean()) >= abs(d.mean()) - 1e-12 for s in itertools.product((1, -1), repeat=7)) / 128
base = run(); B = [x[0] for x in base]; print("BASE", B, round(np.mean(B), 1), "reproduces production", B == REF, "picked", np.mean([x[1] for x in base]).round(1), "big misses", np.mean([x[2] for x in base]).round(1), flush=True)
def rep(lab, res):
    sc = [x[0] for x in res]; d = [a - b for a, b in zip(sc, B)]; ok = np.mean(d) >= 3 and sum(x > 0 for x in d) >= 5 and min(d) >= -5
    print(f"{lab:46} {sc} mean {np.mean(sc):.1f} diff {np.mean(d):+.1f} better {sum(x > 0 for x in d)} worse {sum(x < 0 for x in d)} worst {min(d):+d} p {flip(d):.2f} picked {np.mean([x[1] for x in res]):.1f} big {np.mean([x[2] for x in res]):.1f} {'PASSES' if ok else ''}", flush=True)
S, E = model.SELECT, model.SEED
print("--- field")
SETS = {"conference record": ["z_conf_pct"], "under .500 in league": ["conf_sub500"], "conference record x power": ["z_conf_pct", "conf_x_power"], "non-conference opponents": ["z_nc_opp"], "Q1 win rate": ["z_q1_rate"], "10+ Q1 losses": ["many_q1l"]}
for lab, f in SETS.items(): rep("field + " + lab, run(fs=S + f))
print("--- seeds")
for lab, f in {"conference record": ["z_conf_pct"], "non-conference opponents": ["z_nc_opp"], "Q1 win rate": ["z_q1_rate"], "non-power at-large flag": ["nonpower_atl"], "champion flag": ["champ_f"]}.items(): rep("seeds + " + lab, run(fd=E + f))
print("--- both, and the league definition")
rep("both + conference record", run(fs=S + ["z_conf_pct"], fd=E + ["z_conf_pct"]))
rep("Pac-12 counted as power through 2024", run(data=DP))
print("--- independent check, 2014-18 field picks (trained on 2019-26, real field 68)", flush=True)
OD = {}
for y in OLD:
    rows = common.old_year(y)
    for r in rows:
        r["is_power"] = 1.0 if r["lg"] in ("ACC", "B12", "BE", "B10", "SEC") else 0.0
    OD[y] = extra(model.prepare(rows), OLD[y], y)
train = [r for y in Y for r in D[y]]
for lab, f in [("base", [])] + list(SETS.items()):
    p = fitsel(train, S + f); res = []
    for y, rows in OD.items():
        pr = p(rows); autos = [r for r in rows if r["champ"]]; pool = sorted((x for x in zip(rows, pr) if not x[0]["champ"]), key=lambda x: -x[1]); fl = autos + [r for r, _ in pool[:68 - len(autos)]]
        res.append(sum(r["in_field"] for r in fl))
    print(f"{lab:30} correct teams {res} mean {np.mean(res):.1f} of 68", flush=True)
