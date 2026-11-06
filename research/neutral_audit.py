"""Neutral-site audit among NET top-90 teams, 2026. Compares locations inferred from NCAA arenas with Torvik's game log.
Reports only: nothing here is tuned, and no committee outcome is used to score the rule."""
import collections
from datetime import date
from bracketology import history
from bracketology.features import build_year
from bracketology.quads import quadrant
from bracketology.sources import ncaa_games, torvik
from bracketology.teams import key
Y = 2026; day = history.SELECTION_SUNDAY[Y]; end = date.fromisoformat(day)
F = build_year(Y); K = {r["key"] for r in F}; net = {r["key"]: r["net"] for r in F}; top = {k for k, n in net.items() if n <= 90}
n = ncaa_games.collect(date(end.year - 1, 11, 1), end)["rows"]; t = torvik.collect_games(Y)["rows"]
ids = sorted({g["id"] for g in n if key(g["team"]) in K and key(g["opp"]) in K})
V = {i: ncaa_games.venue(i) for i in ids}; ncaa_games.mark_neutral(n, V)
print("arena known", sum(bool(v) for v in V.values()), "of", len(V))
def iso(s): m, d, y = s.split("/"); return f"20{y}-{int(m):02d}-{int(d):02d}"
for g in n + t: g["k"] = (iso(g["date"]), key(g["team"]), key(g["opp"]))
ti = {g["k"]: g for g in t if g["type"] in (0, 1, 2) and iso(g["date"]) <= day and key(g["team"]) in top and key(g["opp"]) in K}
ni = {g["k"]: g for g in n if key(g["team"]) in top and key(g["opp"]) in K}
both = set(ti) & set(ni)
print("top-90 team-games, Torvik", len(ti), "NCAA", len(ni), "both", len(both))
c = collections.Counter((ti[k]["loc"], ni[k]["loc"]) for k in both); print("location Torvik -> NCAA", sorted(c.items()))
tn = sum(v for (a, _), v in c.items() if a == "N"); hit = c[("N", "N")]; fp = sum(v for (a, b), v in c.items() if a != "N" and b == "N")
print(f"Torvik neutral games found {hit} of {tn} ({hit / max(1, tn):.1%}); non-neutral games wrongly marked neutral {fp} of {len(both) - tn}")
moved = [k for k in both if ti[k]["loc"] != ni[k]["loc"]]
qm = [k for k in moved if quadrant(net.get(k[2], 365), ti[k]["loc"]) != quadrant(net.get(k[2], 365), ni[k]["loc"])]
per = collections.Counter(k[1] for k in qm); print("location differences that change a game's quadrant", len(qm), "of", len(moved), "; teams affected", len(per), "of 90; most", per.most_common(5))
print("wins among them", sum(ti[k]["win"] for k in qm), "losses", sum(not ti[k]["win"] for k in qm))
print("examples", [(k, ti[k]["loc"], ni[k]["loc"], V.get(ni[k]["id"])) for k in sorted(qm)[:8]])

# Named flaw: conference tournament games can make a tournament arena look like a team's regular home. Same comparison with those games left out of "regular".
blank = [k for k in moved if not V.get(ni[k]["id"])]; print("differences with no arena listed", len(blank), "of", len(moved))
fresh = ncaa_games.collect(date(end.year - 1, 11, 1), end)["rows"]
regular_rows = [g for g in fresh if not g.get("ct")]
use = {}
for g in regular_rows:
    if g["loc"] == "H" and V.get(g["id"]): use.setdefault(g["team"], {}).setdefault(V[g["id"]], set()).add(g["id"])
regular = {}
for x, v in use.items():
    m = max(len(s) for s in v.values()); regular[x] = {a for a, s in v.items() if len(s) >= 3 or len(s) == m}
home = {g["id"]: g["team"] for g in fresh if g["loc"] == "H"}
for g in fresh:
    a = V.get(g["id"])
    if a and a not in regular.get(home[g["id"]], {a}): g["loc"] = "N"
    g["k"] = (iso(g["date"]), key(g["team"]), key(g["opp"]))
n2 = {g["k"]: g for g in fresh if key(g["team"]) in top and key(g["opp"]) in K}; both2 = set(ti) & set(n2)
c2 = collections.Counter((ti[k]["loc"], n2[k]["loc"]) for k in both2); print("without tournament games: location Torvik -> NCAA", sorted(c2.items()))
fp2 = sum(v for (a, b), v in c2.items() if a != "N" and b == "N"); print(f"neutral games found {c2[('N', 'N')]} of {tn}; wrongly marked neutral {fp2}")
print("still different, conference tournament games", sum(n2[k].get("ct", False) and ti[k]["loc"] != n2[k]["loc"] for k in both2))
print("became right", sorted(k for k in both2 if ti[k]["loc"] != ni[k]["loc"] and ti[k]["loc"] == n2[k]["loc"])[:6]); print("became wrong", sorted(k for k in both2 if ti[k]["loc"] == ni[k]["loc"] and ti[k]["loc"] != n2[k]["loc"])[:12])
