"""docs/19: Test 6, carry half the committee's top-16 lean (reveal position minus v2.0's same-day position) into March."""
import ast, json, numpy as np
from bracketology import history, metrics, model, project, fieldformat
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; LAMBDA = 0.5
s = open("research/diagnose.py").read(); T16 = ast.literal_eval(s[s.index("T16 = ") + 6:s.index("\nfor y, lines in T16.items()")])
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def reveal_rows(y, march):
    d = json.load(open(f"data/history/{y}_net_reveal.json")); cap = d["capture"]; day = f"{cap[:4]}-{cap[4:6]}-{cap[6:8]}"
    if d.get("through"):
        from datetime import datetime; day = datetime.strptime(d["through"].replace(".", ""), "%b %d %Y").date().isoformat()
    M = {r["key"]: r for r in march}; rows = []
    for r in d["rows"]:
        k = key(r["team"])
        if k in M: rows.append({**M[k], "net": r["net"], "w": r["w"], "l": r["l"], "champ": False})
    games = torvik.collect_games(y, ttl=10 ** 9)["rows"]
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, dd, yy = g["date"].split("/"); g["date_iso"] = f"20{yy}-{int(m):02d}-{int(dd):02d}"
    met = metrics.compute(games, {r["key"]: r["net"] for r in rows}, day)
    for r in rows: r.update(met.get(r["key"], {}))
    return rows, day
out, top = {"control": [], "Test 6": []}, {"control": [], "Test 6": []}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); march = model.prepare(build_year(h)); m.score(march)
    rv, day = reveal_rows(h, build_year(h)); model.prepare(rv); m.score(rv)
    pool = sorted([r for r in rv if r["net"] <= 100], key=lambda r: -r["rank_score"]); mpos = {r["key"]: i + 1 for i, r in enumerate(pool)}
    order = [key(t) for line in T16[h] for t in line]; lean = {}
    for i, k in enumerate(order):
        if k in mpos: lean[k] = (i + 1) - mpos[k]
    for k, p in mpos.items():
        if p <= 16 and k not in lean: lean[k] = 17 - p
    f, _ = model.choose_field(march, h, project_autos=False); o = model.assign_lines(f, h); slots = fieldformat.format_for(h).slots
    off = {r["key"]: r["seed"] for r in march if r["in_field"]}
    base = {r["key"]: r["line"] for r in o}; pos = {r["key"]: r["overall"] + LAMBDA * lean.get(r["key"], 0) for r in o}
    adj = {k: slots[i] for i, k in enumerate(sorted(pos, key=lambda k: (pos[k], k)))}
    for n, L in (("control", base), ("Test 6", adj)):
        out[n].append(bm.score(L, off)["score"]); top[n].append(sum(1 for k in L if k in off and off[k] <= 4 and L[k] == off[k]))
    big = sorted(lean.items(), key=lambda x: -abs(x[1]))[:5]
    print(f"{h} reveal data through {day}: biggest leans {[(k, v) for k, v in big]}  control {out['control'][-1]} test {out['Test 6'][-1]}  exact 1-4 {top['control'][-1]} -> {top['Test 6'][-1]}", flush=True)
print("control reproduces:", out["control"] == CONTROL)
c = np.array(out["control"]); t = np.array(out["Test 6"]); d = t - c; ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, t)]
print(f"Test 6 {list(t)} mean {t.mean():.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} percentiles {p} all>=75 {min(p) >= 75}; exact 1-4 per season {np.mean(top['control']):.1f} -> {np.mean(top['Test 6']):.1f}")
