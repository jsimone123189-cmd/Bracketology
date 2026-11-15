from __future__ import annotations
"""B2 shadow candidate for 2027 (docs/38): v2.0's seed model plus two pair features, head-to-head net wins and
common-opponent win-share difference (docs/23, Test 10, +1.6 leave-one-season-out, below the replacement bar).
Field selection is v2.0's. Unpublished: it only feeds the review tool and the frozen comparison.
Method frozen as in research/common_opponents.py (C=0.1, pairs within 16 positions)."""
import collections
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from . import model

class PairEvidence:
    """Head-to-head and common-opponent evidence from one season's games through a cutoff day.
    games need team_key, opp_key, date_iso, win."""
    def __init__(self, games: list[dict], day: str):
        self.wins = collections.Counter(); seen = set()
        for g in games:
            if g["date_iso"] > day: continue
            sig = (g["date_iso"], g["team_key"], g["opp_key"])
            if sig in seen: continue
            seen.add(sig)
            if g["win"]: self.wins[(g["team_key"], g["opp_key"])] += 1
        self.rec = collections.defaultdict(lambda: [0, 0]); self.opp = collections.defaultdict(set)
        for (a, b), n in self.wins.items(): self.rec[(a, b)][0] += n; self.rec[(b, a)][1] += n
        for (a, b) in list(self.rec): self.opp[a].add(b)
        self._c = {}

    def h2h(self, a: str, b: str) -> int:
        return self.wins[(a, b)] - self.wins[(b, a)]

    def games_between(self, a: str, b: str) -> tuple[int, int]:
        return self.wins[(a, b)], self.wins[(b, a)]

    def common(self, a: str, b: str) -> float:
        if (a, b) in self._c: return self._c[(a, b)]
        cs = (self.opp[a] & self.opp[b]) - {a, b}
        v = float(np.mean([self.rec[(a, o)][0] / sum(self.rec[(a, o)]) - self.rec[(b, o)][0] / sum(self.rec[(b, o)]) for o in cs])) if cs else 0.0
        self._c[(a, b)] = v; self._c[(b, a)] = -v; return v

    def common_detail(self, a: str, b: str) -> dict:
        cs = sorted((self.opp[a] & self.opp[b]) - {a, b})
        return {"n": len(cs), "a_wins": sum(self.rec[(a, o)][0] for o in cs), "a_losses": sum(self.rec[(a, o)][1] for o in cs),
                "b_wins": sum(self.rec[(b, o)][0] for o in cs), "b_losses": sum(self.rec[(b, o)][1] for o in cs), "diff": round(self.common(a, b), 3)}

    def pair(self, a: str, b: str) -> list[float]:
        return [float(self.h2h(a, b)), self.common(a, b)]

class ShadowH2H:
    def fit(self, train: list[dict], evidence: dict[int, PairEvidence]) -> "ShadowH2H":
        """train: prepared training rows with year, key, in_field and ov. evidence: season -> PairEvidence."""
        field = [r for r in train if r["in_field"] and r.get("ov")]
        self.sd = StandardScaler().fit(model._X(field, model.SEED)); dX, dy = [], []
        for yr in sorted({r["year"] for r in field}):
            rs = [r for r in field if r["year"] == yr]; Z = self.sd.transform(model._X(rs, model.SEED)); ev = evidence[yr]
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    d = rs[i]["ov"] - rs[j]["ov"]
                    if d and abs(d) <= 16:
                        e = ev.pair(rs[i]["key"], rs[j]["key"])
                        dX += [np.r_[Z[i] - Z[j], e], np.r_[Z[j] - Z[i], [-x for x in e]]]; dy += [d < 0, d > 0]
        self.coef = LogisticRegression(C=.1, max_iter=3000, fit_intercept=False).fit(np.array(dX), np.array(dy, int)).coef_[0]
        return self

    def scores(self, field: list[dict], ev: PairEvidence) -> dict[str, float]:
        """Each team's mean win chance against the rest of the field (higher = better)."""
        B = self.sd.transform(model._X(field, model.SEED)); out = {}
        for i, r in enumerate(field):
            Zd = np.array([np.r_[B[i] - B[j], ev.pair(r["key"], field[j]["key"])] for j in range(len(field)) if j != i])
            out[r["key"]] = float((1 / (1 + np.exp(-(Zd @ self.coef)))).mean())
        return out

def history_evidence(years, day_of) -> dict[int, PairEvidence]:
    """Training evidence from the local Torvik game logs (history only; Torvik refuses cloud servers)."""
    from .sources import torvik
    from .teams import key
    from .shadow_anchor import annotate
    return {y: PairEvidence(annotate(torvik.collect_games(y, ttl=10 ** 9)["rows"], key), day_of(y)) for y in years}
