"""docs/40 (exploratory): overreaction audit, D-7 -> final movement analysis, Anchor-CT diagnostic."""
import sys; sys.path.insert(0, "research")
import datetime as dt, json, math, os, numpy as np
from scipy.sparse import csr_matrix
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import Ridge
from bracketology import history, model, project, metrics, dataset, features, shadow_anchor
from bracketology.sources import torvik, bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); CONTROL = [335, 326, 347, 344, 329, 363, 356]; D = "data/history/edge_timing"
MS = {y: sorted(int(v) for k, v in bm.collect(y)["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX") for y in Y}
pct = lambda y, v: round(100 * sum(x < v for x in MS[y]) / len(MS[y])); P = lambda *a: print(*a, flush=True)
SS = {y: history.SELECTION_SUNDAY[y] for y in Y}; D7 = {y: (dt.date.fromisoformat(SS[y]) - dt.timedelta(days=7)).isoformat() for y in Y}
GAMES = {y: shadow_anchor.annotate(torvik.collect_games(y, ttl=10 ** 9)["rows"], key) for y in Y}
FINAL = {y: features.build_year(y) for y in Y}; off_of = lambda y: {r["key"]: r["seed"] for r in FINAL[y] if r["in_field"]}
NET7 = {y: {key(r["team"]): r["net"] for r in json.load(open(f"{D}/{y}_net_d7.json"))["rows"]} for y in Y if os.path.exists(f"{D}/{y}_net_d7.json")}
champF = {y: {r["key"] for r in FINAL[y] if r["champ"]} for y in Y}

# ---------- CT surprise (same definition as docs/39) ----------
def ratings_before(y, day):
    keys = {r["key"]: i for i, r in enumerate(FINAL[y])}; G = metrics._games(GAMES[y], keys, day); n = len(keys); rr, cc, vv, t = [], [], [], []
    for i, g in enumerate(G):
        hh = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]; rr += [i] * 3; cc += [keys[g["team_key"]], keys[g["opp_key"]], n]; vv += [1.0, -1.0, hh]
        t.append(max(-metrics.MARGIN_CAP, min(metrics.MARGIN_CAP, g["pf"] - g["pa"])))
    c = Ridge(alpha=metrics.RIDGE_ALPHA, fit_intercept=False).fit(csr_matrix((vv, (rr, cc)), shape=(len(G), n + 1)), np.array(t)).coef_
    return {k: c[i] for k, i in keys.items()}, c[n]
CT = {}
for y in Y:
    st = shadow_anchor.tournament_starts(GAMES[y], SS[y]); cache, ct, seen = {}, {}, set()
    for g in GAMES[y]:
        if g["type"] != 2 or g["date_iso"] > SS[y] or g["conf"] not in st: continue
        sig = (g["date_iso"], g["team_key"], g["opp_key"])
        if sig in seen: continue
        seen.add(sig); day = (dt.date.fromisoformat(st[g["conf"]]) - dt.timedelta(days=1)).isoformat()
        if day not in cache: cache[day] = ratings_before(y, day)
        r, hca = cache[day]
        if g["team_key"] in r and g["opp_key"] in r:
            hh = {"H": 1.0, "A": -1.0, "N": 0.0}[g["loc"]]; p = 0.5 * (1 + math.erf((r[g["team_key"]] - r[g["opp_key"]] + hh * hca) / 11.0 / math.sqrt(2)))
            ct[g["team_key"]] = ct.get(g["team_key"], 0.0) + float(g["win"]) - p
    CT[y] = ct

# ---------- Part 1: audit ----------
P("== Part 1: overreaction audit (positive residual = committee placed the team WORSE than v2.0)")
def partial(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z); A = np.c_[np.ones(len(rz)), rz]
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]; ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]; return float(np.corrcoef(ex, ey)[0, 1])
cnt = {"at-large": 0, "champions": 0, "partial": 0}; HELD = {}
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare([dict(r) for r in FINAL[h]]); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = sorted(f, key=lambda r: -r["rank_score"]); HELD[h] = (m, f)
    T = [(r["ov"] - p, CT[h].get(r["key"], 0.0), p, r["champ"], r["team"], r["ov"]) for p, r in enumerate(o, 1) if r["in_field"] and r.get("ov")]
    al = [t for t in T if not t[3]]; ch = [t for t in T if t[3]]
    c_al = spearmanr([t[0] for t in al], [t[1] for t in al])[0]; c_ch = spearmanr([t[0] for t in ch], [t[1] for t in ch])[0]
    c_p = partial([t[0] for t in T], [t[1] for t in T], [t[2] for t in T])
    cnt["at-large"] += c_al > 0; cnt["champions"] += c_ch > 0; cnt["partial"] += c_p > 0
    top = sorted(T, key=lambda t: -t[1])[:3]
    P(f"{h}: excluded (v2 wrong teams) {len(o) - len(T)}; at-large corr {c_al:+.3f} (n {len(al)}), champions corr {c_ch:+.3f} (n {len(ch)}), partial|position {c_p:+.3f}")
    P("     biggest out-performers: " + "; ".join(f"{t[4]} surprise {t[1]:+.2f} v2 pos {t[2]} committee {t[5]} resid {t[0]:+d}" for t in top))
