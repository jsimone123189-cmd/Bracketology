"""ChatGPT audit challengers vs the production model, leave-one-season-out. Same data, same scoring, paired by season.
Adoption bar set before running: at least +3 mean, better in 5+ of 7 seasons, no season worse by more than 5."""
import collections, itertools, json, sys
import numpy as np
from scipy.optimize import linear_sum_assignment as hung
from sklearn.ensemble import GradientBoostingClassifier as GB
from sklearn.linear_model import LogisticRegression as LR, Ridge
from sklearn.preprocessing import StandardScaler as SS
from bracketology import fieldformat, history, model, project, quads
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); REF = [335, 326, 347, 344, 329, 363, 356]

def game_feats(rows, y):
    """Wins by opponent NET tier, continuous win and loss quality, bad home losses. As of Selection Sunday."""
    day = history.SELECTION_SUNDAY[y]; net = {r["key"]: r["net"] for r in rows}; F = collections.defaultdict(lambda: collections.Counter())
    for g in torvik.collect_games(y)["rows"]:
        m, d, yy = g["date"].split("/"); iso = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if iso > day or g["type"] not in (0, 1, 2): continue
        a, b = key(g["team"]), key(g["opp"])
        if a not in net or b not in net: continue
        n = net[b]; adj = n * {"H": 50 / 30, "N": 1.0, "A": 50 / 75}[g["loc"]]; f = F[a]; val = float(np.exp(-adj / 50))
        if g["win"]:
            f["w10"] += n <= 10; f["w25"] += n <= 25; f["w50"] += n <= 50; f["road25"] += n <= 25 and g["loc"] == "A"; f["winq"] += val
        else:
            f["lossq"] += 1 - val; f["homebad"] += g["loc"] == "H" and n > 100; f["worst"] = max(f["worst"], adj)
    new = ["w10", "w25", "w50", "road25", "winq", "lossq", "homebad", "worst"]; ref = [r for r in rows if r["net"] <= 120]
    for n in new:
        v = np.array([float(F[r["key"]][n]) for r in ref]); mu, s = v.mean(), v.std() + 1e-9
        for r in rows: r["z_" + n] = (float(F[r["key"]][n]) - mu) / s
    return rows

D = {y: game_feats(model.attach_overall(model.prepare(build_year(y)), y), y) for y in Y}
def tr(h): return [r for y in Y if y != h for r in D[y]]
def X(rows, f): return np.array([[float(r[x]) for x in f] for r in rows])
S = model.SEED; SEL = model.SELECT; NI = model.SELECT
TIER = ["z_w10", "z_w25", "z_w50", "z_road25"]; CONT = ["z_winq", "z_lossq"]; BAD = ["z_homebad", "z_worst"]

def composites(rows):
    for r in rows:
        r["c_str"] = (-r["z_net_log"] + r["z_rating"] - r["rk_rating"]) / 3
        r["c_res"] = (r["z_wab"] + r["z_sor"] - r["rk_wab"] - r["rk_sor"]) / 4
        r["c_qual"] = (r["z_q1a_w"] + r["z_cq1_w"] + r["z_cq2_w"] + r["z_best3"]) / 4
        r["c_bad"] = (r["z_cq3_l"] + r["z_cq4_l"]) / 2
for y in Y: composites(D[y])
COMP = ["c_str", "c_res", "c_qual", "c_bad", "z_cq1_l", "z_win_pct", "z_sos", "z_road_w", "z_neutral_w", "z_last10", "is_power", "few_q1", "q1w_power", "net_nonpower"]

