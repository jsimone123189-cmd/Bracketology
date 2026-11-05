from __future__ import annotations
"""Warren Nolan compare-rankings: one table with NET, ELO, KPI, SOR, WAB, BPI, POM, T-Rank, SAG, RPI for every team.
robots.txt: Allow /. Current-season pages are as-of-today. Past-season pages are FINAL (they include the NCAA tournament),
so they must never be used as Selection Sunday history. Terms of use not yet confirmed: ask the site owner before launch,
and do not republish KenPom/KPI/ESPN values on the public site without checking."""
import html, re
from ..http import fetch

COLUMNS = {"NET": "r_net", "ELO": "r_elo", "KPI": "r_kpi", "SOR": "r_sor", "WAB": "r_wab", "BPI": "r_bpi",
           "POM": "r_kp", "T-Rank": "r_trk", "SAG": "r_sag", "RPI": "r_rpi"}

def url(season): return f"https://www.warrennolan.com/basketball/{season}/compare-rankings"

def parse(text: str) -> list[dict]:
    cell = lambda r: [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
                      for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
    rows = [cell(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)]
    hdr = next(r for r in rows if r[:2] == ["Team", "Record"])
    out = []
    for r in rows:
        if len(r) != len(hdr) or r[0] == "Team":
            continue
        d = {"team": r[0], "record": r[1]}
        for name, dst in COLUMNS.items():
            if name in hdr and r[hdr.index(name)].isdigit() and int(r[hdr.index(name)]) > 0:   # 0 = not published
                d[dst] = int(r[hdr.index(name)])
        out.append(d)
    return out

def parse_autobids(text: str) -> dict[str, str]:
    """{conference: team} for leagues whose auto-bid is decided. Reflects eligibility rules, so reclassifying champions aren't listed."""
    cell = lambda r: [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
    rows = [cell(r) for r in re.split(r"<tr\b", text)[1:]]
    return {r[0]: r[1] for r in rows if len(r) >= 2 and r[0] != "Conference" and r[1] and r[1] != "N/A"}

def autobids(season: int, ttl: int = 3600) -> dict[str, str]:
    return parse_autobids(fetch(f"https://www.warrennolan.com/basketball/{season}/autobids", ttl=ttl))

def collect(season: int, ttl: int = 3600) -> dict:
    return {"source": "warrennolan_compare", "url": url(season), "rows": parse(fetch(url(season), ttl=ttl))}
