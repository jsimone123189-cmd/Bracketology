"""docs/39: audit of docs/36, decomposition of v2.0's championship-week change, CT-surprise diagnostic, Test 26."""
import sys; sys.path.insert(0, "research")
import datetime as dt, json, math, os, numpy as np, matrix_full
from scipy.sparse import csr_matrix
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from bracketology import history, model, project, metrics, dataset, features
from bracketology.sources import torvik, bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; D = "data/history/edge_timing"
GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3", "RFS"]
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y]))
P = lambda *a: print(*a, flush=True)
GAMES = {}
for y in Y:
    gs = torvik.collect_games(y, ttl=10 ** 9)["rows"]
    for g in gs:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/"); g["date_iso"] = f"20{yy}-{int(m):02d}-{int(d):02d}"
    GAMES[y] = gs
SS = {y: history.SELECTION_SUNDAY[y] for y in Y}; D7 = {y: (dt.date.fromisoformat(SS[y]) - dt.timedelta(days=7)).isoformat() for y in Y}
NET7 = {y: {key(r["team"]): r["net"] for r in json.load(open(f"{D}/{y}_net_d7.json"))["rows"]} for y in Y if os.path.exists(f"{D}/{y}_net_d7.json")}
FINAL = {y: features.build_year(y) for y in Y}
def champs_at(y, day):
    sw = dataset.INELIGIBLE_CHAMPS.get(y, {}); return {key(sw.get(t, t)) for t in dataset.completed_champions(GAMES[y], day).values()}
def state(y, net, gday, champs):
    rows = [dict(r) for r in FINAL[y]]
    for r in rows:
        r["net"] = net.get(r["key"], 365) if net is not None else r["net"]; r["champ"] = r["key"] in champs; r.pop("projected_auto", None)
    M = metrics.compute(GAMES[y], {r["key"]: r["net"] for r in rows}, gday)
    for r in rows: r.update(M.get(r["key"], {}))
    byc = {}
    for r in rows: byc.setdefault(r["lg"], []).append(r.get("rating", 0.0))
    for r in rows: r["conf_strength"] = float(np.mean(sorted(byc[r["lg"]], reverse=True)[:4]))
    return rows
def lines(m, rows, y):
    model.prepare(rows); m.score(rows); f, _ = model.choose_field(rows, y, project_autos=True); return {r["key"]: r["line"] for r in model.assign_lines(f, y)}
off_of = lambda y: {r["key"]: r["seed"] for r in FINAL[y] if r["in_field"]}
ex = lambda L, off, ks=None: sum(1 for k, l in L.items() if k in off and off[k] == l and (ks is None or k in ks))
champF = {y: {r["key"] for r in FINAL[y] if r["champ"]} for y in Y}

