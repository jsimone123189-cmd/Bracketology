from __future__ import annotations
"""Game results from ncaa.com via the ncaa-api wrapper, one request per date. Reachable from GitHub Actions, unlike Torvik.
Limit: the feed labels home and away but has no neutral-site flag, so neutral games appear as home/away. Team-game rows match torvik.collect_games."""
import json
from datetime import date, timedelta
from ..http import fetch

def url(d: date) -> str:
    return f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{d.year}/{d.month:02d}/{d.day:02d}/all-conf"

def day_rows(d: date, ttl: int) -> list[dict]:
    try:
        data = json.loads(fetch(url(d), ttl=ttl, retries=2))
    except Exception:
        return []
    rows = []
    for g in data.get("games", []):
        g = g["game"]
        if g.get("gameState") != "final": continue
        h, a = g["home"], g["away"]
        try: hs, aw = int(h["score"]), int(a["score"])
        except (TypeError, ValueError): continue
        if hs == aw: continue
        hc = (h.get("conferences") or [{}])[0].get("conferenceSeo", ""); ac = (a.get("conferences") or [{}])[0].get("conferenceSeo", "")
        typ = 1 if hc and hc == ac else 0
        ds = f"{d.month}/{d.day}/{d.year % 100}"
        rows.append({"date": ds, "type": typ, "team": h["names"]["short"], "conf": hc, "opp": a["names"]["short"], "loc": "H", "win": hs > aw, "pf": hs, "pa": aw, "id": g["gameID"]})
        rows.append({"date": ds, "type": typ, "team": a["names"]["short"], "conf": ac, "opp": h["names"]["short"], "loc": "A", "win": aw > hs, "pf": aw, "pa": hs, "id": g["gameID"]})
    return rows

def collect(start: date, end: date, ttl: int = 86400 * 30) -> dict:
    rows, d = [], start
    while d <= end:
        rows += day_rows(d, ttl); d += timedelta(days=1)
    return {"source": "ncaa_games", "rows": rows}

def venue(game_id: str, ttl: int = 86400 * 365) -> str | None:
    """Arena for one game. Past games never change, so these stay cached."""
    try:
        c = json.loads(fetch(f"https://ncaa-api.henrygd.me/game/{game_id}", ttl=ttl, retries=2))["contests"][0]
        return (c.get("location") or {}).get("venue")
    except Exception:
        return None

def mark_neutral(rows: list[dict], venues: dict[str, str | None]) -> list[dict]:
    """The feed has no neutral flag. A game is neutral when it isn't in an arena the labelled home team regularly hosts in.
    Regular = at least 3 home-labelled games there, or that team's most used arena. Unknown arena keeps the feed's home/away label."""
    use = {}
    for g in rows:
        if g["loc"] == "H" and venues.get(g["id"]): use.setdefault(g["team"], {}).setdefault(venues[g["id"]], set()).add(g["id"])
    regular = {}
    for t, v in use.items():
        top = max(len(x) for x in v.values())
        regular[t] = {a for a, x in v.items() if len(x) >= 3 or len(x) == top}
    home = {g["id"]: g["team"] for g in rows if g["loc"] == "H"}
    for g in rows:
        a = venues.get(g["id"])
        if a and a not in regular.get(home[g["id"]], {a}): g["loc"] = "N"
    return rows

def season_games(season: int, today: date, universe: set[str], key, cache_dir: str = "data/output/gamecache", end: date | None = None) -> list[dict]:
    """All results so far, with neutral sites marked. Keeps a season file so each run only requests recent dates and new arenas."""
    import copy, os
    path = f"{cache_dir}/{season}.json"; store = {"rows": [], "venues": {}, "through": None}
    if os.path.exists(path): store = json.load(open(path))
    first = date(season - 1, 11, 1); last = min(today, end) if end else today
    start = max(first, date.fromisoformat(store["through"]) - timedelta(days=2)) if store["through"] else first
    keep = {}
    for g in store["rows"]: keep[(g["id"], g["team"])] = g
    d = start
    while d <= last:
        for g in day_rows(d, 600): keep[(g["id"], g["team"])] = g
        d += timedelta(days=1)
    rows = list(keep.values())
    for i in sorted({g["id"] for g in rows if key(g["team"]) in universe and key(g["opp"]) in universe} - set(store["venues"])):
        store["venues"][i] = venue(i)
    store.update(rows=rows, through=last.isoformat())
    os.makedirs(cache_dir, exist_ok=True); json.dump(store, open(path, "w"), separators=(",", ":"))
    return mark_neutral(copy.deepcopy(rows), store["venues"])
