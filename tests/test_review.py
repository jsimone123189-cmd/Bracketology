import hashlib, json, os, subprocess, pytest
from datetime import datetime, timezone
from bracketology import review, fieldformat
from bracketology.sources import bracketmatrix as bm

def setup(n_extra=6, season=2026):
    size = fieldformat.format_for(season).size
    order = [f"t{i}" for i in range(size)]; rest = [f"x{i}" for i in range(n_extra)]
    info = {k: {"team": k.upper(), "champ": i >= size - 8, "projected_auto": False, "rank_score": -i, "p_in": 1 - i / 100} for i, k in enumerate(order)}
    info.update({k: {"team": k.upper(), "champ": False, "projected_auto": False, "rank_score": -size - i, "p_in": .4 - i / 100} for i, k in enumerate(rest)})
    return order, rest, info

def E(i, **k): return {"id": f"e{i}", "at": "2026-03-10T12:00:00Z", "reason_code": "head_to_head", "confidence": 2, **k}
def sizes(order, season=2026):
    L = review.lines_of(order, season); return [sum(1 for v in L.values() if v == l) for l in range(1, 17)]

# ---------------- edit engine
def test_move_keeps_line_sizes_and_shifts_one_team_per_boundary():
    order, rest, info = setup(); before = review.lines_of(order, 2026)
    new, rec, notes = review.apply_edits(order, rest, [E(1, op="move", team="t30", to_line=6)], 2026, info)
    assert not notes and sizes(new) == fieldformat.line_sizes(2026)
    after = review.lines_of(new, 2026); assert after["t30"] == 6
    moved = {k for k in after if after[k] != before[k] and k != "t30"}
    assert all(after[k] == before[k] + 1 for k in moved) and len(moved) == before["t30"] - 6
    assert rec[0]["line_before"] == 8 and rec[0]["line_after"] == 6 and rec[0]["overall_after"] == 21

def test_add_remove_swap_undo_and_auto_bid_guard():
    order, rest, info = setup()
    new, rec, notes = review.apply_edits(order, rest, [E(1, op="add", team="x2"), E(2, op="swap", team="t0", **{"with": "t5"}), E(3, op="remove", team="t67")], 2026, info)
    assert "x2" in new and len(new) == len(order) and sizes(new) == fieldformat.line_sizes(2026)
    assert any("not applied" in n for n in notes) and new.index("t5") == 0
    new3, rec3, _ = review.apply_edits(order, rest, [E(4, op="move", team="t1", to_line=3), {"id": "e4", "at": "2026-03-10T13:00:00Z", "op": "undo"}], 2026, info)
    assert new3 == order and rec3 == []

def test_invalid_edits_are_reported_not_applied():
    order, rest, info = setup()
    new, rec, notes = review.apply_edits(order, rest, [{"id": "a", "at": "x", "op": "move", "team": "t3", "to_line": 2, "reason_code": "other", "confidence": 2}], 2026, info)
    assert new == order and "explanation" in notes[0]

def test_76_team_engine_and_scoring():
    order, rest, info = setup(season=2027)
    new, _, notes = review.apply_edits(order, rest, [E(1, op="move", team="t70", to_line=12), E(2, op="add", team="x0")], 2027, info)
    assert not notes and len(new) == 76 and sizes(new, 2027) == [4] * 10 + [6, 8, 4, 4, 6, 8]
    perfect = review.lines_of(order, 2027); s = bm.score(perfect, dict(perfect))
    assert s["score"] == fieldformat.max_score(2027) == 456 and s["picked"] == 76

# ---------------- grading
def test_grade_groups_interacting_edits_and_sums_exactly():
    b1 = {"a": 1, "b": 2, "c": 3, "d": 4}; b3 = {"a": 2, "b": 1, "c": 3, "e": 4}
    fz = {"brackets": {"B1_model": b1, "B2_shadow": None, "B3_manual": b3},
          "edit_history": {"applied": [{"id": "1", "teams_changed": ["a", "b"]}, {"id": "2", "teams_changed": ["b"]}, {"id": "3", "teams_changed": ["d", "e"]}]}}
    g = review.grade(fz, {"a": 2, "b": 1, "c": 3, "e": 4})
    assert g["manual_minus_model"] == g["groups_sum"] == g["scores"]["B3_manual"]["score"] - g["scores"]["B1_model"]["score"]
    assert sorted(len(x["edits"]) for x in g["edit_groups"]) == [1, 2] and any(x["joint"] for x in g["edit_groups"])

