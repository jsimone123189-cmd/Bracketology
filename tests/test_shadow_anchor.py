from bracketology import shadow_anchor

def test_tournament_starts_and_cutoffs(monkeypatch):
    games = [{"type": 1, "conf": "A10", "date_iso": "2027-02-20"},
             {"type": 2, "conf": "A10", "date_iso": "2027-03-10"}, {"type": 2, "conf": "A10", "date_iso": "2027-03-12"},
             {"type": 2, "conf": "B10", "date_iso": "2027-03-11"}, {"type": 2, "conf": "B10", "date_iso": "2027-03-15"},
             {"type": 2, "conf": "SEC", "date_iso": "2027-03-16"}]       # after the cutoff day: ignored
    assert shadow_anchor.tournament_starts(games, "2027-03-14") == {"A10": "2027-03-10", "B10": "2027-03-11"}
    seen = []
    def fake(g, net, day):
        seen.append(day); return {k: {"wab": float(len(day))} for k in net}
    monkeypatch.setattr(shadow_anchor.metrics, "compute", fake)
    rows = [{"key": "a", "lg": "A10", "net": 30, "champ": True}, {"key": "b", "lg": "B10", "net": 5, "champ": False},
            {"key": "c", "lg": "Ivy", "net": 80, "champ": False}]
    out = shadow_anchor.anchored_rows(rows, games, "2027-03-14")
    assert [r["anchor_cutoff"] for r in out] == ["2027-03-09", "2027-03-10", "2027-03-14"]
    assert out[0]["net"] == 30 and out[0]["champ"] is True and "anchor_cutoff" not in rows[0]   # NET/champ kept, input untouched
    assert sorted(set(seen)) == ["2027-03-09", "2027-03-10", "2027-03-14"]                      # one compute per cutoff
