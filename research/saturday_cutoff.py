"""docs/35 Test 25: every feature recomputed with games through the Saturday before Selection Sunday."""
import datetime, json, os, numpy as np
from bracketology import history, model, project, fieldformat, dataset, metrics, features
from bracketology.sources import torvik, bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]
OUT = "/tmp/claude-1000/-home-jsimone123189/6ac436db-a13c-4349-96e9-32259fcb1292/scratchpad/features_sat"
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
def build_sat(year):
    path = f"{OUT}/{year}.json"
    if os.path.exists(path): return json.load(open(path))
    base = {r["key"]: r for r in features.build_year(year)}           # Sunday version: identity, champs, seeds, lg, power
    sat = (datetime.date.fromisoformat(history.SELECTION_SUNDAY[year]) - datetime.timedelta(days=1)).isoformat()
    games = torvik.collect_games(year)["rows"]
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, d, y = g["date"].split("/"); g["date_iso"] = f"20{y}-{int(m):02d}-{int(d):02d}"
    M = metrics.compute(games, {k: r["net"] for k, r in base.items()}, sat)
    rows = []
    for k, r in base.items():
        r = dict(r); r.update(M.get(k, {})); rows.append(r)
    byconf = {}
    for r in rows: byconf.setdefault(r["lg"], []).append(r.get("rating", 0.0))
    st = {c: float(np.mean(sorted(v, reverse=True)[:4])) for c, v in byconf.items()}
    for r in rows: r["conf_strength"] = st.get(r["lg"], 0.0)
    os.makedirs(OUT, exist_ok=True); json.dump(rows, open(path, "w")); return rows
changed = {}
for y in Y:
    a = {r["key"]: r for r in features.build_year(y)}; b = {r["key"]: r for r in build_sat(y)}
    changed[y] = sum(1 for k in a if a[k]["in_field"] and (a[k]["cq1_w"], a[k]["wab"]) != (b[k]["cq1_w"], b[k]["wab"]))
print("field teams whose Q1 wins or WAB change:", changed)
def run(builder):
    project.build_year = builder; out, ex = [], []
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(builder(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); L = {r["key"]: r["line"] for r in model.assign_lines(f, h)}
        off = {r["key"]: r["seed"] for r in rows if r["in_field"]}; out.append(bm.score(L, off)["score"]); ex.append(sum(1 for k in L if k in off and L[k] == off[k]))
    return out, ex
res = {"control": run(features.build_year), "T25 Saturday cutoff": run(build_sat)}
print("control reproduces:", res["control"][0] == CONTROL)
for n, (s, e) in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{n:<20}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} exact {e} ({np.mean(e):.1f}) pct {[pct(y, v) for y, v in zip(Y, s)]}")
