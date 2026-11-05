from __future__ import annotations
"""NCAA NET rankings + combined quadrant records via the open-source ncaa-api wrapper of ncaa.com.
Unofficial wrapper (5 req/s public limit). Fallback: self-host it (github.com/henrygd/ncaa-api)."""
import json
from ..http import fetch

URL = "https://ncaa-api.henrygd.me/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings"
REQUIRED = {"Rank", "School", "Record", "Quad 1", "Quad 2", "Quad 3", "Quad 4"}

def _wl(s: str) -> tuple[int, int]:
    w, l = s.split("-")
    return int(w), int(l)

def collect(url: str = URL, ttl: int = 3600) -> dict:
    d = json.loads(fetch(url, ttl=ttl))
    rows = []
    for r in d["data"]:
        miss = REQUIRED - r.keys()
        if miss:
            raise ValueError(f"NET row missing {miss}: {r}")
        row = {"team": r["School"], "net": int(r["Rank"]), "record": r["Record"], "conf": r.get("Conf")}
        for q in ("1", "2", "3", "4"):
            row[f"q{q}_w"], row[f"q{q}_l"] = _wl(r[f"Quad {q}"])
        rows.append(row)
    return {"source": "ncaa_net", "asof": d.get("updated"), "url": url, "rows": rows}
