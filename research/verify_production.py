"""Production code must reproduce the research result, champion detection must match history, plus a 76-team dry run on 2026."""
import json, numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.dataset import completed_champions, conf_champions
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
Y = sorted(history.SELECTION_SUNDAY); sc = []
for y in Y:
    g = torvik.collect_games(y)["rows"]; d = history.SELECTION_SUNDAY[y]; a, b = conf_champions(g, d), completed_champions(g, d)
    print(y, "champions old/new", len(a), len(b), "differ:", {c: (a.get(c), b.get(c)) for c in set(a) | set(b) if a.get(c) != b.get(c)}, flush=True)
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    field, _ = model.choose_field(rows, h, project_autos=False); order = model.assign_lines(field, h)
    r = bm.score({x["key"]: x["line"] for x in order}, {x["key"]: x["seed"] for x in rows if x["in_field"]}); sc.append(r["score"]); print(h, r, flush=True)
print("production LOSO", sc, "mean", round(np.mean(sc), 1), "research reference [335, 326, 347, 344, 329, 363, 356] mean 342.9")
m = model.Model().fit(project.training_rows(exclude={2026})); rows = build_year(2026); model.prepare(rows); m.score(rows)
f68, _ = model.choose_field(rows, 2026, project_autos=False); ids = {x["key"] for x in f68}
f76, rest = model.choose_field(rows, 2027, project_autos=False); o = model.assign_lines(f76, 2027)
print("76-team dry run, 2026 data:", len(o), "extra 8:", [(x["team"], "NET", x["net"], "p", round(x["p_in"], 3), "line", x["line"]) for x in o if x["key"] not in ids])
print("Per line sizes", [sum(x["line"] == l for x in o) for l in range(1, 17)], "max score", fieldformat.max_score(2027))
