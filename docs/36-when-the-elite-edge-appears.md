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

## Results (2026-11-15)
`research/edge_timing_output.txt`, `research/edge_timing_fetch_output.txt`. Snapshots were found for 2021, 2022, 2023, 2025 and 2026. 2019 and 2024 had no Matrix capture inside the pre-set window and are excluded. 4-7 elite brackets per season were fresh at D-7.

| Season | v2.0 exact D-7 → final | Elite exact D-7 → final | Gap D-7 | Gap final |
|---|---|---|---|---|
| 2021 | 16 → 33 | 24.7 → 48.8 | +8.7 | +15.8 |
| 2022 | 27 → 45 | 26.9 → 46.0 | -0.1 | +1.0 |
| 2023 | 28 → 42 | 33.8 → 52.0 | +5.8 | +10.0 |
| 2025 | 37 → 49 | 29.0 → 51.7 | -8.0 | +2.7 |
| 2026 | 32 → 45 | 28.0 → 55.0 | -4.0 | +10.0 |
| **Mean** | **+14.8** | **+22.2** | **+0.5** | **+7.9** |

- **Verdict, by the fixed rule: the edge is built in the final week.** The gap grows by +7.4 exact seeds on average, positive in 5 of 5 seasons. A week out, v2.0 and the elite are essentially tied (+0.5). By Selection Sunday they lead by 7.9.
- **Game-information share is 67%.** From the new games alone, v2.0 gets about two-thirds of the improvement the elite make in the final week. The remaining third, about 7 exact seeds or 21 points, comes from how they process the final week, not from the games' raw statistics.
- **Bias check:** at D-7 the elite brackets can be up to 3 days old, while v2.0 uses NET from D-9 to D-7 and every game through D-7. In 2025 the Matrix snapshot is from D-9 but v2.0 used NET through D-7. Both lean toward v2.0 at D-7, so the true D-7 gap may be somewhat larger than +0.5. The growth is still positive in every season.
- **What this rules in:** whatever separates the elite isn't held all season. It's what they do with championship week: conference tournament results, Sunday-final contingencies, the bubble shake-out, and converging on each other's brackets. That narrows Path A to one question: **how the committee weighs championship-week results compared with the regular season.**
