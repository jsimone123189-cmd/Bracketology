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
