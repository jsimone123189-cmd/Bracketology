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

# ---------- Summary for the tracker page (collection "bradsum", doc "latest") ----------
# The page shows only this small document; the per-bet documents above stay as the record.
START = "2026-11-18"                        # tracking began; bets first seen after this are the forward test
SHOW = [("NFL", "NFL"), ("CBK", "College basketball")]
TWO = re.compile(r"(rec|rsh|rush|pass|yds|yards|TD|reb|ast|3PM|longest|most)", re.I)


def market(b):
    if b["k"] != "straight":
        return b["k"]
    d = b["d"]
    if re.search(r"\bML\b", d, re.I):
        return "ml"
    if re.search(r"\d\s*(o|u)\b|\bover\b|\bunder\b|\d+\+?\s*(points|pts)\b", d, re.I) and not TWO.search(d):
        return "total"
    if re.search(r"(^|\s)[+-]\d+(\.5)?(\s|$)|\bPK\b", d, re.I) and not TWO.search(d):
        return "spread"
    return "prop"


def prop_type(d):
    for k, rx in (("most", r"\b(most|mst)\b"), ("longest", r"longest|\blng\b"), ("td", r"\bTD"),
                  ("rec", r"\d\+?\s*rec\b|\brec\b(?!.*yd)"), ("recyds", r"rec\.? ?(yds|yards)|rcv"),
                  ("rush", r"rsh|rush"), ("pass", r"pass|cmp|\bint")):
        if re.search(rx, d, re.I if k != "td" else 0):
            return k
    return "other"


def stats(lst):
    """Record, Brad's units, and your result at a $1 flat stake (risk 1 on plus money, to win 1 on minus)."""
    x = {"w": 0, "l": 0, "u": 0.0, "pl": 0.0, "risk": 0.0, "v": 0.0}
    for b in lst:
        r = b.get("r")
        if not r:
            continue
        o = b["o"]
        win, lose = (o / 100, 1.0) if o > 0 else (1.0, -o / 100)
        p0 = 100 / (o + 100) if o > 0 else -o / (-o + 100)
        x["u"] += b.get("n") or 0
        if r == "WIN":
            x["w"] += 1; x["pl"] += win
        elif r == "LOSS":
            x["l"] += 1; x["pl"] -= lose
        if r in ("WIN", "LOSS"):
            x["risk"] += lose; x["v"] += p0 * (1 - p0) * (win + lose) ** 2
    x["z"] = round(x["pl"] / x["v"] ** 0.5, 2) if x["v"] else 0.0
    del x["v"]
    return {k: round(v, 3) if isinstance(v, float) else v for k, v in x.items()}


def full_prop(b, full):
    return b["sport"] == "NFL" and not b.get("live") and market(b) == "prop" and ((b["u"] >= 1) if full else (b["u"] < 1))


STYLES = [
    ("tail", "NFL props he bets at a full unit (1u+)", lambda b: full_prop(b, True)),
    ("tail", "· anytime TD, full unit", lambda b: full_prop(b, True) and prop_type(b["d"]) == "td"),
    ("tail", "· most yards in the game, full unit", lambda b: full_prop(b, True) and prop_type(b["d"]) == "most"),
    ("tail", "· receptions, full unit", lambda b: full_prop(b, True) and prop_type(b["d"]) == "rec"),
    ("watch", "College basketball straight bets", lambda b: b["sport"] == "CBK" and not b.get("live") and b["k"] == "straight"),
    ("avoid", "NFL props at a half unit (his long shots)", lambda b: full_prop(b, False)),
    ("avoid", "NFL rushing-yard props", lambda b: b["sport"] == "NFL" and not b.get("live") and market(b) == "prop" and prop_type(b["d"]) == "rush"),
    ("avoid", "Same-game parlays", lambda b: not b.get("live") and b["k"] == "sgp"),
]

SEGMENTS = [
    ("Live bets (your alerts)", lambda b: b.get("live")),
    ("Everything except live", lambda b: not b.get("live")),
    ("Straight bets", lambda b: not b.get("live") and b["k"] == "straight"),
    ("Regular parlays", lambda b: not b.get("live") and b["k"] == "parlay"),
    ("Same-game parlays", lambda b: not b.get("live") and b["k"] == "sgp"),
]


