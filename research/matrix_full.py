"""Research-only reader: every team each bracket listed, including the Matrix's "other at-large" rows, which
bracketmatrix.parse leaves out of submissions. Production is unchanged."""
import re
from bracketology.http import fetch
from bracketology.sources import bracketmatrix as bm

def submissions(year: int) -> dict:
    text = fetch(bm.url(year), ttl=86400 * 30); rows = [bm._cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)]
    hdr = next(r for r in rows if len(r) > 10 and "RESULTS" in r[1]); sites = {i: n for i, n in enumerate(hdr) if i >= 5 and n}
    subs = {n: {} for n in sites.values()}
    for r in rows:
        if len(r) > 5 and r[1] and re.fullmatch(r"\d+\.\d+", r[3] or "") and re.fullmatch(r"\d+", r[4] or ""):
            for i, n in sites.items():
                if i < len(r) and re.fullmatch(r"\d{1,2}", r[i] or ""): subs[n][r[1]] = int(r[i])
    return subs
