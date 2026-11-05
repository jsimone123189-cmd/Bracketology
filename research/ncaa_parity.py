"""Can NCAA scoreboard data replace Torvik's game log? Compare games and locations on 2026, then rebuild metrics and score the model."""
import collections, json, sys
from datetime import date
import numpy as np
from scipy.stats import spearmanr
from bracketology import history, metrics, model, project
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm, ncaa_games, torvik
from bracketology.teams import key
Y = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
day = history.SELECTION_SUNDAY[Y]; end = date.fromisoformat(day); start = date(end.year - 1, 11, 1)
n = ncaa_games.collect(start, end)["rows"]; t = torvik.collect_games(Y)["rows"]
F = build_year(Y); K = {r["key"] for r in F}; nr = {r["key"]: r["net"] for r in F}
ids = sorted({g["id"] for g in n if key(g["team"]) in K and key(g["opp"]) in K}); print("fetching venues for", len(ids), "games", flush=True)
V = {i: ncaa_games.venue(i) for i in ids}; print("venue known", sum(1 for v in V.values() if v), flush=True); ncaa_games.mark_neutral(n, V)
def iso(s): m, d, y = s.split("/"); return f"20{y}-{int(m):02d}-{int(d):02d}"
for g in n + t: g["team_key"], g["opp_key"], g["date_iso"] = key(g["team"]), key(g["opp"]), iso(g["date"])
print("unmatched NCAA names (D-I vs D-I expected none):", collections.Counter(g["team"] for g in n if g["team_key"] not in K and g["opp_key"] in K).most_common(12), flush=True)
ti = {(g["date_iso"], g["team_key"], g["opp_key"]): g for g in t if g["type"] in (0, 1, 2) and g["date_iso"] <= day and g["team_key"] in K and g["opp_key"] in K}
ni = {(g["date_iso"], g["team_key"], g["opp_key"]): g for g in n if g["team_key"] in K and g["opp_key"] in K}
both = set(ti) & set(ni)
print("Torvik D-I team-games", len(ti), "NCAA", len(ni), "both", len(both), "missing from NCAA", len(set(ti) - set(ni)), flush=True)
print("score agrees", sum(ti[k]["pf"] == ni[k]["pf"] and ti[k]["pa"] == ni[k]["pa"] for k in both))
c = collections.Counter((ti[k]["loc"], ni[k]["loc"]) for k in both); print("location Torvik->NCAA", dict(c))
print("Example missing", sorted(set(ti) - set(ni))[:5])
for g in n:
    g["type"] = g["type"]
M0 = metrics.compute(n, nr, day); T0 = {r["key"]: r for r in F}
top = [r["key"] for r in F if r["net"] <= 90]
for f in ("wab", "sor", "rating"): print(f, "spearman vs Torvik-based, NET<=90", round(spearmanr([M0[k][f] for k in top], [T0[k][f] for k in top])[0], 3))
print("Q1A exact", sum(M0[k]["q1a_w"] == T0[k]["q1a_w"] and M0[k]["q1a_l"] == T0[k]["q1a_l"] for k in top), "/", len(top), "Q1 exact", sum(M0[k]["cq1_w"] == T0[k]["cq1_w"] and M0[k]["cq1_l"] == T0[k]["cq1_l"] for k in top))
rows = [dict(r, **M0[r["key"]]) for r in F]; model.prepare(rows)
m = model.Model().fit(project.training_rows(exclude={Y})); m.score(rows)
f, _ = model.choose_field(rows, Y, project_autos=False); o = model.assign_lines(f, Y)
truth = {r["key"]: r["seed"] for r in rows if r["in_field"]}
print(Y, "score with NCAA game data", bm.score({r["key"]: r["line"] for r in o}, truth), "(Torvik-based 2026 was 356)", flush=True)
