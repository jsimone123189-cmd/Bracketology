"""docs/23 Test 11: recent NCAA tournament appearances (previous three tournaments held) in both models."""
import numpy as np
from bracketology import history, model, project
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
FIELDS = {y: {key(t) for t in bm.collect(y)["official"]} for y in range(2016, 2026) if y != 2020}
PREV = {2019: [2016, 2017, 2018], 2021: [2017, 2018, 2019], 2022: [2018, 2019, 2021], 2023: [2019, 2021, 2022], 2024: [2021, 2022, 2023], 2025: [2022, 2023, 2024], 2026: [2023, 2024, 2025]}
_c = {}
def rows_with(y):
    if y not in _c:
        rows = raw_build(y)
        for r in rows: r["recent_apps"] = float(sum(r["key"] in FIELDS[p] for p in PREV[y]))
        _c[y] = rows
    return [dict(r) for r in _c[y]]
project.build_year = rows_with; model.BASE = model.BASE + ["recent_apps"]; SEL, SEED = list(model.SELECT), list(model.SEED)
for y in Y:
    fl = [r for r in rows_with(y) if r["in_field"]]; print(f"  {y}: field teams with 0/1/2/3 recent appearances {[sum(r['recent_apps'] == n for r in fl) for n in range(4)]}")
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def loso(sel, seed):
    model.SELECT, model.SEED = sel, seed; s, e = [], []
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(rows_with(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h); off = {r["key"]: r["seed"] for r in rows if r["in_field"]}
        L = {r["key"]: r["line"] for r in o}; s.append(bm.score(L, off)["score"]); e.append(sum(1 for k in L if k in off and L[k] == off[k]))
    return s, e
cs, ce = loso(SEL, SEED); print("control", cs, "reproduces:", cs == CONTROL, flush=True)
s, e = loso(SEL + ["z_recent_apps"], SEED + ["z_recent_apps"]); d = np.array(s) - np.array(cs); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
print(f"Test 11 recent apps {s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75} exact {np.mean(ce):.1f} -> {np.mean(e):.1f}")
