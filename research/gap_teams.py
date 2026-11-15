"""docs/41 addendum (descriptive): final-gap teams (elite majority exact, v2.0 not) - when did each side get it right or wrong?"""
import sys; sys.argv = ["x"]; sys.path.insert(0, "research")
src = open("research/model_inertia.py").read().split("cats = {c")[0]; exec(src)
from collections import Counter
C = Counter(); own = {"v2 moved away": [], "v2 wrong at D-7 too": []}; elite_tr = Counter(); rev = Counter()
for h in Y5:
    off = {r["key"]: r["seed"] for r in FINAL[h] if r["in_field"]}; m = model.Model().fit(project.training_rows(exclude={h}))
    net7 = {key(r["team"]): r["net"] for r in json.load(open(f"{D}/{h}_net_d7.json"))["rows"]}; sw = dataset.INELIGIBLE_CHAMPS.get(h, {})
    c7 = {key(sw.get(t, t)) for t in dataset.completed_champions(GAMES[h], D7[h]).values()}; cF = {r["key"] for r in FINAL[h] if r["champ"]}
    o7, R7 = run(m, state(h, net7, D7[h], c7), h); oF, RF = run(m, state(h, None, SS[h], cF), h)
    M7 = json.load(open(f"{D}/{h}_matrix_d7.json")); snap = dt.date.fromisoformat(M7["updated"]); fin = matrix_full.submissions(h); E = []
    for g in GROUP:
        if g in M7["subs"] and g in fin and g in M7["dates"] and snap - dt.timedelta(days=3) <= dt.date.fromisoformat(M7["dates"][g]) <= snap:
            E.append(({key(t): l for t, l in M7["subs"][g].items()}, {key(t): l for t, l in fin[g].items()}))
    n_gap = n_rev = 0
    for k, s in off.items():
        eF = [b.get(k) == s for _, b in E]; e7 = [a.get(k) == s for a, _ in E]
        vF = RF.get(k, {}).get("line") == s; v7 = R7.get(k, {}).get("line") == s
        if sum(eF) > len(E) / 2 and not vF:
            n_gap += 1; elite_was = "elite right at D-7" if sum(e7) > len(E) / 2 else "elite fixed it in the week"
            if k not in RF: v2c = "v2 missed the team (selection)"
            elif v7 and not vF: v2c = "v2 moved away"
            elif k in R7 and R7[k]["line"] == RF[k]["line"]: v2c = "v2 wrong at D-7 too, unchanged"
            else: v2c = "v2 wrong at D-7, moved but still wrong"
            C[(v2c, elite_was)] += 1
        if sum(eF) <= len(E) / 2 and vF: n_rev += 1
    print(f"{h}: teams elite-majority exact & v2 not: {n_gap}; v2 exact & elite-majority not: {n_rev}", flush=True)
print("\nFinal-gap teams by when each side was right/wrong (5 seasons):")
for (a, b), n in sorted(C.items(), key=lambda x: -x[1]): print(f"  {n:>3}  {a:<40} | {b}")
