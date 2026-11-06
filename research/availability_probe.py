"""Player availability feasibility only. Nothing here reaches the model. Sample: the NET top 12 of 2026, every game through Selection Sunday.
Questions: are box scores there, do they list minutes, are names stable, do they list players who sat out, and what would the plan's measure look like?"""
import collections, json
from datetime import date
from bracketology import history
from bracketology.features import build_year
from bracketology.http import fetch
from bracketology.sources import ncaa_games
from bracketology.teams import key
Y = 2026; end = date.fromisoformat(history.SELECTION_SUNDAY[Y])
F = sorted(build_year(Y), key=lambda r: r["net"])[:12]; top = {r["key"]: r["team"] for r in F}
rows = ncaa_games.collect(date(end.year - 1, 11, 1), end)["rows"]; games = collections.defaultdict(list)
for g in rows:
    if key(g["team"]) in top: m, d, y = g["date"].split("/"); games[key(g["team"])].append((f"20{y}-{int(m):02d}-{int(d):02d}", g["id"], g["team"]))
def box(i):
    return json.loads(fetch(f"https://ncaa-api.henrygd.me/game/{i}/boxscore", ttl=86400 * 365, retries=2))
want = got = no_min = 0; keys = set()
for k, gs in games.items():
    gs.sort(); mins = collections.defaultdict(float); by_game = []; dnp = 0; ids = collections.defaultdict(set)
    for d, i, name in gs:
        want += 1
        try: b = box(i)
        except Exception: continue
        side = next((t["teamId"] for t in b["teams"] if key(t["nameShort"]) == k), None)
        ps = next((t["playerStats"] for t in b["teamBoxscore"] if str(t["teamId"]) == str(side)), None)
        if ps is None: continue
        got += 1; keys |= set(ps[0]) if ps else set(); seen = {}
        for p in ps:
            n = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(); ids[n].add(p.get("id"))
            try: m = float(p.get("minutesPlayed") or 0)
            except ValueError: m = 0; no_min += 1
            seen[n] = m; dnp += m == 0
        by_game.append(seen)
    for g in by_game[:-3]:
        for n, m in g.items(): mins[n] += m
    five = sorted(mins, key=mins.get, reverse=True)[:5]; total = sum(mins[n] for n in five) or 1
    last3 = by_game[-3:]; lost = sum(mins[n] / total * sum(not g.get(n) for g in last3) / max(1, len(last3)) for n in five)
    print(f"{top[k]:<14} games {len(by_game)}/{len(gs)} players listed at 0 min {dnp}; names with changing id {sum(len(v) > 1 for v in ids.values())}; top-5 minutes share missing, last 3 games {lost:.2f}; missed: {[n for n in five if any(not g.get(n) for g in last3)]}", flush=True)
print("box scores found", got, "of", want, "; unreadable minutes", no_min); print("player fields", sorted(keys))
old = next((g for g in ncaa_games.collect(date(2022, 3, 1), date(2022, 3, 1))["rows"]), None)
print("older season box score, 2022:", bool(old) and "teamBoxscore" in box(old["id"]))
