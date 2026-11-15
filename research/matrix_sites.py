"""Matrix entry abbreviation -> link, per season, plus seven-season percentile record. Diagnostic."""
import re, html, statistics as st
from bracketology.http import fetch
from bracketology.sources import bracketmatrix as bm
Y = [2019, 2021, 2022, 2023, 2024, 2025, 2026]
def links(y):
    t = fetch(bm.url(y), ttl=86400 * 30); hdr = next(r for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S) if "RESULTS" in r)
    return {re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", a))).strip(): u for u, a in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', hdr, re.S)}
L = {y: links(y) for y in Y}
S = {y: {k: int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX"} for y in Y}
pct = lambda y, s: 100 * sum(v < s for v in S[y].values()) / len(S[y])
rec = {}
for k in {k for y in Y for k in S[y]}:
    ys = [y for y in Y if k in S[y]]; p = [pct(y, S[y][k]) for y in ys]
    url = next((L[y].get(k) for y in reversed(Y) if L[y].get(k)), "")
    rec[k] = (len(ys), st.mean(p), min(p), url, [round(x) for x in p])
if __name__ == "__main__":
    print("== the consistent nine")
    for k in ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]: print(f"  {k:<8} {rec[k][3]}")
    print("\n== entries whose link suggests a model or rating site (5+ seasons)")
    pat = re.compile(r"torvik|warrennolan|teamrankings|haslam|model|analytic|metric|kenpom|espn.com/.*bpi|rating|numbers|data|stat|algorithm|dancecard|computer|sim", re.I)
    for k, v in sorted(rec.items(), key=lambda x: -x[1][1]):
        if v[0] >= 5 and (pat.search(v[3]) or pat.search(k)): print(f"  {k:<10} n{v[0]} mean pct {v[1]:.0f} worst {v[2]:.0f} {v[4]} {v[3]}")
