import json, pytest
from datetime import datetime, timezone
from bracketology import review, fieldformat

def setup(n_extra=6, season=2026):
    size = fieldformat.format_for(season).size
    order = [f"t{i}" for i in range(size)]; rest = [f"x{i}" for i in range(n_extra)]
    info = {k: {"team": k.upper(), "champ": i >= size - 8, "projected_auto": False, "rank_score": -i, "p_in": 1 - i / 100} for i, k in enumerate(order)}
    info.update({k: {"team": k.upper(), "champ": False, "projected_auto": False, "rank_score": -size - i, "p_in": .4 - i / 100} for i, k in enumerate(rest)})
    return order, rest, info

def E(i, **k): return {"id": f"e{i}", "at": "2026-03-10T12:00:00Z", "reason_code": "head_to_head", "confidence": 2, **k}

def sizes(order, season=2026):
    L = review.lines_of(order, season); return [sum(1 for v in L.values() if v == l) for l in range(1, 17)]

def test_move_keeps_line_sizes_and_shifts_one_team_per_boundary():
    order, rest, info = setup(); before = review.lines_of(order, 2026)
    new, rec, notes = review.apply_edits(order, rest, [E(1, op="move", team="t30", to_line=6)], 2026, info)
    assert not notes and sizes(new) == fieldformat.line_sizes(2026)
    after = review.lines_of(new, 2026); assert after["t30"] == 6
    moved = {k for k in after if after[k] != before[k] and k != "t30"}
    assert all(after[k] == before[k] + 1 for k in moved) and len(moved) == before["t30"] - 6   # one team pushed down per boundary crossed
    assert rec[0]["line_before"] == 8 and rec[0]["line_after"] == 6 and rec[0]["phase"] in ("championship_week", "pre_championship_week")

def test_add_remove_swap_undo_and_auto_bid_guard():
    order, rest, info = setup()
    new, rec, notes = review.apply_edits(order, rest, [E(1, op="add", team="x2"), E(2, op="swap", team="t0", **{"with": "t5"}), E(3, op="remove", team="t67"),
                                                       E(4, op="move", team="t1", to_line=3), E(5, op="undo")], 2026, info)
    assert "x2" in new and len(new) == len(order) and sizes(new) == fieldformat.line_sizes(2026)
    assert any("not applied" in n for n in notes)                          # t67 is an automatic bid: can't be removed
    assert new.index("t5") == 0
    undo = [E(4, op="move", team="t1", to_line=3), {"id": "e4", "at": "2026-03-10T13:00:00Z", "op": "undo"}]
    new3, rec3, _ = review.apply_edits(order, rest, undo, 2026, info); assert new3 == order and rec3 == []

def test_invalid_edits_are_reported_not_applied():
    order, rest, info = setup()
    new, rec, notes = review.apply_edits(order, rest, [{"id": "a", "at": "x", "op": "move", "team": "t3", "to_line": 2, "reason_code": "other", "confidence": 2}], 2026, info)
    assert new == order and "explanation" in notes[0]

def test_grade_groups_interacting_edits_and_sums_exactly():
    b1 = {"a": 1, "b": 2, "c": 3, "d": 4}; b3 = {"a": 2, "b": 1, "c": 3, "e": 4}
    fz = {"brackets": {"B1_model": b1, "B2_shadow": None, "B3_manual": b3},
          "edits": [{"id": "1", "teams_changed": ["a", "b"]}, {"id": "2", "teams_changed": ["b"]}, {"id": "3", "teams_changed": ["d", "e"]}]}
    off = {"a": 2, "b": 1, "c": 3, "e": 4}
    g = review.grade(fz, off)
    assert g["manual_minus_model"] == g["groups_sum"] == g["scores"]["B3_manual"]["score"] - g["scores"]["B1_model"]["score"]
    assert sorted(len(x["edits"]) for x in g["edit_groups"]) == [1, 2] and any(x["joint"] for x in g["edit_groups"])

def test_freeze_is_immutable_and_respects_deadline(tmp_path):
    rv = {"season": 2027, "generated_at": "2027-03-14T15:30:00Z", "asof": "2027-03-14", "sources": {}, "model_version": "v2.0",
          "brackets": {"B1_model": {"a": 1}, "B2_shadow": None, "B3_manual": {"a": 1}}, "edits": [], "edit_notes": [], "model_order": ["a"]}
    assert review.freeze_deadline(2027) == datetime(2027, 3, 14, 16, 0, tzinfo=timezone.utc)      # noon EDT
    p = review.freeze(rv, str(tmp_path)); body = open(p, "rb").read()
    import hashlib; assert open(p + ".sha256").read().strip() == hashlib.sha256(body).hexdigest()
    with pytest.raises(SystemExit): review.freeze(rv, str(tmp_path))
    with pytest.raises(SystemExit): review.freeze({**rv, "generated_at": "2027-03-14T16:30:00Z"}, str(tmp_path / "late"))
