from __future__ import annotations
"""Builds the static site: site/template.html + data -> data/output/site/{preview.html (private Artifact), index.html (Cloudflare Pages)}.
Run: python -m bracketology.sitebuild demo-2026   (held-out 2026 preview). Live seasons get the same data shape from project.py."""
import itertools, json, os, statistics, sys, time
from . import fieldformat, model, project
from .features import build_year
from .sources import bracketmatrix as bm

ORDER = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

def assign_regions(order: list[dict]) -> None:
    """Illustrative placement: keep the four regions balanced along the seed list and split conference mates where possible.
    Bracket Matrix scores seed lines only, so this does not affect the score."""
    totals, leagues = [0, 0, 0, 0], [set(), set(), set(), set()]
    lines = {}
    for r in order: lines.setdefault(r["line"], []).append(r)
    for line in sorted(lines):
        rs = lines[line]; games = max(0, len(rs) - 4)        # lines with extra teams hold opening-round games
        singles, low = rs[:4 - games], rs[4 - games:]        # the lowest teams on the line play their seed-list neighbour
        units = [[r] for r in singles] + [low[i:i + 2] for i in range(0, len(low), 2)]
        best, best_cost = None, None
        for perm in itertools.permutations(range(4)):
            cost, t = 0, list(totals)
            for u, g in zip(units, perm):
                t[g] += u[0]["overall"]
                if any(r.get("lg") in leagues[g] for r in u): cost += 1000 if line <= 4 else 100
            cost += max(t) - min(t)
            if best_cost is None or cost < best_cost: best, best_cost = perm, cost
        for u, g in zip(units, best):
            totals[g] += u[0]["overall"]
            for r in u:
                r["region"], r["play_in"] = g, len(u) > 1; leagues[g].add(r.get("lg"))

