"""NFL results for the Betalytics Ledger: final scores and player stats from nflverse.

nflverse publishes schedules with scores and weekly player stats as GitHub release files (free).
Betalytics uses nflverse's own game ids (2026_10_WAS_NYG) and player ids (00-0038576), so
everything joins on ids, no name matching.

Usage: python3 nfl_results.py <db_dir> <out_dir>
  Reads <db_dir>/nflgames/*.json, nflprops/*.json, nflresults/*.json (ArtifactData `list` out_dir).
  Writes <out_dir>/nflresults-<week>.json for each week that changed (ArtifactData `set` on collection
  "nflresults", doc_id <week>). A game is added once its score is final AND its player stats are
  published, so props are never graded on missing stats. A player with no stat line did not play:
  the tracker treats those props as void (no action), as sportsbooks do.
"""
import csv
import glob
import io
import json
import os
import sys
import urllib.request

GAMES = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
STATS = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv"
PROP_STAT = {
    "player_anytime_td": ["rushing_tds", "receiving_tds", "special_teams_tds"],
    "player_receptions": ["receptions"], "player_reception_yds": ["receiving_yards"],
    "player_rush_attempts": ["carries"], "player_rush_yds": ["rushing_yards"],
    "player_pass_attempts": ["attempts"], "player_pass_completions": ["completions"],
    "player_pass_interceptions": ["passing_interceptions"], "player_pass_tds": ["passing_tds"],
    "player_pass_yds": ["passing_yards"],
}


def get_csv(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bracketology-ledger/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def load(pattern):
    return {os.path.splitext(os.path.basename(p))[0]: json.load(open(p)) for p in glob.glob(pattern)}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main(db_dir, out_dir):
    games = load(os.path.join(db_dir, "nflgames", "*.json"))
    props = load(os.path.join(db_dir, "nflprops", "*.json"))
    stored = load(os.path.join(db_dir, "nflresults", "*.json"))
    done = {gid for doc in stored.values() for gid in (doc.get("games") or {})}
    week_of, todo = {}, set()
    for wk, doc in games.items():
        for gid in (doc.get("games") or {}):
            week_of[gid] = wk
            if gid not in done:
                todo.add(gid)
    os.makedirs(out_dir, exist_ok=True)
    if not todo:
        print(json.dumps({"pending": 0, "added": 0, "files": []}))
        return
    sched = {r["game_id"]: r for r in get_csv(GAMES) if r["game_id"] in todo}
    seasons = sorted({gid.split("_")[0] for gid in todo})
    stats = {}
    for s in seasons:
        for r in get_csv(STATS.format(season=s)):
            if r.get("game_id") in todo:
                stats.setdefault(r["game_id"], {})[r["player_id"]] = r
    changed = {}
    for gid in sorted(todo):
        g = sched.get(gid)
        if not g or g.get("home_score") in ("", None) or gid not in stats:
            continue                      # not final, or player stats not published yet
        wk = week_of[gid]
        doc = changed.setdefault(wk, {"games": dict((stored.get(wk) or {}).get("games", {})),
                                      "stats": dict((stored.get(wk) or {}).get("stats", {}))})
        doc["games"][gid] = {"hs": int(g["home_score"]), "as": int(g["away_score"])}
        need = {}
        for p in ((props.get(gid) or {}).get("props") or {}).values():
            need.setdefault(p["pid"], set()).add(p["mk"])
        per = {}
        for pid, mks in need.items():
            row = stats[gid].get(pid)
            if row is None:
                continue                  # did not play: void
            per[pid] = {mk: sum(num(row.get(c)) for c in PROP_STAT[mk]) for mk in mks if mk in PROP_STAT}
        doc["stats"][gid] = per
    files = []
    for wk, doc in sorted(changed.items()):
        path = os.path.join(out_dir, f"nflresults-{wk}.json")
        json.dump({"week": wk, **doc}, open(path, "w"))
        files.append({"doc_id": wk, "file": path, "existed": wk in stored})
    print(json.dumps({"pending": len(todo), "added": sum(len(d["games"]) for d in changed.values()) - sum(
        len((stored.get(w) or {}).get("games", {})) for w in changed), "files": files}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
