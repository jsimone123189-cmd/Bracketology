"""Where the points go (leave-one-season-out, production model), plus an integrity audit of the historical cutoffs.
Oracles are diagnostic ceilings, not achievable scores. Benchmarks are never model inputs."""
import collections, json, sys
import numpy as np
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY)

def real_slots(rows):
    return sorted(r["seed"] for r in rows if r["in_field"])
def pts(line, seed):
    if line is None: return 0
    d = abs(line - seed); return 6 if d == 0 else 4 if d == 1 else 3

print("=== Cutoff audit ===")
for y in Y:
    day = history.SELECTION_SUNDAY[y]; g = torvik.collect_games(y)["rows"]; rows = build_year(y); net = json.load(open(f"data/history/{y}_net.json"))
    cnt = collections.Counter(); late = collections.Counter(); types = collections.Counter()
    for x in g:
        m, d, yy = x["date"].split("/"); iso = f"20{yy}-{int(m):02d}-{int(d):02d}"; types[x["type"]] += iso > day
        if iso <= day and x["type"] in (0, 1, 2): cnt[key(x["team"])] += 1
    diffs = collections.Counter(); over = []
    for r in net["rows"]:
        k = key(r["team"])
        if r["w"] is None or k not in cnt: continue
        d = r["w"] + r["l"] - cnt[k]; diffs[d] += 1
        if d > 0: over.append((r["team"], d))
    fld = [r for r in rows if r["in_field"]]; champs = [r for r in rows if r["champ"]]
    print(y, "NET through", net.get("through"), "| NET games minus log games through Sunday:", dict(sorted(diffs.items())), "| log rows after cutoff by type:", {k: v for k, v in sorted(types.items()) if v},
          "| champs", len(champs), "champs out of field", [r["team"] for r in champs if not r["in_field"]], "| field", len(fld))
    if over: print("   more NET games than log:", over[:8])

print("\n=== Loss decomposition ===")
tot = collections.defaultdict(list); detail = []
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    field, _ = model.choose_field(rows, h, project_autos=False); order = model.assign_lines(field, h)
    line = {r["key"]: r["line"] for r in order}; true = {r["key"]: r["seed"] for r in rows if r["in_field"]}; by = {r["key"]: r for r in rows}
    s = sum(pts(line.get(k), v) for k, v in true.items())
    missed = [k for k in true if k not in line]; ex = sum(line.get(k) == v for k, v in true.items()); one = sum(k in line and abs(line[k] - v) == 1 for k, v in true.items()); two = sum(k in line and abs(line[k] - v) >= 2 for k, v in true.items())
    # A: real field, model order, fixed line sizes. B: same but that season's real line sizes. C: model field, perfect seeds.
    tf = sorted((r for r in rows if r["in_field"]), key=lambda r: -r["rank_score"])
    A = sum(pts(l, r["seed"]) for r, l in zip(tf, __import__("bracketology.fieldformat", fromlist=["x"]).slot_lines(h)))
    B = sum(pts(l, r["seed"]) for r, l in zip(tf, real_slots(rows)))
    # D: model field with that season's real line sizes for the teams it did pick (only line-size effect)
    C = 6 * (68 - len(missed))
    # boundary errors: right order-neighbourhood, wrong side of a line. Off-by-one where true list position is within 2 of the model's.
    rk = {r["key"]: i + 1 for i, r in enumerate(tf)}; tr = sorted((r for r in rows if r["in_field"]), key=lambda r: r.get("ov") or 0)
    lost_field = 6 * len(missed); lost_one = 2 * one; lost_two = 3 * two
    auto_lost = sum(6 - pts(line.get(r["key"]), r["seed"]) for r in rows if r["in_field"] and r["champ"])
    al_lost = sum(6 - pts(line.get(r["key"]), r["seed"]) for r in rows if r["in_field"] and not r["champ"])
    hi = sum(6 - pts(line.get(k), v) for k, v in true.items() if k in line and by[k]["net"] <= 40 and v >= by[k]["net"] / 4 + 3)
    print(h, "score", s, "| picked", 68 - len(missed), "exact", ex, "off1", one, "off2+", two, "| lost: field", lost_field, "off1", lost_one, "off2+", lost_two, "| auto", auto_lost, "at-large", al_lost, "| oracle real field", A, "+real line sizes", B, "| oracle perfect seeds", C)
    for k, v in dict(score=s, picked=68 - len(missed), exact=ex, one=one, two=two, lf=lost_field, l1=lost_one, l2=lost_two, auto=auto_lost, al=al_lost, A=A, B=B, C=C).items(): tot[k].append(v)
    L = collections.Counter()
    for k, v in true.items(): L[v] += 6 - pts(line.get(k), v)
    for k, v in L.items(): tot[f"line{k}"].append(v)
    for k, v in true.items(): detail.append((h, by[k]["team"], v, line.get(k), by[k]["champ"]))
print("means:", {k: round(float(np.mean(v)), 1) for k, v in tot.items() if not k.startswith("line")})
print("points lost per season by true seed line:", {l: round(sum(tot[f'line{l}']) / 7, 1) for l in range(1, 17) if f'line{l}' in tot})
