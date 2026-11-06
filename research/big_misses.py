"""Big seed misses (2+ lines) and wrong-team picks under leave-one-season-out production. Looks for patterns repeating across seasons."""
import collections, json
import numpy as np
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.sources import torvik
from bracketology.teams import key
Y = sorted(history.SELECTION_SUNDAY); ALL = []; OUT = []; IN = []
def extra(rows, y):
    """Non-conference schedule strength, conference record, opponent NET among games, from the log as of the cutoff."""
    day = history.SELECTION_SUNDAY[y]; net = {r["key"]: r["net"] for r in rows}; F = collections.defaultdict(lambda: collections.defaultdict(list))
    for g in torvik.collect_games(y)["rows"]:
        m, d, yy = g["date"].split("/"); iso = f"20{yy}-{int(m):02d}-{int(d):02d}"
        if iso > day: continue
        a, b = key(g["team"]), key(g["opp"])
        if a not in net or b not in net: continue
        F[a]["t%d" % g["type"]].append((net[b], g["win"], g["loc"]))
    for r in rows:
        f = F[r["key"]]; nc = f["t0"]; cf = f["t1"]; ct = f["t2"]
        r["nc_opp"] = float(np.mean([n for n, _, _ in nc])) if nc else 200.; r["nc_q"] = sum(n <= 75 for n, _, _ in nc); r["nc_w"] = sum(w for _, w, _ in nc)
        r["conf_pct"] = sum(w for _, w, _ in cf) / max(1, len(cf)); r["ct_w"] = sum(w for _, w, _ in ct); r["nc_sub"] = sum(n > 240 for n, _, _ in nc) / max(1, len(nc))
    return rows
for h in Y:
    m = model.Model().fit(project.training_rows(exclude={h})); rows = extra(model.prepare(build_year(h)), h); m.score(rows)
    field, rest = model.choose_field(rows, h, project_autos=False); order = model.assign_lines(field, h); line = {r["key"]: r["line"] for r in order}
    for r in rows:
        r["_line"] = line.get(r["key"])
        if r["in_field"]:
            r["_err"] = (r["_line"] - r["seed"]) if r["_line"] else None; ALL.append(r)   # positive: model line worse than committee
            if not r["_line"]: OUT.append(r)
        elif r["_line"]: IN.append(r)
def fmt(r): return f"{r['year']} {r['team']:18}{r['lg']:6} seed {str(r['seed']):4} model {str(r['_line']):5} NET {r['net']:3} WAB {r['wab']:5.1f} ratRk {np.exp(r['rk_rating']):3.0f} Q1 {r['cq1_w']:.0f}-{r['cq1_l']:.0f} Q3/4L {r['cq3_l']:.0f}/{r['cq4_l']:.0f} rec {r['w']}-{r['l']} conf {r['conf_pct']:.2f} ncOpp {r['nc_opp']:3.0f} p {r['p_in']:.2f} champ {int(r['champ'])}"
big = [r for r in ALL if r["_err"] is not None and abs(r["_err"]) >= 2]
print("=== model too HIGH on the team (committee seeded worse), 2+ lines"); [print(fmt(r)) for r in sorted(big, key=lambda r: r["_err"]) if r["_err"] < 0]
print("=== model too LOW (committee seeded better), 2+ lines"); [print(fmt(r)) for r in sorted(big, key=lambda r: -r["_err"]) if r["_err"] > 0]
print("=== committee took, model left out"); [print(fmt(r)) for r in OUT]
print("=== model took, committee left out"); [print(fmt(r)) for r in IN]
def grp(lab, f, rows=None):
    s = [r for r in (rows or ALL) if r["_err"] is not None and f(r)]
    if not s: return
    by = collections.defaultdict(list)
    for r in s: by[r["year"]].append(r["_err"])
    mn = np.mean([r["_err"] for r in s]); same = sum(np.sign(np.mean(v)) == np.sign(mn) for v in by.values())
    print(f"{lab:44} n {len(s):3} mean err {mn:+.2f} big {sum(abs(r['_err']) >= 2 for r in s):3} same sign {same}/{len(by)}")
print("=== signed error by group (+ = model line worse than the committee's)")
grp("non-power champions", lambda r: r["champ"] and not r["is_power"])
grp("non-power champions, model line <= 12", lambda r: r["champ"] and not r["is_power"] and r["_line"] <= 12)
grp("power champions", lambda r: r["champ"] and r["is_power"])
grp("non-power at-large", lambda r: not r["champ"] and not r["is_power"])
grp("power at-large", lambda r: not r["champ"] and r["is_power"])
grp("0-2 Q1 wins, NET<=50", lambda r: r["cq1_w"] <= 2 and r["net"] <= 50)
grp("6+ Q1 losses at-large", lambda r: r["cq1_l"] >= 8 and not r["champ"])
grp("12+ losses", lambda r: r["l"] >= 12)
grp("NET much better than WAB rank", lambda r: r["rk_wab"] - np.log(r["net"]) > .5)
grp("WAB rank much better than NET", lambda r: np.log(r["net"]) - r["rk_wab"] > .5)
grp("NET much better than own rating", lambda r: r["rk_rating"] - np.log(r["net"]) > .4)
grp("conference record .700+", lambda r: r["conf_pct"] >= .7 and r["net"] <= 60)
grp("conference record under .500", lambda r: r["conf_pct"] < .5)
grp("strong non-conference schedule (avg NET<=90)", lambda r: r["nc_opp"] <= 90)
grp("weak non-conference schedule (avg NET>=200)", lambda r: r["nc_opp"] >= 200 and r["net"] <= 75)
print("=== OUT vs IN group means")
for n in ("net", "wab", "cq1_w", "cq1_l", "cq3_l", "cq4_l", "l", "conf_pct", "nc_opp", "nc_q", "ct_w", "is_power"):
    print(f"{n:10} committee-only {np.mean([float(r[n]) for r in OUT]):7.2f}   model-only {np.mean([float(r[n]) for r in IN]):7.2f}")