# ---------------- freeze, verify, recovery
CUT = datetime(2027, 3, 14, 16, 0, tzinfo=timezone.utc)          # noon EDT
V2FP = review._saved_fp("models/v2.joblib")
def fake_review(collected, generated=None, b2=True, broken=False, alert=False, shadow_years=(2019, 2026), v2fp=None, pending=None, edits=()):
    order = [f"t{i}" for i in range(76)]; L = review.lines_of(order, 2027)
    if broken: L = dict(list(L.items())[:70])
    return {"season": 2027, "generated_at": generated or collected, "model_version": "v2.0", "asof": "2027-03-14",
            "inputs": {"collected_at": collected, "games_through": "2027-03-14", "latest_game_used": "2027-03-14", "net_source": "ncaa", "net_asof": "Mar. 13 2027", "conference_games_pending": pending},
            "sources": {"checks": [{"level": "alert", "message": "x"}] if alert else []}, "consistency": {"B2_same_field_as_B1": True},
            "shadow": {"train_years": list(shadow_years)}, "brackets": {"B1_model": L, "B2_shadow": dict(L) if b2 else None, "B3_manual": dict(L)},
            "all_info": {k: {"team": k.upper(), "champ": False, "projected_auto": False, "rank_score": -i} for i, k in enumerate(order)},
            "edits": list(edits), "edit_notes": [], "v2_fingerprint": v2fp or V2FP}

def put(folder, rv):
    os.makedirs(folder, exist_ok=True); json.dump(rv, open(f"{folder}/2027_{rv['inputs']['collected_at'].replace(':', '')}.json", "w"))

def test_deadline_is_noon_eastern():
    assert review.freeze_deadline(2027) == CUT

def test_1201_run_freezes_and_post_noon_data_is_never_frozen(tmp_path):
    f = str(tmp_path / "rv"); put(f, fake_review("2027-03-14T10:17:00Z")); put(f, fake_review("2027-03-14T15:30:00Z")); put(f, fake_review("2027-03-14T16:01:00Z"))
    r = review.freeze(2027, f, str(tmp_path / "fz"), now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file=str(tmp_path / "none.json"))
    b = json.load(open(r["path"]))
    assert r["status"] == "frozen" and b["inputs"]["collected_at"] == "2027-03-14T15:30:00Z" and b["cutoff"] == "2027-03-14T16:00:00Z"
    assert any("after the" in p for s in b["skipped_reviews"] for p in s["problems"])        # the 16:01 review was refused
    assert len(b["brackets"]["B1_model"]) == 76 and b["model"]["version"] == "v2.0" and "edit_history" in b

def test_missed_run_recovers_from_morning_review_late(tmp_path):
    f = str(tmp_path / "rv"); put(f, fake_review("2027-03-14T10:17:00Z"))
    r = review.freeze(2027, f, str(tmp_path / "fz"), now=datetime(2027, 3, 14, 16, 20, tzinfo=timezone.utc), edits_file="nope")
    b = json.load(open(r["path"])); assert b["frozen_after_cutoff"] and b["inputs"]["collected_at"] == "2027-03-14T10:17:00Z"

def test_incomplete_reviews_are_skipped_and_none_valid_fails(tmp_path):
    f = str(tmp_path / "rv"); put(f, fake_review("2027-03-14T10:17:00Z"))
    put(f, fake_review("2027-03-14T15:20:00Z", b2=False)); put(f, fake_review("2027-03-14T15:25:00Z", broken=True)); put(f, fake_review("2027-03-14T15:30:00Z", alert=True))
    put(f, fake_review("2027-03-14T15:31:00Z", shadow_years=(2019, 2027)))
    open(f"{f}/2027_garbage.json", "w").write("{half written")
    r = review.freeze(2027, f, str(tmp_path / "fz"), now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file="nope")
    b = json.load(open(r["path"])); assert b["inputs"]["collected_at"] == "2027-03-14T10:17:00Z" and len(b["skipped_reviews"]) == 4
    g = str(tmp_path / "rv2"); put(g, fake_review("2027-03-14T15:20:00Z", b2=False))
    with pytest.raises(SystemExit): review.freeze(2027, g, str(tmp_path / "fz2"), now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file="nope")

