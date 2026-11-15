"""docs/14: seeding with the actual field, v2.0 vs real team-sheet metrics, four seasons."""
import sys; sys.path.insert(0, "research")
import numpy as np, matrix_full
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik_sheets as ts
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); S4 = [2021, 2022, 2023, 2025]
GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]
def seed_by(order, off, season):
    slots = fieldformat.format_for(season).slots; lines = {k: slots[i] for i, k in enumerate(order)}
    return sum(lines[k] == off[k] for k in order), bm.score(lines, off)["score"]
res = {}
for h in S4:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    R = {r["key"]: r for r in rows}; off = {k: r["seed"] for k, r in R.items() if r["in_field"]}
    sh = ts.parse(open(f"data/raw/teamsheets/{h}.html", errors="replace").read())
    miss = [k for k in off if k not in sh]
    if miss: print(h, "teams missing from sheet:", miss)
    fld = [k for k in off if k in sh]
    avg = lambda k, cols: np.mean([sh[k][c] for c in cols])
    z = lambda d: {k: (v - np.mean(list(d.values()))) / np.std(list(d.values())) for k, v in d.items()}
    v2 = {k: -R[k]["rank_score"] for k in fld}; tsa = {k: avg(k, ["r_net", "r_kpi", "r_sor", "r_bpi", "r_kp"]) for k in fld}
    blend = {k: .5 * z(v2)[k] + .5 * z(tsa)[k] for k in fld}
    methods = {"v2.0": v2, "sheet average": tsa, "resume only": {k: avg(k, ["r_kpi", "r_sor"]) for k in fld},
               "predictive only": {k: avg(k, ["r_bpi", "r_kp"]) for k in fld}, "blend": blend}
    offf = {k: off[k] for k in fld}; out = {}
    for n, d in methods.items(): out[n] = seed_by(sorted(fld, key=lambda k: (d[k], R[k]["net"])), offf, h)
    subs = matrix_full.submissions(h); g = []
    for s in GROUP:
        if s in subs:
            x = {key(t): l for t, l in subs[s].items()}; g.append(sum(1 for k in fld if x.get(k) == off[k]))
    out["group (own fields)"] = (np.mean(g), None); res[h] = out
    print(h, f"n={len(fld)}", "  ".join(f"{n}: {e:.1f} exact" + (f", {s}" if s else "") for n, (e, s) in out.items()), flush=True)
for n in ("sheet average", "blend"):
    w = sum(res[h][n][0] - res[h]["v2.0"][0] >= 2 for h in S4)
    print(f"DECISION {n}: beats v2.0 by 2+ exact in {w}/4 seasons, mean diff {np.mean([res[h][n][0] - res[h]['v2.0'][0] for h in S4]):+.1f} -> missing piece: {w >= 3}")
