# Diagnosis: why the fly dies, and the ceiling of its two-number input

2026-09-24. Local data and the stand-in brain (`calibration/response_surface.json`) only; the real Brian2 brain
was not built and nothing was spent. Recorded runs on seeds below 1000 (`runs/20260919-154809`, seeds 0–19)
were skipped and never read.

## Summary (10 lines)

1. **The input is the bottleneck.** On v2 the best lookup table from today's (left, right) looming levels to an action
   scores **66.7 rows on held-out seeds**; the fly scores **66.0** on the same seeds with the stand-in brain (67.9 on practice
   seeds; the real brain scored 68.0 on 1000–1004). The readout already sits at its input's ceiling.
2. **Re-fixing the thresholds on v2 buys 0 rows.** The calibrate grid run on v2 practice seeds picks the frozen v1 numbers again
   (gain 250, falloff 3, turn 0 Hz, jump 200 Hz), both in the threshold-only grid (48 candidates) and in the full grid (768).
3. **Every death is a jump into a gap**: 25 of 25 deaths (20 on v1, 5 on v2). A safe landing tile existed every time, and 15 of the 25
   fatal jumps were made when running straight on was safe.
4. The cause is how *we* encode the game. Any gap in row 1, on any of the 7 visible lanes, adds 250 Hz to its eye and saturates
   it, so input (250, 250) means either "gap straight ahead" or "gaps somewhere on both sides". Those are the states where the Giant Fiber fires.
5. (250, 250) covers 30% of the floor states in rows 30–149. Even there, the best single action is **jump, and it still lands on a gap 23% of the time**.
   The jump reflex is not miswired. It is the least bad guess for an input that has thrown away where the gap is.
6. Among all fly jumps, 46% (v1, 86 of 185) and 54% (v2, 14 of 26) were made when running straight was safe. Those were "phantom" jumps, set off by gaps 2–3 lanes away.
7. The jump reflex is still needed. Stopping jumps (jump threshold 225 Hz or more) drops the fly to 39 rows. Jumping more often (threshold 175 Hz or less) is worse too.
8. Richer inputs that we choose (held-out rows, best table): narrow eyes that only see offsets −1..1 give **91.5**, a separate straight-ahead channel **100.9**, narrow eyes split near/far
   **109.2**, 4 landing-tile bits **108.3**, a 3×3 patch of rows 1–3 **136.3**. The solver scores 147.3.
9. Reading today's best table *through* the fly's 8 DN counts (nearest-centroid decode) drops it to 44 rows (the decoder recovers the right input
   88% of the time). A rich readout would therefore also lose to the brain's noise. The simple two-threshold readout is robust and already optimal.
10. **Next step for the pure fly:** make each eye report *where* the gap is, not only that one exists. The retinotopic LPLC2/LC4 subsets per lane, or a
    straight-ahead-only drive, are the input changes worth trying. Fixing the jump's blindness to the landing row needs row-2 information that
    reaches the Giant Fiber decision (see the circuits brief).

## 1. Failure anatomy (recorded runs, seeds ≥ 1000)

Script: `diag/anatomy.py`. Full output with the last 5 decisions of all 25 deaths: `diag/anatomy.out`. Runs used: v1
`20260919-151934` (seeds 1000–1019) plus the live v1 runs on 1001; v2 `20260921-192037` (1000–1004) plus the live v2 runs on
1001/1004. Identical replays (same seed, same length) are counted once, so 20 v1 and 5 v2 games are left.

| | v1 | v2 |
| --- | --- | --- |
| decisions | 2194 | 319 |
| deaths | 20, all `jumped_into_gap` | 5, all `jumped_into_gap` |
| decisions landing on a gap when a safe landing existed | 20 (0.91%) | 5 (1.57%) |
| jumps / onto a gap | 185 / 20 | 26 / 5 |
| jumps when "stay" was safe | 86 (46%) | 14 (54%) |
| fatal jumps when "stay" was safe | 12 | 3 |
| fatal jumps with C1 and C2 both gaps (should have turned) | 8 | 2 |
| agreement with the solver | 0.54 | 0.51 |

