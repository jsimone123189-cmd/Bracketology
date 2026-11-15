"""Runs docs/12: Test 1 (conf_wpct, field model), Test 2 (nc_sos_np, seed model), team confidence with nested spreads,
Test 3 only if a group qualifies, and the consistent group's strengths. Research only; production is untouched."""
import collections, math
import numpy as np
from bracketology import history, model, project, fieldformat
from bracketology.features import build_year as raw_build
from bracketology.sources import bracketmatrix as bm, torvik
from bracketology.teams import key

Y = sorted(history.SELECTION_SUNDAY); GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]
CONTROL = [335, 326, 347, 344, 329, 363, 356]
_cache = {}

def feats(y):
    if y in _cache: return [dict(r) for r in _cache[y]]
    rows = raw_build(y); day = history.SELECTION_SUNDAY[y]; by = {r["key"]: r for r in rows}
    conf = {r["key"]: r["lg"] for r in rows}; cw, cg, nc = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    for g in torvik.collect_games(y, ttl=10 ** 9)["rows"]:
        a, b = key(g["team"]), key(g["opp"]); m, d, yy = g["date"].split("/")
        if f"20{yy}-{int(m):02d}-{int(d):02d}" > day or a not in by or b not in by: continue
        if conf[a] and conf[a] == conf[b]: cg[a] += 1; cw[a] += bool(g["win"])
        else: nc[a].append(math.log(by[b]["net"]))
    for r in rows:
        k = r["key"]; r["conf_wpct"] = cw[k] / cg[k] if cg[k] else r["w"] / max(1, r["w"] + r["l"])
        r["nc_sos"] = float(np.mean(nc[k])) if nc[k] else math.log(180); r["nc_sos_np"] = r["nc_sos"] * (1 - r["is_power"])
        r["_conf_games"], r["_nc_games"] = cg[k], len(nc[k])
    _cache[y] = rows
    return [dict(r) for r in rows]

project.build_year = feats
BASE_SEL, BASE_SEED = list(model.SELECT), list(model.SEED)

def run(h, train_years, sel, seed):
    model.SELECT, model.SEED = sel, seed
    m = model.Model().fit(project.training_rows(exclude=set(Y) - set(train_years)))
    rows = model.prepare(feats(h)); model.attach_overall(rows, h); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h)
    return {"rows": {r["key"]: r for r in rows}, "order": o, "lines": {r["key"]: r["line"] for r in o}, "overall": {r["key"]: r["overall"] for r in o}}

def truth(res): return {k: r["seed"] for k, r in res["rows"].items() if r["in_field"]}
def score(res): return bm.score(res["lines"], truth(res))["score"]

def verdict(name, s, base):
    d = np.array(s) - np.array(base); ok = d.mean() >= 3 and (d > 0).sum() >= 5 and d.min() >= -5
    print(f"{name:<34}{s} mean {np.mean(s):.1f} diff {d.mean():+.1f} better {(d > 0).sum()} worse {(d < 0).sum()} worst {d.min():+d} PASS={bool(ok)}", flush=True)

ctrl = {h: run(h, set(Y) - {h}, BASE_SEL, BASE_SEED) for h in Y}
cs = [score(ctrl[h]) for h in Y]; print("control", cs, "reproduces:", cs == CONTROL, flush=True)
for y in Y:
    fld = [r for r in feats(y) if r["in_field"]]
    print(f"  coverage {y}: in-field teams with conference games {sum(r['_conf_games'] > 0 for r in fld)}/{len(fld)}, with non-conference games {sum(r['_nc_games'] > 0 for r in fld)}/{len(fld)}")

print("\n== Test 1: conf_wpct in the field model")
t1 = {h: run(h, set(Y) - {h}, BASE_SEL + ["conf_wpct"], BASE_SEED) for h in Y}; verdict("Test 1", [score(t1[h]) for h in Y], cs)
for h in Y:
    w0, w1 = set(ctrl[h]["lines"]) - set(truth(ctrl[h])), set(t1[h]["lines"]) - set(truth(t1[h]))
    print(f"   {h} wrong teams v2.0 {len(w0)} -> {len(w1)}  fixed {sorted(w0 - w1)} new {sorted(w1 - w0)}")
print("\n== Test 2: nc_sos_np in the seed model")
t2 = {h: run(h, set(Y) - {h}, BASE_SEL, BASE_SEED + ["nc_sos_np"]) for h in Y}; verdict("Test 2", [score(t2[h]) for h in Y], cs)

