from __future__ import annotations
"""Backtest using REAL committee metrics (archived Torvik team sheets) on the seasons where a near-cutoff capture exists.
Configurations are fixed up front, every one is reported, nothing is selected on the held-out score."""
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from .backtest import pick_field, slot, _s
from .features import build_year
from .sources import bracketmatrix as bm, torvik_sheets

SEASONS = (2021, 2022, 2023, 2025)
RANKS = ["r_net", "r_kpi", "r_sor", "r_bpi", "r_kp"]
RECORD = ["q1a_w", "cq1_w", "cq1_l", "cq2_w", "cq3_l", "cq4_l"]
MISSING_RANK = 300

def load(y):
    rows = build_year(y)
    S = torvik_sheets.parse(open(f"data/raw/teamsheets/{y}.html", errors="replace").read())
    wr = {r["key"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r["wab"]))}
    for r in rows:
        d = S.get(r["key"], {})
        for c in RANKS:
            r[c] = d.get(c, MISSING_RANK)
        r["r_wab"] = d.get("r_wab", wr[r["key"]])   # official only in 2025; otherwise our rebuilt WAB rank
        r["own_wab_rank"] = wr[r["key"]]
    return rows

def v1_score(r):
    return (r["q1a_w"]*.15 + r["cq1_w"]*.13 + r["cq2_w"]*.12 - r["cq3_l"]*.5 - r["cq4_l"]*1.5
            + .24*_s(r["r_wab"]) + .19*_s(r["r_sor"]) + .17*_s(r["r_net"]) + .10*_s(r["r_kp"]))

def X(rows, ranks, power=True):
    return np.array([[np.log(r[c]) for c in ranks] + [float(r[c]) for c in RECORD] + ([r["is_power"]] if power else [])
                     for r in rows])

def fit_predict(train, test, ranks, gbm):
    pool = [r for r in train if not r["champ"]]
    Xp, yp = X(pool, ranks), np.array([r["in_field"] for r in pool], int)
    Xt = X(test, ranks); sc = StandardScaler().fit(Xp)
    p = LogisticRegression(C=0.3, max_iter=3000).fit(sc.transform(Xp), yp).predict_proba(sc.transform(Xt))[:, 1]
    tf = [r for r in train if r["in_field"]]
    Xf, yf = X(tf, ranks), np.array([r["seed"] for r in tf], float); s2 = StandardScaler().fit(Xf)
    mu = Ridge(alpha=10).fit(s2.transform(Xf), yf).predict(s2.transform(Xt))
    if gbm:
        p = (p + GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8,
                                            random_state=0).fit(Xp, yp).predict_proba(Xt)[:, 1]) / 2
        mu = (mu + GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=.05, subsample=.8,
                                             random_state=0).fit(Xf, yf).predict(Xt)) / 2
    return p, mu

def bracket(test, fkey, skey):
    return slot(sorted(pick_field(test, fkey), key=lambda r: r[skey]))

def run():
    data = {y: load(y) for y in SEASONS}
    out = {}
    for hold in SEASONS:
        train = [r for y in SEASONS if y != hold for r in data[y]]
        test = data[hold]
        truth = {r["key"]: r["seed"] for r in test if r["in_field"]}
        for r in test:
            r["v1r"] = v1_score(r); r["nv1"] = -r["v1r"]
        cfg = {"V1 formula on real metrics": bracket(test, "v1r", "nv1")}
        for name, ranks, gbm in (("Ridge/logistic, real metrics", RANKS + ["r_wab"], False),
                                 ("Ensemble, real metrics", RANKS + ["r_wab"], True)):
            p, mu = fit_predict(train, test, ranks, gbm)
            for r, a, b in zip(test, p, mu):
                r["_p"], r["_m"] = a, b
            cfg[name] = bracket(test, "_p", "_m")
        for name, s in cfg.items():
            out.setdefault(name, {})[hold] = bm.score(s, truth)
    return out

if __name__ == "__main__":
    res = run()
    for n, d in res.items():
        print(f"{n:32}", {y: d[y]["score"] for y in SEASONS}, "mean", round(np.mean([d[y]["score"] for y in SEASONS]), 1),
              "picked", round(np.mean([d[y]["picked"] for y in SEASONS]), 1), "exact", round(np.mean([d[y]["exact"] for y in SEASONS]), 1))