# ---------------- Part 1 + 2 ----------------
P("== Part 1 audit and Part 2 decomposition (seasons with D-7 NET)")
S7 = {y: state(y, NET7[y], D7[y], champs_at(y, D7[y])) for y in NET7}
for y in S7: model.attach_overall(S7[y], y)
audit, decomp = [], []
for h in sorted(NET7):
    off = off_of(h); mF = model.Model().fit(project.training_rows(exclude={h}))
    m7 = model.Model().fit([r for s in NET7 if s != h for r in model.prepare([dict(x) for x in S7[s]])])
    L0 = lines(mF, [dict(r) for r in S7[h]], h); L0b = lines(m7, [dict(r) for r in S7[h]], h)
    L1 = lines(mF, state(h, NET7[h], D7[h], champF[h]), h); L2 = lines(mF, state(h, None, D7[h], champF[h]), h); L3 = lines(mF, state(h, None, SS[h], champF[h]), h)
    sc = lambda L: bm.score(L, off)["score"]
    decomp.append((h, ex(L0, off), ex(L1, off), ex(L2, off), ex(L3, off), sc(L0), sc(L1), sc(L2), sc(L3), ex(L0b, off)))
    P(f"{h} exact: D-7 {ex(L0, off)} (D-7-trained {ex(L0b, off)}) -> +final champions {ex(L1, off)} -> +final NET {ex(L2, off)} -> +final games {ex(L3, off)} | score {sc(L0)} -> {sc(L1)} -> {sc(L2)} -> {sc(L3)}")
    fm = f"{D}/{h}_matrix_d7.json"
    if not os.path.exists(fm): continue
    M7 = json.load(open(fm)); snap = dt.date.fromisoformat(M7["updated"]); fin = matrix_full.submissions(h); dates = []; c7, cF, c7b = [], [], []
    for n in GROUP:
        if n not in M7["subs"] or n not in fin or n not in M7["dates"]: continue
        dd = dt.date.fromisoformat(M7["dates"][n])
        if not (snap - dt.timedelta(days=3) <= dd <= snap): continue
        dates.append(dd.isoformat()); a = {key(t): l for t, l in M7["subs"][n].items()}; b = {key(t): l for t, l in fin[n].items()}
        k7 = set(a) & set(L0) & set(off); kF = set(b) & set(L3) & set(off); k7b = set(a) & set(L0b) & set(off)
        c7.append((ex(a, off, k7) - ex(L0, off, k7), len(k7))); cF.append((ex(b, off, kF) - ex(L3, off, kF), len(kF))); c7b.append(ex(a, off, k7b) - ex(L0b, off, k7b))
    audit.append((h, np.mean([x for x, _ in c7]), np.mean([x for x, _ in cF]), np.mean(c7b)))
    P(f"   audit: expert entry dates {min(dates)}..{max(dates)} (D-7 = {D7[h]}, all <= D-7: {max(dates) <= D7[h]}); common-team gap D-7 {audit[-1][1]:+.1f} (n~{np.mean([n for _, n in c7]):.0f}), final {audit[-1][2]:+.1f} (n~{np.mean([n for _, n in cF]):.0f}); D-7-trained v2.0 gap {audit[-1][3]:+.1f}")
a = np.array([x[1:] for x in audit]); P(f"AUDIT common-team gap: D-7 {a[:, 0].mean():+.1f}, final {a[:, 1].mean():+.1f}, growth {np.mean(a[:, 1] - a[:, 0]):+.1f} positive in {int(((a[:, 1] - a[:, 0]) > 0).sum())}/{len(a)}; with D-7-trained v2.0: D-7 gap {a[:, 2].mean():+.1f}")
d = np.array([x[1:] for x in decomp], float)
P(f"DECOMPOSITION mean exact: D-7 {d[:, 0].mean():.1f}, champions {d[:, 1].mean() - d[:, 0].mean():+.1f}, NET/quadrant reclassification {d[:, 2].mean() - d[:, 1].mean():+.1f}, new games {d[:, 3].mean() - d[:, 2].mean():+.1f}, final {d[:, 3].mean():.1f}")
P(f"DECOMPOSITION mean score: D-7 {d[:, 4].mean():.1f}, champions {d[:, 5].mean() - d[:, 4].mean():+.1f}, NET {d[:, 6].mean() - d[:, 5].mean():+.1f}, new games {d[:, 7].mean() - d[:, 6].mean():+.1f}, final {d[:, 7].mean():.1f}")

# ---------------- CT surprise ----------------
def ratings_before(y, day):
    keys = {r["key"]: i for i, r in enumerate(FINAL[y])}; G = metrics._games(GAMES[y], keys, day); n = len(keys); rows, cols, vals, t = [], [], [], []
    for i, g in enumerate(G):
        hh = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]; rows += [i] * 3; cols += [keys[g["team_key"]], keys[g["opp_key"]], n]; vals += [1.0, -1.0, hh]
        t.append(max(-metrics.MARGIN_CAP, min(metrics.MARGIN_CAP, g["pf"] - g["pa"])))
    c = Ridge(alpha=metrics.RIDGE_ALPHA, fit_intercept=False).fit(csr_matrix((vals, (rows, cols)), shape=(len(G), n + 1)), np.array(t)).coef_
    return {k: c[i] for k, i in keys.items()}, c[n]
