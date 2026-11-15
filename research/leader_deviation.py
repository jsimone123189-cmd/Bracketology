"""docs/15: do the consistent nine's disagreements with v2.0 point toward the committee, and what explains them."""
import sys; sys.path.insert(0, "research")
import collections, math, numpy as np, matrix_full
from scipy.stats import spearmanr
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.sources import torvik, torvik_sheets as ts
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3"]
NAMES = ["conf_reg_champ", "ct_wins", "ct_lost_first", "losses", "q34_losses", "is_power", "champ", "net_vs_rating", "kpi_sor_vs_net", "last10"]
def extra(y, rows):
    day = history.SELECTION_SUNDAY[y]; R = {r["key"]: r for r in rows}; cw, cg, ctw, ctfirst = collections.Counter(), collections.Counter(), collections.Counter(), {}
    for g in sorted(torvik.collect_games(y, ttl=10 ** 9)["rows"], key=lambda g: (g["date"][-2:], g["date"])):
        a = key(g["team"]); m, d, yy = g["date"].split("/")
        if a not in R or f"20{yy}-{int(m):02d}-{int(d):02d}" > day: continue
        if g["type"] == 1: cg[a] += 1; cw[a] += bool(g["win"])
        if g["type"] == 2:
            ctw[a] += bool(g["win"]); ctfirst.setdefault(a, bool(g["win"]))
    best = collections.defaultdict(float)
    for k, r in R.items():
        if cg[k]: best[r["lg"]] = max(best[r["lg"]], cw[k] / cg[k])
    sh = {}
    try: sh = ts.parse(open(f"data/raw/teamsheets/{y}.html", errors="replace").read())
    except FileNotFoundError: pass
    for k, r in R.items():
        r["conf_reg_champ"] = float(bool(cg[k]) and cw[k] / cg[k] >= best[r["lg"]] - 1e-9); r["ct_wins"] = float(ctw[k]); r["ct_lost_first"] = float(ctfirst.get(k) is False)
        r["losses"] = float(r["l"]); r["q34_losses"] = float(r["cq3_l"] + r["cq4_l"]); r["net_vs_rating"] = math.log(r["net"]) - math.log(r["rating_rank"])
        r["kpi_sor_vs_net"] = (np.mean([math.log(sh[k]["r_kpi"]), math.log(sh[k]["r_sor"])]) - math.log(sh[k]["r_net"])) if k in sh else None
        r["last10"] = float(r["last10"]); r["champ"] = float(r["champ"])
corr = collections.defaultdict(dict); ccorr = collections.defaultdict(dict); agree = []
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); o = model.assign_lines(f, h); v2 = {r["key"]: r["line"] for r in o}
    extra(h, rows); R = {r["key"]: r for r in rows}; subs = matrix_full.submissions(h)
    G = [{key(t): l for t, l in subs[g].items()} for g in GROUP if g in subs]
    ks = [k for k, r in R.items() if r["in_field"] and k in v2 and sum(k in g for g in G) >= 3]
    gd = {k: np.mean([g[k] for g in G if k in g]) - v2[k] for k in ks}; cd = {k: R[k]["seed"] - v2[k] for k in ks}
    big = [k for k in ks if abs(gd[k]) >= .5]; same = [np.sign(gd[k]) == np.sign(cd[k]) for k in big if cd[k] != 0]
    agree.append(spearmanr([gd[k] for k in ks], [cd[k] for k in ks])[0])
    print(f"{h}: teams {len(ks)}  corr(group dev, committee dev) {agree[-1]:+.2f}  group moved {len(big)} teams by 0.5+; committee moved the same way {sum(same)}/{len(same)} (others: committee kept v2.0's line {sum(1 for k in big if cd[k] == 0)})", flush=True)
    for n in NAMES:
        x = [(R[k][n], gd[k], cd[k]) for k in ks if R[k][n] is not None]
        if len(x) > 10 and np.std([a for a, _, _ in x]) > 0:
            corr[n][h] = spearmanr([a for a, _, _ in x], [b for _, b, _ in x])[0]; ccorr[n][h] = spearmanr([a for a, _, _ in x], [c for _, _, c in x])[0]
print("\ncharacteristic     corr with group deviation by season          mean   same sign   committee mean  qualifies")
best = None
for n in NAMES:
    v = corr[n]; vs = list(v.values())
    if not vs: continue
    need = 3 if n == "kpi_sor_vs_net" else 6; same = max(sum(x > 0 for x in vs), sum(x < 0 for x in vs)); mean = float(np.mean(vs)); cm = float(np.mean(list(ccorr[n].values())))
    q = same >= need and abs(mean) >= .15 and np.sign(cm) == np.sign(mean)
    print(f"{n:<16} {[round(float(v[h]), 2) for h in v]}  {mean:+.2f}   {same}/{len(vs)}     {cm:+.2f}        {q}")
    if q and n != "kpi_sor_vs_net" and (best is None or abs(mean) > best[1]): best = (n, abs(mean))
print("\nSTRONGEST QUALIFYING (seven seasons):", best)
