# Bracket Matrix scoring (from the site's "What's this all about?" text, provided by owner 2026-11-05)

Rubric (Paymon / PHSports): per team
- 3 pts: team correctly picked (in the field)
- 3 pts: team correctly seeded
- 1 pt: seeded incorrectly but within one seed line
Perfect score with "76 teams" = 456 = 76 x 6.
Table uses the last 5 seasons, weighted toward recent; only brackets with 68 teams count.

## Open interpretation (do NOT guess in V2 scoring)
68 field teams x 6 = 408, so 456 implies 8 more scored teams. Most likely the 8 teams just outside the field
(First Four Out / Next Four Out) are also scored, but the rule for how an "out" team earns points is not stated
(treated as seeded on a 69-76 pseudo-line? exact-order? unordered set?). Needs the site's blog / owner confirmation.
Until confirmed, the optimizer reports the unambiguous 68-team component (max 408) separately.

## Implications for modeling
- Seed accuracy is worth as much as field accuracy: exact seed line = 3, off-by-one = 1, so a wrong-by-one guess
  still earns 1/3. Optimal pick for each team is the seed line maximizing expected score, which is NOT the mean
  or mode: E[score(s)] = 3*P(seed=s) + 1*(P(s-1)+P(s+1)).
- "Seed" means seed line 1-16 (not 1-68 overall rank). The overall 1-68 list matters only for assigning lines
  and for the four 11/16 First Four pairs.
- Field membership (3 pts) is a separate decision: include a team iff P(in) is high enough relative to the
  bubble competition (exactly 68 slots, 36ish at-large), solved jointly, not by an independent 0.5 cutoff.