def test_duplicate_freeze_is_idempotent_and_tampering_is_caught(tmp_path):
    f = str(tmp_path / "rv"); fz = str(tmp_path / "fz"); put(f, fake_review("2027-03-14T15:30:00Z"))
    now = datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc)
    r1 = review.freeze(2027, f, fz, now=now, edits_file="nope"); raw = open(r1["path"], "rb").read()
    put(f, fake_review("2027-03-14T15:45:00Z"))                                                  # a newer pre-noon review appears
    r2 = review.freeze(2027, f, fz, now=now, edits_file="nope")
    assert r2["status"] == "already_frozen" and open(r1["path"], "rb").read() == raw              # never overwritten
    v = review.verify(2027, fz, now=datetime(2027, 3, 14, 16, 5, tzinfo=timezone.utc)); assert v["ok"]
    assert any(n.startswith("2027_research_verify_") for n in os.listdir(fz)) and open(r1["path"], "rb").read() == raw
    os.chmod(r1["path"], 0o644); open(r1["path"], "ab").write(b" ")
    assert not review.verify(2027, fz, write_record=False)["ok"]
    with pytest.raises(SystemExit): review.freeze(2027, f, fz, now=now, edits_file="nope")

# ---------------- privacy
def test_private_paths_are_ignored_and_untracked():
    assert "private/" in open(".gitignore").read()
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
    assert not any(t.startswith("private/") or (t.startswith("reviews/") and t.endswith(".json")) for t in tracked)
    with pytest.raises(SystemExit): review.write({"season": 2027, "inputs": {"collected_at": "x"}}, "data/output/site/review")

def test_verify_rejects_a_substituted_model_for_a_live_season(tmp_path):
    f = str(tmp_path / "rv"); fz = str(tmp_path / "fz"); put(f, fake_review("2027-03-14T15:30:00Z", v2fp="0" * 64))
    review.freeze(2027, f, fz, now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file="nope")
    v = review.verify(2027, fz, write_record=False); assert not v["ok"] and any("saved v2.0" in p for p in v["problems"])

# ---------------- final competitive snapshot (docs/43)
FINAL = datetime(2027, 3, 14, 21, 45, tzinfo=timezone.utc)        # example deadline 5:45 p.m. EDT; the real one is set once confirmed

def test_final_deadline_refuses_until_confirmed_and_converts_new_york_time(monkeypatch):
    monkeypatch.setitem(review.FINAL_DEADLINE_ET, 2027, None)
    with pytest.raises(SystemExit): review.freeze_deadline(2027, "final")
    monkeypatch.setitem(review.FINAL_DEADLINE_ET, 2027, "2027-03-14 17:45")
    assert review.freeze_deadline(2027, "final") == FINAL

def test_final_freeze_waits_for_finals_and_never_uses_post_deadline_data(tmp_path):
    f = str(tmp_path / "rv"); fz = str(tmp_path / "fz"); now = datetime(2027, 3, 14, 21, 40, tzinfo=timezone.utc)
    put(f, fake_review("2027-03-14T15:30:00Z", pending=None))                                       # research-time review
    put(f, fake_review("2027-03-14T20:50:00Z", pending=[{"conf": "big-ten"}]))                      # Big Ten final still on
    put(f, fake_review("2027-03-14T21:35:00Z", pending=[], edits=[{"id": "a", "at": "2027-03-14T21:20:00.123Z", "teams_changed": []}]))
    put(f, fake_review("2027-03-14T21:50:00Z", pending=[]))                                         # after the deadline: refused
    r = review.freeze(2027, f, fz, now=now, deadline=FINAL, edits_file="nope", kind="final"); b = json.load(open(r["path"]))
    assert r["path"].endswith("2027_final_freeze.json") and b["kind"] == "final" and b["final_results_complete"]
    assert b["inputs"]["collected_at"] == "2027-03-14T21:35:00Z" and len(b["brackets"]["B3_manual"]) == 76
    assert review.verify(2027, fz, FINAL, write_record=False, kind="final")["ok"]
    assert not review.verify(2027, fz, CUT, write_record=False, kind="final")["ok"]                  # wrong cutoff is caught