def pairwise(train, test, f=S, win=16, C=.1, team_equal=False):
    fld = [r for r in train if r["in_field"]]; sc = SS().fit(X(fld, f)); A, b, w = [], [], []; by = {}
    for r in fld: by.setdefault(r["year"], []).append(r)
    for rs in by.values():
        Z = sc.transform(X(rs, f)); cnt = collections.Counter()
        for i, j in itertools.combinations(range(len(rs)), 2):
            if rs[i]["ov"] != rs[j]["ov"] and abs(rs[i]["ov"] - rs[j]["ov"]) <= win: cnt[i] += 1; cnt[j] += 1
        for i, j in itertools.combinations(range(len(rs)), 2):
            d = rs[i]["ov"] - rs[j]["ov"]
            if d and abs(d) <= win:
                wt = (1 / cnt[i] + 1 / cnt[j]) if team_equal else 1.0
                A += [Z[i] - Z[j], Z[j] - Z[i]]; b += [d < 0, d > 0]; w += [wt, wt]
    m = LR(C=C, max_iter=3000, fit_intercept=False).fit(np.array(A), np.array(b, int), sample_weight=np.array(w))
    return sc.transform(X(test, f)) @ m.coef_[0]

def ridge(train, test, f=S, a=10.0, target="seed"):
    fld = [r for r in train if r["in_field"]]; sc = SS().fit(X(fld, f))
    return -Ridge(alpha=a).fit(sc.transform(X(fld, f)), np.array([float(r[target]) for r in fld])).predict(sc.transform(X(test, f)))

def ordinal(train, test, f=S, C=.05):
    """Per-line probabilities from cumulative logits P(line <= k), forced monotone."""
    fld = [r for r in train if r["in_field"]]; sc = SS().fit(X(fld, f)); Zt = sc.transform(X(test, f)); Z = sc.transform(X(fld, f)); y = np.array([r["seed"] for r in fld]); cum = []
    for k in range(1, 16): cum.append(LR(C=C, max_iter=3000).fit(Z, (y <= k).astype(int)).predict_proba(Zt)[:, 1])
    c = np.maximum.accumulate(np.column_stack(cum + [np.ones(len(test))]), axis=1)
    return np.diff(np.column_stack([np.zeros(len(test)), c]), axis=1)

def assign(field, P, season):
    """Best total expected score given fixed line sizes: U = 3 + 3 P(line) + P(line-1) + P(line+1)."""
    L = fieldformat.slot_lines(season); C = np.zeros((len(field), len(L)))
    for j, l in enumerate(L):
        C[:, j] = 3 * P[:, l - 1] + (P[:, l - 2] if l > 1 else 0) + (P[:, l] if l < 16 else 0)
    i, j = hung(-C); return {field[a]["key"]: L[b] for a, b in zip(i, j)}

def slots(field, score, season):
    return {field[i]["key"]: l for i, l in zip(np.argsort(-score, kind="stable"), fieldformat.slot_lines(season))}

BASEP = {}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); m.score(D[h])
    BASEP[h] = {r["key"]: r["p_in"] for r in D[h]}
    for r in D[h]: r["_q"] = r["rank_score"]
print("selection Brier/log loss among at-large candidates (NET<=100, not champions):", flush=True)
from sklearn.metrics import brier_score_loss as BR
pl = [(r["in_field"], BASEP[h][r["key"]]) for h in Y for r in D[h] if r["net"] <= 100 and not r["champ"]]
print(" Brier", round(BR([a for a, _ in pl], [b for _, b in pl]), 4), "n", len(pl))
for a, b in ((0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.01)):
    s = [x for x in pl if a <= x[1] < b]; print(f"  p {a:.1f}-{b:.1f}: n {len(s):3} predicted {np.mean([x[1] for x in s]):.2f} actual {np.mean([x[0] for x in s]):.2f}")

def field_of(h, p):
    rows = D[h]; autos = [r for r in rows if r["champ"]]; pool = sorted((r for r in rows if not r["champ"]), key=lambda r: -p[r["key"]])
    return autos + pool[:68 - len(autos)]
def run(seed=None, sel=None):
    """seed(train, test, h) gives a dict team->line. sel(train, rows, h) gives dict team->p, default the base selection."""
    out = []
    for h in Y:
        p = sel(tr(h), D[h], h) if sel else BASEP[h]; fl = field_of(h, p)
        line = seed(tr(h), fl, h) if seed else slots(fl, pairwise(tr(h), fl), h)
        out.append(bm.score(line, {r["key"]: r["seed"] for r in D[h] if r["in_field"]})["score"])
    return out
def signflip(d):
    d = np.array(d, float); obs = abs(d.mean()); n = 0
    for s in itertools.product((1, -1), repeat=len(d)): n += abs((d * s).mean()) >= obs - 1e-12
    return n / 2 ** len(d)
