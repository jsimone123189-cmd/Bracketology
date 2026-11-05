"""Top-16 reveal test, then where the best model loses to T-Rank and the human median (benchmarks only, never model inputs)."""
import json, sys, collections, statistics as st
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
    for r in D[y]: r["ov"] = pos.get(r["key"])
T16 = {2019: [["Duke", "Tennessee", "Virginia", "Gonzaga"], ["Michigan", "North Carolina", "Kentucky", "Michigan St."], ["Marquette", "Purdue", "Houston", "Kansas"], ["Iowa St.", "Nevada", "Wisconsin", "Louisville"]],
       2021: [["Gonzaga", "Baylor", "Michigan", "Ohio St."], ["Alabama", "Illinois", "Houston", "Villanova"], ["Oklahoma", "Tennessee", "West Virginia", "Virginia"], ["Iowa", "Texas", "Missouri", "Texas Tech"]],
       2022: [["Gonzaga", "Auburn", "Arizona", "Kansas"], ["Baylor", "Kentucky", "Purdue", "Duke"], ["Villanova", "Texas Tech", "Tennessee", "Illinois"], ["UCLA", "Providence", "Texas"]],
       2023: [["Alabama", "Houston", "Purdue", "Kansas"], ["Texas", "Arizona", "Baylor", "UCLA"], ["Tennessee", "Virginia", "Iowa St.", "Kansas St."], ["Indiana", "Gonzaga", "Xavier"]],
       2024: [["Purdue", "UConn", "Houston", "Arizona"], ["North Carolina", "Tennessee", "Marquette", "Kansas"], ["Alabama", "Baylor", "Iowa St.", "Duke"], ["Auburn", "San Diego St.", "Illinois", "Wisconsin"]],
       2025: [["Auburn", "Alabama", "Duke", "Florida"], ["Tennessee", "Texas A&M", "Purdue", "Houston"], ["Iowa St.", "Kentucky", "Wisconsin", "Arizona"], ["Texas Tech", "Michigan", "Kansas", "St. John's (NY)"]],
       2026: [["Michigan", "Duke", "Arizona", "Iowa St."], ["UConn", "Houston", "Illinois", "Purdue"], ["Florida", "Kansas", "Nebraska", "Gonzaga"], ["Texas Tech", "Michigan St.", "Vanderbilt", "Virginia"]]}
for y, lines in T16.items():
    by = {r["key"]: r for r in D[y]}; miss = []
    for r in D[y]: r["rv_line"], r["rv_flag"] = 6.0, 0.0
    for i, L in enumerate(lines, 1):
        for t in L:
            if key(t) in by: by[key(t)]["rv_line"], by[key(t)]["rv_flag"] = float(i), 1.0
            else: miss.append(t)
    print(y, "top-16 names unmatched", miss, "| not in final field:", [r["team"] for r in D[y] if r["rv_flag"] and not r["in_field"]], flush=True)

def sel(pool, te, f):
    Xp, yp = A(pool, f), np.array([r["in_field"] for r in pool], int); sc = SS().fit(Xp); Xt = A(te, f)
    return (LR(C=.3, max_iter=3000).fit(sc.transform(Xp), yp).predict_proba(sc.transform(Xt))[:, 1] + GC(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(Xp, yp).predict_proba(Xt)[:, 1]) / 2
def pair(tf, te, f, win=16, C=.1):
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
def run(f_sel=F, f_seed=F, keep=False):
    out = {}
    for h in Y:
        tr = [r for y in Y if y != h for r in D[y]]; te = D[h]
        for r, p, m in zip(te, sel([r for r in tr if not r["champ"]], te, f_sel), pair([r for r in tr if r["in_field"]], te, f_seed)): r["_p"], r["_m"] = float(p), float(m)
        s = B.slot(sorted(B.pick_field(te, "_p"), key=lambda r: r["_m"])); out[h] = B.bm_score(s, truth(te))
        if keep:
            for r in te: r["_line"] = s.get(r["key"])
    return out
base = run(); summarize("BASE: pairwise on official order", base)
summarize("+ Top-16 reveal line and flag, seeding", run(f_seed=F + ["rv_line", "rv_flag"]), base)
summarize("+ Top-16 reveal, seeding and selection", run(f_sel=F + ["rv_line", "rv_flag"], f_seed=F + ["rv_line", "rv_flag"]), base)
run(keep=True)
print("\nPoints lost per season by true seed line: model / T-Rank / human median site")
def lost(sub, off):
    L = collections.Counter()
    for t, s in off.items():
        p = sub.get(t); L[s] += 6 - (0 if p is None else 3 + (3 if p == s else 1 if abs(p - s) == 1 else 0))
    return L
tot = {k: collections.Counter() for k in ("model", "T-Rank", "median")}
for y in Y:
    off = truth(D[y]); tot["model"] += lost({r["key"]: r["_line"] for r in D[y] if r["_line"]}, off)
    m = bm.collect(y); O = {key(t): s for t, s in m["official"].items()}
    tot["T-Rank"] += lost({key(t): s for t, s in m["submissions"]["T-Rank"].items()}, O)
    sc = {n: int(v) for n, v in m["reported"]["SCORE"].items() if v.isdigit() and n not in ("MATRIX", "")}
    med = st.median(sc.values()); near = sorted(sc, key=lambda n: abs(sc[n] - med))[:15]
    agg = collections.Counter()
    for n in near: agg += lost({key(t): s for t, s in m["submissions"][n].items()}, O)
    for k in agg: agg[k] = agg[k] / 15
    tot["median"] += collections.Counter({k: v for k, v in agg.items()})
for a, b in ((1, 4), (5, 7), (8, 9), (10, 11), (12, 13), (14, 16)):
    print(f"lines {a}-{b}", *[f"{k} {sum(tot[k][l] for l in range(a, b + 1)) / 7:.1f}" for k in tot])
print("total", *[f"{k} {sum(tot[k].values()) / 7:.1f}" for k in tot])
print("\nLargest model misses (true seed - model line). Negative = committee seeded them better.")
E = [(abs(r["seed"] - (r["_line"] or 18)), r) for y in Y for r in D[y] if r["in_field"]]
for _, r in sorted(E, key=lambda e: -e[0])[:28]:
    print(r["year"], f'{r["team"]:18} {r["lg"]:5} true {r["seed"]:2} model {r["_line"]} NET {r["net"]:3} ratingRk {r["rating_rank"]:3} WAB {r["wab"]:5.1f} Q1 {r["cq1_w"]}-{r["cq1_l"]} Q3/4L {r["cq3_l"]}/{r["cq4_l"]} rec {r["w"]}-{r["l"]} champ {int(r["champ"])}')
print("\nField misses (team left out / wrongly in)")
for y in Y:
    print(y, "OUT:", [(r["team"], r["seed"], "NET", r["net"]) for r in D[y] if r["in_field"] and not r["_line"]], " IN:", [(r["team"], "NET", r["net"]) for r in D[y] if r["_line"] and not r["in_field"]])
