"""Daily grading step for the Betalytics NCAAB Ledger artifact.

Reads the tracker's stored documents (as saved by ArtifactData `list` with
`out_dir`): <db_dir>/slates/<date>.json and <db_dir>/scores/<date>.json.
Finds games that tipped at least 2.5 hours ago (and within the last 5 days,
so games ESPN never lists stop being retried) and have no score yet, looks
them up on ESPN, and writes one merged document per changed date to
<out_dir>/scores-<date>.json, ready for an ArtifactData `set` on
collection "scores", doc_id <date>.

Usage: python3 update_scores.py <db_dir> <out_dir>
"""
import glob
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scores as espn  # noqa: E402


def load(pattern):
    out = {}
    for path in glob.glob(pattern):
        with open(path) as f:
            doc = json.load(f)
        out[os.path.splitext(os.path.basename(path))[0]] = doc
    return out


def main(db_dir, out_dir):
    now = datetime.now(timezone.utc)
    slates = load(os.path.join(db_dir, "slates", "*.json"))
    stored = load(os.path.join(db_dir, "scores", "*.json"))
    todo, date_of = [], {}
    for date, doc in slates.items():
        have = (stored.get(date) or {}).get("games", {})
        for gid, g in (doc.get("games") or {}).items():
            tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
            if gid in have or not (now - timedelta(days=5) < tip < now - timedelta(hours=2.5)):
                continue
            todo.append({"id": gid, "t": g["t"], "h": g["h"], "a": g["a"]})
            date_of[gid] = date
    os.makedirs(out_dir, exist_ok=True)
    if not todo:
        print(json.dumps({"checked": 0, "new_scores": 0, "files": []}))
        return
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"games": todo}, f)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        espn.main(f.name)
    result = json.loads(buf.getvalue())
    os.unlink(f.name)

    changed = {}
    for gid, s in result["scores"].items():
        date = date_of[gid]
        if date not in changed:
            changed[date] = dict((stored.get(date) or {}).get("games", {}))
        changed[date][gid] = {"hs": s["hs"], "as": s["as"]}
    files = []
    for date, games in sorted(changed.items()):
        path = os.path.join(out_dir, f"scores-{date}.json")
        with open(path, "w") as f:
            json.dump({"date": date, "games": games, "checked_at": result["checked_at"]}, f)
        files.append({"doc_id": date, "file": path,
                      "existed": date in stored})
    print(json.dumps({"checked": len(todo), "new_scores": len(result["scores"]),
                      "still_pending": len(result["pending"]),
                      "not_on_espn": len(result["unmatched"]), "files": files}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
