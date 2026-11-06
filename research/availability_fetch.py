"""Builds avail_missing for docs/10-availability-test.md. Saved locally to data/history/availability.json. Safe to rerun: responses are cached on disk."""
import collections, json, sys
from datetime import date
from bracketology import history
from bracketology.features import build_year
from bracketology.http import fetch
from bracketology.sources import ncaa_games
from bracketology.teams import key

def minutes(v):
    v = str(v or "0").strip()
    if ":" in v: m, s = v.split(":")[:2]; return int(m) + int(s) / 60
    return float(v)

def team_box(game_id, home):
    b = json.loads(fetch(f"https://ncaa-api.henrygd.me/game/{game_id}/boxscore", ttl=86400 * 365, retries=2))
    side = next(t["teamId"] for t in b["teams"] if t["isHome"] == home)
    ps = next(t["playerStats"] for t in b["teamBoxscore"] if str(t["teamId"]) == str(side))
    return {f"{p.get('firstName', '')} {p.get('lastName', '')}".strip().lower(): minutes(p.get("minutesPlayed")) for p in ps}

def spaced(items, n):
    if len(items) <= n: return list(items)
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]

out = {}
for y in sorted(history.SELECTION_SUNDAY):
    day = history.SELECTION_SUNDAY[y]; end = date.fromisoformat(day); F = build_year(y); scope = {r["key"] for r in F if r["net"] <= 100}
    games = collections.defaultdict(list)
    for g in ncaa_games.collect(date(end.year - 1, 11, 1), end)["rows"]:
        k = key(g["team"])
        if k in scope: m, d, yy = g["date"].split("/"); games[k].append((f"20{yy}-{int(m):02d}-{int(d):02d}", g["id"], g["loc"] == "H"))
    values, failed = {}, {}
    for n, k in enumerate(sorted(scope)):
        gs = sorted(games.get(k, []))
        if len(gs) < 6: failed[k] = f"only {len(gs)} games"; continue
        try:
            last = [team_box(i, h) for _, i, h in gs[-3:]]; base = [team_box(i, h) for _, i, h in spaced(gs[:-3], 10)]
        except Exception as e:
            failed[k] = repr(e)[:120]; continue
        total = collections.Counter()
        for b in base: total.update(b)
        five = [p for p, _ in total.most_common(5)]; whole = sum(total[p] for p in five)
        if whole <= 0: failed[k] = "no baseline minutes"; continue
        values[k] = {"avail_missing": sum(total[p] / whole * sum(not b.get(p) for b in last) / 3 for p in five), "missing": [p for p in five if any(not b.get(p) for b in last)]}
        if n % 25 == 0: print(y, n, len(scope), flush=True)
    out[str(y)] = {"values": values, "failed": failed, "coverage": len(values) / len(scope)}
    print(y, "coverage", round(out[str(y)]["coverage"], 3), "failed", list(failed.items())[:4], flush=True)
    json.dump(out, open("data/history/availability.json", "w"))
print("done", flush=True)