print("\n== Part 3: confidence (nested spreads)")
BANDS = [(1, 16), (17, 32), (33, 48), (49, 999)]
band = lambda p: next(i for i, (a, b) in enumerate(BANDS) if a <= p <= b)
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def pexact(p, line, slots, sig):
    pos = [i + 1 for i, l in enumerate(slots) if l == line]
    return Phi((max(pos) + .5 - p) / sig) - Phi((min(pos) - .5 - p) / sig)
def group(r): return ("power" if r["is_power"] else "nonpower") + ("_auto" if r["champ"] else "_atlarge")

inner = {}
for h in Y:
    res = collections.defaultdict(list)
    for s in Y:
        if s == h: continue
        out = run(s, set(Y) - {h, s}, BASE_SEL, BASE_SEED)
        for k, p in out["overall"].items():
            r = out["rows"][k]
            if r["in_field"] and r["ov"]: res[band(p)].append((r["ov"] - p, s, k, out))
    inner[h] = res
    print(f"  {h}: inner spread by band", [round(float(np.std([x[0] for x in res[b]])), 1) if res[b] else None for b in range(4)], flush=True)

records = []
for h in Y:
    sig = {b: max(1.0, float(np.std([x[0] for x in inner[h][b]]))) for b in range(4)}; slots = fieldformat.format_for(h).slots; c = ctrl[h]
    for k, line in c["lines"].items():
        r = c["rows"][k]; p = c["overall"][k]; pe = pexact(p, line, slots, sig[band(p)]); pin = 1.0 if r["champ"] else r["p_in"]
        records.append({"y": h, "k": k, "team": r["team"], "conf": pin * pe, "pin": pin, "in": bool(r["in_field"]), "seed": r["seed"] if r["in_field"] else None, "line": line, "g": group(r), "p": p})
bins = [(0, .3), (.3, .5), (.5, .7), (.7, 1.01)]
print("  bin        n  mean conf  actual exact  wrong-team  mean |err|  2+ off")
for a, b in bins:
    x = [r for r in records if a <= r["conf"] < b]; inn = [r for r in x if r["in"]]
    print(f"  {a:.1f}-{min(b, 1):.1f}  {len(x):>4}   {np.mean([r['conf'] for r in x]):.2f}       {np.mean([r['in'] and r['seed'] == r['line'] for r in x]):.2f}        {np.mean([not r['in'] for r in x]):.2f}       {np.mean([abs(r['seed'] - r['line']) for r in inn]):.2f}      {np.mean([abs(r['seed'] - r['line']) >= 2 for r in inn]):.2f}")
print(f"  exact-line Brier {np.mean([(r['conf'] - (r['in'] and r['seed'] == r['line'])) ** 2 for r in records]):.4f}, always-mean Brier {np.var([float(r['in'] and r['seed'] == r['line']) for r in records]):.4f}")
qual = []
print("  under 0.5 confidence, mean signed error (actual seed minus line) by season:")
for g in ("power_atlarge", "nonpower_atlarge", "power_auto", "nonpower_auto"):
    per = [np.mean([r["seed"] - r["line"] for r in records if r["y"] == h and r["g"] == g and r["conf"] < .5 and r["in"]] or [np.nan]) for h in Y]
    n = sum(1 for r in records if r["g"] == g and r["conf"] < .5 and r["in"]); v = [x for x in per if not np.isnan(x)]
    same = max(sum(x > 0 for x in v), sum(x < 0 for x in v)); m = float(np.mean([r["seed"] - r["line"] for r in records if r["g"] == g and r["conf"] < .5 and r["in"]]))
    ok = same >= 6 and abs(m) >= .5; qual += [g] if ok else []
    print(f"    {g:<17} n {n:>3} by season {[round(float(x), 2) for x in per]} mean {m:+.2f} same sign {same}/7 -> predictable {ok}")

