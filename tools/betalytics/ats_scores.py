"""Final scores for every college game in the "lines" collection (the ATS-form study).

closing.py stores the consensus spread of every NCAAB game it sees; this grades those games from the
NCAA.com scoreboard, the same feed and team matching the Betalytics picks use.

Usage: python3 ats_scores.py <db_dir> <out_dir>
  <db_dir>/lines/*.json and <db_dir>/atsscores/*.json as saved by ArtifactData `list` with out_dir.
Writes <out_dir>/atsscores-<date>.json for each date that changed (collection "atsscores", doc_id <date>).
Standard library only.
"""
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scores as feed  # noqa: E402

# Second word of two-word mascots ("Blue Devils"), so "Duke Blue Devils" also reads as "Duke".
TWO_WORD = {"blue", "tar", "red", "golden", "fighting", "crimson", "yellow", "sun", "horned", "demon", "nittany",
            "scarlet", "green", "mean", "rainbow", "big", "black", "purple", "ragin", "river", "thundering",
            "running", "wolf", "great", "orange", "lady", "delta", "flying", "screaming", "golden"}


def side(name):
    w = name.split()
    forms = {"n": name, "s": " ".join(w[:-1]) if len(w) > 1 else name}
    if len(w) > 2 and w[-2].lower().strip("'") in TWO_WORD:
        forms["k"] = " ".join(w[:-2])
    return forms


def load(pattern):
    return {os.path.splitext(os.path.basename(p))[0]: json.load(open(p)) for p in glob.glob(pattern)}


def main(db_dir, out_dir):
    now = datetime.now(timezone.utc)
    lines = load(os.path.join(db_dir, "lines", "*.json"))
    stored = load(os.path.join(db_dir, "atsscores", "*.json"))
    todo = {}
    for date, doc in lines.items():
        have = (stored.get(date) or {}).get("games", {})
        for gid, g in (doc.get("games") or {}).items():
            tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
            if gid in have or not (now - timedelta(days=5) < tip < now - timedelta(hours=2.5)):
                continue
            todo.setdefault(date, []).append((gid, g))
    changed, pending, unmatched = {}, 0, 0
    for date, games in sorted(todo.items()):
        day = datetime.strptime(date, "%Y-%m-%d")
        events = feed.fetch_day(day) + feed.fetch_day(day + timedelta(days=1))
        for gid, g in games:
            m = feed.match({"t": g["t"], "h": side(g["h"]), "a": side(g["a"])}, events)
            if not m:
                unmatched += 1
                continue
            ev, hs, aw = m
            if not ev["final"]:
                pending += 1
                continue
            if date not in changed:
                changed[date] = dict((stored.get(date) or {}).get("games", {}))
            changed[date][gid] = {"hs": hs, "as": aw}
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for date, games in sorted(changed.items()):
        path = os.path.join(out_dir, f"atsscores-{date}.json")
        json.dump({"date": date, "games": games}, open(path, "w"), separators=(",", ":"))
        files.append({"doc_id": date, "file": path, "existed": date in stored})
    print(json.dumps({"scored": sum(len(v) for v in changed.values()), "pending": pending,
                      "not_in_feed": unmatched, "files": files}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
