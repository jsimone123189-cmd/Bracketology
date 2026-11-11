"""Match Betalytics NCAAB games to NCAA.com final scores (via the public ncaa-api wrapper
this repo already uses; see docs/02-data-source-feasibility.md).

Input (JSON file): {"games": [{"id", "t" (ISO tip time), "h": {"n", "s", "a"}, "a": {...}}]}
  n = full name, s = short name, a = abbreviation (as Betalytics gives them).
Output (stdout JSON): {"scores": {game_id: {"hs", "as", "ncaa"}}, "unmatched": [ids], "pending": [ids]}
  hs/as are the Betalytics home/away teams' final points (oriented by team, so
  neutral-site games where the feed lists the teams the other way round still grade right).

Usage: python3 scores.py games.json > scores.json
Uses only the NCAA scoreboard feed; no Betalytics access. Standard library only.
ESPN is not used: espn.com's robots.txt disallows Anthropic's crawler.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

import time
import urllib.request

NCAA = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{y}/{m:02d}/{d:02d}/all-conf"
USER_AGENT = "bracketology-bot/0.1 (free open bracketology project)"
ALIASES = {"state": "st", "saint": "st", "university": "", "univ": "", "u": "", "the": "",
           "and": "", "&": "", "mount": "mt", "fort": "ft", "of": "",
           # NCAA.com short-name abbreviations and Betalytics initials, mapped to full words
           "ky": "kentucky", "mich": "michigan", "tenn": "tennessee", "la": "louisiana",
           "ind": "indiana", "ark": "arkansas", "colo": "colorado", "ga": "georgia",
           "fla": "florida", "miss": "mississippi", "ill": "illinois", "ala": "alabama",
           "wash": "washington", "conn": "connecticut", "val": "valley", "col": "college",
           "e": "eastern", "w": "western", "n": "northern", "s": "southern", "c": "central",
           "se": "southeastern", "sw": "southwestern", "ne": "northeastern", "nw": "northwestern"}


def norm(s):
    s = re.sub(r"[^a-z0-9& ]+", " ", (s or "").lower().replace("'", "").replace(".", ""))
    return " ".join(ALIASES.get(w, w) for w in s.split() if ALIASES.get(w, w))


def keys(forms):
    """Normalized name forms a team can be recognized by."""
    return {k for k in (norm(f) for f in forms if f) if k}


def feed_keys(t):
    """(names, abbreviations) for one side of an NCAA.com game."""
    n = t.get("names") or {}
    return (keys([n.get("short"), n.get("full"), (n.get("seo") or "").replace("-", " ")]),
            keys([n.get("char6")]))


def bl_keys(side):
    """(names, abbreviations) for one side of a Betalytics game."""
    return keys([side.get("n"), side.get("s"), side.get("k")]), keys([side.get("a")])


def fetch_day(day):
    """Games the NCAA lists for one US Eastern date."""
    req = urllib.request.Request(NCAA.format(y=day.year, m=day.month, d=day.day),
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    events = []
    for item in data.get("games", []):
        g = item["game"]
        try:
            hs, aw = int(g["home"]["score"]), int(g["away"]["score"])
        except (KeyError, TypeError, ValueError):
            hs = aw = 0
        events.append({
            "id": g["gameID"],
            "t": datetime.fromtimestamp(int(g["startTimeEpoch"]), timezone.utc),
            "final": g.get("gameState") == "final",
            "teams": [(feed_keys(g["home"]), hs), (feed_keys(g["away"]), aw)],
        })
    time.sleep(0.5)  # the wrapper allows 5 requests/second; stay well under
    return events


def match(game, events):
    """The feed game for a Betalytics game, oriented to Betalytics' home/away, or None.

    Both teams matching by name (or abbreviation) within 18 hours wins. Otherwise
    one team matching by full name within 3 hours is enough: a D-I team plays at most
    once a day, and Betalytics leaves many non-D-I opponents unnamed. That fallback
    must be unambiguous.
    """
    tip = datetime.fromisoformat(game["t"].replace("Z", "+00:00"))
    (hn, ha), (an, aa) = bl_keys(game["h"]), bl_keys(game["a"])
    both, single = [], []
    for ev in events:
        gap = abs((ev["t"] - tip).total_seconds())
        if gap > 18 * 3600:
            continue
        ((n1, a1), s1), ((n2, a2), s2) = ev["teams"]
        hit = lambda names, abbrs, fn, fa: bool(names & fn) or bool(abbrs & fa)
        if hit(hn, ha, n1, a1) and hit(an, aa, n2, a2):
            both.append((gap, (ev, s1, s2)))
        elif hit(hn, ha, n2, a2) and hit(an, aa, n1, a1):
            both.append((gap, (ev, s2, s1)))
        elif gap <= 3 * 3600:
            if hn & n1 or an & n2:
                single.append((gap, (ev, s1, s2)))
            elif hn & n2 or an & n1:
                single.append((gap, (ev, s2, s1)))
    if both:
        return min(both, key=lambda x: x[0])[1]
    if len(single) == 1:
        return single[0][1]
    return None


def main(path):
    games = json.load(open(path))["games"]
    days = set()
    for g in games:
        tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
        et = (tip - timedelta(hours=5)).date()  # the feed groups by US Eastern date
        days.update({et, et - timedelta(days=1), et + timedelta(days=1)})
    events = []
    for d in sorted(days):
        events.extend(fetch_day(d))
    out = {"scores": {}, "unmatched": [], "pending": [],
           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for g in games:
        m = match(g, events)
        if not m:
            out["unmatched"].append(g["id"])
        elif not m[0]["final"]:
            out["pending"].append(g["id"])
        else:
            out["scores"][g["id"]] = {"hs": m[1], "as": m[2], "ncaa": m[0]["id"]}
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
