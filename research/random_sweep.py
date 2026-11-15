"""Owner follow-up to docs/13: random shifts at other sizes and only on the lowest-confidence teams. Diagnostic only."""
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

BANDS = [(1, 16), (17, 32), (33, 48), (49, 999)]
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

def sweep(lines, keys, p2, p1, rnd, n=500, off=None):
    out = []
    for _ in range(n):
        new = dict(lines); ks = list(keys); rnd.shuffle(ks); n2 = round(p2 * len(lines)); n1 = round(p1 * len(lines))
        n2, n1 = min(n2, len(ks)), min(n1, max(0, len(ks) - n2))
        for i, k in enumerate(ks[:n2 + n1]):
            step = 2 if i < n2 else 1; tgt = new[k] + rnd.choice((-step, step))
            if not 1 <= tgt <= 16: tgt = new[k] - (tgt - new[k])
            new[k] = tgt
        out.append((score(new, off) - score(lines, off), exact58(new, off) - exact58(lines, off)))
    return out
def exact58(lines, off): return sum(1 for k in lines if k in off and 5 <= off[k] <= 8 and lines[k] == off[k])
rnd = random.Random(7)
print("\n== Size sweep: share of the FIELD moved 2 lines / 1 line, random direction, 500 draws per season")
print("pool              2-line  1-line  teams  mean/season  worst season  best season  P(any season +3)  lines 5-8 exact")
for label, cut in (("all teams", 9), ("conf < 0.5", .5), ("conf < 0.3", .3), ("conf < 0.2", .2), ("conf < 0.1", .1)):
    for p2, p1 in ((0, .01), (.01, .02), (.02, .05), (.05, .25), (.10, .40), (.20, .50)):
        per, e58, hit = [], [], []
        for h in Y:
            lines = ctrl[h]["lines"]; off = truth(ctrl[h]); keys = [k for k in lines if conf[h][k] < cut]
            r = sweep(lines, keys, p2, p1, rnd, off=off); per.append(np.mean([a for a, _ in r])); e58.append(np.mean([b for _, b in r])); hit.append(np.mean([a >= 3 for a, _ in r]))
        moved = min(round((p2 + p1) * 68), np.mean([sum(conf[h][k] < cut for k in ctrl[h]["lines"]) for h in Y]))
        print(f"{label:<16} {p2:>5.0%}  {p1:>5.0%}  {moved:>5.1f}   {np.mean(per):+6.1f}      {min(per):+6.1f}       {max(per):+6.1f}        {np.mean(hit):6.1%}          {np.mean(e58):+.2f}", flush=True)
print("\n== Why: expected points from moving one team 1 line in a random direction, by confidence")
print("  confidence  teams  exact  off by 1  off 2+  expected points per move")
recs = [(conf[h][k], ctrl[h]["rows"][k], ctrl[h]["lines"][k]) for h in Y for k in ctrl[h]["lines"]]
for a, b in ((0, .1), (.1, .2), (.2, .3), (.3, .5), (.5, 1.01)):
    x = [(r, l) for c, r, l in recs if a <= c < b and r["in_field"]]
    if not x: continue
    e = [abs(r["seed"] - l) for r, l in x]; pe, p1_, p2_ = np.mean([d == 0 for d in e]), np.mean([d == 1 for d in e]), np.mean([d >= 2 for d in e])
    ev = pe * -2 + p1_ * (0.5 * 2 + 0.5 * -1) + np.mean([d == 2 for d in e]) * 0.5 * 1
    print(f"  {a:.1f}-{min(b, 1):.1f}     {len(x):>4}   {pe:.2f}   {p1_:.2f}     {p2_:.2f}    {ev:+.2f}")
