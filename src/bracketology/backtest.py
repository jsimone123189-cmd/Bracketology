from __future__ import annotations
"""Leave-one-season-out backtest of field selection + seeding, scored with the real Bracket Matrix rubric."""
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from .features import build_year
from .history import SELECTION_SUNDAY
from .sources.bracketmatrix import score as bm_score

CAP = [4] * 10 + [6] + [4] * 4 + [6]           # seed lines 1..16 (First Four makes 11 and 16 six-deep)
YEARS = sorted(SELECTION_SUNDAY)

def _s(rank): return 100 * (1 - (rank - 1) / 199) ** 2

# ---------- V1 proxy: original weights; SOR rank -> our own SOR rank; Torvik rank -> our own rating rank ----------
def v1_proxy(rows):
    sor_rank = {r["key"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r["sor"]))}
    wab_rank = {r["key"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r["wab"]))}
    for r in rows:
        r["v1"] = (r["q1a_w"]*.15 + r["cq1_w"]*.13 + r["cq2_w"]*.12 - r["cq3_l"]*.5 - r["cq4_l"]*1.5
                   + .24*_s(wab_rank[r["key"]]) + .19*_s(sor_rank[r["key"]]) + .17*_s(r["net"]) + .10*_s(r["rating_rank"]))
    return rows

def _f(r, n):
    if n == "net_log": return float(np.log(r["net"]))
    if n == "win_pct": return r["w"] / max(1, r["w"] + r["l"])
    return float(r[n])

FEATS_BASE = ["net_log", "wab", "sor", "rating", "q1a_w", "cq1_w", "cq3_l", "cq4_l", "win_pct"]
FEATS_EXT = FEATS_BASE + ["sos", "road_w", "neutral_w", "last10", "best3", "cq2_w", "cq1_l"]
FEATS_CONS = FEATS_EXT + ["cons_avg_all", "cons_share"]
FEATS = FEATS_EXT
def X_of(rows, feats=None):
    return np.array([[_f(r, n) for n in (feats or FEATS)] for r in rows])

def slot(order: list[dict]) -> dict[str, int]:
    """order = best-first. Assign seed lines respecting CAP."""
    out, i = {}, 0
    for line, cap in enumerate(CAP, 1):
        for r in order[i:i + cap]: out[r["key"]] = line
        i += cap
    return out

def pick_field(rows, score_key, n_auto_total=68):
    champs = [r for r in rows if r["champ"]]
    pool = sorted((r for r in rows if not r["champ"]), key=lambda r: -r[score_key])
    chosen = champs + pool[: n_auto_total - len(champs)]
    return sorted(chosen, key=lambda r: -r[score_key])

def evaluate(year, rows, field, seeds_by_key):
    truth = {r["key"]: r["seed"] for r in rows if r["in_field"]}
    return bm_score(seeds_by_key, truth)

def run(verbose=True):
    data = {y: v1_proxy(build_year(y)) for y in YEARS}
    results = {}
    for hold in YEARS:
        train = [r for y in YEARS if y != hold for r in data[y]]
        test = data[hold]
        # --- selection models trained on at-large pool (non-champions) ---
        tr_pool = [r for r in train if not r["champ"]]
        Xtr, ytr = X_of(tr_pool), np.array([r["in_field"] for r in tr_pool], int)
        sc = StandardScaler().fit(Xtr)
        lr = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(Xtr), ytr)
        gb = GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=0.05, subsample=0.8,
                                        random_state=0).fit(Xtr, ytr)
        Xte = X_of(test)
        for r, p1, p2 in zip(test, lr.predict_proba(sc.transform(Xte))[:, 1], gb.predict_proba(Xte)[:, 1]):
            r["p_lr"], r["p_gb"] = p1, p2
            r["s_net"], r["s_wab"], r["s_cons"] = -r["net"], r["wab"], -r["cons_avg_all"]
        # --- seed models trained on true-field teams: predict seed (continuous) ---
        tr_f = [r for r in train if r["in_field"]]
        Xf, yf = X_of(tr_f), np.array([r["seed"] for r in tr_f], float)
        scf = StandardScaler().fit(Xf)
        rg = Ridge(alpha=10).fit(scf.transform(Xf), yf)
        gbr = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8,
                                        random_state=0).fit(Xf, yf)
        for r, a, b in zip(test, rg.predict(scf.transform(Xte)), gbr.predict(Xte)):
            r["seed_rg"], r["seed_gb"] = a, b
            r["seed_ens"] = (a + b) / 2
        methods = {  # name -> (field score key, seed score key (higher=better))
            "V1-proxy": ("v1", "v1"), "Consensus only": ("s_cons", "s_cons"), "NET only": ("s_net", "s_net"), "WAB only": ("s_wab", "s_wab"),
            "LogReg+Ridge": ("p_lr", "neg_seed_rg"), "GBM+GBM": ("p_gb", "neg_seed_gb"),
            "Ensemble (LR+GBM avg)": ("p_ens", "neg_seed_ens")}
        for r in test:
            r["neg_seed_rg"], r["neg_seed_gb"], r["neg_seed_ens"] = -r["seed_rg"], -r["seed_gb"], -r["seed_ens"]
            r["p_ens"] = (r["p_lr"] + r["p_gb"]) / 2
        for name, (fk, sk) in methods.items():
            field = pick_field(test, fk)
            order = sorted(field, key=lambda r: -r[sk])
            results.setdefault(name, {})[hold] = evaluate(hold, test, field, slot(order))
            if name in ("Consensus only", "Ensemble (LR+GBM avg)"):   # alt: round predicted line, no capacity constraint
                val = {"Consensus only": lambda r: r["cons_avg"] if r["cons_share"] > 0 else 16.0,
                       "Ensemble (LR+GBM avg)": lambda r: r["seed_ens"]}[name]
                rnd = {r["key"]: int(min(16, max(1, round(val(r))))) for r in field}
                results.setdefault(name + " [round]", {})[hold] = evaluate(hold, test, field, rnd)
    return results

def report(res):
    names = list(res); years = YEARS
    lines = ["| Method | " + " | ".join(map(str, years)) + " | Mean | Mean picked | Mean exact |", "|---" * (len(years) + 4) + "|"]
    for n in names:
        sc = [res[n][y]["score"] for y in years]
        lines.append(f"| {n} | " + " | ".join(map(str, sc)) + f" | **{np.mean(sc):.1f}** | "
                     f"{np.mean([res[n][y]['picked'] for y in years]):.1f} | {np.mean([res[n][y]['exact'] for y in years]):.1f} |")
    return "\n".join(lines)

if __name__ == "__main__":
    print(report(run()))
