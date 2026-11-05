from __future__ import annotations
"""As-of-Selection-Sunday history from Internet Archive captures of public pages.
Captures can be slightly AFTER the reveal (up to 06:00 UTC Monday), but no games are played by then and the NET page's
own "Through Games" date is checked, so ratings contain no postseason results. Pages must not contribute seed info."""
import html, json, re
from datetime import date, timedelta
from .http import fetch

SELECTION_SUNDAY = {2019: "2019-03-17", 2021: "2021-03-14", 2022: "2022-03-13", 2023: "2023-03-12",
                    2024: "2024-03-17", 2025: "2025-03-16", 2026: "2026-03-15"}
NET_URL = "ncaa.com/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings"
TRANK_URL = "barttorvik.com/trank.php"

def captures(url: str, day: str) -> list[str]:
    d = date.fromisoformat(day)
    frm = (d - timedelta(days=3)).strftime("%Y%m%d"); to = (d + timedelta(days=2)).strftime("%Y%m%d")
    q = (f"https://web.archive.org/cdx/search/cdx?url={url}&from={frm}&to={to}"
         f"&filter=statuscode:200&output=txt&fl=timestamp,original")
    return [l.split()[0] for l in fetch(q, ttl=86400 * 365, allow_empty=True).splitlines() if l.strip() and "<" not in l]

def pick(stamps: list[str], day: str) -> list[str]:
    """Candidates newest-first, capped at 06:00 UTC the morning after Selection Sunday (data are frozen by then;
    the caller rejects any whose own as-of date is after Selection Sunday)."""
    cutoff = (date.fromisoformat(day) + timedelta(days=1)).strftime("%Y%m%d") + "060000"
    return sorted((s for s in stamps if s <= cutoff), reverse=True)

def snapshot(url: str, stamp: str) -> str:
    return fetch(f"https://web.archive.org/web/{stamp}id_/https://{'www.' if 'ncaa' in url else ''}{url}", ttl=86400 * 365)

def _rows(h: str):
    c = lambda r: [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
    return [c(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)]

def _wl(s):
    m = re.fullmatch(r"(\d+)-(\d+)", s or "")
    return (int(m[1]), int(m[2])) if m else (None, None)

def parse_net(h: str) -> dict:
    rows = _rows(h); hdr = next(r for r in rows if "School" in r and "Rank" in r)
    ix = {n: i for i, n in enumerate(hdr)}
    out = []
    for r in rows:
        if len(r) != len(hdr) or not r[0].isdigit(): continue
        d = {"team": r[ix["School"]], "net": int(r[0]), "conf": r[ix["Conference"]] if "Conference" in ix else None}
        d["w"], d["l"] = _wl(r[ix["Record"]])
        if "WAB" in ix and r[ix["WAB"]].lstrip("-").isdigit(): d["wab_rank"] = int(r[ix["WAB"]])
        for q in "1234":
            k = f"Quad {q}"
            if k in ix: d[f"q{q}_w"], d[f"q{q}_l"] = _wl(r[ix[k]])
        out.append(d)
    m = re.search(r"Through Games ([A-Za-z.]+ \d+ \d{4})", html.unescape(h))
    return {"through": m[1] if m else None, "rows": out}

def parse_trank(h: str) -> dict:
    rows = _rows(h); hdr = next(r for r in rows if r[:2] == ["Rk", "Team"])
    ix = {n: i for i, n in enumerate(hdr)}; out = []
    for r in rows:
        if len(r) != len(hdr) or not r[0].isdigit(): continue
        rec = re.search(r"(\d+-\d+)\s*$", r[ix["Rec"]])
        try:
            out.append({"team": r[ix["Team"]], "trank": int(r[0]), "adjoe": float(r[ix["AdjOE"]]),
                        "adjde": float(r[ix["AdjDE"]]), "barthag": float(r[ix["Barthag"]]),
                        "rec": rec[1] if rec else None})
        except (ValueError, KeyError):
            continue
    return {"rows": out}

def _asof(through: str | None):
    from datetime import datetime
    if not through: return None
    try: return datetime.strptime(through.replace(".", ""), "%b %d %Y").date()
    except ValueError: return None

def build(year: int, outdir="data/history") -> dict:
    import os; os.makedirs(outdir, exist_ok=True)
    day = SELECTION_SUNDAY[year]; res = {"year": year, "selection_day": day}
    for name, url, parser in (("net", NET_URL, parse_net), ("trank", TRANK_URL, parse_trank)):
        res[name] = None
        for st in pick(captures(url, day), day)[:6]:
            try: p = parser(snapshot(url, st))
            except Exception: continue
            asof = _asof(p.get("through"))
            if len(p["rows"]) < 300 or (asof and asof > date.fromisoformat(day)): continue
            res[name] = {"capture": st, "through": p.get("through"), "n": len(p["rows"])}
            json.dump(p, open(f"{outdir}/{year}_{name}.json", "w")); break
    return res
