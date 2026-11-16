from bracketology import early

def rows(n=40, games=4):
    # model loves team 0; outside ranks put it 30th
    out = [{"key": f"t{i}", "w": games, "l": 0, "rank_score": 100 - i, "r_net": i + 1, "r_bpi": i + 1, "r_kp": i + 1, "r_trk": i + 1} for i in range(n)]
    out[0].update(r_net=30, r_bpi=30, r_kp=30, r_trk=30)
    return out

def test_weight_schedule():
    assert early.weight(4) == 0.8 and early.weight(20) == 0 and early.weight(32) == 0

def test_unmarked_rows_never_change():
    r = rows(); before = [x["rank_score"] for x in r]
    early.stabilize(r)
    assert [x["rank_score"] for x in r] == before

def test_selection_sunday_is_a_no_op():
    r = rows(games=30); early.mark(r); before = [x["rank_score"] for x in r]
    early.stabilize(r)
    assert [x["rank_score"] for x in r] == before

def test_early_blend_moves_outlier_and_keeps_score_set():
    r = rows(); early.mark(r); scores = sorted(x["rank_score"] for x in r)
    early.stabilize(r)
    order = [x["key"] for x in sorted(r, key=lambda x: -x["rank_score"])]
    assert order.index("t0") > 15
    assert sorted(x["rank_score"] for x in r) == scores
    assert r[0]["model_pos"] == 1 and r[0]["outside_rank"] == 30
