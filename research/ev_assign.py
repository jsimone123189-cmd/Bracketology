"""docs/33 Test 23: expected-score line assignment from nested empirical residuals."""
import collections, math, numpy as np
from scipy.optimize import linear_sum_assignment
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
BANDS = [(1, 16), (17, 32), (33, 48), (49, 999)]; band = lambda p: next(i for i, (a, b) in enumerate(BANDS) if a <= p <= b)
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def ranked(h, exclude):
    m = model.Model().fit(project.training_rows(exclude=exclude)); rows = model.prepare(build_year(h)); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); return rows, sorted(f, key=lambda r: -r["rank_score"])
def pos_probs(p, kind, R, n):
    x = np.arange(1, n + 1)
    if kind == "normal": w = np.exp(-.5 * ((x - p) / R) ** 2)
    else: w = np.exp(-.5 * ((x[:, None] - (p + R[None, :])) / 1.0) ** 2).sum(1)
    return w / w.sum()
def assign(order, slots, kind, R):
    n = len(order); lines = sorted(set(slots)); cost = np.zeros((n, n)); evs = []
    for t in range(n):
        pp = pos_probs(t + 1, kind, R[band(t + 1)], n); pl = {l: pp[[i for i, s in enumerate(slots) if s == l]].sum() for l in lines}
        ev = {l: 3 * pl[l] + pl.get(l - 1, 0) + pl.get(l + 1, 0) for l in lines}; evs.append(ev)
        for j, s in enumerate(slots): cost[t, j] = -ev[s]
    r, c = linear_sum_assignment(cost)
    L = {order[t]["key"]: slots[j] for t, j in zip(r, c)}
    straight = sum(evs[t][slots[t]] for t in range(n)); opt = -cost[r, c].sum()
    return L, opt - straight
res = {n: [] for n in ("control", "T23 empirical EV", "normal EV (reported)")}; ex = {n: [] for n in res}; moved = []; pred_gain = []
for h in Y:
    pool = collections.defaultdict(list)
    for s in Y:
        if s == h: continue
        _, o = ranked(s, {h, s})
        for p, r in enumerate(o, 1):
            if r["in_field"] and r.get("ov"): pool[band(p)].append(r["ov"] - p)
    emp = {b: np.array(pool[b], float) for b in range(4)}; nor = {b: max(1.0, float(np.std(pool[b]))) for b in range(4)}
    rows, o = ranked(h, {h}); off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; slots = fieldformat.format_for(h).slots
    Ls = {"control": {r["key"]: slots[i] for i, r in enumerate(o)}}
    Ls["T23 empirical EV"], g1 = assign(o, slots, "emp", emp); Ls["normal EV (reported)"], g2 = assign(o, slots, "normal", nor)
    moved.append(sum(Ls["T23 empirical EV"][k] != Ls["control"][k] for k in Ls["control"])); pred_gain.append(round(g1, 2))
    for n, L in Ls.items(): res[n].append(bm.score(L, off)["score"]); ex[n].append(sum(1 for k in L if k in off and L[k] == off[k]))
    print(h, {n: v[-1] for n, v in res.items()}, "exact", {n: v[-1] for n, v in ex.items()}, f"| teams moved {moved[-1]} model-predicted EV gain {g1:.2f} (normal {g2:.2f}) | band residual mean {[round(float(emp[b].mean()),2) for b in range(4)]}", flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{n:<22}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} exact {np.mean(ex[n]):.1f} pct {[pct(y, v) for y, v in zip(Y, s)]}")
