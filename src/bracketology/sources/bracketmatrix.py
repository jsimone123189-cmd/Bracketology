from __future__ import annotations
"""Parse final Bracket Matrix pages (matrix_YYYY.html): official seeds + every site's submitted bracket.
Fetch over plain http (https handshake fails from some hosts). One request per season, cached on disk."""
import html, re
from ..http import fetch

def url(year): return f"http://bracketmatrix.com/matrix_{year}.html"

def _cells(row: str) -> list[str]:
    """Cell texts with colspan expanded so every row is column-aligned with the header."""
    out = []
    for attrs, c in re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", row, re.S):
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c))).replace("\xa0", "").strip()
        m = re.search(r"colspan\s*=\s*\"?(\d+)", attrs, re.I)
        out.append(txt)
        out.extend([""] * (int(m.group(1)) - 1 if m else 0))
    return out

def parse(text: str) -> dict:
    rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)]
    hdr = next(r for r in rows if len(r) > 10 and r[1] in ("FINAL RESULTS", "OFFICIAL RESULTS"))
    sites = {i: n for i, n in enumerate(hdr) if i >= 5 and n}
    reported = {}
    for r in rows:
        if r and len(r) > 5 and r[1] in ("TEAMS PICKED CORRECTLY", "TEAMS SEEDED CORRECTLY",
                                         "TEAMS SEEDED CORRECTLY OR +/- 1", "SCORE"):
            reported[r[1]] = {n: r[i] for i, n in sites.items() if r[i]}
    teams, official = [], {}
    # team rows: col0 = official seed line (1-16), col1 = team, col2 = conf, col3 = avg seed, col4 = # brackets
    for r in rows:
        if len(r) > 6 and re.fullmatch(r"\d{1,2}", r[0] or "") and r[1] and re.fullmatch(r"\d+\.\d+", r[3] or ""):
            teams.append(r)
    subs = {n: {} for n in sites.values()}
    for r in teams:
        official[r[1]] = int(r[0])
        for i, n in sites.items():
            if i < len(r) and re.fullmatch(r"\d{1,2}", r[i] or ""): subs[n][r[1]] = int(r[i])
    return {"sites": list(sites.values()), "official": official, "submissions": subs, "reported": reported}

def score(sub: dict[str, int], official: dict[str, int]) -> dict:
    picked = sum(1 for t in sub if t in official)
    exact = sum(1 for t, s in sub.items() if official.get(t) == s)
    near = sum(1 for t, s in sub.items() if t in official and abs(official[t] - s) <= 1)
    return {"picked": picked, "exact": exact, "within1": near, "score": 3 * picked + 3 * exact + (near - exact)}

def collect(year: int) -> dict:
    return parse(fetch(url(year), ttl=86400 * 30))
