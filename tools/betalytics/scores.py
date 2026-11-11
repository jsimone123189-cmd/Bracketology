"""Match Betalytics NCAAB games to ESPN final scores.

Input (JSON file): {"games": [{"id", "t" (ISO tip time), "h": {"n", "s", "a"}, "a": {...}}]}
  n = full name, s = short name, a = abbreviation (as Betalytics gives them).
Output (stdout JSON): {"scores": {game_id: {"hs", "as", "espn"}}, "unmatched": [ids], "pending": [ids]}
  hs/as are the Betalytics home/away teams' final points (oriented by team, so
  neutral-site games where ESPN lists the teams the other way round still grade right).

Usage: python3 scores.py games.json > scores.json
Only uses ESPN's public scoreboard; no Betalytics access.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

ESPN = ("https://site.api.espn.com/apis/site/v2/sports/basketball/"
        "mens-college-basketball/scoreboard")
ALIASES = {"state": "st", "saint": "st", "university": "", "univ": "", "the": "",
           "and": "", "&": "", "mount": "mt", "fort": "ft"}


def norm(s):
    s = re.sub(r"[^a-z0-9& ]+", " ", (s or "").lower().replace("'", ""))
    return " ".join(ALIASES.get(w, w) for w in s.split() if ALIASES.get(w, w))


def keys(team):
    """Name forms a team can be recognized by."""
    out = set()
    for f in team:
        if f:
            out.add(norm(f))
    return {k for k in out if k}


def espn_keys(t):
    return keys([t.get("displayName"), t.get("shortDisplayName"), t.get("location"),
                 t.get("abbreviation"), t.get("name") and f"{t.get('location')} {t['name']}"])


def bl_keys(side):
    return keys([side.get("n"), side.get("s"), side.get("a"), side.get("k")])


def fetch_day(day, session):
    r = session.get(ESPN, params={"dates": day.strftime("%Y%m%d"), "groups": 50,
                                  "limit": 500}, timeout=30)
    r.raise_for_status()
    events = []
    for e in r.json().get("events", []):
        comp = e["competitions"][0]
        teams = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in teams or "away" not in teams:
            continue
        events.append({
            "id": e["id"],
            "t": datetime.fromisoformat(e["date"].replace("Z", "+00:00")),
            "final": comp["status"]["type"].get("completed", False),
            "teams": [(espn_keys(c["team"]), int(c.get("score") or 0))
                      for c in (teams["home"], teams["away"])],
        })
    return events


def match(game, events):
    tip = datetime.fromisoformat(game["t"].replace("Z", "+00:00"))
    hk, ak = bl_keys(game["h"]), bl_keys(game["a"])
    best = None
    for ev in events:
        if abs((ev["t"] - tip).total_seconds()) > 18 * 3600:
            continue
        (k1, s1), (k2, s2) = ev["teams"]
        if hk & k1 and ak & k2:
            cand = (ev, s1, s2)
        elif hk & k2 and ak & k1:
            cand = (ev, s2, s1)
        else:
            continue
        if best is None or abs(ev["t"] - tip) < abs(best[0]["t"] - tip):
            best = cand
    return best


def main(path):
    games = json.load(open(path))["games"]
    session = requests.Session()
    days = set()
    for g in games:
        tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
        et = (tip - timedelta(hours=5)).date()  # ESPN groups by US Eastern date
        days.update({et, et - timedelta(days=1), et + timedelta(days=1)})
    events = []
    for d in sorted(days):
        events.extend(fetch_day(d, session))
    out = {"scores": {}, "unmatched": [], "pending": [],
           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for g in games:
        m = match(g, events)
        if not m:
            out["unmatched"].append(g["id"])
        elif not m[0]["final"]:
            out["pending"].append(g["id"])
        else:
            out["scores"][g["id"]] = {"hs": m[1], "as": m[2], "espn": m[0]["id"]}
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
