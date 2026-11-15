"""docs/24 Test 12: 2014-18 added to training with our RPI rank in NET's slot; seeding pairs from seed lines for those seasons."""
import sys; sys.path.insert(0, "research")
import collections, numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from bracketology import history, metrics, model, project
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
import common
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; OLD = common.OLD; X = model._X
FIVE = {"ACC", "B12", "BE", "B10", "SEC"}
def old_rows(y):
    day = OLD[y]; rows = common.old_year(y); games = torvik.collect_games(y, ttl=10 ** 9)["rows"]; ks = {r["key"] for r in rows}
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); a, b, c = g["date"].split("/"); g["date_iso"] = f"20{c}-{int(a):02d}-{int(b):02d}"
    G = collections.defaultdict(list); seen = set()
    for g in games:
        if g["date_iso"] <= day and g["team_key"] in ks and g["opp_key"] in ks and (g["date_iso"], g["team_key"], g["opp_key"]) not in seen:
            seen.add((g["date_iso"], g["team_key"], g["opp_key"])); G[g["team_key"]].append((g["opp_key"], bool(g["win"]), g["loc"]))
    W = {"H": (.6, 1.4), "A": (1.4, .6), "N": (1.0, 1.0)}
    def wp(t, ex=None):
        v = [w for o, w, _ in G[t] if o != ex]; return sum(v) / len(v) if v else 0.0
    wwp = {t: (lambda a, b: a / (a + b) if a + b else 0.0)(sum(W[l][0] for _, w, l in gs if w), sum(W[l][1] for _, w, l in gs if not w)) for t, gs in G.items()}
    owp = {t: np.mean([wp(o, t) for o, _, _ in gs]) if gs else 0.0 for t, gs in G.items()}
    oowp = {t: np.mean([owp.get(o, 0) for o, _, _ in gs]) if gs else 0.0 for t, gs in G.items()}
    rpi = {k: .25 * wwp.get(k, 0) + .5 * owp.get(k, 0) + .25 * oowp.get(k, 0) for k in ks}
    rank = {k: i + 1 for i, k in enumerate(sorted(ks, key=lambda k: -rpi[k]))}
    M = metrics.compute(games, rank, day)
    for r in rows: r.update(M.get(r["key"], {})); r["net"] = rank[r["key"]]; r["is_power"] = 1.0 if r["lg"] in FIVE else 0.0; r["ov"] = None
    return model.prepare(rows)
OLDR = {}
for y in OLD:
    OLDR[y] = old_rows(y); f = [r for r in OLDR[y] if r["in_field"]]; print(f"  {y}: field teams matched {len(f)}/68, champs {sum(r['champ'] for r in OLDR[y])}, power teams in field {sum(r['is_power'] for r in f):.0f}", flush=True)
def fit(train, old_sel, old_seed):
    m = model.Model(); sel_pool = [r for r in train + (sum(OLDR.values(), []) if old_sel else []) if not r["champ"]]
    Xs = X(sel_pool, model.SELECT); y = np.array([r["in_field"] for r in sel_pool], int); m.s_sel = StandardScaler().fit(Xs)
    m.lr = LogisticRegression(C=.3, max_iter=3000).fit(m.s_sel.transform(Xs), y)
    m.gb = GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(Xs, y)
    field = [r for r in train if r["in_field"]]; oldf = [r for v in OLDR.values() for r in v if r["in_field"]] if old_seed else []
    m.s_seed = StandardScaler().fit(X(field + oldf, model.SEED)); dX, dy = [], []
    for rs, by_ov in [([r for r in field if r["year"] == yr], True) for yr in {r["year"] for r in field}] + [([r for r in oldf if r["year"] == yr], False) for yr in {r["year"] for r in oldf}]:
        Z = m.s_seed.transform(X(rs, model.SEED))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = (rs[i]["ov"] - rs[j]["ov"]) if by_ov else (rs[i]["seed"] - rs[j]["seed"]); lim = 16 if by_ov else 4
                if d and abs(d) <= lim: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
    m.rank = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int)); return m
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
res = {n: [] for n in ("control", "Test 12 both", "seeding only (reported)")}
for h in Y:
    train = project.training_rows(exclude={h})
    for n, a, b in (("control", False, False), ("Test 12 both", True, True), ("seeding only (reported)", False, True)):
        m = fit(train, a, b) if (a or b) else model.Model().fit(train)
        rows = model.prepare(build_year(h)); m.score(rows); f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
        res[n].append(bm.score({r["key"]: r["line"] for r in o}, {r["key"]: r["seed"] for r in rows if r["in_field"]})["score"])
    print(h, {n: v[-1] for n, v in res.items()}, flush=True)
print("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    d = np.array(s) - np.array(CONTROL); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5; p = [pct(y, v) for y, v in zip(Y, s)]
    print(f"{n:<26}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)} pct {p} all>=75 {min(p) >= 75}")
