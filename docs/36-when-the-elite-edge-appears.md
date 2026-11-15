# Research assessment, and when the elite edge appears

Committed before Part 2 was run.

## Part 1: assessment of the remaining information gap (Task 1)
**What the committee sees, and v2.0 already has:** the team sheet. Our rebuild matches it: quadrant records for 93-100% of field teams, and SOR, WAB, KenPom and BPI substitutes at .95-.99 (docs/33). The real sheet metrics add nothing (docs/14, docs/29).

**What's left of the committee's real process, and what can be checked historically:**
| Committee input | Free historical record? | Status |
|---|---|---|
| Team sheets | Yes | Matched (docs/33) |
| Head-to-head, common opponents | Yes | +1.0/+1.6, below the bar (docs/22-23) |
| Injuries / "team as it is now" | No free archive | Can't test (docs/27) |
| Eye test, member discussion | No | Not observable |
| The committee's own February top-16 | Yes | -1.3 (docs/19) |
| Timing: Sunday results | Yes | No effect (docs/35) |
| Contingency brackets for Sunday finals | No public record | Not observable |

**Conclusion:** every committee input with a free historical record has now been tested. What's left (injury news, discussion, the eye test) has no free archive. So Path A can't discover new committee information from history. The one new thing history can still tell us is **when and how elite bracketologists gain their edge**, which shows where to aim both paths.

## Part 2: experiment (Task 2), when do elite brackets pull ahead?
**Question:** is the roughly 7-exact-seed edge already there before conference-tournament week (pre-existing judgment or crowd information), or built during that week (processing final results, Sunday contingencies, committee signals)?

**Data (retrospective only, never a model input):**
- Internet Archive captures of bracketmatrix.com.
- **"D-7" snapshot:** the capture whose "Updated" date is the Sunday one week before Selection Sunday, or the nearest earlier date within 2 days.
- **Final:** the Matrix's season page (`matrix_{year}.html`).
- An entry counts at D-7 only if its own column date is within 3 days before the snapshot date, so stale brackets are excluded.
- **Brackets:** the nine (docs/11) and RFS. The Matrix consensus is reported for reference.

**v2.0 at D-7 (game-information baseline):** features recomputed with games through D-7 and the NET capture whose "Through Games" date is D-9 to D-7 (Wayback, ncaa.com). Automatic bids: champions only for leagues whose tournament was complete by D-7 (`dataset.completed_champions`); other leagues get their projected team, as production does. The model trains on the other six seasons' final data, as production would. This is a stated mismatch: production would also train on final data.

**Measures**, each bracket against the final committee bracket:
- exact seed lines among actual-field teams it includes, and
- the Matrix score.

Per season:
- gap at D-7 = the group's mean exact (the nine plus RFS) minus v2.0's exact at D-7;
- gap at final, the same measured at the final;
- the group's improvement and v2.0's improvement from D-7 to final.

**Interpretation rules, fixed now:**
- **Built in the final week:** (final gap − D-7 gap) ≥ 3 exact seeds on average and positive in at least 5 of 7 seasons. Next step: target how the committee processes final-week results.
- **Already there before:** the D-7 gap is at least 70% of the final gap on average. Timing isn't the source; the edge is judgment or crowd information held all season.
- Otherwise: mixed, reported as such.
- **Game-information share** = v2.0's improvement ÷ the group's improvement over the final week. It estimates how much of the elite's late improvement a statistical model also gets from the new games alone.
