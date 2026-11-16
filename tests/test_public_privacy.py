"""The public page and snapshots show only the published bracket (docs/44): nothing that reveals the model's own line, its odds,
the owner's reasons or confidence, or the model bracket next to the published one."""
import json, time
from bracketology import sitebuild, fieldformat

TABLE = json.load(open("site/accuracy.json"))["seed_error"]

def row(k, line, i):
    return {"key": k, "team": k.upper(), "lg": "x", "w": 1, "l": 0, "net": i + 1, "line": line, "model_line": line, "override_reason": "secret why", "overall": i + 1,
            "champ": False, "projected_auto": False, "p_in": .5, "wab": 0, "sor": 0, "sos": 0, "last10": .5, "rank_score": -i, "seed": 3, "in_field": True}

def field(season=2027):
    slots = fieldformat.format_for(season).slots
    return [row(f"t{i}", slots[i], i) for i in range(len(slots))], [row(f"x{i}", None, 100 + i) for i in range(10)]

def test_public_team_record_drops_private_fields():
    order, _ = field(); d = sitebuild.team_record(order[0], TABLE, 2027, public=True)
    assert not set(d) & {"model_line", "override_reason", "p_in", "seed", "in_field"} and d["line"] == 1

def test_published_lines_rebuild_the_field_exactly_and_bad_ones_are_refused():
    order, rest = field(); slots = fieldformat.format_for(2027).slots
    keys = [r["key"] for r in order]; keys.remove("t25"); keys.insert(5, "t25"); keys.remove("t70"); keys.append("x0")     # a move and an add
    pub = {"teams": [{"key": k, "line": slots[i]} for i, k in enumerate(keys)]}
    final, bad = sitebuild.apply_published(order, rest, pub, 2027)
    assert not bad and {r["key"]: r["line"] for r in final} == {k: slots[i] for i, k in enumerate(keys)}
    assert sitebuild.apply_published(order, rest, {"teams": pub["teams"][:-1]}, 2027)[1]                              # wrong size
    assert sitebuild.apply_published(order, rest, {"teams": pub["teams"][:-1] + [{"key": "nobody", "line": 16}]}, 2027)[1]
    assert sitebuild.apply_published(order, rest, {"teams": pub["teams"][:-1] + [pub["teams"][0]]}, 2027)[1]         # duplicate

def test_snapshot_carries_no_model_bracket_ledger_or_odds():
    order, _ = field()
    data = {"mode": "live", "season": 2027, "teams": [sitebuild.team_record(r, TABLE, 2027, public=True) for r in order], "accuracy": {},
            "archive": {"sources": {"net_source": "ncaa"}, "published": {"source": "final_freeze", "sha256": "ab"}}}
    s = json.dumps(sitebuild.snapshot(data, time.gmtime()))
    for w in ("model_bracket", "ledger", "overrides", "ranked", "\"review\"", "p_in", "model_line", "override_reason", "secret why"): assert w not in s, w

def test_template_never_shows_edits_or_model_odds_for_a_live_season():
    t = open("site/template.html", encoding="utf-8").read()
    for w in ("override_reason", "model_line", "Edited", "Manual edit", "manual edits, marked"): assert w not in t, w
    assert t.count("pct(t.p_in)") == t.count("demo?pct(t.p_in)") + t.count("demo||t.champ?`<div><b>${t.champ?\"Auto\":pct(t.p_in)}")   # odds only in the historical demo

def test_incomplete_final_is_labelled_never_silent():
    st = sitebuild.public_status({"source": "final_freeze", "complete": False, "pending": ["Purdue vs Michigan"], "frozen_at": "2027-03-14T21:36:00Z"}, "final_freeze")
    assert st == {"final": True, "complete": False, "pending": ["Purdue vs Michigan"], "frozen_at": "2027-03-14T21:36:00Z"}
    assert sitebuild.public_status({"source": "published"}, "published") == {"final": False}
    t = open("site/template.html", encoding="utf-8").read()
    assert "frozen before every conference final ended" in t and "Those automatic bids are projected" in t