base = run(); print("BASE", base, np.mean(base), "reproduces production:", base == REF, flush=True)
def rep(lab, sc):
    d = [a - b for a, b in zip(sc, base)]; ok = np.mean(d) >= 3 and sum(x > 0 for x in d) >= 5 and min(d) >= -5
    print(f"{lab:50} {sc} mean {np.mean(sc):.1f} diff {np.mean(d):+.1f} better {sum(x > 0 for x in d)} worse {sum(x < 0 for x in d)} worst {min(d):+d} p {signflip(d):.2f} {'PASSES BAR' if ok else ''}", flush=True)
def pw(**k): return lambda a, f, h: slots(f, pairwise(a, f, **k), h)
def rd(**k): return lambda a, f, h: slots(f, ridge(a, f, **k), h)
print("--- seed objective")
for al in (1, 10, 100, 500): rep(f"ridge on seed line alpha {al}", run(rd(a=al)))
for al in (10, 100): rep(f"ridge on 1-68 position alpha {al}", run(rd(a=al, target="ov")))
for c in (.01, .05, .3): rep(f"ordinal, order by expected line C {c}", run(lambda a, f, h, c=c: slots(f, -(ordinal(a, f, C=c) @ np.arange(1, 17)), h)))
for c in (.01, .05, .3): rep(f"ordinal + expected-score assignment C {c}", run(lambda a, f, h, c=c: assign(f, ordinal(a, f, C=c), h)))
print("--- effective sample size / simplification")
rep("pairwise, all pairs", run(pw(win=67)))
rep("pairwise, all pairs, each team equal weight", run(pw(win=67, team_equal=True)))
rep("pairwise, window 16, each team equal weight", run(pw(team_equal=True)))
rep("no interaction features", run(pw(f=NI)))
rep("composite features, pairwise", run(pw(f=COMP)))
rep("composite features, ridge alpha 10", run(rd(f=COMP, a=10)))
for c in (.01, .03, 1): rep(f"pairwise C {c}", run(pw(C=c)))
print("--- feature families, added to seeding")
for lab, fam in (("wins by NET tier and road", TIER), ("continuous win and loss quality", CONT), ("bad home losses, worst loss", BAD), ("all three", TIER + CONT + BAD)):
    rep(lab, run(pw(f=S + fam)))
print("--- selection")
def selfit(f, mode="both"):
    def go(a, rows, h):
        pool = [r for r in a if not r["champ"]]; A, b = X(pool, f), np.array([r["in_field"] for r in pool], int); sc = SS().fit(A); T = X(rows, f)
        pa = LR(C=.3, max_iter=3000).fit(sc.transform(A), b).predict_proba(sc.transform(T))[:, 1]
        pb = GB(n_estimators=120, max_depth=2, learning_rate=.05, subsample=.8, random_state=0).fit(A, b).predict_proba(T)[:, 1]
        return {r["key"]: float({"both": (x + y) / 2, "lr": x, "gb": y}[mode]) for r, x, y in zip(rows, pa, pb)}
    return go
rep("logistic only", run(sel=selfit(SEL, "lr")))
rep("boosting only", run(sel=selfit(SEL, "gb")))
for lab, fam in (("wins by NET tier and road", TIER), ("continuous win and loss quality", CONT), ("bad home losses, worst loss", BAD), ("all three", TIER + CONT + BAD)):
    rep("selection + " + lab, run(sel=selfit(SEL + fam)))
def shared(a, rows, h):
    """Seeding score as a selection feature. Training rows get it from a model that did not see their season."""
    seasons = sorted({r["year"] for r in a}); pool = []
    for s in seasons:
        rs = [r for r in a if r["year"] == s]; q = pairwise([r for r in a if r["year"] != s], rs)
        for r, v in zip(rs, q): r["_shared"] = float(v)
        pool += rs
    q = pairwise(a, rows)
    for r, v in zip(rows, q): r["_shared"] = float(v)
    return selfit(SEL + ["_shared"])(pool, rows, h)
rep("shared resume score in selection", run(sel=shared))
