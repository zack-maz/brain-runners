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
