from __future__ import annotations
"""Game results from ncaa.com via the ncaa-api wrapper, one request per date. Reachable from GitHub Actions, unlike Torvik.
Limit: the feed labels home and away but has no neutral-site flag, so neutral games appear as home/away. Team-game rows match torvik.collect_games."""
import json
from datetime import date, timedelta
from ..http import fetch

def url(d: date) -> str:
    return f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{d.year}/{d.month:02d}/{d.day:02d}/all-conf"

MAX_STRAIGHT_FAILURES = 5      # stop asking during an outage; whatever is left stays on the retry list for the next run

def day_rows(d: date, ttl: int) -> list[dict]:
    try:
        return fetch_day(d, ttl)
    except Exception:
        return []

def fetch_day(d: date, ttl: int) -> list[dict]:
    """Raises when the date could not be read. A date with no games returns an empty list."""
    data = json.loads(fetch(url(d), ttl=ttl, retries=2))
    if "games" not in data: raise ValueError(f"no games list for {d}")
    rows = []
    for g in data["games"]:
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
    """Arena for one game. Past games never change, so these stay cached. None means the lookup failed; "" means the game lists no arena."""
    try:
        c = json.loads(fetch(f"https://ncaa-api.henrygd.me/game/{game_id}", ttl=ttl, retries=2))["contests"][0]
        return (c.get("location") or {}).get("venue") or ""
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

def season_games(season: int, today: date, universe: set[str], key, cache_dir: str = "data/output/gamecache", end: date | None = None, warn: list[str] | None = None) -> list[dict]:
    """All results so far, with neutral sites marked. Keeps a season file so each run only requests recent dates, new arenas and anything that failed before.
    A file saved before failures were tracked may have gaps, so it gets one full refetch."""
    import copy, os
    warn = warn if warn is not None else []
    path = f"{cache_dir}/{season}.json"; store = {"rows": [], "venues": {}, "through": None}
    if os.path.exists(path): store = json.load(open(path))
    tracked = "missing_days" in store
    first = date(season - 1, 11, 1); last = min(today, end) if end else today
    start = max(first, date.fromisoformat(store["through"]) - timedelta(days=2)) if store["through"] and tracked else first
    keep = {}
    for g in store["rows"]: keep[(g["id"], g["team"])] = g
    days = {date.fromisoformat(s) for s in store.get("missing_days", [])}
    d = start
    while d <= last:
        days.add(d); d += timedelta(days=1)
    missing, straight = [], 0
    for d in sorted(days):
        if straight >= MAX_STRAIGHT_FAILURES: missing.append(d.isoformat()); continue
        try:
            for g in fetch_day(d, 600): keep[(g["id"], g["team"])] = g
            straight = 0
        except Exception:
            missing.append(d.isoformat()); straight += 1
    rows = list(keep.values())
    venues = {i: v for i, v in store["venues"].items() if v is not None}
    wanted = sorted({g["id"] for g in rows if key(g["team"]) in universe and key(g["opp"]) in universe} - set(venues))
    straight = 0; lost = []
    for i in wanted:
        v = venue(i) if straight < MAX_STRAIGHT_FAILURES else None
        if v is None: lost.append(i); straight += 1
        else: venues[i] = v; straight = 0
    if missing: warn.append(f"Game results missing for {len(missing)} dates, {missing[0]} to {missing[-1]}. Will retry next run.")
    if lost: warn.append(f"Arena unknown for {len(lost)} games, so they keep the feed's home/away label. Will retry next run.")
    store.update(rows=rows, venues=venues, through=last.isoformat(), missing_days=missing)
    os.makedirs(cache_dir, exist_ok=True); json.dump(store, open(path, "w"), separators=(",", ":"))
    return mark_neutral(copy.deepcopy(rows), venues)
