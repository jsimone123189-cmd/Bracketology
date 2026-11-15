"""docs/31 Test 21: re-order predicted positions 49+ by NET."""
import numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
names = {"control": None, "T21 cut 49": 49, "cut 45 (reported)": 45, "cut 53 (reported)": 53}
res = {n: [] for n in names}; ex = {n: [] for n in names}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    base = sorted(f, key=lambda r: -r["rank_score"])
    for n, c in names.items():
        o = base if c is None else base[:c - 1] + sorted(base[c - 1:], key=lambda r: r["net"])
        L = {r["key"]: slots[i] for i, r in enumerate(o)}; res[n].append(bm.score(L, off)["score"]); ex[n].append(sum(1 for k in L if k in off and L[k] == off[k]))
    print(h, {n: v[-1] for n, v in res.items()}, flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{n:<20}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} exact {np.mean(ex[n]):.1f} pct {[pct(y, v) for y, v in zip(Y, s)]}")
