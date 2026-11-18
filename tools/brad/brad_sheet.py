"""Brad Evans' public betting sheet -> Betalytics Ledger documents (collection "brad").

Reads the sheet's CBK, NFL and NCAAF tabs as CSV (the sheet is public; no login), parses every bet
row (description, odds, units, net units, book, result, boost note) and groups them by sport and
season. Results and net units are Brad's own as recorded on the sheet. Each bet keeps the date this
tool first saw it ("fs"), so bets posted after tracking began can be scored on their own.

Usage: python3 brad_sheet.py <db_dir> <out_dir>
  <db_dir>/brad/*.json: the stored documents (ArtifactData `list` out_dir), used to keep first-seen dates.
  Writes <out_dir>/brad-<doc_id>.json for each document that changed (ArtifactData `set`, collection "brad").
Standard library only.
"""
import csv
import glob
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

SHEET = "1iSoCt8jYVcC0mye6pOQ57NVsxYzOBeKNEKRsnvgmGYk"
TABS = {"CBK": "1337232798", "NFL": "0", "NCAAF": "769882725"}
CURRENT = {"CBK": "2026-27", "NFL": "2026", "NCAAF": "2026"}
RESULTS = {"WIN", "LOSS", "VOID", "PUSH"}
PART = 500                              # bets per stored document (keeps each well under the size limit)


def fetch(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers={"User-Agent": "bracketology-ledger/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8"))))


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def odds_of(s):
    m = re.search(r"[+-]?\d{3,5}", str(s))
    if not m:
        return None
    v = int(m.group())                  # "(+125)", "-102", typo "I+100)"; unsigned counts as plus
    return v if abs(v) >= 100 else None


def season_of(sport, header):
    if sport == "CBK":
        m = re.search(r"'(\d\d)-'(\d\d)", header)
        return f"20{m.group(1)}-{m.group(2)}" if m else None
    m = re.search(r"\b(20\d\d)\b", header)
    return m.group(1) if m else None


def kind_of(desc, section):
    d = desc.strip()
    if re.search(r"futures?", section, re.I):
        return "future"
    if re.match(r"SGP", d, re.I):
        return "sgp"
    if re.match(r"\d+-leg", d, re.I) or re.search(r"parlay", section, re.I):
        return "parlay"
    return "straight"


def parse(sport, rows):
    """Bets in sheet order (newest first) with season, week/section, fields."""
    sections = []                       # (row index, header text, explicit season or None)
    for i, r in enumerate(rows):
        a = (r[0] if r else "").strip()
        if len(r) > 1 and r[1].strip() == "Juice":
            sections.append((i, a, season_of(sport, a)))
        elif a.upper() == "FUTURES":
            sections.append((i, "FUTURES", None))
    # Headers without a year: postseason ones (NCAAT, CFP, Super Bowl, Championship...) sit above the
    # season they finish, so take the nearest explicit season below; others (plain "NFL Week 10",
    # "FUTURES") belong to the nearest explicit season above, else the current season.
    post = re.compile(r"NCAAT|NIT|Champ|Crown|Final|Elite|Sweet|Round|CFP|Bowl|Playoff|title", re.I)
    resolved = []
    for j, (i, h, s) in enumerate(sections):
        if s is None:
            above = [x[2] for x in sections[:j] if x[2]]
            below = [x[2] for x in sections[j + 1:] if x[2]]
            if post.search(h) and not re.search(r"futures?", h, re.I) and below:
                s = below[0]
            else:
                s = above[-1] if above else CURRENT[sport]
        resolved.append((i, h, s))
    bets, seen = [], {}
    for j, (start, header, season) in enumerate(resolved):
        end = resolved[j + 1][0] if j + 1 < len(resolved) else len(rows)
        for r in rows[start + 1:end]:
            r = (r + [""] * 8)[:8]
            desc = r[0].strip()
            o, u = odds_of(r[1]), num(r[2])
            if not desc or o is None or u is None or u <= 0:
                continue
            res = r[5].strip().upper()
            res = res if res in RESULTS else ""
            net = num(r[3])
            note = (r[6] + " " + r[7]).lower()
            base = f"{sport}|{season}|{header}|{desc}|{o}|{u}"
            n = seen.get(base, 0)
            seen[base] = n + 1
            key = hashlib.md5(f"{base}|{n}".encode()).hexdigest()[:12]
            b = {"key": key, "season": season, "w": header, "d": desc, "o": o, "u": u, "k": kind_of(desc, header)}
            if res:
                b["r"], b["n"] = res, net if net is not None else 0.0
            if r[4].strip():
                b["b"] = r[4].strip()
            if re.search(r"\blive\b", desc, re.I):
                b["live"] = 1
            if "boost" in note:
                b["boost"] = 1
            bets.append(b)
    return bets


def first_seen(stored, key):
    for d in stored.values():
        b = (d.get("bets") or {}).get(key)
        if b and b.get("fs"):
            return b["fs"]
    return None


def main(db_dir, out_dir):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stored = {}
    for p in glob.glob(os.path.join(db_dir, "brad", "*.json")):
        stored[os.path.splitext(os.path.basename(p))[0].replace("@", "~")] = json.load(open(p))   # ArtifactData spells "~" as "@"
    os.makedirs(out_dir, exist_ok=True)
    files, counts = [], {}
    for sport, gid in TABS.items():
        seasons = {}
        for b in parse(sport, fetch(gid)):
            seasons.setdefault(b["season"], []).append(b)
        for season, lst in seasons.items():
            # Oldest first, PART bets per document, so new bets only ever change the last part.
            lst.reverse()
            for pi in range(0, len(lst), PART):
                doc_id = f"{sport}-{season}" + (f"~{pi // PART + 1}" if pi else "")
                prev = (stored.get(doc_id) or {}).get("bets") or {}
                bets = {}
                for idx, b in enumerate(lst[pi:pi + PART]):
                    key = b.pop("key")
                    b["i"] = pi + idx           # position in the season, oldest = 0 (sheet order)
                    b.pop("season")
                    b["fs"] = (prev.get(key) or {}).get("fs") or first_seen(stored, key) or today
                    bets[key] = b
                counts[doc_id] = len(bets)
                if prev == bets:
                    continue
                path = os.path.join(out_dir, f"brad-{doc_id}.json")
                json.dump({"sport": sport, "season": season, "updated": today, "bets": bets},
                          open(path, "w"), separators=(",", ":"))
                files.append({"doc_id": doc_id, "file": path, "existed": doc_id in stored,
                              "bytes": os.path.getsize(path)})
    print(json.dumps({"bets": counts, "files": files}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
