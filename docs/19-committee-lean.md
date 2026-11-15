# The committee's lean from the top-16 reveal

Committed before running.

## Named flaw in the old reveal test (docs/06, -1.0)
It ran on an older model, not v2.0, and added the February line as a plain feature. A month-old seed mostly repeats February's résumé, which the model already sees. The useful part of the reveal is how far the committee placed a team from where the stats placed it **that same day**. That's the committee's own lean, and it's the only pre-selection view of the committee's judgment.

## Data
- The NCAA's top 16 for each season, in the reveal's order (as in `research/diagnose.py`).
- NET as of each reveal from Internet Archive captures of the NCAA NET page (`research/fetch_reveal_net.py`). Captures fall 0-4 days before the reveal; "through" dates run Feb. 11-18.
- Game results through the capture date.

## Test 6
For each held-out season, with v2.0 trained on the other seasons:
1. Rebuild every team's features as of the reveal: reveal-day NET, games through the capture date (records, quadrants, WAB, SOR, rating and the rest). No team is an automatic bid yet.
2. Score them with v2.0. Model position = rank by v2.0's rank score among teams with NET 100 or better.
3. **Lean** for each revealed team = reveal position minus model position. For a team in the model's top 16 that the committee left out, lean = 17 minus model position.
4. In March, each team with a lean has its predicted overall position moved by half its lean (0.5 × lean, fixed). Then the field is reslotted in that order. Selection is unchanged.

The usual bar applies. Also reported: percentile each season, whether it reaches the 75th in all seven, and exact seeds on lines 1-4.
