"""docs/25 Test 13: average NET of wins and losses, NET SOS and non-conference NET SOS, in both models."""
import collections, numpy as np
from bracketology import history, model, project
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; NEW = ["avg_net_w", "avg_net_l", "net_sos", "net_ncsos"]; _c = {}
def rows_with(y):
    if y not in _c:
        rows = raw_build(y); day = history.SELECTION_SUNDAY[y]; R = {r["key"]: r for r in rows}; W, L, A, NC = (collections.defaultdict(list) for _ in range(4)); seen = set()
        for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
            a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); di = f"20{yy}-{int(m):02d}-{int(d):02d}"
            if a not in R or b not in R or di > day or (di, a, b) in seen: continue
            seen.add((di, a, b)); n = R[b]["net"]; A[a].append(n); (W if g["win"] else L)[a].append(n)
            if R[a]["lg"] != R[b]["lg"]: NC[a].append(n)
        for r in rows:
            k = r["key"]; r["avg_net_w"] = float(np.mean(W[k])) if W[k] else 300.0; r["avg_net_l"] = float(np.mean(L[k])) if L[k] else 300.0
            r["net_sos"] = float(np.mean(A[k])) if A[k] else 300.0; r["net_ncsos"] = float(np.mean(NC[k])) if NC[k] else 300.0
        _c[y] = rows
    return [dict(r) for r in _c[y]]
project.build_year = rows_with; model.BASE = model.BASE + NEW; SEL, SEED = list(model.SELECT), list(model.SEED)
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
    print(f"{n:<30}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75}", flush=True)
cs = loso(SEL, SEED); print("control", cs, "reproduces:", cs == CONTROL, flush=True)
z = ["z_" + n for n in NEW]; show("Test 13 all four, both models", loso(SEL + z, SEED + z), cs)
for n in NEW: show(f"  reported: {n} in seeding", loso(SEL, SEED + ["z_" + n]), cs)
