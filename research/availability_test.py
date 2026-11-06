"""The one test in docs/10-availability-test.md, with its reported-only diagnostics."""
import json
import numpy as np
from bracketology import history, model, project
from bracketology.features import build_year as raw_build
from bracketology.report import bracket_stats
from bracketology.sources import bracketmatrix as bm
A = json.load(open("data/history/availability.json")); Y = sorted(history.SELECTION_SUNDAY)
print("coverage", {y: round(A[y]["coverage"], 3) for y in A})
def with_feature(y):
    rows = raw_build(y)
    for r in rows: r["avail_missing"] = A[str(y)]["values"].get(r["key"], {}).get("avail_missing", 0.0)
    return rows
project.build_year = with_feature
SELECT, SEED = list(model.SELECT), list(model.SEED)
def loso(sel, seed):
    model.SELECT, model.SEED = sel, seed; out = {}
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(with_feature(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
        truth = {r["key"]: r["seed"] for r in rows if r["in_field"]}; lines = {r["key"]: r["line"] for r in o}
        cand = [r for r in rows if r["net"] <= 100 and not r["champ"]]
        out[h] = {"stats": bracket_stats(lines, truth, [r["key"] for r in o]), "brier": float(np.mean([(r["p_in"] - r["in_field"]) ** 2 for r in cand])), "lines": lines, "rows": rows}
    return out
def show(name, r, base=None):
    s = [r[h]["stats"]["score"] for h in Y]; line = f"{name:<26}{s} mean {np.mean(s):.1f}"
    if base:
        b = [base[h]["stats"]["score"] for h in Y]; d = np.array(s) - np.array(b)
        passed = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
        line += f" diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(passed)}"
    print(line, flush=True)
    for k in ("two_plus_line_misses", "mean_excess_seed_error", "boundary_pair_agreement"): print(f"   {k} {np.mean([r[h]['stats'][k] for h in Y]):.3f}")
    print(f"   selection Brier {np.mean([r[h]['brier'] for h in Y]):.4f}", flush=True)
base = loso(SELECT, SEED); show("control v2.0", base)
print("control reproduces:", [base[h]["stats"]["score"] for h in Y] == [335, 326, 347, 344, 329, 363, 356])
test = loso(SELECT + ["avail_missing"], SEED + ["avail_missing"]); show("THE TEST: field + seeds", test, base)
show("reported only: seeds alone", loso(SELECT, SEED + ["avail_missing"]), base)
errs = []
for h in Y:
    for r in base[h]["rows"]:
        if r["avail_missing"] >= .2 and r["in_field"] and r["key"] in base[h]["lines"]:
            errs.append(r["seed"] - base[h]["lines"][r["key"]]); print("  ", h, r["team"], round(r["avail_missing"], 2), "v2.0 line", base[h]["lines"][r["key"]], "real seed", r["seed"], A[str(h)]["values"][r["key"]]["missing"])
print("teams at 0.2 or higher in both fields", len(errs), "mean real seed minus v2.0 line", round(float(np.mean(errs)), 2) if errs else None, "(positive means the committee seeded them worse than v2.0)")
print("share of teams at 0.2 or higher", {y: sum(v["avail_missing"] >= .2 for v in A[y]["values"].values()) for y in A})