CT = {}
for y in Y:
    start = {}
    for g in GAMES[y]:
        if g["type"] == 2 and g["date_iso"] <= SS[y]: start[g["conf"]] = min(start.get(g["conf"], "9999"), g["date_iso"])
    cache = {}; ct = {}; seen = set()
    for g in GAMES[y]:
        if g["type"] != 2 or g["date_iso"] > SS[y] or g["conf"] not in start: continue
        sig = (g["date_iso"], g["team_key"], g["opp_key"])
        if sig in seen: continue
        seen.add(sig); day = (dt.date.fromisoformat(start[g["conf"]]) - dt.timedelta(days=1)).isoformat()
        if day not in cache: cache[day] = ratings_before(y, day)
        r, hca = cache[day]
        if g["team_key"] not in r or g["opp_key"] not in r: continue
        hh = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]; p = 0.5 * (1 + math.erf((r[g["team_key"]] - r[g["opp_key"]] + hh * hca) / 11.0 / math.sqrt(2)))
        ct[g["team_key"]] = ct.get(g["team_key"], 0.0) + (float(g["win"]) - p)
    CT[y] = ct
P("\n== CT-surprise diagnostic (v2.0 held-out final residual; positive residual = committee placed the team worse)")
cors, gcors = [], []
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare([dict(r) for r in FINAL[h]]); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = sorted(f, key=lambda r: -r["rank_score"])
    res = [(r["ov"] - p, CT[h].get(r["key"], 0.0)) for p, r in enumerate(o, 1) if r["in_field"] and r.get("ov")]
    c = spearmanr([a for a, _ in res], [b for _, b in res])[0]; cors.append(c); L = {r["key"]: i for i, r in enumerate(o)}
    line = {r["key"]: r["line"] for r in model.assign_lines(f, h)}; fin = matrix_full.submissions(h); dev = []
    for k in line:
        gl = [ {key(t): l for t, l in fin[n].items()}.get(k) for n in GROUP if n in fin]; gl = [x for x in gl if x]
        if gl and k in CT[h] or gl: dev.append((np.mean(gl) - line[k], CT[h].get(k, 0.0)))
    gc = spearmanr([a for a, _ in dev], [b for _, b in dev])[0]; gcors.append(gc)
    P(f"  {h}: corr(residual, CT surprise) {c:+.3f}   corr(elite deviation from v2.0, CT surprise) {gc:+.3f}")
neg = sum(c < 0 for c in cors); P(f"Committee rewards CT surprise beyond v2.0: negative in {neg}/7, mean {np.mean(cors):+.3f} -> {neg >= 6 and np.mean(cors) <= -.10}")

# ---------------- Test 26 ----------------
P("\n== Test 26: ct_surprise in selection and seed models")
BASE0, SEL0, SEED0 = list(model.BASE), list(model.SELECT), list(model.SEED); orig = project.build_year
def with_ct(y):
    rows = [dict(r) for r in features.build_year(y)]
    for r in rows: r["ct_surprise"] = CT[y].get(r["key"], 0.0)
    return rows
res = {"control": [], "T26 both models": [], "seed only (reported)": []}; exa = {n: [] for n in res}; e58 = {n: [] for n in res}
for n, sel, seed in (("control", SEL0, SEED0), ("T26 both models", SEL0 + ["z_ct_surprise"], SEED0 + ["z_ct_surprise"]), ("seed only (reported)", SEL0, SEED0 + ["z_ct_surprise"])):
    model.BASE, model.SELECT, model.SEED = BASE0 + ["ct_surprise"], sel, seed; project.build_year = with_ct
    for h in Y:
        m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(with_ct(h)); m.score(rows)
        f, _ = model.choose_field(rows, h, project_autos=False); L = {r["key"]: r["line"] for r in model.assign_lines(f, h)}; off = off_of(h)
        res[n].append(bm.score(L, off)["score"]); exa[n].append(ex(L, off)); e58[n].append(sum(1 for k, l in L.items() if k in off and off[k] == l and 5 <= off[k] <= 8))
    P(n, res[n])
model.BASE, model.SELECT, model.SEED = BASE0, SEL0, SEED0; project.build_year = orig
P("control reproduces:", res["control"] == CONTROL)
for n, s in res.items():
    dd = np.array(s) - np.array(CONTROL); ok = dd.mean() >= 3 and (dd > 0).sum() >= 5 and dd.min() >= -5
    P(f"{n:<22}{s} mean {np.mean(s):.1f} diff {dd.mean():+.1f} better {(dd > 0).sum()} worse {(dd < 0).sum()} worst {dd.min():+d} PASS={bool(ok)} exact {np.mean(exa[n]):.1f} ({np.mean(exa[n]) - np.mean(exa['control']):+.1f}) lines5-8 exact {np.mean(e58[n]):.1f} pct {[pct(y, v) for y, v in zip(Y, s)]}")
