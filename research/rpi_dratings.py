"""docs/18: Test 5 (our RPI in both models) and dRatings' (DII) errors versus v2.0."""
import sys; sys.path.insert(0, "research")
import collections, math, numpy as np, matrix_full
from scipy.stats import spearmanr
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; _c = {}
def rpi_rows(y):
    if y in _c: return [dict(r) for r in _c[y]]
    rows = raw_build(y); day = history.SELECTION_SUNDAY[y]; R = {r["key"]: r for r in rows}; games = collections.defaultdict(list)
    for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/")
        if a in R and b in R and f"20{yy}-{int(m):02d}-{int(d):02d}" <= day: games[a].append((b, bool(g["win"]), g["loc"]))
    def wp(t, excl=None):
        gs = [w for o, w, _ in games[t] if o != excl]; return sum(gs) / len(gs) if gs else 0.0
    W = {"H": (.6, 1.4), "A": (1.4, .6), "N": (1.0, 1.0)}
    wwp = {}
    for t, gs in games.items():
        ww = sum(W[l][0] for _, w, l in gs if w); wl = sum(W[l][1] for _, w, l in gs if not w); wwp[t] = ww / (ww + wl) if ww + wl else 0.0
    owp = {t: np.mean([wp(o, excl=t) for o, _, _ in gs]) if gs else 0.0 for t, gs in games.items()}
    oowp = {t: np.mean([owp.get(o, 0.0) for o, _, _ in gs]) if gs else 0.0 for t, gs in games.items()}
    for r in rows: k = r["key"]; r["rpi"] = .25 * wwp.get(k, 0) + .5 * owp.get(k, 0) + .25 * oowp.get(k, 0)
    _c[y] = rows; return [dict(r) for r in rows]
project.build_year = rpi_rows; model.BASE = model.BASE + ["rpi"]
SEL, SEED = list(model.SELECT), list(model.SEED)
for y in Y:
    t = [r for r in rpi_rows(y) if r["net"] <= 100]; print(f"  {y} RPI vs NET rank corr (NET top 100): {spearmanr([-r['rpi'] for r in t], [r['net'] for r in t])[0]:.3f}")
def loso(sel, seed):
    model.SELECT, model.SEED = sel, seed; out = {}
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(rpi_rows(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
        out[h] = ({r["key"]: r["line"] for r in o}, {r["key"]: r for r in rows})
    return out
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, s: round(100 * sum(v < s for v in MS[y]) / len(MS[y]))
truth = lambda R: {k: r["seed"] for k, r in R.items() if r["in_field"]}
ctrl = loso(SEL, SEED); cs = [bm.score(ctrl[h][0], truth(ctrl[h][1]))["score"] for h in Y]; print("control", cs, "reproduces:", cs == CONTROL, flush=True)
t5 = loso(SEL + ["z_rpi"], SEED + ["z_rpi"]); s = [bm.score(t5[h][0], truth(t5[h][1]))["score"] for h in Y]
d = np.array(s) - np.array(cs); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
print(f"Test 5 RPI {s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} percentiles {p} all>=75 {min(p) >= 75}", flush=True)

print("\n== dRatings (DII) versus v2.0, actual field")
def prof(lines, R):
    off = truth(R); both = [k for k in lines if k in off]
    grp = lambda k: "auto" if R[k]["champ"] else ("power_atl" if R[k]["is_power"] else "nonpower_atl")
    o = {"exact": sum(lines[k] == off[k] for k in both), "wrong": sum(k not in off for k in lines), "score": bm.score(lines, off)["score"]}
    for g in ("power_atl", "nonpower_atl", "auto"):
        e = [lines[k] - off[k] for k in both if grp(k) == g]; o[g] = (round(float(np.mean(e)), 2), round(float(np.mean(np.abs(e))), 2))
    for b in range(4): o[f"band{4*b+1}-{4*b+4}"] = round(float(np.mean([lines[k] == off[k] for k in both if (off[k] - 1) // 4 == b])), 2)
    return o
agg = collections.defaultdict(list)
for h in Y:
    lines, R = ctrl[h]; dii = {key(t): l for t, l in matrix_full.submissions(h).get("DII", {}).items()}
    a, b = prof(lines, R), prof(dii, R); off = truth(R)
    print(f"{h} v2.0 {a}\n     DII  {b}")
    for k in a: agg[("v2", k)].append(a[k]); agg[("dii", k)].append(b[k])
    print("     v2.0 exact, DII not:", [(R[k]["team"], off[k], dii.get(k)) for k in lines if k in off and lines[k] == off[k] and dii.get(k) != off[k]])
    print("     DII exact, v2.0 not:", [(R[k]["team"], off[k], lines.get(k)) for k in dii if k in off and dii[k] == off[k] and lines.get(k) != off[k]])
print("\nseven-season means (signed, abs) by group and exact by band:")
for k in ("exact", "wrong", "score", "power_atl", "nonpower_atl", "auto", "band1-4", "band5-8", "band9-12", "band13-16"):
    f = lambda v: tuple(round(float(np.mean([x[i] for x in v])), 2) for i in range(2)) if isinstance(v[0], tuple) else round(float(np.mean(v)), 2)
    print(f"  {k:<13} v2.0 {f(agg[('v2', k)])}   DII {f(agg[('dii', k)])}")
