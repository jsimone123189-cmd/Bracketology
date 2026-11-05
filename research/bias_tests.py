"""Do recency, program, preseason or conference effects improve the independent model? Leave-one-season-out, every test reported."""
import json, re, html, sys, collections
import numpy as np
from scipy.stats import norm
from sklearn.ensemble import GradientBoostingClassifier as GC, GradientBoostingRegressor as GR
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler as SS
from bracketology import backtest as B, history
from bracketology.features import build_year
from bracketology.http import fetch
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key

Y = B.YEARS; BASE = B.FEATS_EXT
data = {y: B.v1_proxy(build_year(y)) for y in Y}
cell = lambda r: [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]

def preseason(y):
    t = fetch(f"https://www.warrennolan.com/basketball/{y}/polls/week/2", ttl=86400 * 30)
    i, j = t.find("AP Poll</th>"), t.find("Coaches Poll</th>")
    rows = [cell(r) for r in re.split(r"<tr\b", t[i:j if j > i else None])[1:]]
    return {key(re.sub(r"\s*\(\d+\)$", "", r[1])): int(r[4]) for r in rows if len(r) >= 5 and r[0].isdigit() and r[4].isdigit()}

unmatched = {}
for y, rows in data.items():
    day = history.SELECTION_SUNDAY[y]
    ref = [r for r in rows if r["net"] <= 120]
    for n in BASE:
        v = np.array([B._f(r, n) for r in ref]); m, s = v.mean(), v.std() + 1e-9
        for r in rows: r["z_" + n] = (B._f(r, n) - m) / s
    for n in ("wab", "sor", "rating"):
        for i, r in enumerate(sorted(rows, key=lambda r: -r[n])): r["rk_" + n] = np.log(i + 1)
    by = {r["key"]: r for r in rows}
    bub = sorted((r["rating"] for r in rows), reverse=True)[44]
    hist = collections.defaultdict(list)
    for g in torvik.collect_games(y)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); mm, dd, yy = g["date"].split("/"); iso = f"20{yy}-{int(mm):02d}-{int(dd):02d}"
        if g["type"] in (0, 1, 2) and iso <= day and a in by and b in by:
            h = {"H": 3.5, "A": -3.5, "N": 0.0}[g["loc"]]
            hist[a].append((iso, float(g["win"]), float(g["win"]) - norm.cdf((bub - by[b]["rating"] + h) / 11.0), g["type"]))
    pre = {} if y == 2019 else preseason(y)
    unmatched[y] = [k for k in pre if k not in by]
    for r in rows:
        H = sorted(hist[r["key"]])
        r["last5"] = np.mean([x[1] for x in H[-5:]]) if H else 0.0
        r["recent_wab10"] = sum(x[2] for x in H[-10:])
        r["recent_share"] = r["recent_wab10"] - r["wab"] * min(10, len(H)) / max(1, len(H))
        r["ct_wins"] = sum(x[1] for x in H if x[3] == 2)
        r["pre_rank"] = pre.get(r["key"])
        r["pre_log"] = np.log(pre.get(r["key"], 60))
        r["pre_flag"] = 1.0 if r["key"] in pre else 0.0
        r["pre_top10"] = 1.0 if pre.get(r["key"], 99) <= 10 else 0.0
print("preseason names unmatched", {k: v for k, v in unmatched.items() if v}, flush=True)
for i, y in enumerate(Y):
    prev = Y[:i]
    for r in data[y]:
        hits = [next((x for x in data[p] if x["key"] == r["key"]), None) for p in prev]
        seeds = [h["seed"] for h in hits if h and h["in_field"]]
        r["prior_bid"] = len(seeds) / len(prev) if prev else 0.35
        r["prior_seed"] = np.mean(seeds) if seeds else 17.0
LGS = ["ACC", "B12", "BE", "B10", "SEC"]
for rows in data.values():
    for r in rows:
        for c in LGS: r["lg_" + c] = 1.0 if r["lg"] == c else 0.0
        r["hi_mid"] = 1.0 if r["lg"] in ("A10", "MWC", "WCC", "Amer", "MVC") else 0.0

Z = ["z_" + n for n in BASE] + ["rk_wab", "rk_sor", "rk_rating"]
A = lambda rs, f: np.array([[float(r[x]) for x in f] for r in rs])

def run(feats, seed=0, weight=None, chrono=False, years=Y, keep=False):
    out = {}
    for h in years:
        tr_years = [y for y in Y if (y < h if chrono else y != h)]
        tr = [r for y in tr_years for r in data[y]]; te = data[h]
        sw = (lambda rs: np.array([weight ** abs(h - r["year"]) for r in rs])) if weight else (lambda rs: None)
        pool = [r for r in tr if not r["champ"]]; Xp = A(pool, feats); yp = np.array([r["in_field"] for r in pool], int); sc = SS().fit(Xp)
        Xt = A(te, feats)
        p = (LogisticRegression(C=.3, max_iter=3000).fit(sc.transform(Xp), yp, sample_weight=sw(pool)).predict_proba(sc.transform(Xt))[:, 1]
             + GC(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=seed).fit(Xp, yp, sample_weight=sw(pool)).predict_proba(Xt)[:, 1]) / 2
        tf = [r for r in tr if r["in_field"]]; Xf = A(tf, feats); yf = np.array([r["seed"] for r in tf], float); s2 = SS().fit(Xf)
        m = (Ridge(alpha=10).fit(s2.transform(Xf), yf, sample_weight=sw(tf)).predict(s2.transform(Xt))
             + GR(n_estimators=150, max_depth=2, learning_rate=.05, subsample=.8, random_state=seed).fit(Xf, yf, sample_weight=sw(tf)).predict(Xt)) / 2
        for r, a, b in zip(te, p, m): r["_p"], r["_m"] = float(a), float(b)
        s = B.slot(sorted(B.pick_field(te, "_p"), key=lambda r: r["_m"]))
        out[h] = B.bm_score(s, {r["key"]: r["seed"] for r in te if r["in_field"]})
        if keep:
            for r in te: r["_line"] = s.get(r["key"])
    return out

