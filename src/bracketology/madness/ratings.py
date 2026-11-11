from __future__ import annotations
"""Pre-tournament team ratings, leak-free by construction.

Fit only on games played on or before Selection Sunday (from Torvik's game-log CSV, the endpoint
its robots.txt allows). Rating = points better than an average D-I team on a neutral court:
    margin = r_team - r_opp + home * h,   ridge-regularized least squares, margins capped.
Torvik's own pre-tournament ratings would be better but its time machine is disallowed and the
Internet Archive route (history.py) was unreachable from this machine when this was built.
"""
from datetime import date, timedelta
import math
import numpy as np

CAP = 25          # blowouts past this margin carry no extra information
RIDGE = 2.0       # shrinkage toward average, in games' worth of evidence
HALF_LIFE = None  # days; None = every pre-tournament game weighs the same


def _d(s: str) -> date:
    m, d, y = s.split("/")
    return date(2000 + int(y), int(m), int(d))


def selection_sunday(rows: list[dict], field_keys: set[str], key) -> date:
    """The Sunday before the first NCAA tournament game (type 3 between two field teams)."""
    first = min(_d(r["date"]) for r in rows
                if r["type"] == 3 and key(r["team"]) in field_keys and key(r["opp"]) in field_keys)
    return first - timedelta(days=(first.weekday() + 1) % 7 or 7)


def fit(rows: list[dict], through: date, key, half_life=HALF_LIFE, cap=CAP, ridge=RIDGE) -> dict[str, float]:
    """{team key: rating} from games on or before `through`."""
    games = []
    for r in rows:
        if r["type"] == 3:
            continue
        d = _d(r["date"])
        a, b = key(r["team"]), key(r["opp"])
        if d > through or a >= b:          # each game is listed once per side; keep one
            continue
        m = max(-cap, min(cap, r["pf"] - r["pa"]))
        home = {"H": 1.0, "A": -1.0, "N": 0.0}[r["loc"]]
        w = 1.0 if not half_life else 0.5 ** ((through - d).days / half_life)
        games.append((a, b, m, home, w))
    teams = sorted({g[0] for g in games} | {g[1] for g in games})
    ix = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    X = np.zeros((len(games), n + 1))
    y = np.zeros(len(games))
    w = np.zeros(len(games))
    for k, (a, b, m, home, wt) in enumerate(games):
        X[k, ix[a]] = 1.0; X[k, ix[b]] = -1.0; X[k, n] = home
        y[k] = m; w[k] = wt
    sw = np.sqrt(w)
    A = X * sw[:, None]
    reg = np.eye(n + 1) * ridge
    reg[n, n] = 0.0                         # home-court edge is not shrunk
    beta = np.linalg.solve(A.T @ A + reg, A.T @ (y * sw))
    r = beta[:n] - beta[:n].mean()
    out = {t: float(r[ix[t]]) for t in teams}
    out["__home__"] = float(beta[n])
    return out


def win_prob(diff: float, sigma: float) -> float:
    """P(team with rating edge `diff` wins on a neutral court)."""
    return 0.5 * (1 + math.erf(diff / (sigma * math.sqrt(2))))
