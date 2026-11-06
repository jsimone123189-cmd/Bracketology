# Player availability: feasibility only

Nothing here reaches the model. Script and output: `research/availability_probe.py`, `research/availability_probe_output.txt`.

## What was tested
Box scores for the 2026 NET top 12, every game through Selection Sunday, through the same third-party NCAA feed the site already uses.

## Results
- **Coverage:** 403 of 403 box scores found, all with readable minutes. A 2022 box score also exists, so older seasons look reachable; only that one game was checked before 2026.
- **Names:** no player's listed ID changed within a season, but the ID matched the jersey number in the box score inspected. It isn't a true player ID, so matching relies on names and needs care with transfers and spelling.
- **Sat-out players:** not reliable. Most teams list some players at 0 minutes, but Gonzaga listed none, so a missing player has to be treated as not playing.
- **Measure:** share of the top five players' earlier minutes missing over the final three games. Duke scored 0.36, with Caleb Foster and Patrick Ngongba missing. Purdue scored 0.08 and Gonzaga 0.06. The other nine scored 0.
- **Timing:** box scores carry a game time but no publication time. Using only games played before the cutoff avoids future information, but this doesn't prove a box was public by then.

## Limits
- Twelve top teams is a small sample, and bubble teams matter more for field picks.
- A zero doesn't say why: injury, suspension, illness and coach's choice look the same. Nothing here checks the reason.
- A player hurt early in the season has few earlier minutes and can fall out of the top five, so the measure misses long absences.
- The feed is third-party, and the terms for ncaa.com data are unconfirmed.

## Next step, if wanted
Run the measure on all seven seasons as one pre-registered test against the bar in `docs/08-baseline.md`. It can't move a seed automatically unless it passes.

**Outcome:** the seven-season test failed. NCAA box scores turned out to be unavailable before 2023 through the wrapper and largely empty for 2023, which is more than this check's 12 teams could show. See `docs/10-availability-test.md`.