def show(lab, res, ref=None):
    ys = list(res); sc = [res[y]["score"] for y in ys]
    d = f" vs base {np.mean(sc) - np.mean([ref[y]['score'] for y in ys]):+.1f}, better in {sum(res[y]['score'] > ref[y]['score'] for y in ys)}, worse in {sum(res[y]['score'] < ref[y]['score'] for y in ys)} of {len(ys)}" if ref else ""
    print(f"{lab:44} {sc} mean {np.mean(sc):.1f}{d}", flush=True)

base = run(Z); show("BASE (no conference flag)", base)
noise = [np.mean([v["score"] for v in run(Z, seed=s).values()]) for s in (1, 2, 3, 4)]
print("noise floor: same model, different random seed, means", np.round(noise, 1), flush=True)
print("--- recent form")
show("drop last10 entirely", run([f for f in Z if f != "z_last10"]), base)
for lab, f in (("+ last 5 win pct", ["last5"]), ("+ WAB over last 10 games", ["recent_wab10"]), ("+ recent minus season WAB pace", ["recent_share"]), ("+ conference tournament wins", ["ct_wins"])):
    show(lab, run(Z + f), base)
print("--- programs")
for lab, f in (("+ prior_bid", ["prior_bid"]), ("+ mean past seed", ["prior_seed"])):
    show(lab, run(Z + f), base)
print("--- preseason AP rank (2021-26 only, no 2019 poll)")
Y6 = [y for y in Y if y != 2019]; b6 = {y: base[y] for y in Y6}
for lab, f in (("+ preseason log rank", ["pre_log"]), ("+ preseason ranked flag", ["pre_flag"]), ("+ preseason top 10", ["pre_top10"])):
    show(lab, run(Z + f, years=Y6), b6)
print("--- conferences")
for lab, f in (("+ is_power", ["is_power"]), ("+ each power conference", ["lg_" + c for c in LGS]), ("+ league strength", ["conf_strength"]), ("+ top mid-major leagues flag", ["hi_mid"]), ("+ is_power + top mid-major flag", ["is_power", "hi_mid"])):
    show(lab, run(Z + f), base)
print("--- recent seasons count more (weight per season of distance)")
for w in (.85, .7, .5):
    show(f"season weight {w}", run(Z, weight=w), base)
Yc = [y for y in Y if y >= 2023]; bc = {y: base[y] for y in Yc}
show("train only on earlier seasons (real-life order)", run(Z, chrono=True, years=Yc), bc)
print("--- where the base model is biased (true seed minus model line; negative = committee seeded them BETTER)")
run(Z, keep=True)
G = [r for y in Y for r in data[y] if r["in_field"] and r.get("_line")]
def bias(lab, fn):
    g = [r for r in G if fn(r)]; by = collections.defaultdict(list)
    for r in g: by[r["year"]].append(r["seed"] - r["_line"])
    m = [np.mean(v) for v in by.values()]
    print(f"{lab:38} n={len(g):3} mean {np.mean([r['seed'] - r['_line'] for r in g]):+.2f}  same sign in {max(sum(x > 0 for x in m), sum(x < 0 for x in m))} of {len(m)} seasons", flush=True)
for c in LGS + ["A10", "MWC", "WCC", "Amer", "MVC"]: bias("league " + c, lambda r, c=c: r["lg"] == c)
bias("low majors", lambda r: r["lg"] not in LGS + ["A10", "MWC", "WCC", "Amer", "MVC"])
bias("won league tournament, power", lambda r: r["champ"] and r["is_power"])
bias("did not win league tournament, power", lambda r: not r["champ"] and r["is_power"])
bias("last 10: 9+ wins", lambda r: r["last10"] >= .9)
bias("last 10: 5 or fewer wins", lambda r: r["last10"] <= .5)
bias("preseason top 10", lambda r: r["pre_top10"] == 1)
bias("preseason ranked", lambda r: r["pre_flag"] == 1)
bias("preseason unranked, at-large", lambda r: r["pre_flag"] == 0 and not r["champ"] and r["year"] != 2019)
bias("made field 2+ of prior seasons", lambda r: r["prior_bid"] >= .5 and r["year"] >= 2022)
bias("no prior bids, at-large", lambda r: r["prior_bid"] == 0 and not r["champ"] and r["year"] >= 2022)
for name in ("duke", "kansas", "kentucky", "northcarolina", "gonzaga", "michiganstate", "villanova", "ucla", "uconn", "houston", "purdue", "saintmarysca", "memphis", "sandiegostate"):
    bias("team " + name, lambda r, n=name: r["key"] == n)
