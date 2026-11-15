"""docs/41 (exploratory): classify elite championship-week moves that v2.0 missed."""
import sys; sys.path.insert(0, "research")
import datetime as dt, json, os, numpy as np, matrix_full
from bracketology import history, model, project, metrics, dataset, features
from bracketology.sources import torvik
from bracketology.teams import key
from bracketology import shadow_anchor
P = lambda *a: print(*a, flush=True)
Y5 = [2021, 2022, 2023, 2025, 2026]; D = "data/history/edge_timing"
GROUP = ["Dom", "Bauer", "BKS", "Sluder", "DII", "HHD-JT", "801", "Elam", "T3", "RFS"]
SS = {y: history.SELECTION_SUNDAY[y] for y in Y5}; D7 = {y: (dt.date.fromisoformat(SS[y]) - dt.timedelta(days=7)).isoformat() for y in Y5}
GAMES = {y: shadow_anchor.annotate(torvik.collect_games(y, ttl=10 ** 9)["rows"], key) for y in Y5}
FINAL = {y: features.build_year(y) for y in Y5}
def state(y, net, gday, champs):
    rows = [dict(r) for r in FINAL[y]]
    for r in rows: r["net"] = net.get(r["key"], 365) if net is not None else r["net"]; r["champ"] = r["key"] in champs; r.pop("projected_auto", None)
    M = metrics.compute(GAMES[y], {r["key"]: r["net"] for r in rows}, gday)
    for r in rows: r.update(M.get(r["key"], {}))
    return rows
def run(m, rows, y):
    model.prepare(rows); m.score(rows); f, _ = model.choose_field(rows, y, project_autos=True); o = model.assign_lines(f, y)
    return o, {r["key"]: r for r in o}
