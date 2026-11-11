"""Which bracket strategy wins a 120-entry pool scored 1-2-3-4-5-6 per round? Backtest 2008-2026.

For each season (win-probability spread fit on the OTHER seasons only):
  chalk       better seed every game
  max points  the bracket with the most expected points under the rating model
  pool pick   among max-points brackets forced to each of the 8 likeliest champions, the one with
              the best simulated chance to finish first against 119 public entries
Then each strategy is scored on what actually happened: points (of 120), and its share of first
place and average finish against many draws of 119 simulated public entries.

The public is simulated, because historical pick percentages are not available to us:
  seed public     picks each game by seed, with the historical seed-upset rates
  informed public picks like the rating model but leans harder toward favorites (logit x 1.5)
Real public picks lean on brand names and the top 1-seeds; replace with ESPN/Yahoo pick
percentages in March. Run: PYTHONPATH=src python3 research/madness_pool.py
"""
import numpy as np
from bracketology.madness import history, pool, ratings

PTS = pool.points_table((1, 2, 3, 4, 5, 6))
ENTRIES = 120
SIMS = 3000            # tournaments simulated to choose the pool pick
DRAWS = 3000           # public fields drawn to score each strategy on the real result
rng = np.random.default_rng(2027)


def sigma_fit(tables):
    d, y = [], []
    for t in tables:
        for g in t["games"]:
            d += [g["wr"] - g["lr"], g["lr"] - g["wr"]]
            y += [1, 0]
    d, y = np.array(d), np.array(y)
    best = None
    for s in np.arange(6.0, 16.01, 0.1):
        p = np.clip([ratings.win_prob(x, s) for x in d], 1e-6, 1 - 1e-6)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        best = min(best or (ll, s), (ll, s))
    return best[1]


def seed_slope(tables):
    """Logistic slope on seed difference (no intercept), fit by Newton's method."""
    x, y = [], []
    for t in tables:
        for g in t["games"]:
            x += [g["ls"] - g["ws"], g["ws"] - g["ls"]]
            y += [1, 0]
    x, y, w = np.array(x, float), np.array(y, float), 0.0
    for _ in range(50):
        p = 1 / (1 + np.exp(-w * x))
        w -= np.sum((p - y) * x) / (np.sum(p * (1 - p) * x * x) + 1e-9)
    return w


def season_inputs(t):
    b = t["bracket"]
    teams, seeds = [], []
    for region in b["final_four"]:
        teams += b["regions"][region]
        seeds += b["region_seeds"][region]
    keys = [history.key(n) for n in teams]
    rating = np.array([t["ratings"][k] for k in keys])
    # actual winner of each slot
    played = {(history.key(g["w"]), history.key(g["l"])) for g in t["games"]}
    later = {history.key(g[k]) for g in t["games"] if g["round"] >= 2 for k in ("w", "l")}
    actual = np.empty(63, dtype=np.int16)
    for s, (leaf, a, b2) in enumerate(pool.KIDS):
        A, B = (a, b2) if leaf else (actual[a], actual[b2])
        if (keys[A], keys[B]) in played:
            actual[s] = A
        elif (keys[B], keys[A]) in played:
            actual[s] = B
        else:                                  # 2021 VCU-Oregon no contest: Oregon advanced
            actual[s] = A if keys[A] in later else B
    return teams, np.array(seeds), rating, actual


def logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def main():
    tables = history.all_seasons()
    names = ["chalk", "max points", "pool pick"]
    publics = ["seed public", "informed public"]
    tot = {(pu, n): {"pts": [], "win": [], "pct": [], "exp_win": []} for pu in publics for n in names}
    lines = []
    for i, t in enumerate(tables):
        others = tables[:i] + tables[i + 1:]
        sigma, slope = sigma_fit(others), seed_slope(others)
        teams, seeds, rating, actual = season_inputs(t)
        D = rating[:, None] - rating[None, :]
        P = 0.5 * (1 + np.vectorize(__import__("math").erf)(D / (sigma * np.sqrt(2))))
        q = pool.advance(P)
        publicQ = {
            "seed public": 1 / (1 + np.exp(-slope * (seeds[None, :] - seeds[:, None]))),
            "informed public": 1 / (1 + np.exp(-1.5 * logit(P))),
        }
        chalk = pool.chalk_bracket(seeds, rating)
        maxp = pool.max_points_bracket(P, PTS)
        champs = np.argsort(-q[62])[:8]
        cands = [pool.max_points_bracket(P, PTS, champion=int(c)) for c in champs]
        outcomes = pool.simulate(P, SIMS, rng)
        for pu in publics:
            Q = publicQ[pu]
            opp = pool.simulate(Q, SIMS * (ENTRIES - 1), rng).reshape(SIMS, ENTRIES - 1, 63)
            opp_sc = pool.scores(opp, outcomes[:, None, :], PTS)
            exp_win = [pool.win_credit(pool.scores(c[None, :], outcomes, PTS), opp_sc).mean() for c in cands]
            pick = cands[int(np.argmax(exp_win))]
            # score every strategy on the real result against fresh public fields
            field = pool.simulate(Q, DRAWS * (ENTRIES - 1), rng).reshape(DRAWS, ENTRIES - 1, 63)
            field_sc = pool.scores(field, actual[None, None, :], PTS)
            for n, br in zip(names, (chalk, maxp, pick)):
                mine = pool.scores(br, actual, PTS)
                win = pool.win_credit(np.full(DRAWS, mine), field_sc).mean()
                pct = (field_sc < mine).mean() + 0.5 * (field_sc == mine).mean()
                ew = pool.win_credit(pool.scores(br[None, :], outcomes, PTS), opp_sc).mean()
                for k, v in (("pts", mine), ("win", win), ("pct", pct), ("exp_win", ew)):
                    tot[(pu, n)][k].append(v)
            if pu == "seed public":
                lines.append(f"{t['season']}: champion picks chalk={teams[chalk[62]]}, max points={teams[maxp[62]]}, "
                             f"pool pick={teams[pick[62]]}; actual={teams[actual[62]]}; "
                             f"points {pool.scores(chalk, actual, PTS)}/{pool.scores(maxp, actual, PTS)}/"
                             f"{pool.scores(pick, actual, PTS)}")
        print(t["season"], "done", flush=True)
    print("\nPer season (seed public), points chalk/max points/pool pick of 120:")
    print("\n".join(lines))
    n = len(tables)
    print(f"\nTotals over {n} seasons, {ENTRIES}-entry pool, 1-2-3-4-5-6 scoring. "
          f"A random entry wins {1 / ENTRIES:.2%} of pools, i.e. {n / ENTRIES:.2f} of {n} seasons.")
    for pu in publics:
        print(f"\n  vs {pu}:")
        print(f"  {'strategy':11} {'avg pts':>7} {'expected wins':>14} {'actual wins':>12} {'avg finish pct':>15}")
        for nm in names:
            r = tot[(pu, nm)]
            print(f"  {nm:11} {np.mean(r['pts']):7.1f} {np.sum(r['exp_win']):14.2f} {np.sum(r['win']):12.2f} "
                  f"{np.mean(r['pct']):14.1%}")


if __name__ == "__main__":
    main()
