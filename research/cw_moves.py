"""Exploratory (not pre-registered), docs/39: are championship-week line moves toward or away from the committee's seed? v2.0 vs elite."""
import sys; sys.argv = ["x"]; sys.path.insert(0, "research")
exec(open("research/championship_week.py").read().split("# ---------------- Part 1 + 2")[0])
import datetime as dt
def moves(a, b, off, ks):
    tow = awa = 0
    for k in ks:
        if a[k] == b[k]: continue
        if abs(b[k] - off[k]) < abs(a[k] - off[k]): tow += 1
        elif abs(b[k] - off[k]) > abs(a[k] - off[k]): awa += 1
    return tow, awa
T = {"v2 game-driven (champions fixed)": [0, 0], "v2 all": [0, 0], "elite all": [0, 0]}
for h in sorted(NET7):
    off = off_of(h); mF = model.Model().fit(project.training_rows(exclude={h}))
    S7h = state(h, NET7[h], D7[h], champs_at(h, D7[h])); model.attach_overall(S7h, h)
    L0 = lines(mF, S7h, h); L1 = lines(mF, state(h, NET7[h], D7[h], champF[h]), h); L3 = lines(mF, state(h, None, SS[h], champF[h]), h)
    ks = set(L1) & set(L3) & set(off); t, a = moves(L1, L3, off, ks); T["v2 game-driven (champions fixed)"][0] += t; T["v2 game-driven (champions fixed)"][1] += a
    ks0 = set(L0) & set(L3) & set(off); t0, a0 = moves(L0, L3, off, ks0); T["v2 all"][0] += t0; T["v2 all"][1] += a0
    line = f"{h} v2 game-driven moves toward/away {t}/{a}; v2 all {t0}/{a0}"
    fm = f"{D}/{h}_matrix_d7.json"
    if os.path.exists(fm):
        M7 = json.load(open(fm)); snap = dt.date.fromisoformat(M7["updated"]); fin = matrix_full.submissions(h); et = ea = 0; n = 0
        for g in GROUP:
            if g not in M7["subs"] or g not in fin or g not in M7["dates"] or not (snap - dt.timedelta(days=3) <= dt.date.fromisoformat(M7["dates"][g]) <= snap): continue
            A = {key(x): l for x, l in M7["subs"][g].items()}; B = {key(x): l for x, l in fin[g].items()}; x, y = moves(A, B, off, set(A) & set(B) & set(off)); et += x; ea += y; n += 1
        T["elite all"][0] += et; T["elite all"][1] += ea; line += f"; elite all (sum over {n}) {et}/{ea}, per bracket {et / n:.1f}/{ea / n:.1f}"
    print(line, flush=True)
for k, (t, a) in T.items(): print(f"{k:<34} toward {t} away {a}  share toward {t / (t + a):.0%}")
