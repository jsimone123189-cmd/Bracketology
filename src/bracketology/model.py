from __future__ import annotations
"""V2 independent model. Field: logistic + boosting on at-large teams. Seeds: pairwise ranking trained on the committee's
published overall seed order. Uses only pre-selection stats and the known auto-bids; no other bracketologists' picks.
LOSO reference on 68-team seasons: 335 326 347 344 329 363 356, mean 342.9 (see docs/06)."""
import json
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from . import fieldformat

BASE = ["net_log", "wab", "sor", "rating", "q1a_w", "cq1_w", "cq3_l", "cq4_l", "win_pct", "sos", "road_w", "neutral_w",
        "last10", "best3", "cq2_w", "cq1_l"]
SELECT = ["z_" + n for n in BASE] + ["rk_wab", "rk_sor", "rk_rating", "is_power"]
SEED = SELECT + ["q1_games", "few_q1", "q1w_power", "net_nonpower"]

def _value(r: dict, n: str) -> float:
    if n == "net_log": return float(np.log(r["net"]))
    if n == "win_pct": return r["w"] / max(1, r["w"] + r["l"])
    return float(r[n])

def prepare(rows: list[dict]) -> list[dict]:
    """Season-relative features. Must be applied to one season's D-I rows at a time."""
    ref = [r for r in rows if r["net"] <= 120] or rows
    for n in BASE:
        v = np.array([_value(r, n) for r in ref]); m, s = v.mean(), v.std() + 1e-9
        for r in rows: r["z_" + n] = (_value(r, n) - m) / s
    for n in ("wab", "sor", "rating"):
        for i, r in enumerate(sorted(rows, key=lambda r: -r[n])): r["rk_" + n] = float(np.log(i + 1))
    for r in rows:
        g = r["cq1_w"] + r["cq1_l"]
        r["q1_games"], r["few_q1"] = float(g), 1.0 if g <= 3 else 0.0
        r["q1w_power"], r["net_nonpower"] = r["cq1_w"] * r["is_power"], float(np.log(r["net"])) * (1 - r["is_power"])
    return rows

def attach_overall(rows: list[dict], season: int, path="data/history/scurve.json") -> list[dict]:
    seq = json.load(open(path))[str(season)]; seeds = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    if seeds[seq[-1]] <= 2: seq = [seq[-1]] + seq[:-1]      # one source article's header pushed the top team to the end
    pos = {k: i + 1 for i, k in enumerate(seq)}
    for r in rows: r["ov"] = pos.get(r["key"])
    return rows

def _X(rows, feats): return np.array([[float(r[f]) for f in feats] for r in rows])

class Model:
    def fit(self, train: list[dict], window: int = 16):
        pool = [r for r in train if not r["champ"]]
        X, y = _X(pool, SELECT), np.array([r["in_field"] for r in pool], int)
        self.s_sel = StandardScaler().fit(X)
        self.lr = LogisticRegression(C=.3, max_iter=3000).fit(self.s_sel.transform(X), y)
        self.gb = GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(X, y)
        field = [r for r in train if r["in_field"]]; self.s_seed = StandardScaler().fit(_X(field, SEED)); dX, dy = [], []
        seasons = {}
        for r in field: seasons.setdefault(r["year"], []).append(r)
        for rs in seasons.values():
            Z = self.s_seed.transform(_X(rs, SEED))
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    d = rs[i]["ov"] - rs[j]["ov"]
                    if d and abs(d) <= window: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
        self.rank = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int))
        return self

    def score(self, rows: list[dict]) -> list[dict]:
        X = _X(rows, SELECT)
        p = (self.lr.predict_proba(self.s_sel.transform(X))[:, 1] + self.gb.predict_proba(X)[:, 1]) / 2
        q = self.s_seed.transform(_X(rows, SEED)) @ self.rank.coef_[0]
        for r, a, b in zip(rows, p, q): r["p_in"], r["rank_score"] = float(a), float(b)
        return rows

def choose_field(rows: list[dict], season: int, project_autos: bool = True) -> tuple[list[dict], list[dict]]:
    """Auto-bids first: real champions, else each unfinished league's top team (independents get none).
    Remaining bids go to at-large by p_in. Set project_autos=False once every league is decided, as in backtests."""
    size = fieldformat.field_size(season)
    done = {r.get("lg") for r in rows if r["champ"]}; autos = [r for r in rows if r["champ"]]; proj = {}
    for r in rows:
        lg = r.get("lg")
        if project_autos and lg and lg.lower() not in ("ind", "independent", "independents", "di-independent") and lg not in done and r.get("eligible", True) and (lg not in proj or r["rank_score"] > proj[lg]["rank_score"]): proj[lg] = r
    ids = {r["key"] for r in autos}
    for r in proj.values(): r["projected_auto"] = True; ids.add(r["key"])
    autos = autos + list(proj.values())
    pool = sorted((r for r in rows if r["key"] not in ids), key=lambda r: -r["p_in"])
    n = size - len(autos)
    return autos + pool[:n], pool[n:]

def assign_lines(field: list[dict], season: int) -> list[dict]:
    order = sorted(field, key=lambda r: -r["rank_score"]); lines = fieldformat.slot_lines(season)
    for i, r in enumerate(order): r["overall"], r["line"] = i + 1, lines[i]
    return order
