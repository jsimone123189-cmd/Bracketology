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
    assert ff.slot_lines(2027).count(11) == 8 and len(ff.slot_lines(2027)) == 76

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
