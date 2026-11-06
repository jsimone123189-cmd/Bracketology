from __future__ import annotations
"""Daily data checks. An alert blocks the public page and fails the run, so GitHub emails the owner; the snapshot is still saved. A note is only recorded.
Game-count baseline, 2026 final: our D-I count matched the NCAA NET record for 363 of 365 teams, and our all-games count matched Warren Nolan's record for all teams checked."""
from datetime import date

GAME_TOLERANCE = 2          # a feed may trail by a day or two of games
NET_DUE = (12, 15)          # after this date a missing official NET stops being normal
NET_MAX_AGE_DAYS = 3

def _item(level: str, check: str, message: str) -> dict:
    return {"level": level, "check": check, "message": message}

def _games(record: str) -> int | None:
    try:
        w, l = record.split("-")[:2]; return int(w) + int(l)
    except (AttributeError, ValueError):
        return None

def game_counts(counts: dict[str, int], records: dict[str, str], net: dict[str, int], source: str) -> list[dict]:
    """counts and records must define a game the same way: D-I only for the NET feed, all games for Warren Nolan."""
    off = {}
    for k, rec in records.items():
        n = _games(rec)
        if n is not None and abs(counts.get(k, 0) - n) > GAME_TOLERANCE: off[k] = (counts.get(k, 0), n)
    if not off: return []
    top = sorted(k for k in off if net.get(k, 999) <= 90)
    sample = ", ".join(f"{k} {off[k][0]} vs {off[k][1]}" for k in (top or sorted(off))[:5])
    level = "alert" if top or len(off) > .02 * len(records) else "note"
    return [_item(level, "game_counts", f"{len(off)} teams' game counts differ from {source} by more than {GAME_TOLERANCE}, {len(top)} of them in the NET top 90: {sample}.")]

def source_health(today: date, season: int, net_source: str, net_age_days: int | None, n_teams: int, missing_days: int, arena_unknown: int, arena_total: int) -> list[dict]:
    out = []
    if not 340 <= n_teams <= 400: out.append(_item("alert", "universe", f"Team table has {n_teams} teams, expected about 365."))
    if net_source != "ncaa":
        late = today >= date(season - 1, *NET_DUE)
        out.append(_item("alert" if late else "note", "net_source", "Official NET is not being used; ranks come from Warren Nolan's NET column."))
    elif net_age_days is not None and net_age_days > NET_MAX_AGE_DAYS:
        out.append(_item("alert", "net_age", f"Official NET is {net_age_days} days old."))
    if missing_days: out.append(_item("alert", "missing_days", f"Game results are missing for {missing_days} dates."))
    if arena_unknown:
        share = arena_unknown / max(1, arena_total)
        out.append(_item("alert" if share > .02 else "note", "arenas", f"Arena unknown for {arena_unknown} of {arena_total} games."))
    return out

def team_matching(universe: set[str], net_keys: set[str], games_by_team: dict[str, int], today: date, season: int) -> list[dict]:
    out = []
    if net_keys:
        no_table, no_net = sorted(net_keys - universe), sorted(universe - net_keys)
        if no_table or no_net: out.append(_item("alert", "team_names", f"Team names don't line up. NET only: {no_table[:8]}. Team table only: {no_net[:8]}."))
    if today >= date(season - 1, 11, 25):
        idle = sorted(k for k in universe if not games_by_team.get(k))
        if idle: out.append(_item("alert", "no_games", f"{len(idle)} teams have no games: {idle[:8]}."))
    return out

def champions(ncaa: set[str], listed: set[str], decided: bool) -> list[dict]:
    """Compares champions worked out from NCAA results with the auto-bid list. A staggered tournament can name a champion early, so a conflict only alerts once every league should be done.
    A team only on the list is a note: reclassifying champions and relabelled conferences make NCAA results miss the odd one, about one a season in 2025 and 2026."""
    out = []
    only_ncaa, only_list = sorted(ncaa - listed), sorted(listed - ncaa)
    if only_ncaa: out.append(_item("alert" if decided else "note", "champions", f"NCAA results show these champions, but the auto-bid list doesn't: {only_ncaa}."))
    if only_list: out.append(_item("note", "champions", f"Auto-bid list shows these champions, not confirmed from NCAA results: {only_list}."))
    return out

def autos(found: int, expected: int) -> list[dict]:
    if found == expected: return []
    return [_item("alert", "automatic_bids", f"{found} automatic bids found, format expects {expected}.")]

def field_size(found: int, expected: int) -> list[dict]:
    if found == expected: return []
    return [_item("alert", "field_size", f"Final field has {found} teams, format expects {expected}.")]
