"""Builds avail_missing for all seven seasons from one source, the hoopR-mbb-data archive (CC BY 4.0, https://github.com/sportsdataverse/hoopR-mbb-data). See docs/10, "First run and restart".
Input: data/history/espn_box/{year}.json from availability_archive_convert.py. Output: data/history/availability.json."""
import collections, json
from bracketology import history
from bracketology.features import build_year
from bracketology.teams import key

MIN_BOX_MINUTES = 190      # a full game is 200 team minutes; less means an incomplete box score, which counts as missing

def spaced(items, n):
    if len(items) <= n: return list(items)
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]

out = {}
for y in sorted(history.SELECTION_SUNDAY):
    day = history.SELECTION_SUNDAY[y]; scope = {r["key"] for r in build_year(y) if r["net"] <= 100}
    box = collections.defaultdict(lambda: collections.defaultdict(dict)); dates = {}
    for r in json.load(open(f"data/history/espn_box/{y}.json")):
        if r["game_date"] > day: continue
        if not r["team_location"]: continue
        k = "miamifl" if r["team_display_name"] == "Miami Hurricanes" else next((c for c in (key(r["team_location"]), key(r["team_short_display_name"] or r["team_location"])) if c in scope), None)
        if k is None: continue
        dates[r["game_id"]] = r["game_date"]
        if not r["did_not_play"] and r["minutes"]: box[k][r["game_id"]][r["athlete_id"]] = (r["minutes"], r["athlete_display_name"])
    values, failed, stats = {}, {}, collections.Counter()
    for k in sorted(scope):
        games = sorted(box[k], key=lambda g: dates[g])
        if len(games) < 6: failed[k] = f"only {len(games)} games"; continue
        whole = lambda g: sum(m for m, _ in box[k][g].values()) >= MIN_BOX_MINUTES
        last = games[-3:]; base = [g for g in spaced(games[:-3], 10) if whole(g)]
        stats["games"] += len(games); stats["bad_last"] += sum(not whole(g) for g in last); stats["bad_base"] += 10 - len(base) if len(games) > 12 else 0
        if not all(whole(g) for g in last): failed[k] = "incomplete last-three box score"; continue
        if len(base) < 3: failed[k] = f"{len(base)} baseline games"; continue
        total, names = collections.Counter(), {}
        for g in base:
            for a, (m, n) in box[k][g].items(): total[a] += m; names[a] = n
        five = [a for a, _ in total.most_common(5)]; all_min = sum(total[a] for a in five)
        values[k] = {"avail_missing": sum(total[a] / all_min * sum(a not in box[k][g] for g in last) / 3 for a in five), "missing": [names[a] for a in five if any(a not in box[k][g] for g in last)], "games": len(games)}
    out[str(y)] = {"values": values, "failed": failed, "coverage": len(values) / len(scope)}
    print(y, "coverage", round(out[str(y)]["coverage"], 3), dict(stats), "failed", failed, flush=True)
json.dump(out, open("data/history/availability.json", "w"))
