import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "v1"))
from bracketology.quads import quadrant, records
from bracketology.teams import key
from reproduce_v1 import v1_scores

def test_quadrant_boundaries():
    assert quadrant(15, "H") == "1A" and quadrant(16, "H") == "1B" and quadrant(30, "H") == "1B" and quadrant(31, "H") == "2"
    assert quadrant(75, "A") == "1B" and quadrant(76, "A") == "2" and quadrant(240, "A") == "3" and quadrant(241, "A") == "4"
    assert quadrant(25, "N") == "1A" and quadrant(200, "N") == "3" and quadrant(201, "N") == "4"

def test_team_keys_cross_source():
    assert key("Illinois") == key("Illinois") and key("Eastern Ill.") == key("Eastern Illinois")
    assert key("Mississippi") == key("Ole Miss") and key("UNI") == key("Northern Iowa")
    assert key("Michigan St.") == key("Michigan State") and key("Merrimack 153") == key("Merrimack")

def test_records_ignores_non_d1_and_asof():
    g = [dict(team_key="a", opp_key="b", loc="H", win=True, date_iso="2026-01-01"),
         dict(team_key="a", opp_key="zz", loc="H", win=True, date_iso="2026-01-02"),
         dict(team_key="a", opp_key="b", loc="H", win=False, date_iso="2026-03-01")]
    assert records(g, {"b": 10}, asof="2026-02-01") == {"a": {"q1A_w": 1}}

def test_v1_blank_columns_add_constant():
    base = dict(B=1, C=1, D=1, E=0, F=0, G=0, H=10, I=10, J=10, K=10)
    other = dict(base, H=50)
    (o1, p1), (o2, p2) = v1_scores(base), v1_scores(other)
    assert abs((p1 - o1) - (p2 - o2)) < 1e-12 and abs((p1 - o1) - 8.0806) < 1e-3

def test_bracketmatrix_score_rubric():
    from bracketology.sources.bracketmatrix import score
    off = {"A": 1, "B": 2, "C": 3}
    s = score({"A": 1, "B": 3, "C": 9, "D": 5}, off)   # D not in field
    assert s == {"picked": 3, "exact": 1, "within1": 2, "score": 3 * 3 + 3 * 1 + 1}

def test_picker_respects_capacity_and_reproduces_rank_slotting():
    import numpy as np
    from bracketology import picker
    mu = np.array(picker.SLOT_LINE, float)           # rank-consistent predictions
    lines = picker.assign(mu, 0.8)
    assert [int((lines == l).sum()) for l in range(1, 17)] == picker.CAP
    assert list(lines) == picker.SLOT_LINE           # symmetric uncertainty + fixed capacities => rank order is optimal

def test_formats():
    from bracketology import fieldformat as ff
    assert ff.field_size(2026) == 68 and ff.field_size(2027) == 76 and ff.max_score(2027) == 456
    assert len(ff.slot_lines(2027)) == 76 and ff.line_sizes(2027) == [4] * 10 + [6, 8, 4, 4, 6, 8]
    f = ff.format_for(2027)
    assert f.automatic == 32 and f.at_large == 44 and sum(f.opening_at_large.values()) == sum(f.opening_automatic.values()) == 6
    assert ff.line_sizes(2026) == [4] * 10 + [6] + [4] * 4 + [6]

def test_format_rejects_inconsistent_layouts():
    import pytest
    from bracketology.fieldformat import Format
    with pytest.raises(ValueError): Format(tuple([4] * 10 + [6, 8, 4, 4, 6, 8]), 32, 40, {11: 2, 12: 4}, {15: 2, 16: 4})    # bids don't add up
    with pytest.raises(ValueError): Format(tuple([4] * 9 + [6, 8, 4, 4, 4, 6, 8]), 32, 44, {11: 2, 12: 4}, {15: 2, 16: 4})  # games on the wrong lines

def _stub_feed(monkeypatch, days=None, venues=None):
    """days: iso date -> game list, or an exception to raise. venues: game id -> arena, or an exception."""
    import json as _json
    from bracketology.sources import ncaa_games
    calls = []
    def fake(url, **kw):
        calls.append(url)
        if "/game/" in url:
            v = (venues or {}).get(url.rsplit("/", 1)[1], "Arena")
            if isinstance(v, Exception): raise v
            return _json.dumps({"contests": [{"location": {"venue": v}}]})
        y, m, d = url.split("/")[-4:-1]; v = (days or {}).get(f"{y}-{m}-{d}", [])
        if isinstance(v, Exception): raise v
        return _json.dumps({"games": v})
    monkeypatch.setattr(ncaa_games, "fetch", fake)
    return calls

