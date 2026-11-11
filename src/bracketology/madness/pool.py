from __future__ import annotations
"""Bracket pool math for a 64-team bracket (picks made after the First Four).

Teams are indexed 0-63: the four regions in Final Four order (semifinals pair regions 0-1 and 2-3),
each region's 16 teams in bracket order. Slots 0-31 are first-round games, 32-47 second round,
48-55 Sweet 16, 56-59 Elite Eight, 60-61 national semifinals, 62 the final.
A bracket (or a simulated tournament) is an array of 63 team indexes: the winner of each slot.
"""
import numpy as np

ROUND_OF_SLOT = np.array([1] * 32 + [2] * 16 + [3] * 8 + [4] * 4 + [5] * 2 + [6])


def points_table(per_round=(1, 2, 3, 4, 5, 6)) -> np.ndarray:
    return np.array([per_round[r - 1] for r in ROUND_OF_SLOT])


def _children():
    kids = [(True, 2 * s, 2 * s + 1) for s in range(32)]      # first round: two teams
    start, n = 0, 32
    while n > 1:
        kids += [(False, start + 2 * i, start + 2 * i + 1) for i in range(n // 2)]
        start += n
        n //= 2
    return kids


KIDS = _children()
SPAN = []            # (first team, last team + 1) each slot covers
for s, (leaf, a, b) in enumerate(KIDS):
    SPAN.append((a, b + 1) if leaf else (SPAN[a][0], SPAN[b][1]))


def simulate(P: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """n tournaments (n x 63), each game won by row team a over b with probability P[a, b]."""
    W = np.empty((n, 63), dtype=np.int16)
    for s, (leaf, a, b) in enumerate(KIDS):
        A = np.full(n, a) if leaf else W[:, a]
        B = np.full(n, b) if leaf else W[:, b]
        W[:, s] = np.where(rng.random(n) < P[A, B], A, B)
    return W


def advance(P: np.ndarray) -> np.ndarray:
    """Exact probabilities (63 x 64) that each team wins each slot."""
    q = np.zeros((63, 64))
    for s, (leaf, a, b) in enumerate(KIDS):
        if leaf:
            q[s, a], q[s, b] = P[a, b], P[b, a]
        else:
            L, R = q[a], q[b]
            q[s] = L * (P @ R) + R * (P @ L)
    return q


def max_points_bracket(P: np.ndarray, pts: np.ndarray, champion: int | None = None) -> np.ndarray:
    """The bracket with the most expected points (exact, by dynamic programming over the tree),
    optionally forced to a given champion."""
    q = advance(P)
    best = np.full((63, 64), -np.inf)
    for s, (leaf, a, b) in enumerate(KIDS):
        lo, hi = SPAN[s]
        for t in range(lo, hi):
            own = pts[s] * q[s, t]
            if leaf:
                best[s, t] = own
            else:
                left = t < SPAN[a][1]
                mine, other = (a, b) if left else (b, a)
                best[s, t] = own + best[mine, t] + best[other].max()
    pick = np.empty(63, dtype=np.int16)

    def fill(s, t):
        pick[s] = t
        leaf, a, b = KIDS[s]
        if leaf:
            return
        mine, other = (a, b) if t < SPAN[a][1] else (b, a)
        fill(mine, t)
        fill(other, int(np.argmax(best[other])))

    fill(62, int(np.argmax(best[62])) if champion is None else champion)
    return pick


def chalk_bracket(seeds: np.ndarray, rating: np.ndarray) -> np.ndarray:
    """Better seed every game; equal seeds go to the higher rating."""
    pick = np.empty(63, dtype=np.int16)
    for s, (leaf, a, b) in enumerate(KIDS):
        A, B = (a, b) if leaf else (pick[a], pick[b])
        pick[s] = A if (seeds[A], -rating[A]) <= (seeds[B], -rating[B]) else B
    return pick


def scores(brackets: np.ndarray, outcomes: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Points for each bracket against each outcome. brackets (..., 63), outcomes broadcastable."""
    return ((brackets == outcomes) * pts).sum(axis=-1)


def win_credit(mine: np.ndarray, others: np.ndarray) -> np.ndarray:
    """Share of first place: 1 for an outright win, 1/k for a k-way tie at the top, else 0.
    mine (n,), others (n, m)."""
    top = others.max(axis=1)
    ties = (others == mine[:, None]).sum(axis=1)
    return np.where(mine > top, 1.0, np.where(mine == top, 1.0 / (ties + 1), 0.0))
