from __future__ import annotations
"""Expected-score seed picker. Given each team's predicted seed distribution over lines 1..16, choose lines that
maximize expected Bracket Matrix points (3 exact, 1 within one) subject to the real capacity of each line
(4 per line, 6 on the 11 and 16 lines because of the First Four) -> optimal assignment problem."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import norm

CAP = [4] * 10 + [6] + [4] * 4 + [6]
SLOT_LINE = [line for line, c in enumerate(CAP, 1) for _ in range(c)]       # 68 slots -> line number

def line_probs(mu: np.ndarray, sigma: np.ndarray | float) -> np.ndarray:
    """P(true seed line = s) for s=1..16 under a discretized normal around mu (tails folded into 1 and 16)."""
    edges = np.arange(0.5, 17.5, 1.0)                                          # 0.5 .. 16.5
    mu = np.asarray(mu, float)[:, None]; sg = np.broadcast_to(np.asarray(sigma, float).reshape(-1, 1), mu.shape)
    cdf = norm.cdf((edges[None, :] - mu) / sg)                                  # (n,17)
    p = np.diff(cdf, axis=1)
    p[:, 0] += cdf[:, 0]; p[:, -1] += 1 - cdf[:, -1]
    return p

def expected_points(p: np.ndarray) -> np.ndarray:
    """E[points] of assigning line s to a team: 3*P(s) + 1*(P(s-1)+P(s+1))  (field-pick points are separate)."""
    e = 3 * p
    e[:, 1:] += p[:, :-1]; e[:, :-1] += p[:, 1:]
    return e

def assign(mu: np.ndarray, sigma) -> np.ndarray:
    """Return optimal seed line per team (len n == 68) under capacities."""
    e = expected_points(line_probs(mu, sigma))
    cost = -e[:, [l - 1 for l in SLOT_LINE]]                                   # (n, 68 slots)
    rows, cols = linear_sum_assignment(cost)
    out = np.zeros(len(mu), int); out[rows] = [SLOT_LINE[c] for c in cols]
    return out
