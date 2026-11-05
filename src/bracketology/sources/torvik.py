from __future__ import annotations
"""Bart Torvik T-Rank team table + game log. Only the CSV endpoints (robots.txt allows; Crawl-Delay 10 honored in http.py).
Attribute barttorvik.com on the site. Do not use .json or time-machine pages (disallowed by robots.txt)."""
import csv, io
from ..http import fetch

def team_url(year): return f"https://barttorvik.com/{year}_team_results.csv"
def games_url(year): return f"https://barttorvik.com/getgamestats.php?year={year}&csv=1"

def collect_teams(year: int, ttl: int = 3600) -> dict:
    rdr = csv.DictReader(io.StringIO(fetch(team_url(year), ttl=ttl)))
    rows = []
    for r in rdr:
        def f(k):
            try: return float(r[k])
            except (KeyError, ValueError): return None
        rows.append({"team": r["team"], "conf": r["conf"], "record": r["record"], "trank": int(r["rank"]),
                     "adjoe": f("adjoe"), "adjde": f("adjde"), "barthag": f("barthag"),
                     "wab": f("WAB"), "wab_rank": f("WAB Rk"), "sos": f("sos"), "ncsos": f("ncsos"), "adjt": f("adjt")})
    return {"source": "torvik_teams", "year": year, "url": team_url(year), "rows": rows}

def collect_games(year: int, ttl: int = 3600) -> dict:
    """One row per team-game (each game appears twice, once per side). Cols: date,type,team,conf,opp,loc,result,..."""
    rows = []
    for r in csv.reader(io.StringIO(fetch(games_url(year), ttl=ttl))):
        if len(r) < 7 or r[5] not in ("H", "A", "N"):
            continue
        res = r[6]  # e.g. "W, 96-62"
        wl, score = res.split(", ")
        hi, lo = (int(x) for x in score.split("-"))   # score is listed winner-first
        pf, pa = (hi, lo) if wl == "W" else (lo, hi)
        rows.append({"date": r[0], "type": int(r[1]), "team": r[2], "conf": r[3], "opp": r[4], "loc": r[5],
                     "win": wl == "W", "pf": pf, "pa": pa})
    return {"source": "torvik_games", "year": year, "url": games_url(year), "rows": rows}
