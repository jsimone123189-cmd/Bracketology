"""Per-team comparison: where RFS Bracket Science had the exact line and v2.0 (held-out) didn't, and the reverse."""
import matrix_full
from bracketology import history, model, project
from bracketology.features import build_year
from bracketology.teams import key
tot = {"rfs_only": 0, "v2_only": 0}
for h in sorted(history.SELECTION_SUNDAY):
    m = model.Model().fit(project.training_rows(exclude={h})); rows = model.prepare(build_year(h)); m.score(rows)
    f, _ = model.choose_field(rows, h, project_autos=False); L = {r["key"]: r["line"] for r in model.assign_lines(f, h)}
    R = {r["key"]: r for r in rows}; off = {k: r["seed"] for k, r in R.items() if r["in_field"]}
    rfs = {key(t): l for t, l in matrix_full.submissions(h).get("RFS", {}).items()}
    a = [(k, off[k], L.get(k), R[k]["net"], int(R[k]["champ"])) for k in off if rfs.get(k) == off[k] and L.get(k) != off[k]]
    b = [k for k in off if L.get(k) == off[k] and rfs.get(k) != off[k]]
    tot["rfs_only"] += len(a); tot["v2_only"] += len(b)
    print(h, f"RFS exact where v2 wasn't: {len(a)}, v2 exact where RFS wasn't: {len(b)}")
    for k, s, l, n, c in sorted(a, key=lambda x: x[1]): print(f"    {k:<22} seed {s:>2} v2 {l} NET {n} champ {c}")
print(tot)
