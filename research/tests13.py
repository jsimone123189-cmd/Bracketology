"""Runs docs/13: Test 4 (champ in the seed model), random line shifts A/B/C, and the pooled spreads for the daily review list."""
import collections, math, random, statistics as st
import numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm

Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
BASE_SEL, BASE_SEED = list(model.SELECT), list(model.SEED)
BANDS = [(1, 16), (17, 32), (33, 48), (49, 999)]
band = lambda p: next(i for i, (a, b) in enumerate(BANDS) if a <= p <= b)
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))

def run(h, train, sel=BASE_SEL, seed=BASE_SEED):
    model.SELECT, model.SEED = sel, seed
    m = model.Model().fit(project.training_rows(exclude=set(Y) - set(train)))
    rows = model.prepare(build_year(h)); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
    return {"rows": {r["key"]: r for r in rows}, "lines": {r["key"]: r["line"] for r in o}, "overall": {r["key"]: r["overall"] for r in o}}
truth = lambda res: {k: r["seed"] for k, r in res["rows"].items() if r["in_field"]}
score = lambda lines, off: bm.score(lines, off)["score"]

ctrl = {h: run(h, set(Y) - {h}) for h in Y}; cs = [score(ctrl[h]["lines"], truth(ctrl[h])) for h in Y]
print("control", cs, "reproduces:", cs == CONTROL, flush=True)

print("\n== Test 4: champ in the seed model")
t4 = [score(r["lines"], truth(r)) for r in (run(h, set(Y) - {h}, BASE_SEL, BASE_SEED + ["champ"]) for h in Y)]
d = np.array(t4) - np.array(cs); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
print(f"Test 4 {t4} mean {np.mean(t4):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)}", flush=True)

print("\n== Pooled held-out spreads for production (all seven seasons)")
pool = collections.defaultdict(list)
for h in Y:
    for k, p in ctrl[h]["overall"].items():
        r = ctrl[h]["rows"][k]
        if r["in_field"] and r["ov"]: pool[band(p)].append(r["ov"] - p)
SPREAD = [round(float(np.std(pool[b])), 2) for b in range(4)]; print("SPREAD =", SPREAD, "n", [len(pool[b]) for b in range(4)], flush=True)

print("\n== Confidence per season (nested spreads, as docs/12)")
conf = {}
for h in Y:
    res = collections.defaultdict(list)
    for s in Y:
        if s == h: continue
        out = run(s, set(Y) - {h, s})
        for k, p in out["overall"].items():
            r = out["rows"][k]
            if r["in_field"] and r["ov"]: res[band(p)].append(r["ov"] - p)
    sig = {b: max(1.0, float(np.std(res[b]))) for b in range(4)}; slots = fieldformat.format_for(h).slots; c = ctrl[h]; conf[h] = {}
    for k, line in c["lines"].items():
        p = c["overall"][k]; pos = [i + 1 for i, l in enumerate(slots) if l == line]; s_ = sig[band(p)]
        pe = Phi((max(pos) + .5 - p) / s_) - Phi((min(pos) - .5 - p) / s_); r = c["rows"][k]
        conf[h][k] = pe * (1.0 if r["champ"] else r["p_in"])
    print(f"  {h}: {sum(v < .5 for v in conf[h].values())} teams under 0.5", flush=True)

print("\n== Random shifts, 2,000 draws per season")
def matrix_p90(y):
    v = sorted(int(x) for k, x in bm.collect(y)["reported"]["SCORE"].items() if x.isdigit() and k != "MATRIX"); return v[int(.9 * len(v))]
P90 = {y: matrix_p90(y) for y in Y}
def exact58(lines, off): return sum(1 for k in lines if k in off and 5 <= off[k] <= 8 and lines[k] == off[k])
def draw(lines, pool_keys, mode, rnd):
    new = dict(lines); ks = list(pool_keys); rnd.shuffle(ks); n2 = round(.05 * len(ks)); n1 = round(.25 * len(ks))
    for i, k in enumerate(ks[:n2 + n1]):
        step = 2 if i < n2 else 1; tgt = new[k] + rnd.choice((-step, step))
        if not 1 <= tgt <= 16: tgt = new[k] - (tgt - new[k])
        if mode == "swap":
            mates = [x for x in new if new[x] == tgt and x != k]
            if not mates: continue
            m = rnd.choice(mates); new[m] = new[k]
        new[k] = tgt
    return new
rnd = random.Random(2027)
for name, mode, low in (("A all teams", "free", False), ("B low confidence", "free", True), ("C legal swaps, low confidence", "swap", True)):
    print(f"-- {name}"); allc = []
    for h in Y:
        lines = ctrl[h]["lines"]; off = truth(ctrl[h]); base = score(lines, off); b58 = exact58(lines, off)
        keys = [k for k in lines if conf[h][k] < .5] if low else list(lines)
        ch, c58, hit = [], [], 0
        for _ in range(2000):
            n = draw(lines, keys, mode, rnd); s = score(n, off); ch.append(s - base); c58.append(exact58(n, off) - b58); hit += s >= P90[h]
        allc += ch; q = np.percentile(ch, [5, 95])
        print(f"   {h} base {base} mean {np.mean(ch):+.1f}  better {np.mean(np.array(ch) > 0):.0%}  +3 or more {np.mean(np.array(ch) >= 3):.0%}  5th/95th {q[0]:+.0f}/{q[1]:+.0f}  exact 5-8 {np.mean(c58):+.2f}  reach 90th pct ({P90[h]}) {hit / 2000:.1%} vs {'yes' if base >= P90[h] else 'no'} without")
    print(f"   overall mean change {np.mean(allc):+.2f}", flush=True)
