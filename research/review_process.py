"""docs/35 Diagnostic R: does v2.0's low-confidence list capture where informed review pays? Expert brackets as proxy reviewers (diagnostic only)."""
import sys; sys.path.insert(0, "research")
import numpy as np, matrix_full
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); REV = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3", "RFS"]
tot = {"low": 0, "high": 0, "all": 0}; touched = {"low": 0, "all": 0}; season_low = []
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h); project.confidence(o, h)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; V = {r["key"]: r["line"] for r in o}
    C = {r["key"]: r["confidence"] for r in o}; base = bm.score(V, off)["score"]; subs = matrix_full.submissions(h); sl = []
    for rv in REV:
        if rv not in subs: continue
        E = {key(t): l for t, l in subs[rv].items()}; g = {}
        for mode, pick in (("low", lambda k: C[k] < .5), ("high", lambda k: C[k] >= .5), ("all", lambda k: True)):
            L = {k: (E[k] if k in E and pick(k) else v) for k, v in V.items()}; g[mode] = bm.score(L, off)["score"] - base
            if mode in touched: touched[mode] += sum(1 for k in V if k in E and pick(k))
            tot[mode] += g[mode]
        sl.append(g["low"])
        print(f"  {h} {rv:<7} low-confidence only {g['low']:+d}  high-confidence only {g['high']:+d}  everything {g['all']:+d}")
    season_low.append(np.mean(sl)); print(h, f"mean gain from low-confidence review {np.mean(sl):+.1f} over {len(sl)} reviewers; low list size {sum(c < .5 for c in C.values())}", flush=True)
ratio = tot["low"] / tot["all"] if tot["all"] else float("nan"); frac = touched["low"] / touched["all"]
print(f"\nPooled gains: low-only {tot['low']:+d}, high-only {tot['high']:+d}, everything {tot['all']:+d}. Low-only keeps {ratio:.0%} of the full gain while touching {frac:.0%} of teams.")
print(f"Seasons where low-only review gained on average: {sum(x > 0 for x in season_low)}/7 {[round(x,1) for x in season_low]}")
print("CAPTURES WHERE REVIEW PAYS:", ratio >= .6 and frac < .5 and sum(x > 0 for x in season_low) >= 6)