if qual:
    print("\n== Test 3: out-of-fold shift for", qual)
    t3 = []
    for h in Y:
        c = ctrl[h]; slots = fieldformat.format_for(h).slots; sig_all = {b: max(1.0, float(np.std([x[0] for x in inner[h][b]]))) for b in range(4)}
        shift = {}
        for g in qual:
            xs = [d for b in range(4) for d, s, k, out in inner[h][b] if group(out["rows"][k]) == g and pexact(out["overall"][k], out["lines"][k], fieldformat.format_for(s).slots, sig_all[band(out["overall"][k])]) * (1.0 if out["rows"][k]["champ"] else out["rows"][k]["p_in"]) < .5]
            shift[g] = float(np.mean(xs)) if xs else 0.0
        conf_of = {r["k"]: r["conf"] for r in records if r["y"] == h}
        pos = {k: c["overall"][k] + (shift.get(group(c["rows"][k]), 0.0) if conf_of[k] < .5 else 0.0) for k in c["lines"]}
        new = {k: slots[i] for i, k in enumerate(sorted(pos, key=lambda k: (pos[k], c["overall"][k])))}
        t3.append(bm.score(new, truth(c))["score"]); print(f"   {h} shifts {dict((g, round(v, 1)) for g, v in shift.items())}")
    verdict("Test 3", t3, cs)
else: print("\n== Test 3 not run: no group met the predictable-error rule")

print("\n== Part 4: the consistent group's strengths")
def area(lines, off, rows):
    both = [k for k in lines if k in off]
    e58 = [lines[k] == off[k] for k in both if 5 <= off[k] <= 8]
    na = [abs(lines[k] - off[k]) for k in both if rows[k]["champ"] and not rows[k]["is_power"]]
    nl = [abs(lines[k] - off[k]) for k in both if not rows[k]["champ"] and not rows[k]["is_power"]]
    return {"exact5_8": np.mean(e58), "np_auto_abs": np.mean(na) if na else np.nan, "np_atl_abs": np.mean(nl) if nl else np.nan, "wrong": sum(k not in off for k in lines)}
M = collections.defaultdict(dict); V = {}; subs_all = {}
for h in Y:
    rows = ctrl[h]["rows"]; off = truth(ctrl[h]); subs = bm.collect(h)["submissions"]; V[h] = area(ctrl[h]["lines"], off, rows)
    for g in GROUP:
        if g in subs: s = {key(t): l for t, l in subs[g].items() if key(t) in rows}; subs_all[(g, h)] = s; M[g][h] = area(s, off, rows)
better = {"exact5_8": lambda a, b: a > b, "np_auto_abs": lambda a, b: a < b, "np_atl_abs": lambda a, b: a < b, "wrong": lambda a, b: a < b}
for f in better:
    print(f"  {f}: v2.0 mean {np.nanmean([V[h][f] for h in Y]):.2f}")
    rank = []
    for g in GROUP:
        hs = list(M[g]); wins = sum(better[f](M[g][h][f], V[h][f]) for h in hs if not np.isnan(M[g][h][f])); m = np.nanmean([M[g][h][f] for h in hs])
        rank.append((m, g, wins, len(hs)))
    rank.sort(reverse=f == "exact5_8")
    for i, (m, g, wins, n) in enumerate(rank): print(f"     {g:<8} mean {m:.2f} beats v2.0 in {wins}/{n}{'  <- STRONG' if i == 0 and wins >= .75 * n else ''}")

print("\n  What each weights: pooled regression of line on standardized team-sheet numbers (positive = worse line)")
F = ["net_log", "wab", "sor", "rating", "cq1_w", "cq1_l", "conf_wpct", "nc_sos", "is_power", "champ"]
def coefs(pairs):
    X, yv = [], []
    for h, lines in pairs:
        rows = ctrl[h]["rows"]; ks = [k for k in lines if k in rows]
        A = np.array([[math.log(rows[k]["net"]) if f == "net_log" else float(rows[k][f]) for f in F] for k in ks])
        A = (A - A.mean(0)) / (A.std(0) + 1e-9); X.append(A); yv += [lines[k] for k in ks]
    X = np.vstack(X); return np.linalg.lstsq(np.column_stack([np.ones(len(X)), X]), np.array(yv, float), rcond=None)[0][1:]
cm = coefs([(h, truth(ctrl[h])) for h in Y]); vm = coefs([(h, ctrl[h]["lines"]) for h in Y])
print("  " + " ".join(f"{f[:9]:>9}" for f in F) + "   dist to committee")
print("  " + " ".join(f"{x:>9.2f}" for x in cm) + "   committee")
print("  " + " ".join(f"{x:>9.2f}" for x in vm) + f"   v2.0  {np.linalg.norm(vm - cm):.2f}")
for g in GROUP:
    gm = coefs([(h, s) for (gg, h), s in subs_all.items() if gg == g])
    print("  " + " ".join(f"{x:>9.2f}" for x in gm) + f"   {g:<6}{np.linalg.norm(gm - cm):.2f}")
