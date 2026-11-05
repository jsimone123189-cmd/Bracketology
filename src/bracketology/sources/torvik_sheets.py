from __future__ import annotations
"""Parse archived barttorvik.com/teamsheets.php pages: real committee metrics (NET, KPI, SOR, BPI, KenPom rank, Sagarin
or T-Rank, sometimes WAB) as of a capture near Selection Sunday. Team names may carry a trailing seed ("Gonzaga 1"):
that is discarded here because it can be post-selection information."""
import html, re
from ..teams import key

def _cells(r):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
            for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]

def _record(s):
    m = re.search(r"(\d+)-(\d+)\s*$", s or "")
    return (int(m[1]), int(m[2])) if m else (None, None)

def parse(text: str) -> dict[str, dict]:
    # Split on <tr: the page repeats header blocks whose <tr> is never closed, so tag pairing swallows data rows.
    rows = [_cells(r) for r in re.split(r"<tr\b", text)[1:]]
    hdr = next(r for r in rows if r[:2] == ["Rk", "Team"])
    width = max(len(r) for r in rows if r and r[0].isdigit())
    if len(hdr) == width + 1 and "Super Avg." in hdr:   # header-only column: data rows omit it
        hdr = [n for n in hdr if n != "Super Avg."]
    ix = {}
    for i, n in enumerate(hdr):
        ix.setdefault(n, i)
    out = {}
    for r in rows:
        if len(r) < len(hdr) or not r[0].isdigit():
            continue
        name = re.sub(r"\s+(\d{1,2}|F4O|N4O)$", "", r[ix["Team"]])
        d = {"team": name}
        for src, dst in (("NET", "r_net"), ("KPI", "r_kpi"), ("SOR", "r_sor"), ("WAB", "r_wab"), ("BPI", "r_bpi"),
                         ("KP", "r_kp"), ("Sag", "r_sag"), ("TRK", "r_trk")):
            if src in ix and r[ix[src]].isdigit():
                d[dst] = int(r[ix[src]])
        if "Q1A" in ix:
            d["sheet_q1a_w"], d["sheet_q1a_l"] = _record(r[ix["Q1A"]])
        q1 = "All Q1" if "All Q1" in ix else "Q1"
        d["sheet_q1_w"], d["sheet_q1_l"] = _record(r[ix[q1]])
        out[key(name)] = d
    return out
