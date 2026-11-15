from __future__ import annotations
"""Anchor-CT (docs/40), a 2027 shadow candidate. Not used by production.
Seeding uses each team's pre-conference-tournament résumé: every game-derived feature is computed from games before the
team's own league tournament began. NET (official, current), champion status and field selection stay current.
Frozen at docs/40's commit. Exploratory result -5.1: NOT recommended as a shadow (docs/40). Kept for the record."""
from datetime import date, timedelta
from . import metrics

def annotate(games: list[dict], key) -> list[dict]:
    for g in games:
        if "date_iso" not in g:
            g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, d, y = g["date"].split("/"); g["date_iso"] = f"20{y}-{int(m):02d}-{int(d):02d}"
    return games

def tournament_starts(games: list[dict], day: str) -> dict[str, str]:
    """League code -> date of its first conference-tournament game on or before `day`."""
    out = {}
    for g in games:
        if g["type"] == 2 and g["date_iso"] <= day and g.get("conf"):
            out[g["conf"]] = min(out.get(g["conf"], "9999-99-99"), g["date_iso"])
    return out

def anchored_rows(rows: list[dict], games: list[dict], day: str) -> list[dict]:
    """Copies of `rows` (which carry final NET, champion status and league `lg`) with game-derived features recomputed
    from games before each team's league tournament. Teams whose league has no tournament games use `day`."""
    starts = tournament_starts(games, day)
    cut = {lg: (date.fromisoformat(s) - timedelta(days=1)).isoformat() for lg, s in starts.items()}
    net = {r["key"]: r["net"] for r in rows}; cache = {}
    out = []
    for r in rows:
        c = cut.get(r.get("lg"), day)
        if c not in cache: cache[c] = metrics.compute(games, net, c)
        n = dict(r); n.update(cache[c].get(r["key"], {})); n["anchor_cutoff"] = c; out.append(n)
    return out