def test_final_freeze_falls_back_and_flags_incomplete_results(tmp_path):
    f = str(tmp_path / "rv"); fz = str(tmp_path / "fz")
    put(f, fake_review("2027-03-14T20:50:00Z", pending=[])); put(f, fake_review("2027-03-14T21:30:00Z", pending=[{"conf": "big-ten"}]))
    put(f, fake_review("2027-03-14T21:40:00Z", pending=None))                                       # feed unreadable = not complete
    b = json.load(open(review.freeze(2027, f, fz, now=FINAL, deadline=FINAL, edits_file="nope", kind="final")["path"]))
    assert b["inputs"]["collected_at"] == "2027-03-14T20:50:00Z"                                    # newest with every final in
    g = str(tmp_path / "rv2"); put(g, fake_review("2027-03-14T21:30:00Z", pending=[{"conf": "big-ten"}]))
    with pytest.raises(SystemExit, match="Waiting for conference finals"):                          # never frozen incomplete while there's time
        review.freeze(2027, g, str(tmp_path / "fz2"), now=datetime(2027, 3, 14, 21, 30, tzinfo=timezone.utc), deadline=FINAL, edits_file="nope", kind="final")
    b2 = json.load(open(review.freeze(2027, g, str(tmp_path / "fz2"), now=FINAL, deadline=FINAL, edits_file="nope", kind="final")["path"]))
    assert not b2["final_results_complete"] and b2["conference_games_pending"] == [{"conf": "big-ten"}]

def test_research_and_final_are_separate_immutable_files(tmp_path):
    f = str(tmp_path / "rv"); fz = str(tmp_path / "fz")
    put(f, fake_review("2027-03-14T15:30:00Z")); put(f, fake_review("2027-03-14T21:35:00Z", pending=[]))
    r1 = review.freeze(2027, f, fz, now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file="nope")
    r2 = review.freeze(2027, f, fz, now=FINAL, deadline=FINAL, edits_file="nope", kind="final")
    assert r1["path"] != r2["path"] and json.load(open(r1["path"]))["inputs"]["collected_at"] == "2027-03-14T15:30:00Z"
    assert review.verify(2027, fz, write_record=False)["ok"] and review.verify(2027, fz, FINAL, write_record=False, kind="final")["ok"]
    assert oct(os.stat(r1["path"]).st_mode)[-3:] == "444" and oct(os.stat(r2["path"]).st_mode)[-3:] == "444"

def test_edit_logged_after_cutoff_blocks_that_review():
    rv = fake_review("2027-03-14T15:30:00Z", edits=[{"id": "late", "at": "2027-03-14T16:00:01Z", "teams_changed": []}])
    assert any("after the cutoff" in p for p in review.problems(rv, CUT))

def test_results_complete_cross_checks_games_used():
    games = [{"date_iso": "2027-03-14", "ct": True, "id": "g1", "team_key": "a", "opp_key": "b"}, {"date_iso": "2027-03-14", "ct": True, "id": "g1", "team_key": "b", "opp_key": "a"}]
    assert review.results_complete(([], 1), games, "2027-03-14") == []
    assert review.results_complete(([], 2), games, "2027-03-14") is None                               # scoreboard says over, data lacks one
    assert review.results_complete(([{"conf": "x"}], 2), games, "2027-03-14") == [{"conf": "x"}]
    assert review.results_complete(None, games, "2027-03-14") is None

# ---------------- engine fixes found while porting to the Worker (docs/44)
def test_failed_add_with_bad_line_leaves_the_field_intact():
    order, rest, info = setup()
    new, rec, notes = review.apply_edits(order, rest, [E(1, op="add", team="x1", to_line=17)], 2026, info)
    assert new == order and rec == [] and "not applied" in notes[0]

def test_undo_of_names_the_retracted_edit():
    order, rest, info = setup()
    new, rec, _ = review.apply_edits(order, rest, [E(1, op="move", team="t30", to_line=6), {"id": "u1", "at": "2026-03-10T13:00:00Z", "op": "undo", "undo_of": "e1"}], 2026, info)
    assert new == order and rec == []

def test_research_freeze_never_before_1201(tmp_path):
    f = str(tmp_path / "rv"); put(f, fake_review("2027-03-14T15:30:00Z"))
    for t in (datetime(2027, 3, 14, 15, 30, tzinfo=timezone.utc), datetime(2027, 3, 14, 16, 0, 30, tzinfo=timezone.utc)):
        with pytest.raises(SystemExit, match="Too early"): review.freeze(2027, f, str(tmp_path / "fz"), now=t, edits_file="nope")
    assert review.freeze(2027, f, str(tmp_path / "fz"), now=datetime(2027, 3, 14, 16, 1, tzinfo=timezone.utc), edits_file="nope")["status"] == "frozen"