P(f"positive in: at-large {cnt['at-large']}/7, champions {cnt['champions']}/7, partial {cnt['partial']}/7 -> survives: {cnt['at-large'] >= 5 and cnt['partial'] >= 5}")

# ---------- Part 2: movements ----------
P("\n== Part 2: v2.0 line moves D-7 -> Selection Sunday (2021-26)")
def state(y, net, gday, champs):
    rows = [dict(r) for r in FINAL[y]]
    for r in rows: r["net"] = net.get(r["key"], 365) if net is not None else r["net"]; r["champ"] = r["key"] in champs; r.pop("projected_auto", None)
    M = metrics.compute(GAMES[y], {r["key"]: r["net"] for r in rows}, gday)
    for r in rows: r.update(M.get(r["key"], {}))
    return rows
def lines_of(m, rows, y):
    model.prepare(rows); m.score(rows); f, _ = model.choose_field(rows, y, project_autos=True); return {r["key"]: r["line"] for r in model.assign_lines(f, y)}, {r["key"]: r for r in f}
agg = {"auto": [0, 0, 0, 0], "resume": [0, 0, 0, 0]}   # beneficial, harmful, exact gained, exact lost
for h in sorted(NET7):
    off = off_of(h); m = HELD[h][0]; sw = dataset.INELIGIBLE_CHAMPS.get(h, {})
    c7 = {key(sw.get(t, t)) for t in dataset.completed_champions(GAMES[h], D7[h]).values()}
    L7, R7 = lines_of(m, state(h, NET7[h], D7[h], c7), h); LF, RF = lines_of(m, state(h, None, SS[h], champF[h]), h)
    det = {"auto": [], "resume": []}
    for k in set(L7) | set(LF):
        if k not in off: continue
        a, b = L7.get(k), LF.get(k)
        if a == b: continue
        kind = "auto" if (a is None or b is None or (R7[k]["champ"] or R7[k].get("projected_auto")) != RF[k]["champ"]) else "resume"
        if a is None or b is None: agg[kind][2] += b == off[k]; agg[kind][3] += a == off[k]; continue
        good = abs(b - off[k]) < abs(a - off[k]); bad = abs(b - off[k]) > abs(a - off[k])
        agg[kind][0] += good; agg[kind][1] += bad; agg[kind][2] += b == off[k]; agg[kind][3] += a == off[k]
        det[kind].append(f"{RF[k]['team']} {a}->{b} (seed {off[k]}, CT {CT[h].get(k, 0):+.2f}){' +' if good else ' -' if bad else ''}")
    P(f"{h} résumé moves: " + "; ".join(sorted(det["resume"])))
for kind, (g, b, eg, el) in agg.items():
    P(f"{kind:<7} beneficial {g} harmful {b} | exact gained {eg} lost {el} | net exact {eg - el:+d}")
g, b, eg, el = agg["resume"]
P(f"MAXIMUM OPPORTUNITY (résumé moves, 6 seasons): freezing all = {el - eg:+d} exact ({(el - eg) / 6:+.1f}/season); perfect selective freeze <= {el} exact ({el / 6:.1f}/season)")

# ---------- Part 4: Anchor-CT diagnostic ----------
P("\n== Part 4: Anchor-CT, exploratory leave-one-season-out")
ANC = {y: shadow_anchor.anchored_rows(FINAL[y], GAMES[y], SS[y]) for y in Y}
for y in Y: model.attach_overall(ANC[y], y)
res, exa, e58 = [], [], []
for h in Y:
    m_sel, f = HELD[h]; off = off_of(h)
    m_seed = model.Model().fit([r for y in Y if y != h for r in model.prepare([dict(x) for x in ANC[y]])])
    A = {r["key"]: r for r in model.prepare([dict(x) for x in ANC[h]])}; fa = [A[r["key"]] for r in f]; m_seed.score(fa)
    order = sorted(fa, key=lambda r: -r["rank_score"]); slots = __import__("bracketology.fieldformat", fromlist=["x"]).format_for(h).slots
    L = {r["key"]: slots[i] for i, r in enumerate(order)}; res.append(bm.score(L, off)["score"]); exa.append(sum(1 for k, l in L.items() if k in off and off[k] == l))
    e58.append(sum(1 for k, l in L.items() if k in off and off[k] == l and 5 <= off[k] <= 8)); P(h, res[-1], "exact", exa[-1])
CTL_EX = [40, 33, 45, 42, 37, 49, 45]; d = np.array(res) - np.array(CONTROL)
P(f"control  {CONTROL} mean 342.9 exact 41.6")
P(f"Anchor-CT {res} mean {np.mean(res):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} bar-for-information {bool(d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5)} exact {np.mean(exa):.1f} ({np.mean(exa) - np.mean(CTL_EX):+.1f}) lines5-8 exact {np.mean(e58):.1f} (control 6.9) pct {[pct(y, v) for y, v in zip(Y, res)]}")