def _game(i, home="A", away="B"):
    t = lambda n, s: {"score": s, "names": {"short": n}, "conferences": [{"conferenceSeo": "c"}]}
    return {"game": {"gameState": "final", "gameID": i, "home": t(home, 70), "away": t(away, 60)}}

def test_failed_date_is_retried_after_the_refetch_window(monkeypatch, tmp_path):
    from datetime import date
    from bracketology.sources import ncaa_games as ng
    run = lambda today, warn: ng.season_games(2027, today, {"a", "b"}, str.lower, cache_dir=str(tmp_path), warn=warn)
    _stub_feed(monkeypatch, {"2026-11-03": RuntimeError("down")})
    warn = []; run(date(2026, 11, 4), warn)
    assert "2026-11-03" in warn[0] and "1 dates" in warn[0]
    _stub_feed(monkeypatch, {"2026-11-03": [_game("g1")]})      # back up, ten days later and well past the two-day window
    warn = []; rows = run(date(2026, 11, 14), warn)
    assert warn == [] and {r["id"] for r in rows} == {"g1"}

def test_a_quiet_date_is_not_a_failure(monkeypatch, tmp_path):
    from datetime import date
    from bracketology.sources import ncaa_games as ng
    calls = _stub_feed(monkeypatch)
    warn = []; ng.season_games(2027, date(2026, 11, 3), {"a"}, str.lower, cache_dir=str(tmp_path), warn=warn)
    assert warn == [] and len(calls) == 3

def test_failed_arena_lookup_is_retried_but_a_blank_arena_is_not(monkeypatch, tmp_path):
    from datetime import date
    from bracketology.sources import ncaa_games as ng
    day = {"2026-11-01": [_game("g1"), _game("g2", "C", "D")]}
    run = lambda warn: ng.season_games(2027, date(2026, 11, 1), set("abcd"), str.lower, cache_dir=str(tmp_path), warn=warn)
    _stub_feed(monkeypatch, day, {"g1": RuntimeError("down"), "g2": None})
    warn = []; run(warn)
    assert "1 games" in warn[0]
    calls = _stub_feed(monkeypatch, day, {"g1": "Barn"})
    warn = []; run(warn)
    assert warn == [] and [c for c in calls if "/game/" in c] == ["https://ncaa-api.henrygd.me/game/g1"]

def test_old_cache_with_lost_arenas_gets_refetched(monkeypatch, tmp_path):
    import json as _json
    from datetime import date
    from bracketology.sources import ncaa_games as ng
    (tmp_path / "2027.json").write_text(_json.dumps({"rows": [], "venues": {"g1": None}, "through": "2026-11-05"}))
    calls = _stub_feed(monkeypatch, {"2026-11-01": [_game("g1")]}, {"g1": "Barn"})
    rows = ng.season_games(2027, date(2026, 11, 6), {"a", "b"}, str.lower, cache_dir=str(tmp_path))
    assert {r["id"] for r in rows} == {"g1"} and "https://ncaa-api.henrygd.me/game/g1" in calls
    assert _json.loads((tmp_path / "2027.json").read_text())["venues"] == {"g1": "Barn"}

def test_outage_stops_early_and_keeps_everything_for_retry(monkeypatch, tmp_path):
    from datetime import date
    from bracketology.sources import ncaa_games as ng
    down = {f"2026-11-{d:02d}": RuntimeError("down") for d in range(1, 21)}
    calls = _stub_feed(monkeypatch, down)
    warn = []; ng.season_games(2027, date(2026, 11, 20), {"a"}, str.lower, cache_dir=str(tmp_path), warn=warn)
    assert len(calls) == ng.MAX_STRAIGHT_FAILURES and "20 dates" in warn[0]

def test_grade_scores_the_untouched_model_when_a_team_is_removed():
    from bracketology import model, project
    rows = [dict(team=f"T{i}", key=f"t{i}", lg=f"L{i}" if i < 32 else "big", champ=i < 32, p_in=1 - i / 200, rank_score=-i, is_power=0.0) for i in range(100)]
    field, rest = model.choose_field(rows, 2026, project_autos=False); order = model.assign_lines(field, 2026)
    untouched = project.model_bracket(order)
    t0_line = next(r["line"] for r in untouched if r["team"] == "T0")
    final, _ = project.apply_overrides(order, rest, {"T0": {"out": True, "reason": "x"}}, 2026)
    g = project.grade({"teams": final, "model_bracket": untouched}, {"T0": t0_line})
    assert g["model"]["picked"] == 1 and g["model"]["exact"] == 1 and g["final"]["picked"] == 0