Every unsafe move the fly made was a fatal jump. It never ran or dodged into a gap. Its turns are always safe, because an eye at 0 Hz
proves the tile on that side is floor, and the fly turns toward the quiet eye.

The situation at the fatal decision (row-1 tiles L1 C1 R1; C2 is the jump's landing tile, a gap in all 25):

| fatal situation | v1 | v2 | what a safe move was |
| --- | --- | --- | --- |
| row 1 clear in L1–R1, gaps further out on both sides (±2, ±3), C2 gap | 7 | 1 | stay |
| one of L1/R1 gap, centre open, other side gap further out, C2 gap | 5 | 2 | stay |
| gap straight ahead only (C1), C2 gap | 5 | 2 | left or right |
| C1 + one side gap, C2 gap | 3 | 0 | the other side |

The input was (250, 250) at every fatal decision, and the Giant Fiber mean rate was 210–220 Hz against a 200 Hz threshold. Typical
examples (v2): seed 1001, row 28: row 1 `[0]`, row 2 `[0]` → jump into C2, where left or right was safe. Seed 1004, row 87: row 1 `[−3, 3]`
(nothing near the runner) → jump into C2, where stay was safe.

## 2. Information ceiling of the input

Script: `diag/ceiling.py` → `diag/ceiling.json` (includes every best table). v2, practice seeds 1000–1199, held-out 1200–1399. Every
(row, lane) state is encoded once and a table policy is played by lookup. The simulator matches `Game` exactly: 0 mismatches on 30
tracks. The table search starts from the myopic table (per key, the action that lands on a gap least often), then coordinate ascent
(try all 4 actions per visited key, keep improvements, restarts in 3 orders). The practice number is fitted to those seeds; **held-out is the
honest number**. The search finds a local optimum, so these are lower bounds on the best table for each input. The best table in turn bounds
any memoryless readout of that input (caveat: a randomised policy could in principle beat a deterministic table in this partially observed game).

| input (all ours) | keys seen | myopic table | best table, practice | **best table, held-out** |
| --- | --- | --- | --- | --- |
| **A today**: 2 eyes, gain 250, falloff 3, 11 levels | 79 | 59.7 | 78.5 | **66.7** |
| A1 same, falloff 1 | 100 | 38.0 | 52.7 | 41.5 |
| A2 same, falloff 2 | 121 | 58.5 | 77.6 | 62.6 |
| A3 same, falloff 4 | 25 | 59.7 | 72.9 | 62.5 |
| A4 same, uncapped (counts past 250 Hz) | 1289 | 77.7 | 111.2 | 74.8 (overfit) |
| A5 2 narrow eyes (offsets −1..1 only) | 30 | 64.3 | 98.7 | **91.5** |
| B 2 eyes + straight-ahead channel (offset 0) | 175 | 65.4 | 118.1 | **100.9** |
| C 2 eyes split near (row 1) / far (rows 2–6) | 246 | 62.2 | 90.8 | 72.2 |
| D 2 narrow eyes split near/far | 76 | 75.8 | 117.3 | **109.2** |
| E 4 landing-tile bits (L1 C1 R1 C2) | 16 | 112.8 | 117.5 | **108.3** |
| F 3×3 tiles, rows 1–3, offsets −1..1 | 512 | 112.7 | 148.8 | **136.3** |
| G 5×3 tiles, rows 1–3, offsets −2..2 | 16030 | 112.2 | 149.3 | 103.1 (overfit) |
| reference: solver (full 6×7 view) | – | – | 149.0 | 147.3 |
| floors: random / always_jump | – | – | 23.9 / 32.1 | 25.0 / 31.3 |

What the table shows:
- **Where the gap is matters more than how near it is.** Splitting rows (C) adds almost nothing (72 vs 67). Narrowing the eyes to the three lanes
  a move can reach (A5) adds 25 rows. A separate straight-ahead channel (B) adds 34. The wide, saturating eye is the loss.
- **The weighting we fixed is already the best of its family.** Falloff 3 is at or near the top, and with falloff 1 far gaps swamp the eye.
- **The jump needs row-2 information at the landing tile.** E (4 bits) ≈ D ≈ B ≈ 100–109. Only inputs that also see what comes after the
  landing (F) get close to the solver.

Ambiguity per input (`diag/ambiguity.py` → `diag/ambiguity.out`; floor states in rows 30–149, weighted evenly): with today's input the best
single action lands on a gap in **7.1% of decisions**. Almost all of that comes from key (250, 250): 30.5% of states, gap rate stay 69%, left/right 48%,
jump 23%. For comparison: B 5.0%, A5 5.3%, E 1.2% (all but a few of E's remaining states are cases where all four landings are gaps, which only
planning ahead avoids).

## 3. Re-fixing the thresholds on v2 (stand-in brain; report only)

Script: `diag/refix_v2.py` → `diag/refix_v2.json`. Rule fixed beforehand, as in `bakeoff/fly/calibrate.py`: the highest mean rows on v2 practice
seeds 1000–1199 wins, ties go to grid order, and the winner plays held-out seeds 1200–1399 once. Nothing was written to `calibration/`.

| candidate | practice | held-out |
| --- | --- | --- |
| current frozen (250, 3, turn 0, jump 200) | 67.9 | 66.0 |
| winner, thresholds only (48 candidates) | **the same candidate**, 67.9 | 66.0 |
| winner, full grid (768 candidates) | **the same candidate**, 67.9 | 66.0 |
| best table on today's input, played directly | 78.5 | 66.7 |
| the same table read through the fly's DN counts | 44.5 | 44.4 |

Jump threshold with turn 0 (practice): 75 Hz → 30.9, 100 → 36.3, 125 → 41.8, 150 → 50.1, 175 → 58.9, **200 → 67.9**, 225/250 → 39.3 (the Giant
Fiber never reaches it, so the fly never jumps). Turn threshold 10/30 Hz → 65.6/62.0. **Re-fixing buys 0 rows.** How far the stand-in agrees with
the real brain on v2: seeds 1000–1004 score 64/67/116/90/88 (mean 85) with the stand-in and 64/29/45/114/88 (mean 68) with the real brain. Single tracks
differ by noise, as they did on v1 (`calibration/RESULTS.md`). On 200 seeds the stand-in's 66–68 matches the real brain's 68.

## Verdict: which bottleneck dominates

**The input.** The readout is at the ceiling of what (left, right) can carry (66.0 vs 66.7 held-out), so no readout or threshold change on today's input
can help by more than about a row. The jump reflex is the *place* where the fly dies, not the cause. With today's input, jumping is the best action at (250, 250),
and the fly jumps there. It dies because that input cannot tell a gap straight ahead from gaps on both flanks, and it carries nothing about the landing
tile, which the 250 Hz cap and the ±3-lane eye wipe out. Changes that are ours and worth building for the pure fly, in order of rows per change:
narrow or lane-resolved eyes (A5 +25), a straight-ahead channel into the fly (B +34), and landing-row information that can reach the jump decision (D/E ≈ +42).
Each is an upper bound. Whether the fly's own DN outputs can carry the distinction is a separate question: today's rich table loses 22 rows through
the brain's noise (§3), so any richer input should be tested with a readout as simple as today's.

## Files (all under `diag/` in this directory; `ceiling.json`, 1.9 MB, is not kept: `ceiling.py` rebuilds it)

- `anatomy.py`, `anatomy.out`: failure anatomy of the recorded runs
- `ceiling.py`, `ceiling.json`: table ceilings per input (tables included)
- `ambiguity.py`, `ambiguity.out`: per-key gap rates
- `refix_v2.py`, `refix_v2.json`: v2 threshold re-fix, floors, table through the brain

Run each with `PYTHONPATH=. uv run python <script>` from the repo root. Total time about 8 minutes, stand-in brain only.
