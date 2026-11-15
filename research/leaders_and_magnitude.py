"""Runs docs/11: where the consistent group beats v2.0, and the Torvik rating magnitude diagnostic. Diagnostics only."""
import json, statistics as st
import numpy as np
from scipy.stats import spearmanr
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key

Y = sorted(history.SELECTION_SUNDAY); GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]
V2 = {}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
    V2[h] = {"lines": {r["key"]: r["line"] for r in o}, "overall": {r["key"]: r["overall"] for r in o}, "rows": {r["key"]: r for r in rows}}
print("control", [bm.score(V2[h]["lines"], {k: r["seed"] for k, r in V2[h]["rows"].items() if r["in_field"]})["score"] for h in Y], flush=True)

def describe(lines, off, rows):
    s = bm.score(lines, off); both = [k for k in lines if k in off]
    band = {b: np.mean([lines[k] == off[k] for k in both if (off[k] - 1) // 4 == b]) for b in range(4)}
    signed = {p: [lines[k] - off[k] for k in both if not rows[k]["champ"] and rows[k]["is_power"] == p] for p in (1.0, 0.0)}
    return {"picked": s["picked"], "exact": s["exact"], "within1": s["within1"], "score": s["score"], "band": band,
            "power_err": np.mean(signed[1.0]), "nonpower_err": np.mean(signed[0.0]), "wrong": sorted(k for k in lines if k not in off)}

print("\n== 2. Where the group beats v2.0")
cand = []
for h in Y:
    rows = V2[h]["rows"]; off = {k: r["seed"] for k, r in rows.items() if r["in_field"]}
    subs = bm.collect(h)["submissions"]; G = {g: {key(t): l for t, l in subs[g].items()} for g in GROUP if g in subs}
    unk = {k for g in G.values() for k in g if k not in rows}
    if unk: print("   unmatched names", h, sorted(unk)[:6])
    v = describe(V2[h]["lines"], off, rows); gs = [describe(G[g], off, rows) for g in G]
    avg = lambda f: np.mean([x[f] for x in gs])
    print(f"{h} n={len(G)}  picked v2 {v['picked']} grp {avg('picked'):.1f} | exact {v['exact']} vs {avg('exact'):.1f} | within1 {v['within1']} vs {avg('within1'):.1f} | score {v['score']} vs {avg('score'):.1f}")
    print(f"      exact rate by band 1-4/5-8/9-12/13-16  v2 {[float(round(v['band'][b], 2)) for b in range(4)]}  grp {[float(round(np.mean([x['band'][b] for x in gs]), 2)) for b in range(4)]}")
    print(f"      mean signed line error at-large power v2 {v['power_err']:+.2f} grp {avg('power_err'):+.2f} | non-power v2 {v['nonpower_err']:+.2f} grp {avg('nonpower_err'):+.2f}")
    for k in v["wrong"]: print(f"      v2 wrong team in: {rows[k]['team']} (NET {rows[k]['net']}), group had it in {sum(k in G[g] for g in G)}/{len(G)}")
    for k in sorted(off, key=off.get):
        right = sum(1 for g in G.values() if k in g and abs(g[k] - off[k]) <= 1); vl = V2[h]["lines"].get(k)
        if right >= .75 * len(G) and (vl is None or abs(vl - off[k]) >= 2):
            r = rows[k]; cand.append((h, r["team"], off[k], vl, right, len(G), r["net"], r["is_power"], r["champ"], r.get("wab_rank"), r.get("rating_rank"), r["cq1_w"], r["cq1_l"], r["sos"]))
print("\nTeams the group placed (75%+ within one line) where v2.0 missed by 2+ or left out")
print("season team seed v2line grp_right/n NET power champ WABrk ratingrk Q1 W-L SOS")
for c in cand: print("  ", c[0], f"{c[1]:<16}", c[2], c[3], f"{c[4]}/{c[5]}", c[6], int(c[7]), int(c[8]), c[9], c[10], f"{c[11]}-{c[12]}", round(c[13], 1))
print("count", len(cand), "v2 line too good (lower number) in", sum(1 for c in cand if c[3] and c[3] < c[2]), "too bad in", sum(1 for c in cand if c[3] and c[3] > c[2]), "left out", sum(1 for c in cand if c[3] is None))

print("\n== 3. Rating magnitude (Torvik held for 2019, 2022-25)")
per = []
for h in (2019, 2022, 2023, 2024, 2025):
    tr = {key(r["team"].split("\xa0")[0]): r for r in json.load(open(f"data/history/{h}_trank.json"))["rows"]}; rows = V2[h]["rows"]
    fld = [k for k, r in rows.items() if r["in_field"] and k in tr and k in V2[h]["overall"] and rows[k]["ov"]]
    em = np.array([tr[k]["adjoe"] - tr[k]["adjde"] for k in fld]); ours = np.array([rows[k]["rating"] for k in fld])
    mag = (em - em.mean()) / em.std() - (ours - ours.mean()) / ours.std()
    rk = np.array([np.log(rows[k]["rating_rank"]) - np.log(tr[k]["trank"]) for k in fld])
    res = np.array([rows[k]["ov"] - V2[h]["overall"][k] for k in fld], float)
    cm, cr = spearmanr(res, mag)[0], spearmanr(res, rk)[0]
    X = np.column_stack([np.ones(len(fld)), rk, mag]); b = np.linalg.lstsq(X, res, rcond=None)[0]
    per.append((cm, b[2]))
    out_in = [k for k, r in rows.items() if r["in_field"] and k not in V2[h]["lines"] and not r["champ"]]; in_out = [k for k in V2[h]["lines"] if not rows[k]["in_field"]]
    def gaps(ks):
        z = lambda v, a: (v - a.mean()) / a.std()
        return [(rows[k]["team"], round(z(tr[k]["adjoe"] - tr[k]["adjde"], em) - z(rows[k]["rating"], ours), 2), round(float(np.log(rows[k]["rating_rank"]) - np.log(tr[k]["trank"])), 2)) for k in ks if k in tr]
    print(f"{h} n={len(fld)} corr(residual, magnitude gap) {cm:+.3f}  corr(residual, rank gap) {cr:+.3f}  magnitude coef after rank {b[2]:+.2f}")
    print("      committee in, v2 out (magnitude gap, rank gap):", gaps(out_in), " v2 in, committee out:", gaps(in_out))
    big = [(rows[k]["team"], rows[k]["seed"], V2[h]["lines"][k], round(float(m_), 2)) for k, m_ in zip(fld, mag) if abs(V2[h]["lines"][k] - rows[k]["seed"]) >= 2]
    print("      2+ line misses (team, seed, v2 line, magnitude gap):", big)
neg = sum(c < 0 for c, _ in per); mean = np.mean([c for c, _ in per]); negb = sum(b < 0 for _, b in per)
print(f"DECISION: negative in {neg}/5, mean {mean:+.3f}, coefficient negative in {negb}/5 -> explains misses: {neg >= 4 and mean <= -.15 and negb >= 4}")
