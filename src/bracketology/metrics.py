from __future__ import annotations
"""Our own as-of-date resume/strength metrics rebuilt from game results (SOR/KPI/historic WAB are not freely available).
- rating: ridge margin model (Massey with home-court term), margins capped at +/-20.
- wab: wins above a bubble-level team (rating of the 45th-best team) over the same schedule.
- sor: P(an average top-25 team would do at least as well) -> reported as -log10 (bigger = better).
Only games on/before the cutoff date are used -> no leakage."""
import math
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import Ridge
from scipy.stats import norm
from . import quads

SIGMA = 11.0; HCA_FIT = True

def _games(games, keys, day):
    seen, out = set(), []
    for g in games:
        if g["type"] not in (0, 1, 2) or g["date_iso"] > day: continue
        a, b = g["team_key"], g["opp_key"]
        if a not in keys or b not in keys: continue
        sig = (g["date_iso"],) + tuple(sorted((a, b)))
        if sig in seen: continue
        seen.add(sig); out.append(g)
    return out

def compute(games: list[dict], net_rank: dict[str, int], day: str) -> dict[str, dict]:
    keys = {k: i for i, k in enumerate(net_rank)}
    G = _games(games, keys, day)
    n, m = len(keys), len(G)
    rows, cols, vals, y = [], [], [], []
    for r, g in enumerate(G):
        i, j = keys[g["team_key"]], keys[g["opp_key"]]
        h = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]
        rows += [r, r, r]; cols += [i, j, n]; vals += [1.0, -1.0, h]
        y.append(max(-20, min(20, g["pf"] - g["pa"])))
    X = csr_matrix((vals, (rows, cols)), shape=(m, n + 1))
    mdl = Ridge(alpha=3.0, fit_intercept=False).fit(X, np.array(y))
    r = mdl.coef_[:n]; hca = float(mdl.coef_[n])
    inv = {i: k for k, i in keys.items()}
    order = np.sort(r)[::-1]
    bubble, top25 = order[44], order[:25].mean()
    per = {k: {"wins_exp_bub": 0.0, "w": 0, "l": 0, "p25": [], "opp": [], "rw": 0, "nw": 0, "hist": [], "bestw": []} for k in keys}
    q = quads.records([g for g in games if g["date_iso"] <= day], net_rank)  # both orientations, vs D-I opp only
    for g in games:
        if g["type"] not in (0, 1, 2) or g["date_iso"] > day: continue
        a, b = g["team_key"], g["opp_key"]
        if a not in keys or b not in keys: continue
        h = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]
        d = per[a]
        d["w" if g["win"] else "l"] += 1
        pb = norm.cdf((bubble - r[keys[b]] + h * hca) / SIGMA)
        d["wins_exp_bub"] += pb
        d["opp"].append(r[keys[b]])
        if g["win"]:
            d["bestw"].append(r[keys[b]] - h * hca)       # location-adjusted quality of the win
            if g["loc"] == "A": d["rw"] += 1
            if g["loc"] == "N": d["nw"] += 1
        d["hist"].append((g["date_iso"], g["win"]))
        d["p25"].append(norm.cdf((top25 - r[keys[b]] + h * hca) / SIGMA))
    out = {}
    for k, d in per.items():
        w = d["w"]; ps = d["p25"]
        # Poisson-binomial P(W >= w) for an average top-25 team
        dist = np.zeros(len(ps) + 1); dist[0] = 1.0
        for p in ps:
            dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p; dist[0] *= (1 - p)
        sor = float(dist[w:].sum()) if ps else 1.0
        h10 = [w for _, w in sorted(d["hist"])[-10:]]
        bw = sorted(d["bestw"], reverse=True)[:3]
        out[k] = {"sos": float(np.mean(d["opp"])) if d["opp"] else 0.0, "road_w": d["rw"], "neutral_w": d["nw"],
                  "last10": sum(h10) / max(1, len(h10)), "best3": float(np.mean(bw)) if bw else 0.0,
                  "rating": float(r[keys[k]]), "rating_rank": int((r > r[keys[k]]).sum()) + 1,
                  "wab": w - d["wins_exp_bub"], "sor": -math.log10(max(sor, 1e-9)),
                  "q1a_w": q.get(k, {}).get("q1A_w", 0), "q1a_l": q.get(k, {}).get("q1A_l", 0),
                  "cq1_w": q.get(k, {}).get("q1A_w", 0) + q.get(k, {}).get("q1B_w", 0),
                  "cq1_l": q.get(k, {}).get("q1A_l", 0) + q.get(k, {}).get("q1B_l", 0),
                  "cq2_w": q.get(k, {}).get("q2_w", 0), "cq2_l": q.get(k, {}).get("q2_l", 0),
                  "cq3_l": q.get(k, {}).get("q3_l", 0), "cq4_l": q.get(k, {}).get("q4_l", 0)}
    return out
