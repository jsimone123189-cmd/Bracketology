"""Round 3, aimed at the measured gaps: field picks, lines 1-4 and 14-16. All variants reported. Final check is nested: the choice is made without the held-out season."""
import json, sys
sys.path.insert(0, "research")
from common import *
from sklearn.ensemble import GradientBoostingClassifier as GC
from sklearn.linear_model import LogisticRegression as LR
from sklearn.preprocessing import StandardScaler as SS
D = load(); F = Z + ["is_power"]
SC = json.load(open("data/history/scurve.json"))
for y in Y:
    seq = SC[str(y)]; off = truth(D[y])
    if off[seq[-1]] <= 2: seq = [seq[-1]] + seq[:-1]
    pos = {k: i + 1 for i, k in enumerate(seq)}
    for r in D[y]:
        r["ov"] = pos.get(r["key"])
        q1g = r["cq1_w"] + r["cq1_l"]
        r["q1_games"] = float(q1g); r["few_q1"] = 1.0 if q1g <= 3 else 0.0
        r["q1w_power"] = r["cq1_w"] * r["is_power"]; r["net_nonpower"] = np.log(r["net"]) * (1 - r["is_power"])
        r["q12_w"] = float(r["cq1_w"] + r["cq2_w"]); r["bad_l"] = float(r["cq3_l"] + 3 * r["cq4_l"])
X1 = F + ["q1_games", "few_q1", "q1w_power", "net_nonpower"]
FP = {"F": F, "X1": X1}

def sel_cls(tr, te, f):
    pool = [r for r in tr if not r["champ"]]; Xp, yp = A(pool, f), np.array([r["in_field"] for r in pool], int); sc = SS().fit(Xp); Xt = A(te, f)
    return (LR(C=.3, max_iter=3000).fit(sc.transform(Xp), yp).predict_proba(sc.transform(Xt))[:, 1] + GC(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(Xp, yp).predict_proba(Xt)[:, 1]) / 2
def sel_pair(tr, te, f, cap=100, C=.1):
    pool = [r for r in tr if not r["champ"] and r["net"] <= cap]; s = SS().fit(A(pool, f)); dX, dy = [], []; by = {}
    for r in pool: by.setdefault(r["year"], []).append(r)
    for rows in by.values():
        X = s.transform(A(rows, f)); a = [i for i, r in enumerate(rows) if r["in_field"]]; b = [i for i, r in enumerate(rows) if not r["in_field"]]
        for i in a:
            for j in b: dX += [X[i] - X[j], X[j] - X[i]]; dy += [1, 0]
    m = LR(C=C, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy))
    return s.transform(A(te, f)) @ m.coef_[0]
def pair_seed(tf, te, f, win=16, C=.1):
    s = SS().fit(A(tf, f)); dX, dy = [], []; by = {}
    for r in tf: by.setdefault(r["year"], []).append(r)
    for rows in by.values():
        X = s.transform(A(rows, f))
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                d = rows[i]["ov"] - rows[j]["ov"]
                if d and abs(d) <= win: dX += [X[i] - X[j], X[j] - X[i]]; dy += [d < 0, d > 0]
    m = LR(C=C, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int))
    return -(s.transform(A(te, f)) @ m.coef_[0])

def bracket(te, tr, selmode, seedmode, f_sel, f_seed):
    for r, p in zip(te, sel_cls(tr, te, f_sel) if selmode == "cls" else sel_pair(tr, te, f_sel)): r["_p"] = float(p)
    tf = [r for r in tr if r["in_field"]]; m = pair_seed(tf, te, f_seed)
    for r, v in zip(te, m): r["_m"] = float(v)
    field = B.pick_field(te, "_p")
    order = sorted(field, key=lambda r: r["_m"])
    if seedmode == "lowmajor_net":       # bottom auto-bid slots ordered by NET (they rarely have comparable resumes)
        low = [r for r in order if r["champ"] and not r["is_power"]][-16:]; ids = {r["key"] for r in low}
        slots = [i for i, r in enumerate(order) if r["key"] in ids]; low = sorted(low, key=lambda r: r["net"])
        for i, r in zip(slots, low): order[i] = r
    if seedmode == "tiered":             # re-rank top 20 and the rest with models fit only on that part of the list
        top = pair_seed([r for r in tf if r["ov"] <= 28], te, f_seed, win=12); low = pair_seed([r for r in tf if r["ov"] >= 45], te, f_seed, win=12)
        idx = {r["key"]: i for i, r in enumerate(te)}
        a, b, c = order[:20], order[20:48], order[48:]
        order = sorted(a, key=lambda r: top[idx[r["key"]]]) + b + sorted(c, key=lambda r: low[idx[r["key"]]])
    return B.slot(order)

def run(sm="cls", sd="base", fs="F", fd="F", years=Y, pool_years=Y):
    out = {}
    for h in years:
        tr = [r for y in pool_years if y != h for r in D[y]]
        out[h] = B.bm_score(bracket(D[h], tr, sm, sd, FP[fs], FP[fd]), truth(D[h]))
    return out
base = run(); summarize("BASE: classifier field, pairwise seeds", base)
CFG = {"pairwise field": dict(sm="pair"), "pairwise field + bubble features": dict(sm="pair", fs="X1"), "classifier + bubble features": dict(fs="X1"),
       "seeding + bubble features": dict(fd="X1"), "low-major slots ordered by NET": dict(sd="lowmajor_net"), "tiered re-rank top and bottom": dict(sd="tiered"),
       "pairwise field, tiered": dict(sm="pair", sd="tiered"), "pairwise field, low-major NET": dict(sm="pair", sd="lowmajor_net"), "all bubble features, pairwise field": dict(sm="pair", fs="X1", fd="X1")}
R = {}
for n, c in CFG.items():
    R[n] = run(**c); summarize(n, R[n], base)
# nested: for each held-out season, pick the config using only the other seasons' leave-one-out scores
nested = {}
for h in Y:
    others = [y for y in Y if y != h]; S = {"BASE": np.mean([base[y]["score"] for y in others]), **{n: np.mean([R[n][y]["score"] for y in others]) for n in R}}
    pick = max(S, key=S.get); nested[h] = (base if pick == "BASE" else R[pick])[h]; print(h, "picked without this season:", pick, flush=True)
summarize("NESTED honest score of 'choose the best variant'", nested, base)
