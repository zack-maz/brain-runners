# Spike 03: does the fly's wiring use *where* a threat is? (2026-09-22, throwaway)

Question (decision 29): before building `fly_rich`, find an ordering of each eye's looming cells (LPLC2, LC4) that
follows their view, cut each eye into bands, and check on the real brain whether the decision neurons respond
differently by band. If not, `fly_rich` is not built.

## Ordering (`order.py`)

FlyWire's one point per cell (`pos_*`) is where the cell's outputs converge, not where it looks. Instead, each
cell is placed at the synapse-weighted mean position of its presynaptic columnar partners (types with at least 300
cells per side: T4, T5, Tm5f for LPLC2; T2, Tm4, Tm2, Tm3 for LC4), whose positions tile the eye. Positions are in
4 nm voxels for x and y and 40 nm slices for z (the first pass got this wrong and saw a flat sheet). Result: every
cell has columnar input; the centroids spread about 45 um along a mostly dorso-ventral axis (read here as
elevation) and about 25 um along a second axis (read as azimuth). Which end of the second axis faces forward is not
established.

## Probe (`probe.py`, `probe.json`)

Real brain (Shiu et al. model, the project's `Brain`), 100 ms windows, 6 seeded trials per condition, 250 Hz on the
stimulated cells, nothing else. Bands are terciles along each axis, both cell types together (50 to 54 cells each).

| stimulated | turn signal Hz (mean, sd) | jump signal Hz (mean, sd) |
| --- | --- | --- |
| nothing | 0 | 0 |
| whole left eye (162 cells) | +117, 5 | 161, 5 |
| whole right eye (152 cells) | -90, 10 | 157, 4 |
| left eye, elevation bands 0 / 1 / 2 | +73 / +65 / +60 | 120 / 111 / 93 |
| right eye, elevation bands 0 / 1 / 2 (axis flipped) | -57 / -52 / -62 | 99 / 121 / 126 |
| left eye, azimuth bands 0 / 1 / 2 | +58 / +63 / +38 | 100 / 113 / 116 |
| right eye, azimuth bands 0 / 1 / 2 | -30 / -53 / -43 | 121 / 120 / 103 |

## Findings

- **The output does differ by band, but only in how strongly, never in what.** Every band of an eye gives the same
  response as the whole eye, weaker: turn away from that side, plus Giant Fiber drive. No band turns toward, jumps
  without turning, or stays silent.
- Two differences are consistent across both eyes (after mirroring the right eye's axis) and larger than the trial
  noise: the dorsal band drives the Giant Fiber about 30% harder than the ventral band (120-126 against 93-99 Hz),
  and one end of the azimuth axis turns about half as hard as the rest (30-38 against 53-63 Hz).
- The read-out collapses all of this into two numbers (turn = right minus left steering, jump = Giant Fiber mean).
  At that level "where" arrives as a 1.5-2x change in magnitude, which the fly cannot tell apart from "more gaps"
  or "nearer gaps", which also raise magnitude.
- Nothing in the escape pathway knows where a jump lands. The fly's v2 deaths were all jumps into a gap (runs of
  update 2a); richer threat input feeds the same reflex that jumps into gaps.

## Recommendation

The gate passes only weakly. Building `fly_rich` (band mapping, recording, calibration, player, page label) is a
multi-day plan whose likely outcome is the same reflex with slightly different magnitudes, and the tile-to-band
mapping would be mostly ours (floor gaps all lie below the horizon, so the elevation axis has no natural game
meaning, and the forward end of the azimuth axis is unestablished). The honest result for the write-up is this
report: the untrained wiring carries "where" only as strength, and its output neurons act on side and strength.
A cheap way to settle it for good, if wanted: a throwaway band input played with the frozen v1 thresholds against
`fly` on five practice seeds (about ten minutes of simulation).

## Play test (`play.py`, 2026-09-22)

The user chose the ten-minute play test. Rule fixed beforehand: if a band fly survives no longer than `fly`, update
2b stops and this report is its result. Three players, one shared brain, frozen v1 thresholds, game v2, practice
seeds 1100-1104 (run directory kept in the session scratchpad, not in `runs/`):

| player | mean rows | median | deaths ran / jumped / dodged into a gap | jumps made |
| --- | --- | --- | --- | --- |
| fly | 58.2 | 67 | 0 / 5 / 0 | 24 |
| fly_band_a (front = the end that turned least) | 21.6 | 13 | 4 / 0 / 1 | 0 |
| fly_band_b (front = the other end) | 29.6 | 29 | 0 / 0 / 5 | 0 |

(Random scores 24 on v2.) Both band flies are far worse and never jump: a band is a third of an eye's cells, so the
Giant Fiber never reaches the 200 Hz threshold that whole-eye drive reaches, and the flies run or sidestep into
gaps instead. Recalibrating the thresholds for band drive would mostly give back the whole-eye reflex that `fly`
already has; the probe shows no band that asks for a different action.

**Result: update 2b stops.** The untrained wiring carries "where" only as strength of the same escape response, and
spreading the input over bands weakens that response. `fly` stays the only fly.
