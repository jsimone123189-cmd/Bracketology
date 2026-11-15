"""docs/34: owner's V1 spreadsheet formula on all seven seasons, disagreement analysis vs v2.0, conditional hybrid (Test 24)."""
import numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def s(x, clamp): x = min(x, 200) if clamp else x; return 100 * (1 - (x - 1) / 199) ** 2
def add_v1(rows):
    rk = {}
    for f in ("wab", "sor", "rating"):
        for i, r in enumerate(sorted(rows, key=lambda r: -r[f])): rk[(f, r["key"])] = i + 1
    for r in rows:
        for c, name in ((False, "v1"), (True, "v1c")):
            r[name] = (.15 * r["q1a_w"] + .13 * r["cq1_w"] + .12 * r["cq2_w"] - .5 * r["cq3_l"] - 1.5 * r["cq4_l"]
                       + .24 * s(rk[("wab", r["key"])], c) + .19 * s(rk[("sor", r["key"])], c) + .17 * s(r["net"], c) + .10 * s(rk[("rating", r["key"])], c))
SIT = {"pred lines 1-4": lambda r, l: l <= 4, "pred lines 5-8": lambda r, l: 5 <= l <= 8, "pred lines 9-12": lambda r, l: 9 <= l <= 12,
       "pred lines 13-16": lambda r, l: l >= 13, "small-conf champs": lambda r, l: r["champ"] and not r["is_power"],
       "non-power at-large": lambda r, l: not r["champ"] and not r["is_power"], "power at-large": lambda r, l: not r["champ"] and r["is_power"]}
res = {n: [] for n in ("control", "V1-full faithful", "V1-full clamped", "V1-seed (v2 field)")}; ex = {n: [] for n in res}
sit = {k: [] for k in SIT}; keep = {}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows); add_v1(rows)
    off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    f, _ = model.choose_field(rows, h, project_autos=False); o2 = sorted(f, key=lambda r: -r["rank_score"])
    L = {"control": {r["key"]: slots[i] for i, r in enumerate(o2)}}
    for name, key in (("V1-full faithful", "v1"), ("V1-full clamped", "v1c")):
        rr = [dict(r, p_in=r[key], rank_score=r[key]) for r in rows]; ff, _ = model.choose_field(rr, h, project_autos=False)
        L[name] = {r["key"]: slots[i] for i, r in enumerate(sorted(ff, key=lambda r: -r[key]))}
    o1 = sorted(f, key=lambda r: -r["v1"]); L["V1-seed (v2 field)"] = {r["key"]: slots[i] for i, r in enumerate(o1)}
    for n, l in L.items(): res[n].append(bm.score(l, off)["score"]); ex[n].append(sum(1 for k in l if k in off and l[k] == off[k]))
    R = {r["key"]: r for r in f}; keep[h] = (f, o2, L, off, slots)
    for k, fn in SIT.items():
        ks = [x for x in L["control"] if x in off and fn(R[x], L["control"][x])]
        e2 = np.mean([abs(L["control"][x] - off[x]) for x in ks]) if ks else np.nan; e1 = np.mean([abs(L["V1-seed (v2 field)"][x] - off[x]) for x in ks]) if ks else np.nan
        sit[k].append((len(ks), e2, e1))
    print(h, {n: v[-1] for n, v in res.items()}, "exact", {n: v[-1] for n, v in ex.items()}, flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, sc in res.items():
    d = np.array(sc) - np.array(CONTROL)
    print(f"{n:<22}{sc} mean {np.mean(sc):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} exact {np.mean(ex[n]):.1f} pct {[pct(y, v) for y, v in zip(Y, sc)]}")
print("\nDisagreement analysis: mean absolute seed error, v2.0 vs V1-seed, teams in v2.0's field and the real field")
qual = []
for k, v in sit.items():
    wins = sum(1 for n, a, b in v if n and b < a); ties = sum(1 for n, a, b in v if n and b == a)
    print(f"  {k:<20} n/season {[n for n, _, _ in v]}  v2 {np.nanmean([a for _, a, _ in v]):.2f}  V1 {np.nanmean([b for _, _, b in v]):.2f}  V1 better in {wins}/7 (ties {ties})  {'QUALIFIES' if wins >= 6 else ''}")
    if wins >= 6: qual.append(k)
if not qual: print("\nNo situation favors V1 in 6+ seasons: Test 24 not run (docs/34 rule)."); raise SystemExit
print("\nTest 24 hybrid, qualifying situations:", qual)
t24 = []
for h in Y:
    f, o2, L, off, slots = keep[h]; R = {r["key"]: r for r in f}; ctl = L["control"]
    pos = [i for i, r in enumerate(o2) if any(SIT[q](r, ctl[r["key"]]) for q in qual)]
    new = list(o2); grp = sorted([o2[i] for i in pos], key=lambda r: -r["v1"])
    for i, r in zip(pos, grp): new[i] = r
    l = {r["key"]: slots[i] for i, r in enumerate(new)}; t24.append(bm.score(l, off)["score"])
d = np.array(t24) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
print(f"T24 hybrid {t24} mean {np.mean(t24):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {[pct(y, v) for y, v in zip(Y, t24)]}")
