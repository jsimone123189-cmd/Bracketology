"""76-team format stress test. NOT accuracy evidence: no 76-team season exists, so the extra teams have no committee answer.
Each past season's real champions and held-out model scores are pushed through the format to see that it holds up and how much the layout matters.
Layouts: printed = NCAA printable bracket, production. old = the earlier assumption (6 on line 10, 8 on line 11).
strict = the printed layout read literally: the 12 lowest at-large teams on lines 11-12 and the 12 lowest automatic qualifiers on lines 15-16, everyone else by rank."""
import numpy as np
from bracketology import fieldformat as ff, history, model, project, sitebuild
from bracketology.features import build_year

OLD = ff.Format(tuple([4] * 9 + [6, 8, 4, 4, 4, 6, 8]), 32, 44, {10: 2, 11: 4}, {15: 2, 16: 4})

def strict(order, fmt):
    """Line for each team when opening-round games are forced onto the printed lines."""
    al = [r for r in order if not r["champ"]]; aq = [r for r in order if r["champ"]]
    n_al, n_aq = sum(fmt.opening_at_large.values()) * 2, sum(fmt.opening_automatic.values()) * 2
    out = {}
    for group, opening in ((al[-n_al:], fmt.opening_at_large), (aq[-n_aq:], fmt.opening_automatic)):
        i = 0
        for line in sorted(opening):
            for r in group[i:i + opening[line] * 2]: out[r["key"]] = line
            i += opening[line] * 2
    games = {**fmt.opening_at_large, **fmt.opening_automatic}
    open_slots = [l for l, n in enumerate(fmt.lines, 1) for _ in range(n - 2 * games.get(l, 0))]
    for r, l in zip([r for r in order if r["key"] not in out], open_slots): out[r["key"]] = l
    return out

fmt = ff.FORMAT_76; moved_old, moved_strict = [], []
for y in sorted(history.SELECTION_SUNDAY):
    m = model.Model().fit(project.training_rows(exclude={y})); rows = model.prepare(build_year(y)); m.score(rows)
    field, rest = model.choose_field(rows, y, project_autos=False, fmt=fmt)
    autos = sum(r["champ"] for r in field); order = model.assign_lines(field, y, fmt=fmt)
    printed = {r["key"]: r["line"] for r in order}
    assert [sum(v == l for v in printed.values()) for l in range(1, 17)] == list(fmt.lines) and len(order) == 76
    regions = [dict(team=r["team"], key=r["key"], lg=r.get("lg"), overall=r["overall"], line=r["line"]) for r in order]; sitebuild.assign_regions(regions)
    assert all(r["region"] in (0, 1, 2, 3) for r in regions) and sum(r["play_in"] for r in regions) == 24
    old = {r["key"]: l for r, l in zip(order, OLD.slots)}; st = strict(order, fmt)
    assert sorted(st.values()) == fmt.slots
    n_old, n_st = sum(old[k] != printed[k] for k in printed), sum(st[k] != printed[k] for k in printed)
    moved_old.append(n_old); moved_strict.append(n_st)
    aq12 = [r["team"] for r in order if r["champ"] and r["line"] in (11, 12)]; al13 = [r["team"] for r in order if not r["champ"] and r["line"] >= 13]
    print(y, "autos", autos, "at-large", 76 - autos, "| differ from printed: old", n_old, "strict", n_st, "biggest strict move", max(abs(st[k] - printed[k]) for k in printed),
          "| champions on lines 11-12", len(aq12), "| at-large below line 12", al13, flush=True)
print("mean teams on a different line: old", round(np.mean(moved_old), 1), "strict", round(np.mean(moved_strict), 1))
