"""docs/26: nested random-plus-local weight search on team-sheet metrics, aimed at exact seeds."""
import sys; sys.path.insert(0, "research")
import math, numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.sources import bracketmatrix as bm
import team_sheet_rest as T       # reuses its rows (adds average NET of wins/losses); importing runs its own test first
Y = T.Y; CONTROL = T.CONTROL; rnd = np.random.default_rng(2027)
M = [("net", lambda r: -math.log(r["net"])), ("wab", lambda r: r["wab"]), ("sor", lambda r: r["sor"]), ("rating", lambda r: r["rating"]),
     ("q1_w", lambda r: r["cq1_w"]), ("q1a_w", lambda r: r["q1a_w"]), ("q1_l", lambda r: -r["cq1_l"]), ("q34_l", lambda r: -(r["cq3_l"] + r["cq4_l"])),
     ("road_neut_w", lambda r: r["road_w"] + r["neutral_w"]), ("win_pct", lambda r: r["w"] / max(1, r["w"] + r["l"])), ("sos", lambda r: r["sos"]),
     ("avg_net_w", lambda r: -r["avg_net_w"]), ("avg_net_l", lambda r: -r["avg_net_l"]), ("last10", lambda r: r["last10"])]
def zmat(rows):
    ref = [r for r in rows if r["net"] <= 120]; out = {}
    for n, f in M:
        v = np.array([f(r) for r in ref]); m, s = v.mean(), v.std() + 1e-9
        for r in rows: out.setdefault(r["key"], []).append((f(r) - m) / s)
    return {k: np.array(v) for k, v in out.items()}
DATA = {}
for y in Y:
    rows = T.rows_with(y); Zs = zmat(rows); fld = [r["key"] for r in rows if r["in_field"]]; off = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    DATA[y] = (rows, Zs, fld, off, fieldformat.format_for(y).slots)
def exact(w, y):
    rows, Zs, fld, off, slots = DATA[y]; order = sorted(fld, key=lambda k: -(Zs[k] @ w)); return sum(slots[i] == off[k] for i, k in enumerate(order))
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
res = {"control": [], "W1 composite": [], "W2 half v2.0": []}
for h in Y:
    tr = [y for y in Y if y != h]; tot = lambda w: sum(exact(w, y) for y in tr)
    best, bs = None, -1
    for _ in range(3000):
        w = rnd.random(len(M)); s = tot(w)
        if s > bs: best, bs = w, s
    for _ in range(200):
        i = rnd.integers(len(M)); c = best.copy(); c[i] = min(1, max(0, c[i] + rnd.choice([-.1, .1]))); s = tot(c)
        if s >= bs: best, bs = c, s
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(T.rows_with(h)); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); _, Zs, _, off, slots = DATA[h]
    comp = {r["key"]: float(Zs[r["key"]] @ best) for r in f}; v2 = {r["key"]: r["rank_score"] for r in f}
    z = lambda d: {k: (x - np.mean(list(d.values()))) / np.std(list(d.values())) for k, x in d.items()}
    for n, sc in (("control", v2), ("W1 composite", comp), ("W2 half v2.0", {k: .5 * z(v2)[k] + .5 * z(comp)[k] for k in v2})):
        order = sorted(sc, key=lambda k: -sc[k]); res[n].append(bm.score({k: slots[i] for i, k in enumerate(order)}, off)["score"])
    print(h, {n: v[-1] for n, v in res.items()}, f"training exact {bs / 6:.1f}/season", "weights", {n: round(float(x), 2) for (n, _), x in zip(M, best / best.sum())}, flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    print(f"{n:<16}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75}")
