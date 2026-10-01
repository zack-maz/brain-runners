# Innate fly circuits for a gap-avoiding runner (track 1, the pure fly)

Research brief `brief-circuits.md`, 2026-09-24. Static analysis only: no Brian2 model was built, no paid call made,
no tracked file touched. Scratch scripts and raw outputs: `scratch-circuits/` in this directory.

## Summary (10 lines)

1. **Why the fly dies is in our input map, not only in the brain.** A row-1 gap in the fly's own lane counts to both eyes at full gain, so both eyes hit the 250 Hz cap. Side gaps in row 1 are then invisible, and row 2 (the landing tile) adds at most one 25 Hz level (`calibration/response_surface.json`, table B1). The Giant Fiber (GF) only crosses 200 Hz in that saturated corner, so the fly jumps with no way of seeing where it lands.
2. **Nothing in the innate visual wiring can veto a jump.** Screening every visual projection type (VPN), the strongest GF inhibitor over 1–3 hops is LC18 at −1.5, against +59 for LPLC2 and +42 for LC4 (table B6). A "far gap inhibits the jump" design has no innate substrate.
3. **The biology of crossing a gap is climbing, not jumping.** Flies judge gap width from the parallax of the far edge (Pick & Strauss 2005), with C2/C3 cells and the protocerebral bridge (Triphan 2010, 2016). Ventral looming drives the GF weakly (Dombrovski 2023). Our "jump" is ours, and the page should say so.
4. **Our steering readout has a known flaw.** DNb01's axon crosses the midline and has no reported walking-steering role. DNa02 is the best-established walking-steering DN (Rayshubskiy 2025; Yang 2024), with DNa01 and DNg13 as partners.
5. **Our looming cells feed other DNs first.** LPLC2 and LC4 synapse directly onto DNp04, DNp01, DNp02, DNp11, DNp06, DNp35 and DNp03 (the takeoff DNs). DNa01, DNa02 and DNb01 sit 2–3 hops away.
6. **A second lateral pathway exists.** LPLC4/LC22 → DNb05 (2,077 synapses, direct), DNp03, DNa04, DNa15, DNa10 and DNae002 is a lateral-looming → steering route that does not touch the GF. LC10d → DNa10 (247 synapses) is an object-avoidance route (Ribeiro 2026).
7. **Some literature pathways are absent from the brain wiring.** LC16 → MDN (Sen 2017) does not appear in the brain connectome within 3 hops. LC9 → DNp09 (forward walking, 385–470 synapses) and LPC1 −| DNp09 (translational flow) do.
8. **Ranked designs** (section A):
   - (1) an unsaturated two-channel input, a DNa02-based turn and dodge-before-jump;
   - (2) a far-edge check before a jump (heavily ours);
   - (3) a lateral LPLC4/LC22/LC10d steering channel;
   - (4) state carried between decisions;
   - (5) steering toward the floor through approach channels;
   - (6) photoreceptor-level input.
9. **What running without reset gives.** It is defensible, but the Shiu LIF model has τ_m 20 ms, no adaptation and no plasticity, so it buys only latency and reverberation, not memory. Expect a small effect.
10. **Every design needs a probe first.** Designs 1, 3 and 5 each need a short Brian2 probe (one fly process), then thresholds fixed on v2 seeds ≥ 1000 by a rule written beforehand.

Sources for numbers:
- **"Shiu"** = the model's own `Connectivity_783.parquet`: signed synapse counts, each divided by the postsynaptic cell's total input. This is ground truth for what the simulation will do.
- **"FlyWire tool"** = the user's viewer project `~/Documents/PROJECTS/LEARN/flywire/motg-flywire`, read-only: `fafb_783_split_edgelist.feather` (compartments), `neuron_neuropil_counts.parquet`, `flow_rank.bin`, `groupings.*`.
- **"surface"** = `calibration/response_surface.json` (8 trials per cell, 100 ms, real brain, measured at phase 2).

---

## (A) Ranked pure-fly designs

Common rules for every design:
- Input neurons are driven with Poisson rates exactly as now (`bakeoff/fly/brain.py`).
- A new readout or rule is ours and labelled on the page.
- Thresholds are fixed on v2 practice seeds ≥ 1000 (never below) by a rule written down before the run, e.g. "grid-search the thresholds on seeds 1000–1049, maximise mean rows, report on 1050–1099".
- The bar to beat is `fly` at a mean of 68 of 150 rows on v2 seeds 1000–1004. All its deaths were jumps into a gap.

### Design 1 (recommended first): unsaturated input, the fly's walking-steering DNs, dodge before jump

**Input (ours).** Two changes to `looming_rates`:
- **Stop counting the runner's own lane twice at full gain.** Either split offset-0 gaps half to each eye, or keep them bilateral but lift `MAX_HZ` so a side gap still adds on top of a centre gap (for example a 500 Hz cap with 21 levels).
- **Optionally send own-lane gaps to LPLC2 only and side gaps to LC4 only.** LPLC2 carries angular size and so the "it is right in front of me" part; LC4 carries angular velocity (Ache 2019). Both still feed the GF, so this change is secondary.

**Readout (ours, grounded in biology):**
- **Turn** = (DNa02 + DNa01 + DNg13)_right − (…)_left, each read on its soma side. All three turn the fly toward their own side:
  - DNa02: activation tested (Rayshubskiy 2025).
  - DNa01 and DNg13: correlation only (Yang 2024; Cheong 2026).
