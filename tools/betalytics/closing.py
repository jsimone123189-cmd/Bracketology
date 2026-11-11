"""Closing-line snapshots for the Betalytics NCAAB Ledger, from The Odds API.

The API key is never in this file or in any variable: the environment's network proxy adds it
(header x-api-key) to requests to api.the-odds-api.com. One snapshot = one request for
h2h, spreads and totals in the US region = 3 of the plan's monthly requests.

Usage: python3 closing.py <db_dir> <out_dir>
  <db_dir>/slates/*.json and <db_dir>/closing/*.json as saved by ArtifactData `list` with out_dir.
Writes <out_dir>/closing-<date>.json for each date that changed (ArtifactData `set` on collection
"closing", doc_id <date>) and prints a JSON summary. A game's entry is replaced only while the game
has not started, so the stored line is the last one seen before tip-off.
"""
import glob
import json
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scores import norm  # noqa: E402  (same team-name normalization as the score matcher)

URL = ("https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
       "?regions=us&markets=h2h,spreads,totals&oddsFormat=american&dateFormat=iso")


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "bracketology-ledger/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        left = r.headers.get("x-requests-remaining")
        return json.load(r), left


def no_vig(a, b):
    """No-vig win probability of side a from two American prices."""
    imp = lambda p: 100 / (p + 100) if p > 0 else -p / (-p + 100)
    ia, ib = imp(a), imp(b)
    return ia / (ia + ib)


def consensus(event):
    """Median line and prices across bookmakers, oriented to the API's home/away teams."""
    home, away = event["home_team"], event["away_team"]
    sp_pt, sp_hp, sp_ap, tot_pt, ov, un, ml_h, ml_a = ([] for _ in range(8))
    for bk in event.get("bookmakers", []):
        for m in bk.get("markets", []):
            o = {x["name"]: x for x in m.get("outcomes", [])}
            if m["key"] == "spreads" and home in o and away in o:
                sp_pt.append(o[home]["point"]); sp_hp.append(o[home]["price"]); sp_ap.append(o[away]["price"])
            elif m["key"] == "totals" and "Over" in o and "Under" in o:
                tot_pt.append(o["Over"]["point"]); ov.append(o["Over"]["price"]); un.append(o["Under"]["price"])
            elif m["key"] == "h2h" and home in o and away in o:
                ml_h.append(o[home]["price"]); ml_a.append(o[away]["price"])
    med = lambda v: statistics.median(v) if v else None
    out = {"books": len(event.get("bookmakers", []))}
    if sp_pt:
        out["sp"] = {"home": med(sp_pt), "hp": med(sp_hp), "ap": med(sp_ap)}
    if tot_pt:
        out["tot"] = {"line": med(tot_pt), "over": med(ov), "under": med(un)}
    if ml_h:
        out["ml"] = {"home": med(ml_h), "away": med(ml_a), "home_p": round(no_vig(med(ml_h), med(ml_a)), 4)}
    return out


def _forms(name):
    """An Odds API name ('Temple Owls') with and without its mascot ('temple')."""
    w = norm(name).split()
    return {" ".join(w[:k]) for k in (len(w), len(w) - 1, len(w) - 2) if k >= 1}


def match_events(games, events):
    """{betalytics id: (event, flipped)}.

    Best: both full names equal. Next: both teams match with mascots dropped (Betalytics sometimes
    gives 'Temple' where the API says 'Temple Owls'). Last: exactly one candidate where one team
    matches, within an hour of tip. Always within 3 hours of Betalytics' tip time.
    """
    out = {}
    for gid, g in games.items():
        tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
        hk = {norm(g["h"].get("n")), norm(g["h"].get("s"))} - {""}
        ak = {norm(g["a"].get("n")), norm(g["a"].get("s"))} - {""}
        cands = []
        for ev in events:
            gap = abs((datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")) - tip).total_seconds())
            if gap > 3 * 3600:
                continue
            eh, ea = norm(ev["home_team"]), norm(ev["away_team"])
            fh, fa = _forms(ev["home_team"]), _forms(ev["away_team"])
            for flipped, H, A, FH, FA in ((False, eh, ea, fh, fa), (True, ea, eh, fa, fh)):
                if H in hk and A in ak:
                    cands.append((0, gap, ev, flipped))
                elif hk & FH and ak & FA:
                    cands.append((1, gap, ev, flipped))
                elif (hk & FH or ak & FA) and gap <= 3600:
                    cands.append((2, gap, ev, flipped))
        if not cands:
            continue
        cands.sort(key=lambda c: (c[0], c[1]))
        top = cands[0]
        if top[0] < 2 or len({id(c[2]) for c in cands}) == 1:
            out[gid] = (top[2], top[3])
    return out


def orient(c, flipped):
    """Consensus re-expressed in Betalytics' home/away orientation."""
    if not flipped:
        return c
    o = dict(c)
    if "sp" in c:
        o["sp"] = {"home": -c["sp"]["home"], "hp": c["sp"]["ap"], "ap": c["sp"]["hp"]}
    if "ml" in c:
        o["ml"] = {"home": c["ml"]["away"], "away": c["ml"]["home"], "home_p": round(1 - c["ml"]["home_p"], 4)}
    return o


def load(pattern):
    return {os.path.splitext(os.path.basename(p))[0]: json.load(open(p)) for p in glob.glob(pattern)}


def main(db_dir, out_dir, events=None):
    now = datetime.now(timezone.utc)
    slates = load(os.path.join(db_dir, "slates", "*.json"))
    stored = load(os.path.join(db_dir, "closing", "*.json"))
    upcoming = {}
    for date, doc in slates.items():
        for gid, g in (doc.get("games") or {}).items():
            tip = datetime.fromisoformat(g["t"].replace("Z", "+00:00"))
            if now < tip < now + timedelta(hours=30):
                upcoming[gid] = (date, g)
    left = None
    if events is None and upcoming:
        events, left = fetch()
    matched = match_events({k: v[1] for k, v in upcoming.items()}, events or [])
    changed = {}
    for gid, (ev, flipped) in matched.items():
        date = upcoming[gid][0]
        if date not in changed:
            changed[date] = dict((stored.get(date) or {}).get("games", {}))
        changed[date][gid] = {**orient(consensus(ev), flipped), "at": now.isoformat(timespec="seconds")}
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for date, games in sorted(changed.items()):
        path = os.path.join(out_dir, f"closing-{date}.json")
        json.dump({"date": date, "games": games}, open(path, "w"))
        files.append({"doc_id": date, "file": path, "existed": date in stored})
    print(json.dumps({"upcoming": len(upcoming), "matched": len(matched), "requests_left": left,
                      "files": files}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
