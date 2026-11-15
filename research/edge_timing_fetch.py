"""docs/36: fetch D-7 Bracket Matrix snapshots and D-7 NET captures from the Internet Archive (cached)."""
import datetime as dt, json, re, os
from bracketology import history
from bracketology.http import fetch
from bracketology.sources import bracketmatrix as bm
OUT = "data/history/edge_timing"; os.makedirs(OUT, exist_ok=True)
MON = {m: i for i, m in enumerate(["January", "February", "March", "April"], 1)}
def cdx(url, a, b):
    q = f"https://web.archive.org/cdx/search/cdx?url={url}&from={a:%Y%m%d}&to={b:%Y%m%d}&filter=statuscode:200&output=txt&fl=timestamp"
    return [l.split()[0] for l in fetch(q, ttl=86400 * 365, allow_empty=True).splitlines() if l.strip() and "<" not in l]
def parse_live(t, year):
    rows = [bm._cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
    i = next(i for i, r in enumerate(rows) if len(r) > 10 and "Average Seed" in r)
    hdr, dates = rows[i], rows[i + 1]; m = re.search(r"Updated:?\s*([A-Za-z]+)\s+(\d+)", " ".join(hdr))
    upd = dt.date(year, MON[m[1]], int(m[2]))
    sites = {j: n for j, n in enumerate(hdr) if j >= 6 and n}; subs = {n: {} for n in sites.values()}; sd = {}
    for j, n in sites.items():
        d = re.fullmatch(r"(\d+)/(\d+)", dates[j] if j < len(dates) else "")
        if d: sd[n] = dt.date(year, int(d[1]), int(d[2])).isoformat()
    for r in rows[i + 2:]:
        if len(r) > 6 and r[1] and re.fullmatch(r"\d+\.\d+", r[3] or ""):
            for j, n in sites.items():
                if j < len(r) and re.fullmatch(r"\d{1,2}", r[j] or ""): subs[n][r[1]] = int(r[j])
    return upd, subs, sd
for y in sorted(history.SELECTION_SUNDAY):
    ss = dt.date.fromisoformat(history.SELECTION_SUNDAY[y]); d7 = ss - dt.timedelta(days=7); best = None
    for st in sorted(cdx("bracketmatrix.com/", d7 - dt.timedelta(days=3), d7 + dt.timedelta(days=2))):
        try: upd, subs, sd = parse_live(fetch(f"https://web.archive.org/web/{st}id_/http://bracketmatrix.com/", ttl=86400 * 365), y)
        except Exception as e: print(y, st, "parse fail", type(e).__name__); continue
        if d7 - dt.timedelta(days=2) <= upd <= d7 and (best is None or upd >= best[1]): best = (st, upd, subs, sd)
    if best: json.dump({"stamp": best[0], "updated": best[1].isoformat(), "subs": best[2], "dates": best[3]}, open(f"{OUT}/{y}_matrix_d7.json", "w"))
    print(y, "D-7", d7, "matrix:", (best[0], best[1].isoformat(), len(best[2])) if best else None, flush=True)
    net = None
    for st in sorted(cdx(history.NET_URL, d7 - dt.timedelta(days=3), d7 + dt.timedelta(days=1)), reverse=True):
        try: p = history.parse_net(history.snapshot(history.NET_URL, st))
        except Exception: continue
        th = history._asof(p["through"])
        if th and d7 - dt.timedelta(days=2) <= th <= d7 and len(p["rows"]) > 300: net = (st, th, p); break
    if net: json.dump({"stamp": net[0], "through": net[1].isoformat(), "rows": net[2]["rows"]}, open(f"{OUT}/{y}_net_d7.json", "w"))
    print(y, "D-7 NET:", (net[0], net[1].isoformat(), len(net[2]["rows"])) if net else None, flush=True)