- **Drop DNb01.** Its axon crosses and it has no walking role (FBbt:00047582; the Cande 2018 line was later reassigned to DNb09).
- **Jump** = GF (DNp01) mean.
- **Rule: dodge before jump.** If |turn| > T_turn, turn. Else if GF > T_jump, jump. Else stay. Today it is the other way round: jump wins.

**What is biology.**
- Looming on one eye drives the opposite DNa02/DNa01 (spike 01; surface table B1: DNa02 R−L is positive for a left-eye threat).
- Card & Dickinson 2008: before a takeoff, flies adjust posture to move away from the threat, so a directional plan comes first.

**Why it could beat 68.**
- Today a centre gap saturates both eyes, so turn ≈ 0 and GF ≈ 214 Hz: the fly always jumps, even when a sidestep is safe.
- With the cap lifted, "centre gap plus a gap on the left" differs from "centre gap only". The steering DNs can then pick the free side, and a jump happens only when both sides look equally bad.
- This removes exactly the deaths we see (jumps into gaps) whenever a sidestep was open.

**Main risks.**
1. **DNa02 cancels at high input.** Table B1: its R−L is 0 whenever both eyes are ≥ 125 Hz; the see-saw inhibition in Rayshubskiy 2025 is the likely cause. At the rates a centre gap produces, the asymmetry may vanish.
   - Probe first: measure a new response surface with the lifted cap. It is about 20 minutes, one fly process.
   - Fall-back: keep DNa01, which stays asymmetric in the surface.
2. **Dodging can land on a side-lane gap in row 1.** That gap is exactly what the fly now sees, so this should be rarer, but it is the new death mode to watch.
3. **Part of the gain comes from our rule.** The write-up must say that the priority order (dodge before jump) is ours.

**Evidence:**
- Surface table B1.
- Tables B2 and B3: DNa02 is 1 hop from HSS and 2 hops from LPLC2.
- Rayshubskiy et al. 2025; Yang et al. 2024; Cheong et al. 2026; Card & Dickinson 2008; Ache et al. 2019.

### Design 2: a far-edge check before a jump (Pick & Strauss analogue; heavily ours)

**Input.** Normal window as in Design 1. When the rule would jump, run a second 100 ms window from the clean state showing the view the fly would have after the jump: rows shifted by two, so the landing row becomes row 1.

**Readout and rule (ours).** Veto the jump when that second glance itself saturates both eyes (GF over threshold, i.e. the landing tile is a gap). After a veto, take the better of left/right from the first window's turn sign.

**What is biology.**
- Flies cross a gap only after judging the far side: parallax of far-side edges; 0 of 152 approaches climbed when there was no far side (Pick & Strauss 2005; Triphan 2016, count from a snippet, unverified).
- There is a ~200 ms preparatory phase before takeoff (Card & Dickinson 2008).

**What is ours:** the second glance, which is a simulated future view, and the veto. The honest label is "we show the fly the far side before it commits".

**Why it could beat 68.** It targets the only v2 death cause directly.

**Main risks.**
1. Most of the intelligence is then in our loop, and the brain acts as a 1-bit detector. The write-up must not present this as the fly's planning. Recommend it only as a clearly labelled variant (`fly_look`), not as the pure fly.
2. It doubles the simulation time per jump decision (~0.6 s each).

### Design 3: a lateral steering channel that does not touch the GF (LPLC4/LC22, LC10d)

**Input (ours).**
- Own-lane gaps → LPLC2 + LC4 on both eyes (looming → escape pathway).
- Side gaps → the LPLC4 + LC22 cells of that eye (lateral pathway). Or LC10d instead, an object-avoidance pathway (Ribeiro 2026).

**Readout.**
- Turn from DNa02/DNa01/DNg13 as in Design 1, plus DNa10 (the target of LC10d) and DNb05 (the target of LPLC4; turns toward its own side, Yang 2024). The signs must be measured, not assumed.
- Jump from the GF, which this channel hardly drives (LPLC4 → GF −0.6, LC22 −0.3, LC10d −0.2 in the Shiu influence).

**What is biology.**
- LPLC4 and LC22 are lobula looming/motion VPNs with the densest DN output of any VPN type (Namiki 2018: they feed about eight DNs each).
- DNp03, a direct target of LPLC1, LPLC4, LC22 and LC4, is a flight-saccade DN (Current Biology 2024, DNp03).
- LC10d → DNa10 mediates avoidance of visual objects (Ribeiro 2026, bioRxiv).

**What is ours:** routing side gaps to these cell types. They respond to lateral looming or motion of objects, not specifically to floor holes. No floor-hole detector is known in flies.

**Why it could beat 68.** Dodging and jumping are separated at the input, so a side gap never triggers a jump. The GF fires only for own-lane gaps.

