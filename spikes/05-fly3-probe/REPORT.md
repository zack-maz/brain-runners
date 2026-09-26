# Spike 05: the fly3 probe (2026-09-25, throwaway)

Question (decision 45, `docs/superpowers/specs/2026-09-25-fly3-design.md`, "Order and gates → 1. The probe"): can
every LPLC2/LC4 cell get its own place on the eye (part A); do the brain's descending neurons (DNs) then know where a
single gap is (part B); and does a readout learned by imitating the solver play at least as well as the same learner
without the brain, and clearly better than the same readout on a blind brain (part C)?

## Rules fixed before measuring

Written and committed before any brain measurement and before the part A numbers were computed. Measurements do not
change these rules; a rule that proves unworkable is reported as such and that part stops.

### Part A: a place on the eye for every cell

- **A1, positions.** FlyWire `pos_x, pos_y, pos_z` of the annotations (x, y in 4 nm voxels, z in 40 nm slices) in µm.
  A cell's centre in its **own frame** is the synapse-weighted mean position of its presynaptic partners among the
  columnar types (types with at least 300 cells on that side), as spike 03's `order.py`. The model's connectivity
  (`Connectivity_783.parquet`) gives the synapse counts.
- **A2, which way is forward and up (the fly's, by a published rule).** Klapoetke et al. 2017 (Nature 551:237):
  LPLC2's dendrite in each lobula-plate layer extends outward along that layer's preferred motion: layer 1 (T4a, T5a;
  front-to-back) posteriorly, layer 2 (T4b, T5b; back-to-front) anteriorly, layer 3 (T4c, T5c; upward) dorsally,
  layer 4 (T4d, T5d; downward) ventrally. For each LPLC2 cell: `v_post` = centre of its T4a+T5a inputs − centre of its
  T4b+T5b inputs, minus the same difference for the whole populations of that side (the layers' depth offset);
  `v_dors` likewise from c − d. The eye's posterior direction P and dorsal direction D are the means over the eye's
  LPLC2 cells, projected onto the plane of the top two principal axes of those cells' own-frame centres.
  **Accepted** if, per eye, at least 70% of the cells' `v_post` have a positive component along P, at least 70% of
  their `v_dors` along D, and the angle between P and D in the plane is 45°–135°. Then a cell's normalised
  coordinates are `u` = −(its centre · P̂) (anterior positive) and `v` = its centre · D̂′ (D orthogonalised to P̂;
  dorsal positive). **If not accepted, the orientation is ours:** v along −y (FAFB y points ventrally), u along the
  in-plane axis orthogonal to it, with anterior toward −z; labelled ours.
- **A3, LC4 in the same coordinates.** LC4 has no lobula-plate input, so no layer cue. Its **shared frame** is the
  centre over its inputs of types T2, T2a, Tm2, Tm3, Tm4, TmY3 (LC4's main columnar types). The same shared-frame
  centre is computed for every LPLC2 cell with at least 20 synapses from those types; a linear least-squares map
  (3 coordinates + 1 → u, v) is fitted per eye on LPLC2 and applied to LC4. **Accepted** if R² ≥ 0.5 for u and for v
  in both eyes. **If not**, LC4's (u, v) are its own-frame centre's two principal axes, signed by the largest
  correlation with −y (dorsal) and −z (anterior); labelled ours.
- **A4, degrees (ours).** Per eye, over its LPLC2 + LC4 cells: u's 2.5th → 97.5th percentile maps linearly to
  azimuth −10° → +160° away from the midline (negative: 10° into the other eye's half, binocular overlap) and v's
  2.5th → 97.5th percentile to elevation −60° → +60°. Game azimuth: the right eye's cells at +azimuth, the left eye's
  at −azimuth.
- **A5, stop rule.** For each eye and each axis (u, v): distinguishable positions n = (P95 − P5 of the cells'
  coordinate) / (2 × the median over cells of the coordinate's bootstrap SE), the SE from 200 resamples of each cell's
  input partners (with their synapse counts), the linear maps of A2–A4 held fixed. **fly3 stops (DONE `stop A`) if
  n < 3 for any eye and axis.** The number of non-overlapping fields, (P95 − P5 in degrees) / (2σ) with σ of R2, is
  reported beside it, for information only.

### The retina (all ours)

- **R1, tiles on the eye.** The runner's eye is 1 tile above the floor, looking along the track. Visible tile
  (lane offset o ∈ −3…3, row r ∈ 1…6) sits at azimuth atan2(o, r) (right positive), elevation −atan2(1, r) (row 1
  −45.0°, row 2 −26.6°, row 3 −18.4°, row 4 −14.0°, row 5 −11.3°, row 6 −9.5°), and subtends an angular radius
  ρ = atan(0.5 / √(o² + r² + 1)) (looming: nearer is bigger).
- **R2, coverage.** A cell's field is a Gaussian of angular distance with σ = 20° for LPLC2 and 15° for LC4 (receptive
  fields of about 60° and 40°; Klapoetke 2017, von Reyn 2017). A gap is a Gaussian blob of sd s = ρ/2. Its coverage
  of a cell is s²/(s² + σ²) · exp(−d² / (2(s² + σ²))), d the great-circle angle between the gap's and the field's
  centres. A cell's rate = min(500 Hz, gain × the sum of coverages over the visible gaps).
- **R3, gains** (Hz per unit coverage): 500, 1000, 2000, 4000. (A row-1 centre gap covers an LPLC2 field centred on
  it about 0.2, so these give about 100, 200, 400, 500 Hz to the best-placed cell.)

### Part B: does the output know where a gap is?

- **B1, stimuli.** 42 single-gap conditions (one tile a gap, every other visible tile floor) and one blank, 8 noise
  repeats each, at each of the four gains: 43 × 8 × 4 = 1,376 windows of 100 ms. Noise seed = 50,000 + 10,000 × gain
  index + 100 × condition index + repeat.
- **B2, recorded.** The spike count of every DN (annotations `super_class == "descending"`, those in the model) in
  0–100 ms, 0–50 ms and 50–100 ms; the spike count of every input cell; the input rates themselves.
- **B3, readout.** Multinomial logistic regression in NumPy: features log1p(count) standardised by the training
  data's mean and sd (a feature with sd 0 is dropped), mean cross-entropy + λ/2 ‖W‖² (bias unpenalised), weights from
  zero, accelerated proximal gradient (FISTA), up to 3,000 iterations. λ from {0.001, 0.01, 0.1, 1} by inner
  leave-one-repeat-out CV on the training repeats (best mean accuracy, ties within 0.005 to the larger λ). **Outer CV:
  4 folds, fold k holds out repeats 2k and 2k+1 of every condition**, so no repeat is ever in both training and test.
  Accuracy = fraction of held-out single windows classified right; reported as mean and SD over the 4 folds. Lane: 7
  classes (chance 1/7 = 0.143); row: 6 classes (chance 0.167). The blank is not in the fits.
- **B4, feature sets.** DN whole window (one count per DN), DN halves (two per DN), input rates (the no-brain
  control's features; noise-free), input cells' spike counts (noisy; for information).
- **B5, the gain.** The gain with the highest DN whole-window lane accuracy; ties within 0.01 to the lower gain.
- **B6, early/late.** At the chosen gain, the halves are kept only if their lane accuracy exceeds the whole window's
  by more than the larger of the two fold SDs.
- **B7, averaging.** At the chosen gain and window features, the readout trained on single windows is tested on the
  held-out repeats as single windows (a) and as the mean of the two held-out repeats' counts per condition (b).
  **Two windows per decision are adopted only if lane accuracy (b) − (a) ≥ 0.10.**
- **B8, pass.** DN lane accuracy (chosen gain and features, single windows) ≥ 0.30 **and** (accuracy − 1/7) > 3 ×
  its fold SD. Otherwise DONE `stop B`.

### Part C: a small play test

- **C1, seeds.** Game v2. DAgger on practice tracks 1000–1019; every play test on 1300–1309. Brain noise seed per
  decision = crc32(`"fly3probe:{phase}:{track seed}:{row}"`), phase naming the round or play.
- **C2, a decision.** Visible tiles → retina rates at the chosen gain → one 100 ms window (two if B7 adopted) → DN
  features (whole or halves by B6), log1p and standardised with the training mean/sd → readout → the most probable
  move (deterministic).
- **C3, scoring a play.** The readout plays until its first death; the score is the game's rows survived.
- **C4, DAgger.** Round 0 executes the solver's move (`solve`) on every row. In round k ≥ 1 the current readout
  chooses; where its move would die, the solver's move is executed instead (a rescue) and the readout plays on to row
  150. Every row reached is recorded with its features and `solve_depths`. After each round the readout is refitted
  on everything recorded so far. Rounds 1 and 2 follow round 0 (round 2 is dropped, and the report says so, if the
  measured time per decision would take the probe past 3 hours of brain time).
- **C5, labels.** Safe set S = the moves whose depth equals the row's maximum depth. Single target = the solver's
  move (the first maximum in the order stay, left, right, jump). A row is critical when some move has depth 0 and
  another does not; critical rows weigh w, the others 1.
- **C6, loss.** Set target: −Σ ω_i log Σ_{a ∈ S_i} p_i(a) / Σ ω_i. Single target: −Σ ω_i log p_i(y_i) / Σ ω_i. Plus
  λ1 ‖W‖₁ + λ2/2 ‖W‖² (bias unpenalised); weights from zero; FISTA up to 3,000 iterations.
- **C7, penalties.** Grid λ2 ∈ {0.001, 0.01, 0.1} × λ1 ∈ {0, 0.001, 0.01}. At every fit, the penalty is chosen by
  5-fold CV grouped by track (4 tracks per fold) on the recording being fitted: score = the weighted fraction of
  rows whose most probable move is in S. Best mean score; ties within 0.005 to the stronger penalty (larger λ1, then
  larger λ2).
- **C8, the variant.** Round 0's recording is fitted six ways: target ∈ {set, single} × w ∈ {1, 3, 10}. Each plays
  1300–1309 (C3). The best mean rows wins; a variant within 1.0 row of a simpler one loses to it, simplicity in the
  order (set, 1), (single, 1), (set, 3), (single, 3), (set, 10), (single, 10). The winner is used in rounds 1–2.
- **C9, no brain.** The same code, variant and rounds, on the 314 input rates as features (no brain; its own
  readout plays its own rounds 1–2; its own penalties by C7). Plays 1300–1309.
- **C10, blind brain.** fly3's final readout on windows with every input rate 0 (same brain, same noise seeds).
  Plays 1300–1309.
- **C11, pass.** mean rows(fly3) ≥ mean rows(no brain) **and** mean rows(blind) ≤ mean rows(fly3) − max(10, 2 × the
  standard error of the per-track difference fly3 − blind). Otherwise DONE `stop C`.
- **C12, reported.** Seconds per decision (wall clock of the window alone and of the whole decision); DNs that fire;
  the readout's largest weights by DN type (sum of |W| over the four moves per DN, top 20, and the ranks of DNa02,
  DNa01, DNg13 and DNp01 (the Giant Fiber)); how often each move is chosen in every play (a readout that plays
  "a clock" chooses the same moves whatever it sees).

## What was done

### Data sources

- The project's fly data, unchanged (`bakeoff/fly/data.py`): FlyWire v783 model `philshiu/Drosophila_brain_model`
  @ `91bdd1e7`, annotations `flyconnectome/flywire_annotations` @ `17fc5772` (sha256 in `data.py`).
- Fetched: `https://github.com/flyconnectome/ol_annotations` @ `11a4c97980a08e726733e115f553faf8c7023044`
  (2025-02-19), cloned to `data/ol_annotations/`. **It holds no column map**: its data is a cell-type matching table
  between FlyWire and the male optic lobe (`data/olmatching.tsv`, 727 rows). Matsliah et al.'s own repository,
  `murthylab/visual-system-parts-list` @ `0d8574d46627ce7fadd968a3c5d602e837325373`, was inspected through the GitHub
  API (not downloaded): neuron and synapse tables, no column assignment either. Codex's download of the column
  assignment (`codex.flywire.ai/api/download?data_product=column_assignment`) answers with a login page. So the
  column map was not used; the orientation came from the wiring itself (A2), which is the fly's.
- Recordings (not committed, git-ignored): `data/spike05/partB_*.npz`, `data/spike05/partC/*.npz`, logs
  `data/spike05_partB.log`, `data/spike05_partC.log` (`data/` is the main checkout's data directory).

### Part A (`fields.py`, `fields.json`): passes

| eye | cells placed | layer test: posterior agree / dorsal agree / angle | LC4 map R² u / v | spread P5–P95 az / el | median SE az / el | distinguishable positions az / el | fields side by side az / el (info) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| left | 108 LPLC2 + 54 LC4 | 0.79 / 1.00 / 84° | 0.96 / 0.99 | 156° / 110° | 3.2° / 1.1° | **24 / 52** | 3.9 / 2.8 |
| right | 102 LPLC2 + 50 LC4 | 0.94 / 1.00 / 90° | 0.95 / 0.99 | 162° / 114° | 3.5° / 1.0° | **23 / 55** | 4.1 / 2.8 |

- **The orientation is the fly's, by the layer rule, in both eyes.** Every LPLC2 cell's layer-3 inputs sit dorsal
  of its layer-4 inputs; 79% and 94% of cells put layer 1 posterior of layer 2; the two directions are 84° and 90°
  apart. Two independent checks agree: the dorsal direction found this way points along −y (FAFB's y points
  ventrally; −0.89 and −0.93), and the two eyes' directions mirror each other in x (posterior x +0.73 left, −0.85
  right; y and z alike). The rule's fall-back (anterior toward −z) would have been wrong: the posterior direction has
  z −0.54 and −0.38, so the lobula plate's map is tilted against the brain's axes.
- LC4 is placed through its columnar inputs (T2, T2a, Tm2, Tm3, Tm4, TmY3), with a map fitted on LPLC2 cells' own
  inputs from the same types; the map explains 95–99% of the LPLC2 coordinates.
- About 29 (left) and 36 (right) cells lie in the frontal-lower field where the tiles are (|azimuth| < 80°,
  elevation < 0). A row-1 gap covers some field by 0.08–0.29, a row-6 gap by 0.015–0.022 (looming), and 2 to 52
  cells get a coverage above 0.01 per tile.

### Part B (`record_b.py`, `analyze_b.py`, `partB.json`): passes

1,299 of the 1,303 annotated DNs are in the model. 1,376 windows, 0.58–0.62 s each on this Mac (brain built in
29 s). No DN fires on the blank at any gain. Accuracy is mean ± SD over the 4 folds; lane chance 0.143, row 0.167.

| gain | best-placed cell (Hz) | DNs that fire at all | in half the windows | DN spikes / window | DN lane | DN lane, halves | DN row | no brain (input rates) lane / row | input cells' spikes lane / row |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500 | 145 | 24 | 0 | 2.2 | 0.244 ± 0.030 | 0.226 ± 0.047 | 0.351 ± 0.039 | 1.000 / 1.000 | 0.622 / 0.598 |
| 1000 | 289 | 54 | 0 | 6.9 | 0.360 ± 0.046 | 0.342 ± 0.046 | 0.527 ± 0.018 | 1.000 / 1.000 | 0.726 / 0.646 |
| 2000 | 500 | 80 | 2 | 20.7 | 0.524 ± 0.031 | 0.485 ± 0.030 | 0.702 ± 0.010 | 1.000 / 1.000 | 0.771 / 0.667 |
| **4000** | 500 | 144 | 15 | 52.4 | **0.795 ± 0.018** | 0.732 ± 0.044 | 0.732 ± 0.057 | 1.000 / 1.000 | 0.812 / 0.679 |

- **B5, gain: 4000** (best DN lane accuracy). It is the top of the grid, and accuracy was still rising, so a higher
  gain might do better still; the rule did not allow measuring one. At 4000, most tiles' best cells sit at the
  500 Hz cap.
- **B6, halves: not kept.** They are *worse* than the whole window (0.732 against 0.795; the difference, −0.06, is
  below zero, let alone above the spread 0.044).
- **B7, averaging: not adopted.** The mean of two windows scores 0.833 ± 0.019 against 0.795 for one: +0.039, below
  the 0.10 threshold. One window per decision.
- **B8, pass:** 0.795 ≥ 0.30, and 0.795 − 0.143 = 0.65 is 36 fold SDs.
- **What this says about "the brain helps".** The noise-free input rates predict both lane and row perfectly (they
  are a deterministic function of the tile). The fairer comparison, the input cells' own Poisson spikes in the same
  window, gives 0.81 lane, the DNs 0.80: **the DNs keep nearly all of the "where" that the noisy input carries, and
  add none.** For row, the DNs (0.73) are a little better than the input spikes (0.68). The DNs are a lossless-ish,
  not a richer, recoding of the input here. Only 144 of 1,299 DNs fire at all even at the highest gain, and 15 fire
  in at least half the windows.

### Part C (`play_c.py`, `partC.json`): stops

Gain 4000, the whole window, one window per decision (as part B chose). 0.52 s per decision on this Mac, the window
being nearly all of it (0.521 of 0.522 s). Part C used 126 minutes of brain time (136 minutes wall clock, fits
included); part B 14. Round 2 fitted under the 3-hour rule, so both later rounds ran.

**Round 0's six variants** (fitted on the solver's path over 1000–1019, 2,923 rows; each played 1300–1309 until its
first death):

| variant | penalty λ1 / λ2 | CV score | DNs with weight | mean rows | rows per track | moves stay / left / right / jump |
| --- | --- | --- | --- | --- | --- | --- |
| set, w 1 | 0.01 / 0.01 | 0.962 | 35 | 82.7 | 87 60 83 100 76 114 84 54 58 111 | 0 / 214 / 569 / 27 |
| single, w 1 | 0.001 / 0.001 | 0.907 | 149 | 36.7 | 29 49 36 49 33 32 43 48 12 36 | 366 / 8 / 3 / 0 |
| **set, w 3** | 0.01 / 0.1 | 0.943 | 78 | **87.2** | 87 110 83 100 91 114 84 103 58 42 | 0 / 259 / 575 / 24 |
| single, w 3 | 0.001 / 0.001 | 0.855 | 160 | 49.0 | 29 44 64 33 25 38 43 99 79 36 | 467 / 22 / 11 / 0 |
| set, w 10 | 0.01 / 0.01 | 0.934 | 51 | 82.8 | 31 84 68 100 91 114 84 133 75 48 | 0 / 468 / 320 / 25 |
| single, w 10 | 0.001 / 0.001 | 0.825 | 162 | 50.5 | 56 84 36 33 33 70 43 35 79 36 | 478 / 25 / 10 / 1 |

**Winner: set target, w 3** (87.2; 4.5 rows ahead of the simpler set, w 1, more than the 1-row tie margin). The
single-move target is far worse at every weight. It learns "stay" (the solver's first choice in a tie) and dodges
too rarely. The set target never punishes a safe alternative and learns to dodge.

**DAgger** (rows until the first rescue on 1000–1019; the readout plays on after each rescue):

| round | fly3 mean | fly3 rescues | fly3 penalty λ1 / λ2, DNs with weight | no brain mean | no brain rescues | no-brain penalty |
| --- | --- | --- | --- | --- | --- | --- |
| 0 (solver's path) | — | — | 0.01 / 0.1, 78 | — | — | 0 / 0.001 |
| 1 | 75.3 | 57 | 0.01 / 0.01, 35 | 110.7 | 24 | 0 / 0.001 |
| 2 | 92.8 | 50 | 0.01 / 0.001, 23 | 129.7 | 14 | 0 / 0.001 |

**Final plays on 1300–1309** (until the first death):

| player | rows per track | mean | moves stay / left / right / jump |
| --- | --- | --- | --- |
| fly3 (DNs, after round 2) | 87 110 69 101 91 114 84 103 58 48 | **86.5** | 0 / 210 / 607 / 29 |
| no brain (input rates, same learner and rounds) | 87 123 105 101 102 150 83 150 74 150 | **112.5** | 271 / 231 / 343 / 144 |
| blind brain (fly3's readout, input off) | 31 8 20 6 9 21 42 35 12 12 | **19.6** | 0 / 0 / 206 / 0 |

- **C11: fly3 fails the gate.** It is 26.0 rows behind no brain (SE 10.0 over the paired tracks; behind on 7 of 10
  tracks, level on 2, ahead on 1 by one row). The blind half of the gate holds: blind is 66.9 rows below fly3, far
  past the 15.5 needed (2 × SE 7.7).
- **Not a clock.** The blind brain's DNs are silent (no DN fires without input, as in part B), so its readout
  answers every row the same, "right", and dies in 6 to 42 rows. fly3's moves follow what it sees. But the same fact
  shows a flaw: a row whose gaps are too far or too few to make any DN fire looks exactly like no input, and fly3
  then goes right. fly3 never chose "stay" in any play. No brain stays 271 times.
- DAgger helped fly3 (75.3 → 92.8 rows before a rescue on the training tracks) but its final play on 1300–1309
  (86.5) is within a row of round 0's winner (87.2). No brain gained more from the same rounds (110.7 → 129.7).
- **The readout's largest weights** (sum of |W| over the four moves, standardised features), 23 DNs with any
  weight: DNpe025 right 0.90, DNp71 left 0.65, DNp13 left 0.56, DNge054 right 0.37, **DNa01 left 0.32 (rank 5)**,
  DNp31 right 0.30, DNa05 left 0.27, DNbe006 right 0.23, DNge124 right 0.15, DNa05 right 0.15, DNa13 right 0.14,
  DNp57 left 0.14, DNb09 left 0.12, then DNge124 left, DNp02 left, DNp55 left, DNpe040 left, DNb09 right, DNae007
  left, DNpe040 right. **DNa02, DNg13 and DNp01 (the Giant Fiber) get no weight.** The readout found its own
  steering and looming DNs (DNp02, DNp71, DNa05, DNb09, DNa13), not the hand-picked ones of fly and fly2. The one
  overlap is DNa01.

## Findings

1. **The eye map is the fly's, not ours (part A).** LPLC2's layered lobula-plate inputs fix which way is forward and
   up in both eyes, cross-checked by FAFB's dorsal axis and by the eyes' mirror symmetry. Every one of the 314 cells
   has a centre with about 3° of uncertainty. What stays ours is the scale in degrees, the field widths and the
   retina.
2. **The DNs do carry "where" (part B)**, unlike fly's and fly2's summed readouts (spike 03). At the highest gain a
   linear readout names a single gap's lane 80% of the time and its row 73% (chances 14% and 17%). But they carry
   **no more than the input's own spikes do** (81% and 68%). Only 144 of 1,299 DNs fire even at the strongest input,
   and none fire at weak inputs or with nothing in view.
3. **As a layer of features for a learner, the brain is worse than no brain (part C):** 86.5 against 112.5 mean rows,
   with the same learner, the same imitation and the same rounds. It is not a clock (blind brain 19.6), so the brain
   passes what it sees. But it passes less of it than the input holds: faint, far and sparse gaps make no DN spike,
   and a row with nothing firing is read as a blind one.
4. Of the numbers the probe fixed, the "any safe move" target matters most (the single-move target halves the rows).
   The critical-row weight matters little. Halves and averaging were not worth their cost. The gain was the top of
   its grid and was still helping.

## What is ours

The degree scale of the eye (A4), the field shapes and widths, the whole retina (tile placement, looming, gain,
the 500 Hz cap), the readout, its penalties and features, the imitation of the solver with DAgger and rescues, and
every threshold in the rules above. The fly's: the wiring and the model, the cells that receive input, the DNs that
are read, and each cell's place on the eye with its orientation.

## Recommendation

**Stop fly3** (DONE `stop C`). With the same learner, the untrained wiring is a worse layer of features than the
input it is given. That is the honest answer to decision 45's question ("does the fly's wiring help a learner
play?") for this game at these settings: no. The write-up can say so with controls: fly3 86.5, no brain 112.5, blind
brain 19.6, all on 1300–1309. fly3 stays off the page, as the spec already requires when it does not beat no brain.

If the user wants one more look before closing it, the one lever the rules left untested is a stronger input. DN lane
accuracy climbed 0.24 → 0.36 → 0.52 → 0.80 over the gain grid, and the missing-DN-spikes problem is a weak-input
problem. A second probe could extend the gain grid (8000, 16000, with the cap raised) and replay only part C's final
three plays. That is about 30 minutes of brain time plus retraining (about 1.5 hours). It should be judged against
the same no-brain bar (112.5), which does not move. The shuffled-wiring control was never reached. It matters only if
fly3 ever beats no brain.

**The engine question.** Measured: 0.52 s per decision, nearly all of it in the 100 ms Brian2 window. The full
build (five rounds of 20 tracks for fly3 and for the shuffled control, three evaluations of 100 tracks) is about
15,000 + 15,000 + 3 × 12,000 decisions, about 66,000 × 0.52 s ≈ 9.5 hours. That is an overnight run on Brian2,
acceptable, and needs no fast engine. The spec's estimate (about 8 hours at 0.5 s) holds. It is moot while fly3 stops.