def test_snapshot_records_version_and_time():
    import time
    from bracketology import sitebuild
    data = {"season": 2027, "teams": [], "accuracy": {"big": 1}, "archive": {"model_bracket": [], "ranked": [], "overrides": {}, "sources": {}}}
    s = sitebuild.snapshot(data, time.gmtime(0))
    assert s["snapshot_id"] == "2027-19700101T000000Z" and s["generated_at"] == "1970-01-01T00:00:00Z"
    assert s["model"]["version"] == "v2.0" and s["model"]["weights_match"] is True
    assert "accuracy" not in s and "archive" not in s and "ranked" in s

def test_saved_model_matches_frozen_version():
    import hashlib
    from bracketology import model
    assert hashlib.sha256(open("models/v2.joblib", "rb").read()).hexdigest() == model.MODEL_SHA256

def test_net_feed_staleness():
    from bracketology.project import net_is_current
    assert not net_is_current("Through Games Apr. 06 2026", 2027) and net_is_current("Through Games Dec. 01 2026", 2027) and not net_is_current(None, 2027)

def test_champion_not_named_mid_tournament():
    from bracketology.dataset import completed_champions
    g = lambda d, t, w: dict(type=2, date=d, team=t, conf="X", win=w)
    semis = [g("3/9/26", "A", True), g("3/9/26", "B", False), g("3/9/26", "C", True), g("3/9/26", "D", False)]
    assert completed_champions(semis, "2026-03-09") == {}
    assert completed_champions(semis + [g("3/10/26", "A", True), g("3/10/26", "C", False)], "2026-03-10") == {"X": "A"}

def test_projected_auto_and_overrides():
    from bracketology import model, project
    rows = [dict(team=f"T{i}", key=f"t{i}", lg="L1" if i < 60 else f"L{i}", champ=False, p_in=1 - i / 200, rank_score=-i, is_power=0.0) for i in range(100)]
    field, rest = model.choose_field(rows, 2026)
    assert len(field) == 68 and sum(1 for r in field if r.get("projected_auto")) == 41
    order = model.assign_lines(field, 2026)
    final, notes = project.apply_overrides(order, rest, {"T0": {"line": 3, "reason": "x"}, "T1": {"out": True}, rest[0]["team"]: {"line": 11}}, 2026)
    by = {r["team"]: r for r in final}
    assert by["T0"]["line"] == 3 and by["T0"]["model_line"] == 1 and "T1" not in by and rest[0]["team"] in by and len(final) == 68

def test_regions_handle_both_formats():
    from bracketology import fieldformat as ff, sitebuild
    for season in (2026, 2027):
        lines = ff.slot_lines(season)
        order = [dict(team=f"T{i}", key=f"t{i}", lg=f"L{i % 7}", overall=i + 1, line=l) for i, l in enumerate(lines)]
        sitebuild.assign_regions(order)
        assert all(r["region"] in (0, 1, 2, 3) for r in order)
        for line, n in enumerate(ff.line_sizes(season), 1):
            rs = [r for r in order if r["line"] == line]
            assert sum(r.get("play_in", False) for r in rs) == 2 * (n - 4)
            for g in range(4):      # every region has a team (or play-in pair) on every line
                c = [r for r in rs if r["region"] == g]
                assert len(c) == (2 if any(r.get("play_in") for r in c) else 1)


def test_neutral_sites_from_arena():
    from bracketology.sources.ncaa_games import mark_neutral
    r = lambda i, t, o, l: dict(id=i, team=t, opp=o, loc=l)
    rows = []
    for i in "abc": rows += [r(i, "Home U", "X" + i, "H"), r(i, "X" + i, "Home U", "A")]
    rows += [r("n", "Home U", "Other", "H"), r("n", "Other", "Home U", "A"), r("u", "Home U", "Y", "H")]
    v = dict(a="Barn", b="Barn", c="Barn", n="Vegas Arena", u=None)
    out = {(g["id"], g["team"]): g["loc"] for g in mark_neutral(rows, v)}
    assert out[("a", "Home U")] == "H" and out[("n", "Home U")] == "N" and out[("n", "Other")] == "N" and out[("u", "Home U")] == "H"

def test_autobid_parsing_skips_undecided():
    from bracketology.sources.warrennolan import parse_autobids
    t = "<table><tr><th>Conference</th><th>Automatic Bid</th></tr><tr><td>ACC</td><td><a>Duke</a></td></tr><tr><td>SEC</td><td></td></tr></table>"
    assert parse_autobids(t) == {"ACC": "Duke"}
