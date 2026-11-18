"""Final scores for every college game in the "lines" collection (the ATS-form study).

closing.py stores the consensus spread of every NCAAB game it sees; this grades those games from the
NCAA.com scoreboard, the same feed and team matching the Betalytics picks use.

Usage: python3 ats_scores.py <db_dir> <out_dir>
  <db_dir>/lines/*.json and <db_dir>/atsscores/*.json as saved by ArtifactData `list` with out_dir.
Writes <out_dir>/atsscores-<date>.json for each date that changed (collection "atsscores", doc_id <date>),
and <out_dir>/atssum-latest.json (collection "atssum", doc_id "latest"): the study's results, which is
all the tracker page downloads.
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


GROUPS = [("hot3", "Won 3+ ATS in a row"), ("hot4", "4–0 ATS last 4"), ("big", "Covering by 7+ on average, last 4"),
          ("cold3", "Lost 3+ ATS in a row"), ("cold4", "0–4 ATS last 4"), ("bad", "Missing by 7+ on average, last 4")]


def form_of(m):
    """Form groups for a team from its earlier cover margins (oldest first), and its current streak."""
    st = 0
    for x in reversed(m):
        if x > 0: st += 1
        else: break
    cs = 0
    for x in reversed(m):
        if x < 0: cs += 1
        else: break
    out = []
    if st >= 3: out.append("hot3")
    if cs >= 3: out.append("cold3")
    if len(m) >= 4:
        last = m[-4:]; avg = sum(last) / 4
        if all(x > 0 for x in last): out.append("hot4")
        if all(x < 0 for x in last): out.append("cold4")
        if avg >= 7: out.append("big")
        if avg <= -7: out.append("bad")
    return out, (st or -cs)


def study(lines, scores, now):
    games = []
    for d, doc in lines.items():
        sc = (scores.get(d) or {}).get("games", {})
        for gid, g in (doc.get("games") or {}).items():
            games.append((g["t"], gid, g, sc.get(gid)))
    games.sort(key=lambda x: (x[0], x[1]))
    hist, tally, upcoming, graded = {}, {k: [0, 0] for k, _ in GROUPS}, [], 0
    for t, gid, g, s in games:
        sides = ((g["h"], g["a"], 1), (g["a"], g["h"], -1))
        if not s:
            if datetime.fromisoformat(t.replace("Z", "+00:00")) > now - timedelta(hours=3):
                for team, opp, sign in sides:
                    groups, streak = form_of(hist.get(team, []))
                    if groups:
                        upcoming.append({"team": team, "opp": opp, "t": t, "sp": g["sp"] * sign, "groups": groups, "streak": streak})
            continue
        graded += 1
        home_m = (s["hs"] - s["as"]) + g["sp"]          # sp is the home spread
        for team, opp, sign in sides:
            m = home_m * sign
            groups, _ = form_of(hist.get(team, []))
            if m != 0:
                for k in groups:
                    tally[k][0 if m > 0 else 1] += 1
                hist.setdefault(team, []).append(m)
    upcoming.sort(key=lambda u: u["t"])
    return {"updated": now.isoformat(timespec="minutes"), "graded": graded,
            "groups": [{"key": k, "name": n, "w": tally[k][0], "l": tally[k][1]} for k, n in GROUPS],
            "upcoming": upcoming[:40]}


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
    merged = {d: {"games": dict((stored.get(d) or {}).get("games", {}), **changed.get(d, {}))} for d in set(stored) | set(changed)}
    sp = os.path.join(out_dir, "atssum-latest.json")
    json.dump(study(lines, merged, now), open(sp, "w"), separators=(",", ":"))
    print(json.dumps({"scored": sum(len(v) for v in changed.values()), "pending": pending,
                      "not_in_feed": unmatched, "files": files,
                      "summary": {"collection": "atssum", "doc_id": "latest", "file": sp}}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