cats = {c: [] for c in "ABCD"}; ctw = {"with CT": [0, 0, 0], "without CT": [0, 0, 0]}   # teams, elite moved, v2 moved
per_season = {}
for h in Y5:
    off = {r["key"]: r["seed"] for r in FINAL[h] if r["in_field"]}; m = model.Model().fit(project.training_rows(exclude={h}))
    net7 = {key(r["team"]): r["net"] for r in json.load(open(f"{D}/{h}_net_d7.json"))["rows"]}; sw = dataset.INELIGIBLE_CHAMPS.get(h, {})
    c7 = {key(sw.get(t, t)) for t in dataset.completed_champions(GAMES[h], D7[h]).values()}; cF = {r["key"] for r in FINAL[h] if r["champ"]}
    o7, R7 = run(m, state(h, net7, D7[h], c7), h); oF, RF = run(m, state(h, None, SS[h], cF), h)
    sF = np.array([r["rank_score"] for r in oF]); u = float(np.median(np.abs(np.diff(sF))))
    M7 = json.load(open(f"{D}/{h}_matrix_d7.json")); snap = dt.date.fromisoformat(M7["updated"]); fin = matrix_full.submissions(h); E = []
    for g in GROUP:
        if g in M7["subs"] and g in fin and g in M7["dates"] and snap - dt.timedelta(days=3) <= dt.date.fromisoformat(M7["dates"][g]) <= snap:
            E.append(({key(t): l for t, l in M7["subs"][g].items()}, {key(t): l for t, l in fin[g].items()}))
    ctteams = {g["team_key"] for g in GAMES[h] if g["type"] == 2 and D7[h] < g["date_iso"] <= SS[h]}
    s7 = {r["key"]: r["rank_score"] for r in o7}
    rows_out = []
    for k in off:
        if k not in R7 or k not in RF: continue
        pairs = [(a[k], b[k]) for a, b in E if k in a and k in b]
        if len(pairs) < len(E) / 2: continue
        dm = float(np.mean([b - a for a, b in pairs])); v2moved = R7[k]["line"] != RF[k]["line"]
        grp = "with CT" if k in ctteams else "without CT"; ctw[grp][0] += 1; ctw[grp][1] += abs(dm) >= .5; ctw[grp][2] += v2moved
        if abs(dm) < .5 or v2moved: continue
        d = -1 if dm < 0 else 1; sgn = -d   # score up = better line; elite toward better (d=-1) -> positive own change wanted
        own = sgn * (RF[k]["rank_score"] - R7[k]["rank_score"]) / u
        others = [v for kk, v in s7.items() if kk != k]; r_cf = 1 + sum(v > RF[k]["rank_score"] for v in others)
        oth = -d * 0 + (sgn * -1) * (RF[k]["overall"] - r_cf)   # positions toward elite direction: better line (d=-1) means smaller rank
        oth = (r_cf - RF[k]["overall"]) if d == -1 else (RF[k]["overall"] - r_cf)
        L = RF[k]["line"]; adj = [r["rank_score"] for r in oF if r["line"] == L + d]
        bd = ((min(adj) - RF[k]["rank_score"]) if d == -1 else (RF[k]["rank_score"] - max(adj))) / u if adj else float("nan")
        champ_change = bool(R7[k]["champ"] or R7[k].get("projected_auto")) != bool(RF[k]["champ"])
        cat = "D" if champ_change else "A" if own >= 2 else "C" if oth >= 2 else "B"
        new = L + int(round(dm)); gain = int(new == off[k]) - int(L == off[k])
        rec = dict(season=h, team=RF[k]["team"], line=L, elite=round(dm, 2), seed=off[k], own=round(own, 2), others=oth, boundary=round(bd, 2), ct=k in ctteams, cat=cat, gain=gain, dir=d)
        cats[cat].append(rec); rows_out.append(rec)
    # paired: opposite-direction missed move across the same boundary
    for r in rows_out:
        b = r["line"] + (0 if r["dir"] == 1 else -1)   # boundary index between line b and b+1
        r["paired"] = any(o is not r and o["dir"] == -r["dir"] and (o["line"] + (0 if o["dir"] == 1 else -1)) == b for o in rows_out)
    per_season[h] = rows_out
    P(f"\n{h}: u={u:.4f}, fresh elite brackets {len(E)}, missed elite moves {len(rows_out)}")
    for r in sorted(rows_out, key=lambda r: (r["cat"], r["line"])):
        P(f"   {r['cat']} {r['team']:<20} v2 line {r['line']} elite {r['elite']:+.2f} seed {r['seed']} own {r['own']:+.2f}u others {r['others']:+d} boundary {r['boundary']:.2f}u CT {'y' if r['ct'] else 'n'} paired {'y' if r['paired'] else 'n'} adopt-elite exact {r['gain']:+d}")
P("\n== Summary")
tot = sum(len(v) for v in cats.values())
for c in "ABCD":
    v = cats[c]; seas = {h: sum(r["gain"] for r in v if r["season"] == h) for h in Y5}
    P(f"Category {c}: {len(v)} ({len(v) / tot:.0%}) | adopt-elite exact gain {sum(r['gain'] for r in v):+d} ({sum(r['gain'] for r in v) / 5:+.1f}/season) by season {seas} | paired {sum(r['paired'] for r in v)} | median own {np.median([r['own'] for r in v]) if v else float('nan'):+.2f}u, median boundary {np.nanmedian([r['boundary'] for r in v]) if v else float('nan'):.2f}u")
for g, (n, e, v) in ctw.items(): P(f"{g:<11} teams {n}: elite moved {e} ({e / n:.0%}), v2.0 moved {v} ({v / n:.0%})")
A = cats["A"]; sa = [sum(r["gain"] for r in A if r["season"] == h) for h in Y5]
P(f"EXPERIMENT TRIGGER (A gain >= +1.5/season and positive in >= 4/5): {sum(sa) / 5 >= 1.5 and sum(x > 0 for x in sa) >= 4}")
