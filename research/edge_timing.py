"""docs/36 Part 2: when do elite brackets pull ahead of v2.0? D-7 (one week before Selection Sunday) vs final."""
import sys; sys.path.insert(0, "research")
import datetime as dt, json, os, numpy as np, matrix_full
from bracketology import history, model, project, metrics, dataset
from bracketology.features import build_year
from bracketology.sources import torvik, bracketmatrix as bm
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); D = "data/history/edge_timing"
GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3", "RFS"]
def exact(sub, off): return sum(1 for k, l in sub.items() if k in off and off[k] == l)
def v2_d7(h, d7, net7):
    rows = [dict(r) for r in build_year(h)]; nr = {key(r["team"]): r["net"] for r in net7}
    games = torvik.collect_games(h, ttl=10 ** 9)["rows"]
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, d, y = g["date"].split("/"); g["date_iso"] = f"20{y}-{int(m):02d}-{int(d):02d}"
    swap = dataset.INELIGIBLE_CHAMPS.get(h, {}); champs = {key(swap.get(t, t)) for t in dataset.completed_champions(games, d7).values()}
    miss = 0
    for r in rows:
        if r["key"] in nr: r["net"] = nr[r["key"]]
        else: r["net"] = 365; miss += 1
        r["champ"] = r["key"] in champs; r.pop("projected_auto", None)
    M = metrics.compute(games, {r["key"]: r["net"] for r in rows}, d7)
    for r in rows: r.update(M.get(r["key"], {}))
    byc = {}
    for r in rows: byc.setdefault(r["lg"], []).append(r.get("rating", 0.0))
    for r in rows: r["conf_strength"] = float(np.mean(sorted(byc[r["lg"]], reverse=True)[:4]))
    m = model.Model().fit(project.training_rows(exclude={h})); model.prepare(rows); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=True); return {r["key"]: r["line"] for r in model.assign_lines(f, h)}, len(champs), miss
res = []
for h in Y:
    fm, fn = f"{D}/{h}_matrix_d7.json", f"{D}/{h}_net_d7.json"
    if not (os.path.exists(fm) and os.path.exists(fn)): print(h, "skipped: no D-7 snapshot", flush=True); continue
    M7, N7 = json.load(open(fm)), json.load(open(fn)); d7 = (dt.date.fromisoformat(history.SELECTION_SUNDAY[h]) - dt.timedelta(days=7)).isoformat()
    rows = build_year(h); off = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    # final
    m = model.Model().fit(project.training_rows(exclude={h})); pr = model.prepare([dict(r) for r in rows]); m.score(pr)
    f, _ = model.choose_field(pr, h, project_autos=False); vF = {r["key"]: r["line"] for r in model.assign_lines(f, h)}
    v7, nch, miss = v2_d7(h, d7, N7["rows"])
    fin = matrix_full.submissions(h); snap = dt.date.fromisoformat(M7["updated"])
    g7, gF, s7, sF, used = [], [], [], [], []
    for n in GROUP:
        if n not in M7["subs"] or n not in fin or n not in M7["dates"]: continue
        if not (snap - dt.timedelta(days=3) <= dt.date.fromisoformat(M7["dates"][n]) <= snap): continue
        a = {key(t): l for t, l in M7["subs"][n].items()}; b = {key(t): l for t, l in fin[n].items()}
        g7.append(exact(a, off)); gF.append(exact(b, off)); s7.append(bm.score(a, off)["score"]); sF.append(bm.score(b, off)["score"]); used.append(n)
    cons7 = None
    r = dict(season=h, n=len(used), who=used, champs_done=nch, net_unmatched=miss, v2_7=exact(v7, off), v2_F=exact(vF, off), g_7=float(np.mean(g7)) if g7 else None, g_F=float(np.mean(gF)) if gF else None,
             v2s_7=bm.score(v7, off)["score"], v2s_F=bm.score(vF, off)["score"], gs_7=float(np.mean(s7)) if s7 else None, gs_F=float(np.mean(sF)) if sF else None)
    res.append(r)
    print(f"{h} D-7 matrix updated {M7['updated']}, NET through {N7['through']}, champions decided by D-7: {nch}, NET unmatched {miss}, group n={len(used)} {used}")
    if g7: print(f"   exact lines   v2.0 D-7 {r['v2_7']}  final {r['v2_F']}  | group D-7 {r['g_7']:.1f}  final {r['g_F']:.1f}  | gap D-7 {r['g_7']-r['v2_7']:+.1f}  gap final {r['g_F']-r['v2_F']:+.1f}")
    if g7: print(f"   Matrix score  v2.0 D-7 {r['v2s_7']}  final {r['v2s_F']}  | group D-7 {r['gs_7']:.1f}  final {r['gs_F']:.1f}", flush=True)
ok = [r for r in res if r["g_7"] is not None]
gap7 = np.array([r["g_7"] - r["v2_7"] for r in ok]); gapF = np.array([r["g_F"] - r["v2_F"] for r in ok]); grow = gapF - gap7
dv2 = np.array([r["v2_F"] - r["v2_7"] for r in ok]); dg = np.array([r["g_F"] - r["g_7"] for r in ok])
print(f"\nSeasons with data: {[r['season'] for r in ok]}")
print(f"Mean exact-seed gap: D-7 {gap7.mean():+.1f}, final {gapF.mean():+.1f}; growth {grow.mean():+.1f}, positive in {(grow > 0).sum()}/{len(ok)}")
print(f"Final-week improvement: group {dg.mean():+.1f} exact, v2.0 {dv2.mean():+.1f} exact; game-information share {dv2.mean() / dg.mean() if dg.mean() else float('nan'):.0%}")
print("BUILT IN FINAL WEEK:", bool(grow.mean() >= 3 and (grow > 0).sum() >= min(5, len(ok))), "| ALREADY THERE BEFORE:", bool(gap7.mean() >= .7 * gapF.mean()))
