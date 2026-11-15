"""docs/27 Tests 15 and 16: Q1 loss margin and double champions in the seed model."""
import collections, numpy as np
from bracketology import history, model, project, quads
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; _c = {}
def rows_with(y):
    if y not in _c:
        rows = raw_build(y); day = history.SELECTION_SUNDAY[y]; R = {r["key"]: r for r in rows}
        lm = collections.defaultdict(list); cw, cg, ctw, ctl = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter(); seen = set()
        for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
            a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); di = f"20{yy}-{int(m):02d}-{int(d):02d}"
            if a not in R or b not in R or di > day or (di, a, b) in seen: continue
            seen.add((di, a, b))
            if not g["win"] and quads.quadrant(R[b]["net"], g["loc"]) in ("1A", "1B"): lm[a].append(g["pa"] - g["pf"])
            if g["type"] == 1: cg[a] += 1; cw[a] += bool(g["win"])
            if g["type"] == 2: (ctw if g["win"] else ctl)[a] += 1
        best = collections.defaultdict(float)
        for k, r in R.items():
            if cg[k]: best[r["lg"]] = max(best[r["lg"]], cw[k] / cg[k])
        for r in rows:
            k = r["key"]; r["q1_loss_margin"] = float(np.mean(lm[k])) if lm[k] else 0.0
            reg = bool(cg[k]) and cw[k] / cg[k] >= best[r["lg"]] - 1e-9; r["double_champ"] = float(reg and bool(r["champ"]) and ctw[k] > 0 and ctl[k] == 0)
        _c[y] = rows
    return [dict(r) for r in _c[y]]
project.build_year = rows_with; model.BASE = model.BASE + ["q1_loss_margin"]; SEL, SEED = list(model.SELECT), list(model.SEED)
for y in Y:
    fl = [r for r in rows_with(y) if r["in_field"]]; print(f"  {y}: double champions in field {sum(r['double_champ'] for r in fl):.0f}, field teams with Q1 losses {sum(r['q1_loss_margin'] > 0 for r in fl)}")
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def loso(sel, seed):
    model.SELECT, model.SEED = sel, seed; s = []
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(rows_with(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
        s.append(bm.score({r["key"]: r["line"] for r in o}, {r["key"]: r["seed"] for r in rows if r["in_field"]})["score"])
    return s
def show(n, s, base):
    d = np.array(s) - np.array(base); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    print(f"{n:<28}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75}", flush=True)
cs = loso(SEL, SEED); print("control", cs, "reproduces:", cs == CONTROL, flush=True)
show("Test 15 Q1 loss margin", loso(SEL, SEED + ["z_q1_loss_margin"]), cs)
show("Test 16 double champion", loso(SEL, SEED + ["double_champ"]), cs)
