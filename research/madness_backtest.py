"""Backtest tournament win probabilities, leave-one-season-out, 2008-2026 (no 2020).

Models (each season's parameters fit on the other seasons only):
  coin    - 50/50
  seed    - logistic on seed difference
  rating  - Normal CDF of the pre-tournament rating gap (ratings fit on games through Selection Sunday)
  both    - logistic on rating gap and seed difference
Scored on every tournament game: log loss (lower is better), Brier, and how often the favorite won.
Run: PYTHONPATH=src python3 research/madness_backtest.py  (needs data/madness from madness_build.py)
"""
import math
import numpy as np
from bracketology.madness import history, ratings


def rows_of(tables):
    out = []
    for t in tables:
        for g in t["games"]:
            # orient each game from the better seed's side (ties: higher rating) so features are symmetric
            a_is_w = (g["ws"], -g["wr"]) <= (g["ls"], -g["lr"])
            if a_is_w:
                out.append((t["season"], g["wr"] - g["lr"], g["ls"] - g["ws"], 1, g["round"]))
            else:
                out.append((t["season"], g["lr"] - g["wr"], g["ws"] - g["ls"], 0, g["round"]))
    return out


def logistic_fit(X, y, l2=1e-3, iters=200):
    w = np.zeros(X.shape[1])
    for _ in range(iters):                 # Newton's method
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + l2 * w
        H = (X * (p * (1 - p))[:, None]).T @ X + l2 * np.eye(len(w))
        w -= np.linalg.solve(H, g)
    return w


def sigma_fit(d, y):
    best = None
    for s in np.arange(6.0, 16.01, 0.1):
        p = np.clip([ratings.win_prob(x, s) for x in d], 1e-6, 1 - 1e-6)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        if best is None or ll < best[0]:
            best = (ll, s)
    return best[1]


def score(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return (-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)), np.mean((p - y) ** 2),
            np.mean((p > .5) == (y == 1)))


def run(label, tables):
    R = np.array(rows_of(tables), float)
    seasons = sorted(set(R[:, 0]))
    preds = {m: np.zeros(len(R)) for m in ("coin", "seed", "rating", "both")}
    sig = []
    for s in seasons:
        tr, te = R[:, 0] != s, R[:, 0] == s
        y = R[tr, 3]
        preds["coin"][te] = .5
        ws = logistic_fit(np.c_[R[tr, 2]], y)                        # no intercept: symmetric by construction
        preds["seed"][te] = 1 / (1 + np.exp(-(np.c_[R[te, 2]] @ ws)))
        sg = sigma_fit(R[tr, 1], y); sig.append(sg)
        preds["rating"][te] = [ratings.win_prob(x, sg) for x in R[te, 1]]
        wb = logistic_fit(np.c_[R[tr, 1], R[tr, 2]], y)
        preds["both"][te] = 1 / (1 + np.exp(-(np.c_[R[te, 1], R[te, 2]] @ wb)))
    y = R[:, 3]
    print(f"\n== {label}: {len(R)} games, {len(seasons)} seasons; sigma fitted {min(sig):.1f}-{max(sig):.1f}")
    print(f"{'model':8} {'logloss':>8} {'brier':>7} {'fav won':>8}")
    for m, p in preds.items():
        ll, br, acc = score(p, y)
        print(f"{m:8} {ll:8.4f} {br:7.4f} {'-' if m == 'coin' else f'{acc:.1%}':>8}")
    # season by season, rating vs seed
    better = 0
    for s in seasons:
        te = R[:, 0] == s
        a, b = score(preds["rating"][te], y[te])[0], score(preds["seed"][te], y[te])[0]
        better += a < b
    print(f"rating beats seed on log loss in {better} of {len(seasons)} seasons")
    # calibration of the rating model
    p = preds["rating"]
    print("calibration (rating model): predicted -> actual for the side oriented as better seed")
    for lo, hi in ((0, .4), (.4, .55), (.55, .7), (.7, .85), (.85, 1.01)):
        m = (p >= lo) & (p < hi)
        if m.sum():
            print(f"  {lo:.2f}-{min(hi, 1):.2f}: n={int(m.sum()):4d}  predicted {p[m].mean():.3f}  actual {y[m].mean():.3f}")
    return preds, R


if __name__ == "__main__":
    flat = history.all_seasons()
    run("ratings: all pre-tournament games equal", flat)
    recent = history.all_seasons(half_life=45)
    run("ratings: recent games weighted (45-day half-life)", recent)
