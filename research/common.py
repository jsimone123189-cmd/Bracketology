"""Shared setup for research scripts. Leave-one-season-out; older seasons are training-only (no NET existed, own rating rank stands in)."""
import collections, json, os
import numpy as np
from bracketology import backtest as B, metrics
from bracketology.dataset import conf_champions, _d
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key

Y = B.YEARS; BASE = B.FEATS_EXT
Z = ["z_" + n for n in BASE] + ["rk_wab", "rk_sor", "rk_rating"]
OLD = {2014: "2014-03-16", 2015: "2015-03-15", 2016: "2016-03-13", 2017: "2017-03-12", 2018: "2018-03-11"}
POWER = ("ACC", "B12", "BE", "B10", "SEC", "P12", "pac12", "P10")

def finish(rows, games, day):
    """Adds z-scores, log ranks, conference tournament wins, and auto-bid/at-large context."""
    by = {r["key"]: r for r in rows}; ct = collections.Counter()
    for g in games:
        if g["type"] == 2 and g["win"] and _d(g["date"]) <= day and key(g["team"]) in by: ct[key(g["team"])] += 1
    ref = [r for r in rows if r["net"] <= 120]
    for r in rows: r["ct_wins"] = float(ct[r["key"]])
    for n in BASE:
        v = np.array([B._f(r, n) for r in ref]); m, s = v.mean(), v.std() + 1e-9
        for r in rows: r["z_" + n] = (B._f(r, n) - m) / s
    for n in ("wab", "sor", "rating"):
        for i, r in enumerate(sorted(rows, key=lambda r: -r[n])): r["rk_" + n] = np.log(i + 1)
    for r in rows: r["q12_w"] = float(r["cq1_w"] + r["cq2_w"]); r["q1_rate"] = r["cq1_w"] / max(1, r["cq1_w"] + r["cq1_l"])
    return rows

def old_year(y, cache="data/features"):
    path = f"{cache}/old_{y}.json"
    if os.path.exists(path): return json.load(open(path))
    day = OLD[y]; games = torvik.collect_games(y)["rows"]; m = bm.collect(y)
    names = sorted({g["team"] for g in games if g["type"] in (0, 1)}); keys = {key(n): n for n in names}
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); a, b, c = g["date"].split("/"); g["date_iso"] = f"20{c}-{int(a):02d}-{int(b):02d}"
    M0 = metrics.compute(games, {k: 100 for k in keys}, day)
    rank = {k: M0[k]["rating_rank"] for k in keys}; M = metrics.compute(games, rank, day)
    seeds = {key(t): s for t, s in m["official"].items()}
    champs = {key(t) for t in conf_champions(games, day).values()}
    lg = {}
    for g in games: lg.setdefault(g["team_key"], g["conf"])
    rows = []
    for k, n in keys.items():
        rec = M[k]; w = sum(1 for g in games if g["team_key"] == k and g["type"] in (0, 1, 2) and g["date_iso"] <= day and g["win"]); l = sum(1 for g in games if g["team_key"] == k and g["type"] in (0, 1, 2) and g["date_iso"] <= day and not g["win"])
        rows.append({"team": n, "key": k, "year": y, "net": rank[k], "w": w, "l": l, "champ": k in champs, "in_field": k in seeds, "seed": seeds.get(k), "lg": lg.get(k, ""), "is_power": 1.0 if lg.get(k) in POWER else 0.0, "conf_strength": 0.0, **{a: float(b) for a, b in rec.items()}})
    miss = [t for t in seeds if t not in keys]
    print(y, "teams", len(rows), "field matched", sum(r["in_field"] for r in rows), "unmatched", [t for t, s in m["official"].items() if key(t) not in keys], "champs", len(champs), "champs not in field", [r["team"] for r in rows if r["champ"] and not r["in_field"]], flush=True)
    os.makedirs(cache, exist_ok=True); json.dump(rows, open(path, "w")); return rows

def load(old=()):
    d = {}
    for y in Y:
        rows = build_year(y); finish(rows, torvik.collect_games(y)["rows"], __import__("bracketology.history").history.SELECTION_SUNDAY[y]); d[y] = rows
    for y in old:
        rows = old_year(y); finish(rows, torvik.collect_games(y)["rows"], OLD[y]); d[y] = rows
    return d

def A(rows, f): return np.array([[float(r[x]) for x in f] for r in rows])
def truth(rows): return {r["key"]: r["seed"] for r in rows if r["in_field"]}
def summarize(lab, res, ref=None):
    ys = sorted(res); sc = [res[y]["score"] for y in ys]
    d = ""
    if ref:
        d = f"  vs base {np.mean(sc) - np.mean([ref[y]['score'] for y in ys]):+.1f}  better {sum(res[y]['score'] > ref[y]['score'] for y in ys)} worse {sum(res[y]['score'] < ref[y]['score'] for y in ys)}"
    print(f"{lab:46} {sc} mean {np.mean(sc):.1f} picked {np.mean([res[y]['picked'] for y in ys]):.1f} exact {np.mean([res[y]['exact'] for y in ys]):.1f}{d}", flush=True)