**Main risk: unknown steering sign.**
- In the Shiu influence, left-eye LPLC4 drives DNb05 on the same side (+156, which turns toward the gap), DNa01 on the far side (+3.8, which turns away) and DNa10 on the same side (+20, walking sign unknown).
- The net turn could point toward the gap. A probe (drive one eye's LPLC4+LC22, or LC10d, read all candidate steering DNs) must settle the sign before any play.
- If the net turn points toward the gap, reading it as "away" would be our relabelling, which decision 2 forbids.

### Design 4: carry state between decisions (run continuously)

**What changes.** Run the network continuously and change the Poisson rates each row, instead of restoring the clean state. Keep Design 1's readout.

**What is biology.**
- A real fly is never reset.
- Defensive state persists and scales with repeated threat (Gibson 2015). The prior brain state decides freeze, flee or no response (Zacarias 2018; Zucker-Scharff 2026).
- Heading and goal circuits integrate over time (Seelig & Jayaraman 2015; PFL3 → DNa02, Westeinde 2024).

**Caveat: the model barely remembers.**
- The Shiu LIF model has τ_m = 20 ms, synaptic τ = 5 ms, a 0 Hz baseline and no adaptation, neuromodulation or plasticity (Shiu 2024; `model.py`).
- The only carry-over is reverberation in recurrent loops. Minute-scale arousal is not modelled, and any leaky variable we add is ours.

**Why it could help.**
- The first GF spike takes 5 ms and the first DNb01 spike 34 ms (spike 01), so a warm network responds earlier within the window.
- A recently seen side gap may leave residual steering bias, which could keep the fly from stepping back into it.

**Main risks.**
- Runaway or oscillating activity, since the model has no homeostasis.
- Per-row repeatability: seed the Poisson input per run, not per row.
- Cost is the same (spike 01: 0.52–0.65 s per 100 ms continuous).
- Test it as a switch on top of Design 1, not alone.

### Design 5: steer toward the floor through approach channels (LC9 → DNp09, LC10a → DNa02)

**Input (ours).** Present *safe* tiles (floor) near the runner as objects to the approach VPNs of that eye: LC9 and/or LC10a, strongest for row 1.

**Readout.**
- DNp09 asymmetry: forward walking and turning toward its own side (Bidaye 2020).
- DNa02 asymmetry: LC10a → DNa02 on the same side is +10.9, 2 hops through AOTU/CB0359.

**What is biology.**
- LC9 → DNp09 is a strong direct pathway (385–470 synapses; FlyWire tool 470 on the same side).
- LC10 drives turning toward objects (Wu 2016; Hindmarsh Sten 2021; Cowley 2024).

**What is ours:** calling floor an "object". This is a larger relabelling than calling a gap a loom, and LC10a's pursuit role is best known in courting males.

**Why it could help.** It replaces "flee from every gap" with "go to where there is floor". This can resolve the symmetric centre-gap case when only one side is open.

**Main risks.**
- DNp09 also drives freezing (Zacarias 2018).
- LC9 input also drives DNp11, a takeoff DN (+65), which may mean the jump readout needs rethinking.
- The weakest honesty story of the five.

### Design 6 (long shot): photoreceptor-level input

**Input.** Render the floor (column luminance) into R1-6/R7/R8, which are in the model (about 3,900–4,000 R1-6 per side), and let the model's own optic lobe (T4/T5, C2/C3, LC/LPLC) do the rest.

**Why rank it last.**
- The Shiu model was never validated for vision. The real optic lobe is largely graded and non-spiking, which is why flyvis exists (Lappalainen 2024).
- Retinotopy spike 03 changed only strength.
- The path is ≥ 7 flow steps from the sensory neurons (FlyWire tool).
- It is the right direction for the trained track 2 (flyvis front end, as Eon Systems 2026 did), not for the pure fly.

### Recommended order

1. Run the Design 1 probe: a new response surface with the lifted cap, recording DNa02, DNa01, DNg13 and GF.
2. If DNa01/DNa02 stay asymmetric at centre-gap rates, build Design 1 and fix its two thresholds on seeds ≥ 1000.
3. Probe Design 3's sign (≈10 minutes).
4. Test Design 4 as a switch.
5. Keep Design 2 as a labelled variant only.

---

## (B) Pathway analysis

### B0. Cell types present (annotated / in the Shiu model, left and right)

All candidate types are fully present in the model, except for a few hundred photoreceptors.

| inputs | left | right | outputs | left | right |
|---|---|---|---|---|---|
| LPLC2 | 108/108 | 102/102 | DNp01 (GF) | 1/1 | 1/1 |
| LC4 | 54/54 | 50/50 | DNp02, DNp04, DNp11, DNp06, DNp03, DNp05 | 1/1 each | 1/1 each |
| LPLC1 | 68/68 | 72/72 | DNp09 (P9) | 1/1 | 1/1 |
| LPLC4 | 56/56 | 54/54 | MDN (= DNp50; FlyWire label "MDN") | 2/2 | 2/2 |
| LC22 | 43/43 | 46/46 | DNg97 (oDN1), DNg100, DNp42, DNa10 | 1/1 each | 1/1 each |
| LC6 / LC9 / LC11 | 65/87/66 | 60/92/61 | DNa01, DNa02, DNa03, DNa04, DNa05, DNa07 | 1/1 each | 1/1 each |
| LC12 / LC15 / LC16 / LC17 / LC18 | 198/52/77/134/96 | 182/54/74/142/92 | DNb01, DNb05, DNb06, DNg13 | 1/1 each | 1/1 each |
| LC21 / LC10a / LC10d | 68/115/93 | 62/119/– | DNg11 | 3/3 | 3/3 |
| LLPC1/2/3 | 106/120/102 | 113/115/102 | DNb02, DNb03 | 2/2 | 2/2 |
| LPC1 | 82 | – | | | |
| HSE, HSN, HSS, VS1–8, H2 | 1 each | 1 each | | | |
| T4a–d, T5a–d | ~725–760 each | same | | | |
| R1-6 / R7 / R8 | 4423/4044, 672/668, 670/662 | 4029/3888, 670/668, 654/652 | | | |

(A dash means not counted. No "DNp50" or "oDN1" label exists in v783: MDN is labelled `MDN`, and oDN1 is `DNg97` per FBbt.)

### B1. The measured response to our current input (surface)

Mean over 8 trials, 100 ms window; rows = left-eye Hz, columns = right-eye Hz.

| L\R | 0 | 100 | 200 | 250 |
|---|---|---|---|---|
| **GF mean Hz** 0 | 0 | 124 | 149 | 155 |
| 100 | 123 | 161 | 179 | 184 |
| 200 | 149 | 179 | 198 | 208 |
| 250 | 161 | 186 | 207 | **214** |
| **turn (DNa01+DNb01, R−L) Hz** 0 | 0 | −65 | −82 | −94 |
| 100 | 75 | 9 | −42 | −56 |
| 250 | 106 | 70 | 39 | 10 |
| **DNa02 R−L Hz** 0 | 0 | −36 | −29 | −16 |
| 100 | 15 | 1 | −4 | 0 |
| 250 | 11 | 5 | 0 | 2 |

**The GF threshold (200 Hz) is crossed only when both eyes are at ≥ 175–225 Hz.** A single row-1 own-lane gap (250 to each eye) is exactly that corner.

A row-2 gap contributes 250/8 ≈ 31 Hz, i.e. one quantisation step, and a row-3 gap 9 Hz, which rounds to 0. So the jump carries no information about its landing tile.

**DNa02 cancels to 0 once both eyes are ≥ 125 Hz**, while DNa01+DNb01 keeps a graded difference.

### B2. Direct synapses, left-eye type → DN, with the post-synaptic compartment (FlyWire tool, split edgelist)

- All DN input in the brain lands on dendrite. The compartment split therefore does not discriminate between DN inputs; it would only matter for interneurons.
- **Every direct VPN → DN connection is on the same side.**
- Top 30 of the 55 connections with ≥ 10 synapses:

| input (L) | DN | syn | | input (L) | DN | syn |
|---|---|---|---|---|---|---|
| LPLC4 | DNb05 | 2077 | | LPLC1 | DNp06 | 521 |
| LC4 | DNp04 | 1425 | | LLPC1 | DNae002 | 487 |
| LPLC4 | DNp03 | 1146 | | LC9 | DNp09 | 470 |
| LC11 | DNp35 | 1022 | | LC4 | DNp03 | 456 |
| LPLC1 | DNp03 | 978 | | LC4 | DNp01 (GF) | 454 |
| LPLC1 | DNp35 | 866 | | LPLC2 | DNp06 | 447 |
| LPLC2 | DNp04 | 782 | | LC9 | DNp11 | 424 |
| LC4 | DNp11 | 736 | | LC4 | DNp05 | 346 |
| LC4 | DNp02 | 622 | | LPLC4 | DNg82 | 314 |
| LC21 | DNp35 | 572 | | LC10d | DNa10 | 247 (Shiu) |
| LPLC1 | DNp11 | 560 | | LPLC1 | DNa07 | 157 |
| LPLC2 | DNp01 (GF) | 544 | | LPLC4 | DNa04 | 96 |
| LLPC1 | DNa02 | 62 | | HSS | DNa02 | 40 |
| LLPC1 | DNb01 | 43 | | LC10a | DNa08 | 32 |
| LC9 | DNa02 | 14 | | HSS | DNg41 | 16 |

None of LPLC2, LC4, LC16 or LC11 connects directly to DNa01, DNa02, DNg13 or MDN.

### B3. Two-hop paths onto DN dendrites (FlyWire tool)

Weight = Σ over intermediate cells of syn(input → mid) / total input(mid) × syn(mid → DN dendrite). "Via" gives the top 2 intermediate types; the input type itself appearing there means lateral connections within the type. Top rows:

| input (L) | DN | side | weight | via |
|---|---|---|---|---|
| LC10a | DNae002 | ipsi | 235 | CB0359, CB0007 |
| LPLC4 | DNa15 | ipsi | 187 | PLP009, CB0527 |
| LPLC4 | DNb05 | ipsi | 185 | LPLC4, SAD094 |
| LPLC4 | DNae002 | ipsi | 162 | PLP009, PLP029 |
| LC11 | DNp35 | ipsi | 151 | LC11, AVLP282 |
| LC22 | DNa15 | ipsi | 146 | PLP009, CB0527 |
| LPLC4 | DNa04 | ipsi | 145 | PLP009, PLP092 |
| LC9 | DNp09 | ipsi | 132 | LC9, PVLP004/005 |
| LC10a | DNa02 | ipsi | 129 | AOTU025, CB0359 |
| LC10a | DNa03 | ipsi | 99 | AOTUv3B_P01, AOTU025 |
| LLPC1 | DNa02 | ipsi | 71 | PS013, PS230/PLP242 |
| LPLC2 | DNp01 | ipsi | 76 | LPLC2, PVLP122b |
| LPLC4 | DNb01 | contra | 68 | CB2271, CB3066 |
| LC10a | DNa02 | contra | 64 | CB3127, CB2070 |
| LPLC1 | DNa05 | contra | 56 | CB2102, PS208b |
| LC4 | DNp01 | ipsi | 58 | PVLP024, PVLP122b |

(Full list: `scratch-circuits/fw2.out`.)

### B4. Signed influence in the Shiu model, hops 1–3 summed (×1000, per-cell mean, left-eye drive; DN left/right by soma side)

This is linear influence through the model's signed, input-normalised weights. It ignores thresholds and timing, so it predicts direction and relative strength, not firing rates.

| input (L) (n) | GF | DNp04 | DNp03 | DNp11 | DNp09 | MDN | DNa01 | DNa02 | DNg13 | DNb01 | DNb05 | DNa10 | DNg97 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LPLC2 (108) | +115/+3 | +226/−2 | +5/0 | +5/−1 | +12/0 | 0/0 | 0/+1 | 0/0 | 0/0 | 0/0 | +3/0 | +1/0 | +1/0 |
| LC4 (54) | +83/0 | +362/−7 | +72/0 | +124/−7 | +1/0 | 0/0 | 0/+1 | 0/0 | 0/0 | 0/+1 | 0/0 | 0/0 | +1/0 |
| LPLC1 (68) | 0/0 | +5/0 | +171/−2 | +93/0 | +2/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/+1 | 0/0 | 0/0 | +1/0 |
| LPLC4 (56) | −1/0 | 0/0 | +185/−1 | +14/−1 | 0/0 | 0/0 | −3/+4 | +1/+1 | 0/0 | −5/+9 | +156/+1 | +20/+8 | +4/−3 |
| LC22 (43) | 0/0 | 0/0 | +31/−1 | −2/−1 | 0/0 | 0/0 | −1/+1 | −1/0 | 0/0 | −2/+4 | +1/0 | – | – |
| LC9 (87) | +1/0 | +8/0 | +2/0 | +65/0 | +90/−7 | +1/+1 | −1/+4 | +2/+1 | +1/+1 | −1/+2 | +1/0 | +1/0 | +1/0 |
| LC11 (66) | 0/0 | −1/+1 | +1/0 | +2/0 | +6/−5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | +1/0 | 0/0 | 0/0 |
| LC16 (77) | 0/0 | 0/0 | 0/0 | 0/0 | 0/+1 | **0/0** | 0/0 | 0/0 | 0/0 | −1/0 | 0/0 | 0/0 | 0/−1 |
| LC10a (115) | 0/0 | 0/0 | −1/0 | +7/0 | 0/0 | +1/−1 | +1/−1 | +11/+1 | +5/+3 | +9/+6 | 0/0 | +5/+1 | 0/+7 |
| LC10d (93) | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/−1 | 0/0 | +8/−1 | +3/+2 | −3 (R−L) | 0/0 | **+22/−2** | 0/+4 |
| LLPC1 (106) | −1/0 | −2/−1 | +12/0 | −2/−1 | +1/0 | 0/0 | 0/+2 | +8/0 | +1/0 | +8/+2 | +1/0 | +1/0 | +2/+8 |
| LPC1 (82) | −3/+1 | – | – | −4/0 | **−13/0** | +2/+1 | +1/+1 | +1/0 | 0/0 | (R−L +7) | – | −1/0 | +1/0 |
| HSS (1) | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | +3/0 | 0/0 | 0/0 | 0/0 | – | – |
| T5a (741) | +3/0 | +8/0 | +1/0 | −2/0 | 0/0 | 0/0 | 0/0 | +3/0 | 0/0 | +1/0 | 0/0 | – | – |

(– = not computed for that pair; full tables in `scratch-circuits/run3.out` and `run5.out`.)

What the table shows:

- **Looming → takeoff DNs.**
  - LPLC2 and LC4 are overwhelmingly takeoff-DN inputs: DNp04, DNp01, DNp11 and DNp02 (LC4 → DNp02 +187 ipsi, `run5.out`).
  - Their influence on DNa01, DNa02 and DNg13 is about 1/100 of that. The lateralised turn seen in spike 01 is real but comes from a much weaker, multi-hop route.
- **Opposite-side steering via LPLC4.** LPLC4 is the only strong VPN route to an opposite-side steering DN: DNb01 +9 contra and DNa01 +4 contra. Its strongest target, though, is DNb05 on the same side (+156).
- **The approach channels.** LC10a/LC10d → DNa02 (same side) and DNa10 is the approach/avoid channel of the central brain.
- **Forward walking.** LC9 → DNp09 is +90. LPC1 inhibits DNp09 (−13), consistent with LPC1 regulating forward walking from translational optic flow (Isaacson 2023).
- **LC16 → MDN is effectively 0** in the brain-only model. Sen 2017's retreat pathway either goes through cells outside the brain connectome or is too weak here.

### B5. Shortest excitatory path (hops over edges with ≥ 5 excitatory synapses; Shiu), left eye → DN on the same side / opposite side

| input | GF | DNp03 | DNp09 | MDN | DNa01 | DNa02 | DNg13 | DNb01 | DNb05 | DNa04 |
|---|---|---|---|---|---|---|---|---|---|---|
| LPLC2 | 1/2 | 2/4 | 1/3 | 2/2 | 3/2 | 2/2 | 3/2 | 2/2 | 2/3 | 2/2 |
| LC4 | 1/2 | 1/4 | 3/3 | 2/2 | 3/2 | 3/2 | 3/2 | 3/2 | 3/3 | 2/2 |
| LPLC1 | 2/3 | 1/4 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/2 | 2/3 | 2/2 |
| LPLC4 | 2/3 | 1/3 | 3/3 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 |
| LC22 | 2/3 | 1/4 | 2/3 | 3/3 | 2/2 | 2/2 | 2/3 | 2/2 | 2/3 | 2/2 |
| LLPC1 | 3/2 | 1/4 | 2/3 | 3/3 | 2/2 | **1/2** | 2/3 | 1/2 | 1/2 | 1/2 |
| LC9 | 2/2 | 2/4 | **1/3** | 2/2 | 2/2 | 2/2 | 2/3 | 2/2 | 2/3 | 2/3 |
| LC10a | 3/3 | 2/4 | 3/3 | 2/3 | 3/3 | 2/2 | 2/2 | 2/2 | 3/3 | 2/3 |
| HSS | 3/3 | 2/– | 3/3 | 3/3 | 3/3 | **1/3** | 3/3 | 2/3 | 3/3 | 2/3 |

DNp03 on the opposite side is 3–4 hops from every VPN tested: it is strictly driven from its own side. The full table, 26 inputs × 20 DNs, is in `scratch-circuits/run3b.out`.

### B6. Screen: which visual projection types inhibit the GF? (Shiu, hops 1–3, ×1000, left eye, all VPN types with ≥ 3 cells)

| type | GF | | type | GF |
|---|---|---|---|---|
| LC18 | −1.5 | | LPLC2 | **+59.1** |
| LPC1 | −1.0 | | LC4 | **+41.8** |
| LC12 | −0.8 | | LC6 | +1.3 |
| LPLC4 | −0.6 | | LC15 | +1.0 |
| LLPC1 | −0.5 | | LC9 | +0.7 |

The GF's inhibitory input comes from central cells: CB3707 (4 cells, about −630 synapses in total), PVLP010, LHAD1g1, CB0563 and CB0010. No VPN reaches them strongly.

**Conclusion: no innate visual channel can veto a jump.**

This also answers "which LPLC2 cells should a floor hole drive": Dombrovski 2023 and spike 03 both find ventral LPLC2 drives the GF more weakly. A retinotopically honest floor would therefore make the fly jump *less*.

### B7. Where these cells live (FlyWire tool: neuropils, flow step, Infomap flow module)

Neuropil sides in `neuron_neuropil_counts.parquet` are FAFB-raw, i.e. mirrored. They are swapped back here, and "own" or "opposite" is relative to the soma.

| type | flow step | Infomap module | main input → output neuropil |
|---|---|---|---|
| LPLC2, LC4, DNp01, DNp02, DNp04, DNp11, DNp05 | 4–7 | **F77** (the looming-escape module) | LO/LOP → PVLP |
| LPLC1, LC9, LC11, LC12, LC15, LC17, LC18, LC21, DNp06, DNp09, DNp35 | 5–8 | **F14** (object/forward module) | LO → PVLP (LPLC1 also PLP) |
| LPLC4, LC22, DNb05 | 4–7 | **F64** | LO → PLP/SPS |
| DNa02, DNa04, DNa05, DNa08, DNb01, DNae002/004, DNg41, DNb03, DNa15, DNg82, DNg71, DNp03 | 6–8 | **F45** (posterior-slope steering module) | SPS/IPS/LAL |
| MDN, DNa01, DNg13, aSP22 | 5–6 | **F36** | LAL/VES |
| LC10a | 9 | F57 | LO → AOTU |

- **Brain outputs on the opposite side of the soma**, i.e. the axon crosses: DNb01 (outputs 50% in the opposite IPS), DNg41 (97%), DNg11 (94%), DNg71 (86%), DNp03 (64%) and MDN (66%).
- The literature confirms crossing for DNb01, DNg41, DNp03 and MDN, and for DNb06 and DNb02. DNg11's main axon stays on its own side. DNg71 is not established.

The Infomap modules say the same as the paths: our input cells (F77) share a module with the takeoff DNs, and the walking-steering DNs (F45, F36) sit in other modules reached by the posterior-slope and LAL routes.

### B8. Descending neurons: axon side and turn direction (literature, for the readout)

| DN | axon | a one-sided activation turns the fly | source |
|---|---|---|---|
| DNa02 | same side as soma | toward its own side (activation tested); high gain, transient | Rayshubskiy 2025; Yang 2024 |
| DNa01 | same side as soma | toward its own side (correlation); low gain, sustained | Rayshubskiy 2025; Yang 2024 |
| DNg13 | crosses (acts on the opposite legs) | toward its own side (lengthens the outer strides) | Yang 2024; Cheong 2026 |
| DNb05 | same side as soma | toward its own side (correlation) | Yang 2024 |
| DNb06 | crosses | away from its soma side (correlation) | Yang 2024 |
| DNb01 | crosses; glutamatergic | no walking-steering role reported | FBbt:00047582; Cheong 2024 (the Cande 2018 line was DNb09) |
| MDN (DNp50) | crosses | backward; asymmetric activation → backward turn away from its soma side | Bidaye 2014; Sen 2017; Cheong 2026 |
| DNp09 | same side as soma | forward walking, turns toward its own side; also freezing | Bidaye 2020; Zacarias 2018 |
| DNp11 / DNp02+DNp04 | – | forward / backward takeoff (LC4 gradients) | Dombrovski 2023 |
| DNp03 | crosses | flight saccades (wing steering) | Current Biology 2024 (DNp03) |

---

## (C) Sources

URLs were fetched by the literature sub-agent through Europe PMC, PMC or publisher pages unless marked (unverified). Items from 2025–2026 are after my own training data; I rely on the sub-agent's fetched pages for them.

**Gap crossing and the visual cliff**
- Pick S, Strauss R 2005. Goal-driven behavioral adaptations in gap-climbing *Drosophila*. *Curr Biol* 15:1473. https://doi.org/10.1016/j.cub.2005.07.022
- Triphan T, Poeck B, Neuser K, Strauss R 2010. Visual targeting of motor actions in climbing *Drosophila*. *Curr Biol* 20:663. https://doi.org/10.1016/j.cub.2010.02.055
- Triphan T et al. 2016. A screen for constituents of motor control and decision making in *Drosophila* reveals visual distance-estimation neurons. *Sci Rep* 6:27000. https://doi.org/10.1038/srep27000 (success-rate numbers unverified)
- Krause T, Spindler L, Poeck B, Strauss R 2019. *Drosophila* acquires a long-lasting body-size memory from visual feedback. *Curr Biol*. https://doi.org/10.1016/j.cub.2019.04.037
- Dallmann et al. 2026 (bioRxiv), roadrunner/BPN forward-walking circuit. https://doi.org/10.64898/2026.01.04.697356 (full text not read)
- Robie AA, Straw AD, Dickinson MH 2010. *J Exp Biol*. https://doi.org/10.1242/jeb.041749
- No *Drosophila* visual-cliff or floor-edge paper was found (the absence is unverified).

**Descending neurons for walking**
- Namiki S et al. 2018. The functional organization of descending sensory-motor pathways in *Drosophila*. *eLife*. https://doi.org/10.7554/eLife.34272
- Bidaye SS et al. 2014. Neuronal control of *Drosophila* walking direction (MDN). *Science*. https://doi.org/10.1126/science.1249964
- Sen R et al. 2017. Moonwalker descending neurons mediate visually evoked retreat in *Drosophila*. *Curr Biol*. https://doi.org/10.1016/j.cub.2017.02.008
- Bidaye SS et al. 2020. Two brain pathways initiate distinct forward walking programs in *Drosophila* (P9 = DNp09, BPN). *Neuron*. https://doi.org/10.1016/j.neuron.2020.07.032
- Sapkal N et al. 2024. The halting paper: walk-OFF (Foxglove, Bluebell), brake (BRK), oDN1; it used the Shiu model. *Nature* 634:191. https://doi.org/10.1038/s41586-024-07854-7
- Rayshubskiy A et al. 2025. Neural circuit mechanisms for steering control in walking *Drosophila*. *eLife*. https://doi.org/10.7554/eLife.102230
- Yang HH et al. 2024. Fine-grained descending control of steering in walking *Drosophila*. *Cell* 187:6290. https://doi.org/10.1016/j.cell.2024.08.033
- Braun J et al. 2024. Descending networks transform command signals into population motor control. *Nature* 630:686. https://doi.org/10.1038/s41586-024-07523-9
- Cande J et al. 2018. Optogenetic dissection of descending behavioral control in *Drosophila*. *eLife*. https://doi.org/10.7554/eLife.34275
- Stürner T et al. 2025. Comparative connectomics of *Drosophila* descending and ascending neurons. *Nature* 643:158. https://doi.org/10.1038/s41586-025-08925-z
- Cheong HSJ et al. 2026. Organization of an ascending/descending circuit for leg and wing control (MANC). *eLife*. https://doi.org/10.7554/eLife.96084
- Bates AS et al. 2026 (BANC, brain and nerve cord connectome). *Nature*. https://doi.org/10.1038/s41586-026-10735-w
- Berg S et al. 2026 (male CNS connectome). *Cell*. https://doi.org/10.1016/j.cell.2026.08.015
- Israel S et al. 2022 (MooSEZ). *Curr Biol*. https://doi.org/10.1016/j.cub.2022.01.035
- Feng K et al. 2020 (MDN in the VNC). *Nat Commun*. https://doi.org/10.1038/s41467-020-19936-x
- FBbt ontology (DN anatomy, synonyms oDN1 = DNg97, MDN = DNp50). https://www.ebi.ac.uk/ols4/ontologies/fbbt

**Escape**
- Card G, Dickinson MH 2008. Visually mediated motor planning in the escape response of *Drosophila*. *Curr Biol*. https://doi.org/10.1016/j.cub.2008.07.094
- von Reyn CR et al. 2014. A spike-timing mechanism for action selection. *Nat Neurosci*. https://doi.org/10.1038/nn.3741
- Ache JM et al. 2019. Neural basis for looming size and velocity encoding in the *Drosophila* giant fiber escape pathway. *Curr Biol* 29:1073. https://www.sciencedirect.com/science/article/pii/S0960982219301381 (DOI unverified)
- Dombrovski M et al. 2023. Synaptic gradients transform object location to action. *Nature* 613:534. https://doi.org/10.1038/s41586-022-05562-8
- Zacarias R et al. 2018. Speed dependent descending control of freezing behavior in *Drosophila*. *Nat Commun*. https://doi.org/10.1038/s41467-018-05875-1
- Gibson WT et al. 2015. Behavioral responses to a repetitive visual threat stimulus express a persistent state. *Curr Biol*. https://pubmed.ncbi.nlm.nih.gov/25981791/ (DOI unverified)
- Zucker-Scharff et al. 2026. *Curr Biol*. https://doi.org/10.1016/j.cub.2026.07.077
- Ribeiro et al. 2026 (LC10d → DNa10 object avoidance), bioRxiv. https://doi.org/10.64898/2026.01.26.701771
- DNp03 as a flight-saccade hub: *Curr Biol* 2024. https://www.cell.com/current-biology/fulltext/S0960-9822(24)01641-5 ; PMC version https://pmc.ncbi.nlm.nih.gov/articles/PMC12977095/

**Visual projection neurons**
- Wu M et al. 2016. Visual projection neurons in the *Drosophila* lobula link feature detection to distinct behavioral programs. *eLife*. https://doi.org/10.7554/eLife.21022
- Klapoetke NC et al. 2017. Ultra-selective looming detection from radial motion opponency. *Nature* 551:237. https://doi.org/10.1038/nature24626
- Klapoetke NC et al. 2022. A functionally ordered visual feature map in the *Drosophila* brain. *Neuron* 110:1700. https://www.cell.com/neuron/fulltext/S0896-6273(22)00178-7
- Tanaka R, Clark DA 2020. Object-displacement-sensitive visual neurons drive freezing in *Drosophila* (LC11). *Curr Biol*. https://doi.org/10.1016/j.cub.2020.04.068
- Tanaka R, Clark DA 2022. Neural mechanisms to exploit positional geometry for collision avoidance (LPLC1). *Curr Biol* 32:2357. https://doi.org/10.1016/j.cub.2022.04.023
- Hindmarsh Sten T et al. 2021. Sexual arousal gates visual processing during *Drosophila* courtship (LC10a). *Nature*. https://doi.org/10.1038/s41586-021-03714-w
- Cowley BR et al. 2024. Mapping model units to visual neurons reveals population code for social behaviour. *Nature*. https://doi.org/10.1038/s41586-024-07451-8
- Isaacson MD et al. 2023. Small-field visual projection neurons detect translational optic flow and support walking control (LPC1, LLPC1). bioRxiv. https://www.biorxiv.org/content/10.1101/2023.06.21.546024v1
- Aptekar JW et al. 2015. *J Neurosci*. https://doi.org/10.1523/JNEUROSCI.0652-15.2015
- Nern A et al. 2025. Connectome-driven neural inventory of a complete visual system. *Nature*. https://doi.org/10.1038/s41586-025-08746-0
- Matsliah A et al. 2024. Neuronal parts list and wiring diagram for a visual system. *Nature*. https://doi.org/10.1038/s41586-024-07981-1

**Optic flow and walking**
- Creamer MS, Mano O, Clark DA 2018. Visual control of walking speed in *Drosophila*. *Neuron*. https://doi.org/10.1016/j.neuron.2018.10.028
- Busch C, Borst A, Mauss AS 2018. Bi-directional control of walking behavior by horizontal optic flow sensors. *Curr Biol*. https://doi.org/10.1016/j.cub.2018.11.010
- Mauss AS et al. 2015. Neural circuit to integrate opposing motions in the visual field. *Cell*. https://doi.org/10.1016/j.cell.2015.06.035
- Zhao A et al. Lobula plate tangential neuron survey. *eLife* reviewed preprint. https://elifesciences.org/reviewed-preprints/93659

**Models, simulations and memory**
- Shiu PK et al. 2024. A *Drosophila* computational brain model reveals sensorimotor processing. *Nature* 634:210. https://doi.org/10.1038/s41586-024-07763-9
- Lappalainen JK et al. 2024. Connectome-constrained networks predict neural activity across the fly visual system (flyvis). *Nature*. https://doi.org/10.1038/s41586-024-07939-3
- Wang-Chen S et al. 2024. NeuroMechFly v2. *Nat Methods*. https://doi.org/10.1038/s41592-024-02497-y
- Eon Systems 2026. Embodied brain emulation (Shiu brain + flyvis + NeuroMechFly; DNa01/DNa02 steering, oDN1 speed). https://eon.systems/updates/embodied-brain-emulation
- Seelig JD, Jayaraman V 2015. Neural dynamics for landmark orientation and angular path integration. *Nature*. https://doi.org/10.1038/nature14446
- Mussells Pires P et al. 2024. *Nature*. https://doi.org/10.1038/s41586-023-07006-3
- Westeinde EA et al. 2024. PFL3 → DNa02 goal steering. *Nature* (correction https://doi.org/10.1038/s41586-024-08245-8; main-paper DOI unverified)

**Repositories** (licence, last push, checked 2026-09-24 by `gh api`)
- philshiu/Drosophila_brain_model: MIT, 2024-09-14
- eonsystemspbc/fly-brain: GPL-2.0, 2026-08-29
- TuragaLab/flyvis: MIT, 2026-08-18
- NeLy-EPFL/flygym: Apache-2.0, 2026-08-24
- navis-org/fafbseg-py: GPL-3.0, 2026-07-09
- flyconnectome/flywire_annotations: no licence file, 2026-07-21
- jasper-tms/the-BANC-fly-connectome: GPL-3.0, 2026-05-16
- murthylab/codex: Apache-2.0, 2026-09-08

**Local data**
- FlyWire v783 annotations and the Shiu model data in `data/`.
- The user's FlyWire viewer data (CC BY-NC 4.0) in `~/Documents/PROJECTS/LEARN/flywire/motg-flywire/data/raw` and `public/data`.
- `calibration/response_surface.json`.
- Spikes 01 and 03 (branches `spike/fly-steering`, `spike/fly-bands`).