BANDS = [("Minus money", -100000, -101), ("+100 to +134", 100, 134), ("+135 to +199", 135, 199), ("+200 and up", 200, 100000)]
PRIOR = 40          # pseudo-bets at the market's break-even rate: a small band can't swing its estimate far


def implied(o):
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def american(p):
    """American price whose break-even rate is p (rounded to whole points)."""
    return round(100 * (1 - p) / p) if p < 0.5 else -round(100 * p / (1 - p))


def band_of(o):
    return next((i for i, (_, lo, hi) in enumerate(BANDS) if lo <= o <= hi), None)


def price_bands(lst):
    """His straight bets by price band: record, hit rate, break-even, and the worst price still worth taking.

    The estimate shrinks the band's hit rate toward the market's rate with PRIOR pseudo-bets, so a 3-10 or
    4-4 band moves its fair price only part of the way."""
    out = []
    for name, lo, hi in BANDS:
        l = [b for b in lst if lo <= b["o"] <= hi and b.get("r") in ("WIN", "LOSS")]
        x = stats(l)
        n = x["w"] + x["l"]
        need = sum(implied(b["o"]) for b in l) / n if n else None
        est = (x["w"] + PRIOR * need) / (n + PRIOR) if n else None
        # ratio: how much more often than break-even his bets in this band win (1.05 = 5% more often).
        # Applied to a single bet's own price, so a +214 isn't judged by a band whose average is +314.
        out.append({"name": name, "w": x["w"], "l": x["l"], "pl": x["pl"], "z": x["z"],
                    "hit": round(x["w"] / n, 3) if n else None, "need": round(need, 3) if need else None,
                    "est": round(est, 3) if est else None, "ratio": round(est / need, 3) if n else None,
                    "min": american(est) if est else None,
                    "avg": round(sum(b["o"] for b in l) / n) if n else None})
    return out


def verdict(cur, prev, both):
    n = both["w"] + both["l"]
    if n < 100:
        return "Too few"
    if both["z"] >= 1.28 and cur["pl"] > 0 and (prev["w"] + prev["l"] < 30 or prev["pl"] > 0):
        return "Tail"
    if both["z"] <= -1.28:
        return "Skip"
    return "Losing" if both["pl"] < 0 else "Not yet"


