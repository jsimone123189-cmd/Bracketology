from __future__ import annotations
"""One table of past NCAA tournament games with each team's seed and pre-tournament rating.

Needs data/madness/bracket_{y}.json (wiki.season) and games_{y}.json (Torvik game log), built by
research/madness_build.py. Every Wikipedia tournament name is matched to a Torvik team or the
build fails loudly.
"""
import json
from ..teams import key as _key
from . import ratings, wiki

WIKI_TO_TORVIK = {
    "Texas–Arlington": "UT Arlington", "Arkansas-Little Rock": "Little Rock", "Loyola (MD)": "Loyola MD",
    "Louisiana–Lafayette": "Louisiana", "Virginia Commonwealth": "VCU", "California-Irvine": "UC Irvine",
    "Texas A&M–Corpus Christi": "Texas A&M Corpus Chris", "SE Missouri State": "Southeast Missouri St.",
}


def key(name: str) -> str:
    return _key(WIKI_TO_TORVIK.get(name, name))


def season_table(year: int, folder: str = "data/madness", **fit_kw) -> dict:
    b = json.load(open(f"{folder}/bracket_{year}.json"))
    rows = json.load(open(f"{folder}/games_{year}.json"))
    field = {key(g[k]) for g in b["games"] for k in ("w", "l")}
    known = {_key(r["team"]) for r in rows}
    missing = sorted(t for t in field if t not in known)
    if missing:
        raise ValueError(f"{year}: tournament teams not in the Torvik log: {missing}")
    ss = ratings.selection_sunday(rows, field, _key)
    rt = ratings.fit(rows, ss, _key, **fit_kw)
    games = []
    for g in b["games"]:
        w, l = key(g["w"]), key(g["l"])
        games.append({**g, "season": year, "wr": rt[w], "lr": rt[l]})
    return {"season": year, "selection_sunday": ss.isoformat(), "ratings": rt, "games": games, "bracket": b}


def all_seasons(**fit_kw) -> list[dict]:
    return [season_table(y, **fit_kw) for y in wiki.SEASONS]
