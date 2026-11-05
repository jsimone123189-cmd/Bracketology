from __future__ import annotations
"""One daily run: collect -> normalize -> validate -> snapshot. Never raises on a single failed source."""
import sys, time
from . import store, validate, quads
from .teams import TeamIndex, key
from .sources import ncaa_net, torvik

def season_for(today=None) -> int:
    t = today or time.gmtime()
    return t.tm_year + (1 if t.tm_mon >= 8 else 0)

def run(season: int | None = None, db="data/bracketology.sqlite") -> list[str]:
    season = season or season_for()
    net, tt, gg = ncaa_net.collect(), torvik.collect_teams(season), torvik.collect_games(season)
    idx = TeamIndex([r["team"] for r in net["rows"]])        # NET list = canonical D-I universe
    for payload in (net, tt):
        for r in payload["rows"]: r["team_key"] = key(r["team"])
    unmatched = {"torvik_teams": idx.unmatched(r["team"] for r in tt["rows"]),
                 "torvik_games_team": idx.unmatched({r["team"] for r in gg["rows"]})}
    for r in gg["rows"]:
        r["team_key"], r["opp_key"] = key(r["team"]), key(r["opp"])
        m, d, y = r["date"].split("/"); r["date_iso"] = f"20{y}-{int(m):02d}-{int(d):02d}"
    problems = validate.check(net, tt, gg, unmatched)
    # Cross-check: our computed Q1-Q4 vs NCAA's published combined quads
    net_by = {r["team_key"]: r["net"] for r in net["rows"]}
    mine = quads.records(gg["rows"], net_by)
    bad = 0
    for r in net["rows"]:
        m = mine.get(r["team_key"], {})
        for q, k in (("1", ("1A", "1B")), ("2", ("2",)), ("3", ("3",)), ("4", ("4",))):
            w = sum(m.get(f"q{x}_w", 0) for x in k); l = sum(m.get(f"q{x}_l", 0) for x in k)
            if (w, l) != (r[f"q{q}_w"], r[f"q{q}_l"]): bad += 1; break
    if bad: problems.append(f"computed quad records differ from NCAA for {bad}/{len(net['rows'])} teams")
    c = store.connect(db)
    for payload in (net, tt):
        store.save(c, payload, season, ok=not problems, notes="; ".join(problems))
    store.save(c, {**gg, "rows": gg["rows"]}, season, ok=not problems, notes="; ".join(problems))
    return problems

if __name__ == "__main__":
    probs = run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
    print("OK" if not probs else "\n".join(probs)); sys.exit(0 if not probs else 1)