def summarize(allbets, today):
    # Odds-boosted bets count in their normal category (the user can usually get the same boost).
    bets = [b for b in allbets if b["sport"] in dict(SHOW) and b["k"] != "future"]
    seasons = {sp: sorted({b["season"] for b in bets if b["sport"] == sp}, reverse=True) for sp, _ in SHOW}
    cur = {sp: (v + [None])[0] for sp, v in seasons.items()}
    prev = {sp: (v + [None, None])[1] for sp, v in seasons.items()}
    is_cur = lambda b: b["season"] == cur[b["sport"]]
    is_prev = lambda b: b["season"] == prev[b["sport"]]
    fresh = [b for b in bets if b["fs"] > START]
    out = {"updated": today, "checked": datetime.now(timezone.utc).isoformat(timespec="minutes"), "start": START,
           "since": {"live": stats([b for b in fresh if b.get("live")]),
                     "nonlive": stats([b for b in fresh if not b.get("live")])},
           "styles": [], "sports": [], "open": []}
    for call, name, fn in STYLES:
        a = [b for b in bets if fn(b)]
        if call == "watch":                 # unproven style: promote only when the numbers say so
            c_, p_, b_ = (stats([b for b in a if f(b)]) for f in (is_cur, is_prev, lambda b: is_cur(b) or is_prev(b)))
            call = "tail" if verdict(c_, p_, b_) == "Tail" else "watch"
        out["styles"].append({"call": call, "name": name, "prev": stats([b for b in a if is_prev(b)]),
                              "cur": stats([b for b in a if is_cur(b)]),
                              "both": stats([b for b in a if is_cur(b) or is_prev(b)]),
                              "fw": stats([b for b in a if b["fs"] > START])})
    for sp, name in SHOW:
        mine = [b for b in bets if b["sport"] == sp]
        rows = []
        for label, fn in SEGMENTS:
            a = [b for b in mine if fn(b)]
            c, p = stats([b for b in a if is_cur(b)]), stats([b for b in a if is_prev(b)])
            both = stats([b for b in a if is_cur(b) or is_prev(b)])
            rows.append({"name": label, "cur": c, "prev": p, "both": both, "verdict": verdict(c, p, both)})
        st = [b for b in mine if not b.get("live") and b["k"] == "straight" and (is_cur(b) or is_prev(b))]
        out["sports"].append({"sport": sp, "name": name, "cur": cur[sp], "prev": prev[sp], "rows": rows,
                              "bands": price_bands(st)})
    # Avoid styles win over tail ones (a full-unit rushing prop is still a rushing prop).
    calls = {st["name"]: st["call"] for st in out["styles"]}        # as decided above (a Watch style can be promoted)
    live_styles = [(calls[name], name, fn) for _, name, fn in STYLES]
    order = [st for st in live_styles if st[0] == "avoid"] + [st for st in live_styles if st[0] == "tail"]
    style_of = lambda b: next((c for c, _, fn in order if fn(b)), None)
    rank = {"tail": 0, None: 1, "avoid": 2}
    opn = [b for b in bets if not b.get("r") and not b.get("live") and is_cur(b)]
    opn.sort(key=lambda b: (rank[style_of(b)], -b["i"]))
    bands = {sp["sport"]: sp["bands"] for sp in out["sports"]}

    def fair(b):
        if b["k"] != "straight":
            return None
        i = band_of(b["o"])
        bd = bands[b["sport"]][i] if i is not None else None
        if not bd or bd["min"] is None:
            return None
        p = min(0.97, implied(b["o"]) * bd["ratio"])     # his estimated chance on this bet
        mn = american(p)
        return {"band": bd["name"], "p": round(p, 3), "min": mn, "ok": b["o"] >= mn,
                "edge": round(bd["ratio"] - 1, 3)}
    out["open"] = [{"d": b["d"], "o": b["o"], "u": b["u"], "b": b.get("b", ""), "sport": b["sport"], "w": b["w"],
                    "style": style_of(b), "boost": bool(b.get("boost")), "fair": fair(b)} for b in opn[:100]]
    # Bets the user may have tailed (live, or a Tail style), newest first: the page's "your price" log.
    tailable = [b for b in bets if is_cur(b) and (b.get("live") or style_of(b) == "tail")]
    tailable.sort(key=lambda b: (b["sport"] != "CBK", -b["i"]))
    tailable.sort(key=lambda b: b["fs"], reverse=True)
    out["recent"] = [{"id": b["id"], "d": b["d"], "o": b["o"], "u": b["u"], "b": b.get("b", ""), "sport": b["sport"],
                      "w": b["w"], "r": b.get("r", ""), "live": bool(b.get("live")), "fs": b["fs"]} for b in tailable[:60]]
    return out


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
    files, counts, allbets = [], {}, []
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
                    allbets.append(dict(b, sport=sport, season=season, id=key))
                counts[doc_id] = len(bets)
                if prev == bets:
                    continue
                path = os.path.join(out_dir, f"brad-{doc_id}.json")
                json.dump({"sport": sport, "season": season, "updated": today, "bets": bets},
                          open(path, "w"), separators=(",", ":"))
                files.append({"doc_id": doc_id, "file": path, "existed": doc_id in stored,
                              "bytes": os.path.getsize(path)})
    summ = summarize(allbets, today)
    sp = os.path.join(out_dir, "bradsum-latest.json")
    json.dump(summ, open(sp, "w"), separators=(",", ":"))
    print(json.dumps({"bets": counts, "files": files,
                      "summary": {"collection": "bradsum", "doc_id": "latest", "file": sp, "bytes": os.path.getsize(sp)}}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
