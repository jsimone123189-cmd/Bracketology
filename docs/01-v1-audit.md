# Phase 1 — V1 Excel audit (Bracketology_V1_original.xlsx, preserved unmodified)

Sheet1, A1:P87. Rows 2–79 = 78 teams (rows 65, 69, 70, 76 have no team name). Rows 80–87 = scratch notes (stray ranks/names in A and K), no formulas.

## Inputs (hardcoded, manual entry)
B Q1A wins · C Q1 wins · D Q2 wins · E Q3 losses · F Q4 losses · G Q1/2 "n/a" wins · H WAB rank · I SOR rank · J NET rank · K Torvik rank.
L, M, N: headers absent, cells **entirely blank**. Column R: entirely empty.

## Formulas
Rank transform s(x) = 100·(1 − (x−1)/199)²  (rank 1 → 100, rank 200 → 0).

O ("Seed rank") = 0.15·Q1A + 0.13·Q1 + 0.12·Q2 + R(row+8) − 0.5·Q3L − 1.5·Q4L + 0.06·G
                 + 0.24·s(WAB) + 0.19·s(SOR) + 0.17·s(NET) + 0.10·s(Torvik)
P ("Seed rank fin") = O + 0.03·s(L) + 0.025·s(M) + 0.025·s(N)
Teams are sorted by P descending (sheet order == rank order).

Reproduced exactly: `v1/reproduce_v1.py`, max diff vs Excel cached values 5e-9 for all 78 rows × 2 columns.

## Findings
1. **R10 reference (col O).** `SUM(..., R10, ...)` is a *relative* reference: row 2 → R10, row 3 → R11 … row 79 → R87. It is offset +8 rows from its own row, so it is almost certainly a mis-pointed/leftover cell, not intended. Column R is empty, so it contributes 0 to every team today. Latent bug: anything typed in R10:R87 would silently shift scores. Not fixed in V1.
2. **Blank L–N (col P).** Blank = 0 in Excel, so s(0) = 101.0 for every team; P = O + 0.08·101.0 = **O + 8.0806 constant**. Column P therefore adds **zero ranking information**; P order ≡ O order. Weights 0.03/0.025/0.025 imply three extra rank metrics (probably KPI/BPI/KenPom or similar) were planned but never entered. Which metrics those were is unknown — need your answer.
3. **Rank >200 is non-monotonic.** s() is not clamped: rank 250 → 6.3, 300 → 25.3, 400 → 101. 17 inputs across rows 69, 70, 71, 73, 74, 76, 77 exceed 200 (e.g. rank 354 Torvik → +~57·0.10). Bad teams get credit for being bad. Only affects low-ranked (non-contender) rows here, but it is wrong.
4. **Weight total.** Rank weights sum to 0.70 (O) / 0.80 (P-intended); record terms are unscaled counts, so record weights are not comparable to rank terms and Q-win counts dominate for deep résumés (e.g. Duke 7·.15+15·.13+7·.12).
5. **Correlated inputs / double counting.** WAB, SOR, NET, Torvik are highly correlated, and Q1/Q2 wins are already inside NET/WAB/SOR. Q1A wins are also counted inside Q1 wins (0.15 + 0.13 = 0.28 per Q1A win).
6. **No selection/seed output.** V1 outputs a score only; there is no cutoff, bid-steal handling, conference-champion auto-bids, or seed-line mapping. Scoring against Bracket Matrix needs that layer (V2).
7. **Data hygiene.** Team names mix annotations ("LIU 227*", "NDST 120*", "Bethune 222", "Morgan St 355"); `*` appears to flag auto-bid/conference leaders. Four rows have blank names. No snapshot date, no season label in the workbook (looks like one in-season snapshot, top teams Duke/Michigan/Arizona/Florida/Houston).

## Open questions (only the essential ones)
- What were L, M, N meant to be (and what did you actually submit to Bracket Matrix — columns O or P, and the exact seed list)?
- Which season/date is this snapshot, and is the 393-vs-~370 comparison from that season's final submission?
