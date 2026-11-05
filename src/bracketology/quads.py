from __future__ import annotations
"""NCAA quadrant classification (NET-based), including Quad 1A. Computed per game so V2 can use Q1A and as-of-date cutoffs."""
def quadrant(opp_net: int, loc: str) -> str:
    """Returns '1A','1B','2','3','4' (Q1 = 1A+1B)."""
    if loc == "H":   a, q1, q2, q3 = 15, 30, 75, 160
    elif loc == "N": a, q1, q2, q3 = 25, 50, 100, 200
    else:            a, q1, q2, q3 = 40, 75, 135, 240
    if opp_net <= a: return "1A"
    if opp_net <= q1: return "1B"
    if opp_net <= q2: return "2"
    if opp_net <= q3: return "3"
    return "4"

def records(games: list[dict], net_by_team: dict[str, int], asof: str | None = None) -> dict[str, dict]:
    """games: team-game rows with canonical 'team_key','opp_key'. Only games vs. Division I (opp has a NET rank) count."""
    out: dict[str, dict] = {}
    for g in games:
        if asof and g["date_iso"] > asof: continue
        n = net_by_team.get(g["opp_key"])
        if n is None: continue
        q = quadrant(n, g["loc"])
        d = out.setdefault(g["team_key"], {})
        k = f"q{q}_{'w' if g['win'] else 'l'}"
        d[k] = d.get(k, 0) + 1
    return out