def seed_probs(line: int, table: dict, season: int) -> list[dict]:
    last = 16; d = table[str((line - 1) // 4)]; out = {}
    for k, p in d.items():
        l = min(last, max(1, line + int(k))); out[l] = out.get(l, 0) + p
    t = sum(out.values())
    return [{"line": l, "p": round(p / t, 3)} for l, p in sorted(out.items())]

def team_record(r: dict, table: dict, season: int) -> dict:
    d = {k: r.get(k) for k in ("key", "team", "lg", "w", "l", "net", "line", "model_line", "override_reason", "overall", "region", "play_in", "champ", "projected_auto", "seed", "in_field",
                               "q1a_w", "q1a_l", "cq1_w", "cq1_l", "cq2_w", "cq2_l", "cq3_l", "cq4_l", "road_w", "neutral_w", "rating_rank")}
    d.update(p_in=round(r["p_in"], 3), wab=round(r["wab"], 1), sor=round(r["sor"], 2), sos=round(r["sos"], 1), last10=round(r["last10"] * 10))
    if r.get("line"): d["probs"] = seed_probs(r["line"], table, season)
    return d

def benchmarks(acc: dict) -> dict:
    out = {"t_rank": [], "median": [], "best": []}
    for y in acc["seasons"]:
        s = bm.collect(y)["reported"]["SCORE"]; v = [int(x) for x in s.values() if x.isdigit()]
        out["t_rank"].append(int(s["T-Rank"])); out["median"].append(int(statistics.median(v))); out["best"].append(max(v))
    return out

def demo(season: int = 2026) -> dict:
    acc = json.load(open("site/accuracy.json")); table = acc["seed_error"]
    m = model.Model().fit(project.training_rows(exclude={season})); rows = model.prepare(build_year(season)); m.score(rows)
    field, rest = model.choose_field(rows, season, project_autos=False); order = model.assign_lines(field, season); assign_regions(order)
    truth = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    score = bm.score({r["key"]: r["line"] for r in order}, truth)
    atl = sorted((r for r in order if not r["champ"]), key=lambda r: r["p_in"])
    officially_in = {r["key"] for r in rows if r["in_field"]}
    return {"mode": "demo", "season": season, "generated": time.strftime("%B %-d, %Y"), "max": fieldformat.max_score(season), "score": score,
            "lines": fieldformat.line_sizes(season), "order": ORDER, "teams": [team_record(r, table, season) for r in order], "out": [team_record(r, table, season) for r in rest[:12]],
            "bubble": {"byes": [r["key"] for r in atl[4:8]], "last_in": [r["key"] for r in atl[:4]], "first_out": [r["key"] for r in rest[:4]], "next_out": [r["key"] for r in rest[4:8]]},
            "missed": [{"team": r["team"], "seed": r["seed"], "net": r["net"], "key": r["key"]} for r in rows if r["in_field"] and r["key"] not in {x["key"] for x in order}],
            "accuracy": {**acc, **benchmarks(acc)}}

MIN_MEDIAN_GAMES = 15

def live(season: int, fitted: model.Model) -> dict:
    """Live season: model bracket, then the owner's overrides. Public JSON carries no third-party metric values (r_* columns)."""
    acc = json.load(open("site/accuracy.json")); table = acc["seed_error"]
    rows, warn = project.live_rows(season); model.prepare(rows); fitted.score(rows)
    field, rest = model.choose_field(rows, season); order = model.assign_lines(field, season)
    path = f"overrides/{season}.json"; overrides = json.load(open(path)) if os.path.exists(path) else {}
    final, notes = project.apply_overrides(order, rest, overrides, season)
    final.sort(key=lambda r: (r["line"], r["overall"] if r.get("overall") else 99))
    for i, r in enumerate(final): r["overall"] = i + 1
    assign_regions(final)
    ids = {r["key"] for r in final}; rest = [r for r in rest if r["key"] not in ids]
    atl = sorted((r for r in final if not r["champ"] and not r.get("projected_auto")), key=lambda r: r["p_in"])
    return {"mode": "live", "season": season, "generated": time.strftime("%B %-d, %Y"), "max": fieldformat.max_score(season), "lines": fieldformat.line_sizes(season), "order": ORDER,
            "median_games": statistics.median(r["w"] + r["l"] for r in rows), "warnings": warn + notes,
            "teams": [team_record(r, table, season) for r in final], "out": [team_record(r, table, season) for r in rest[:12]],
            "bubble": {"byes": [r["key"] for r in atl[4:8]], "last_in": [r["key"] for r in atl[:4]], "first_out": [r["key"] for r in rest[:4]], "next_out": [r["key"] for r in rest[4:8]]},
            "missed": [], "accuracy": {**acc, **benchmarks(acc)}}

def load_or_fit(path="models/v2.joblib", season: int = 2027) -> model.Model:
    """CI uses the saved model because training data stays out of the public repo. Refit locally with: python -m bracketology.sitebuild fit"""
    import joblib
    return joblib.load(path) if os.path.exists(path) else model.Model().fit(project.training_rows(exclude={season}))

def render(data: dict, out="data/output/site") -> str:
    t = open("site/template.html", encoding="utf-8").read()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = t.replace("/*DATA*/null", payload)
    os.makedirs(out, exist_ok=True)
    open(f"{out}/preview.html", "w", encoding="utf-8").write(page)
    open(f"{out}/index.html", "w", encoding="utf-8").write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' + page + "</body></html>")
    return f"{out}/preview.html"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "fit":
        import joblib
        os.makedirs("models", exist_ok=True); joblib.dump(model.Model().fit(project.training_rows()), "models/v2.joblib"); print("saved models/v2.joblib")
    elif cmd == "demo":
        print(render(demo()))
    else:      # live: refuses to build a public page on too few games unless --force
        season = int(cmd); data = live(season, load_or_fit(season=season)); print("\n".join(data["warnings"]))
        os.makedirs("data/output/snapshots", exist_ok=True)     # dated history; CI commits these to the snapshots branch, even before the page goes public
        json.dump(data, open(f"data/output/snapshots/{season}_{time.strftime('%Y-%m-%d', time.gmtime())}.json", "w"), separators=(",", ":"))
        if data["median_games"] < MIN_MEDIAN_GAMES and "--force" not in sys.argv:
            print(f"Not publishing: median {data['median_games']} games played, need {MIN_MEDIAN_GAMES}."); sys.exit(3)
        print(render(data))
