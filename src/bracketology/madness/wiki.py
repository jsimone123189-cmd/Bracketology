from __future__ import annotations
"""NCAA men's tournament brackets from Wikipedia (CC BY-SA 4.0; attribute Wikipedia when shown).

One raw-wikitext request per season (action=raw, not the rate-limited API), cached by http.fetch.
The bracket templates ({{2TeamBracket}}, {{16TeamBracket}}, {{4TeamBracket}}) hold every seed,
team and score, so they give both the field and every game's result.
"""
import re
from urllib.parse import quote
from ..http import fetch

SEASONS = [y for y in range(2008, 2027) if y != 2020]   # no tournament in 2020
STANDARD_ORDER = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]   # seeds top to bottom in a region


def url(season: int) -> str:
    title = f"{season}_NCAA_Division_I_men's_basketball_tournament"
    return f"https://en.wikipedia.org/w/index.php?title={quote(title)}&action=raw"


def _close(text: str, start: int) -> int:
    """Index just past the '}}' closing the template that opens at text[start:start+2]."""
    depth, i = 0, start
    while i < len(text) - 1:
        two = text[i:i + 2]
        if two == "{{":
            depth += 1; i += 2; continue
        if two == "}}":
            depth -= 1; i += 2
            if depth == 0:
                return i
            continue
        i += 1
    return len(text)


def _split(body: str) -> list[str]:
    """Split template parameters on '|' outside [[links]] and nested {{templates}}."""
    parts, cur, sq, cu, i = [], [], 0, 0, 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("[[", "]]", "{{", "}}"):
            sq += {"[[": 1, "]]": -1}.get(two, 0); cu += {"{{": 1, "}}": -1}.get(two, 0)
            cur.append(two); i += 2; continue
        if body[i] == "|" and sq == 0 and cu == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(body[i])
        i += 1
    parts.append("".join(cur))
    return parts


WRAPPERS = r"nowrap|strikethrough|strike|s|small|nobold|bold|abbr|nbsp"


def _plain(v: str) -> str:
    v = re.sub(r"<ref[^>]*/>|<ref.*?</ref>|<sup.*?</sup>|<!--.*?-->", "", v, flags=re.S)
    for _ in range(3):
        # [[target|shown]] -> shown, then unwrap formatting templates such as {{nowrap|...}} and
        # {{strikethrough|Memphis}} (a vacated result: the game still counts). Alternate, since each can hold the other.
        v = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]", r"\1", v)
        v = re.sub(r"\{\{\s*(?:" + WRAPPERS + r")\s*\|([^{}|]*)(?:\|[^{}]*)?\}\}", r"\1", v, flags=re.I)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"<[^>]+>", "", v).replace("'''", "").replace("''", "").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", v).strip()


def _score(v: str):
    m = re.search(r"\d+", _plain(v))
    return int(m.group()) if m else None


def templates(text: str):
    """(name, params, heading) for each bracket template, in page order."""
    for m in re.finditer(r"\{\{\s*(\d+TeamBracket[^|}\n]*)", text):
        end = _close(text, m.start())
        parts = _split(text[m.start() + 2:end - 2])
        params = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k.strip()] = v.strip()
        heads = re.findall(r"^=+\s*(.*?)\s*=+\s*(?:<!--.*?-->)?\s*$", text[:m.start()], flags=re.M)
        heads = [_plain(h) for h in heads if "all-tournament" not in h.lower()]
        yield parts[0].strip(), params, (heads[-1] if heads else "")


def _games_of(params: dict, rounds: int) -> list[list[dict]]:
    """Per round, the list of games [{seed, team, score} x2] in bracket order."""
    out = []
    for r in range(1, rounds + 1):
        slots, k = [], 1
        while f"RD{r}-team{k}" in params or f"RD{r}-team{k:02d}" in params:
            def g(field):
                return params.get(f"RD{r}-{field}{k}", params.get(f"RD{r}-{field}{k:02d}", ""))
            seed = re.search(r"\d+", _plain(g("seed")))
            slots.append({"seed": int(seed.group()) if seed else None, "team": _plain(g("team")),
                          "score": _score(g("score"))})
            k += 1
        out.append([slots[i:i + 2] for i in range(0, len(slots) - 1, 2)])
    return out


def _game(round_no: int, region: str, pair: list[dict]) -> dict | None:
    a, b = pair
    if not a["team"] or not b["team"] or a["score"] is None or b["score"] is None or a["score"] == b["score"]:
        return None
    w, l = (a, b) if a["score"] > b["score"] else (b, a)
    return {"round": round_no, "region": region, "w": w["team"], "ws": w["seed"], "wpts": w["score"],
            "l": l["team"], "ls": l["seed"], "lpts": l["score"],
            "top": a["team"], "bottom": b["team"]}


def parse(text: str) -> dict:
    """{'games': [...], 'regions': {region: [16 team names in bracket order]}, 'final_four': [regions in FF order]}.

    round 0 = First Four / opening round, 1-4 = regional rounds, 5 = national semifinal, 6 = final.
    """
    games, regions, ff_teams = [], {}, None
    for name, params, head in templates(text):
        n = int(re.match(r"\d+", name).group())
        if n == 2:
            for pair in _games_of(params, 1)[0]:
                g = _game(0, head, pair)
                if g: games.append(g)
        elif n == 16:
            region = re.sub(r"\s*(Regional|region).*$", "", head, flags=re.I).strip(" –-")
            rounds = _games_of(params, 4)
            regions[region] = [t["team"] for pair in rounds[0] for t in pair]
            regions[region + "#seeds"] = [t["seed"] for pair in rounds[0] for t in pair]
            for r, pairs in enumerate(rounds, start=1):
                for pair in pairs:
                    g = _game(r, region, pair)
                    if g: games.append(g)
        elif n == 4 and ff_teams is None:
            rounds = _games_of(params, 2)
            if not rounds[0] or not all(t["team"] for pair in rounds[0] for t in pair):
                continue          # an empty placeholder bracket
            ff_teams = [t["team"] for pair in rounds[0] for t in pair]
            for r, pairs in enumerate(rounds, start=5):
                for pair in pairs:
                    g = _game(r, "Final Four", pair)
                    if g: games.append(g)
    # Some seasons (2008, 2010) leave first-round seeds implied by bracket position.
    for k in [k for k in regions if k.endswith("#seeds")]:
        regions[k] = [s if s is not None else STANDARD_ORDER[i] for i, s in enumerate(regions[k])]
    seed_of = {t: s for r in regions if not r.endswith("#seeds") for t, s in zip(regions[r], regions[r + "#seeds"])}
    for g in games:
        g["ws"] = g["ws"] if g["ws"] is not None else seed_of.get(g["w"])
        g["ls"] = g["ls"] if g["ls"] is not None else seed_of.get(g["l"])
    seeds = {k: v for k, v in regions.items() if k.endswith("#seeds")}
    regions = {k: v for k, v in regions.items() if not k.endswith("#seeds")}
    # Which region each Final Four slot came from: the region whose round-4 winner is that team.
    champs = {g["w"]: g["region"] for g in games if g["round"] == 4}
    ff_order = [champs.get(t) for t in (ff_teams or [])]
    return {"games": games, "regions": regions, "region_seeds": {k[:-6]: v for k, v in seeds.items()},
            "final_four": ff_order}


def season(year: int) -> dict:
    out = parse(fetch(url(year), ttl=86400 * 365))
    out["season"] = year
    out["source"] = url(year)
    return out
