from __future__ import annotations
"""Leak-free training table: one row per D-I team per season, features as of Selection Sunday, labels from the real field."""
import json
from . import history
from .teams import TeamIndex, key
from .sources import bracketmatrix as bm, torvik

def _d(s):  # 'm/d/yy' -> iso
    m, d, y = s.split("/"); return f"20{y}-{int(m):02d}-{int(d):02d}"

def conf_champions(games: list[dict], day: str) -> dict[str, str]:
    """Winner of the last conference-tournament game (type 2) played on/before Selection Sunday, per conference."""
    last = {}
    for g in games:
        if g["type"] == 2 and g["win"] and _d(g["date"]) <= day:
            if g["conf"] not in last or _d(g["date"]) >= last[g["conf"]][0]:
                last[g["conf"]] = (_d(g["date"]), g["team"])
    return {c: t for c, (_, t) in last.items()}

def build_year(year: int, hist="data/history") -> tuple[list[dict], dict]:
    day = history.SELECTION_SUNDAY[year]
    net = json.load(open(f"{hist}/{year}_net.json"))["rows"]
    try: tr = {key(r["team"]): r for r in json.load(open(f"{hist}/{year}_trank.json"))["rows"]}
    except FileNotFoundError: tr = {}
    idx = TeamIndex([r["team"] for r in net])
    games = torvik.collect_games(year)["rows"]
    champs = {key(t) for t in conf_champions(games, day).values()}
    m = bm.collect(year); seeds = {key(t): s for t, s in m["official"].items()}
    rep = {"year": year, "unmatched_matrix": idx.unmatched(m["official"]), "unmatched_champs": idx.unmatched(
        conf_champions(games, day).values())}
    rows = []
    for r in net:
        k = key(r["team"]); t = tr.get(k)
        rows.append({**r, "year": year, "key": k, "champ": k in champs, "in_field": k in seeds, "seed": seeds.get(k),
                     "barthag": t["barthag"] if t else None, "trank": t["trank"] if t else None})
    rep["field_n"] = sum(r["in_field"] for r in rows); rep["champ_in_field"] = sum(r["champ"] and r["in_field"] for r in rows)
    rep["n_champs"] = sum(r["champ"] for r in rows)
    return rows, rep
