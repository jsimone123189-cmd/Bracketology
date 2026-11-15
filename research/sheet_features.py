"""docs/29 Test 19: real KPI/SOR/BPI/KenPom ranks as learned seed features, LOSO over 2021, 2022, 2023, 2025."""
import math, numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik_sheets as ts
S4 = [2021, 2022, 2023, 2025]; COLS = ["r_kpi", "r_sor", "r_bpi", "r_kp"]; NEW = ["ts_" + c for c in COLS]
SH = {y: ts.parse(open(f"data/raw/teamsheets/{y}.html", errors="replace").read()) for y in S4}
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in S4}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def add(rows, y):
    for r in rows:
        s = SH[y].get(r["key"], {})
        for c, n in zip(COLS, NEW): r[n] = math.log(s.get(c, 365))
    return rows
ROWS = {y: add((lambda rs: (model.attach_overall(rs, y), rs)[1])(model.prepare(build_year(y))), y) for y in S4}
for y in S4:
    f = [r for r in ROWS[y] if r["in_field"]]; print(y, "field teams found on sheet:", sum(r["key"] in SH[y] for r in f), "/", len(f))
BS, BD = list(model.SELECT), list(model.SEED)
def run(h, sel, seed):
    model.SELECT, model.SEED = sel, seed
    m = model.Model().fit([r for y in S4 if y != h for r in ROWS[y]])
    rows = [dict(r) for r in ROWS[h]]; m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False)
    lines = {r["key"]: r["line"] for r in model.assign_lines(f, h)}; off = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    model.SELECT, model.SEED = BS, BD
    return bm.score(lines, off)["score"], sum(1 for k in lines if k in off and lines[k] == off[k])
res = {n: [] for n in ("control (3-season v2.0)", "T19 seed model", "seed + selection (reported)")}
for h in S4:
    for n, (sel, seed) in zip(res, ((BS, BD), (BS, BD + NEW), (BS + NEW, BD + NEW))): res[n].append(run(h, sel, seed))
    print(h, {n: v[-1] for n, v in res.items()}, flush=True)
c = np.array([s for s, _ in res["control (3-season v2.0)"]])
for n, v in res.items():
    s = np.array([x for x, _ in v]); d = s - c; ok = d.mean() >= 3 and (d > 0).sum() >= 3 and d.min() >= -5
    print(f"{n:<30}{list(s)} mean {s.mean():.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} exact {np.mean([e for _, e in v]):.1f} pct {[pct(y, x) for y, x in zip(S4, s)]}")
