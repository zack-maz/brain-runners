# Spike 04: does any fly2 candidate turn away from a gap while the centre is driven hard? (2026-09-24, throwaway)

Gate 1 of `docs/history/superpowers/specs/2026-09-24-fly2-design.md` ("Order and gates", step 1). Real brain (Shiu et al.
model, the project's `Brain`), one PoissonGroup over LPLC2, LC4, LPLC4 and LC22 of both eyes, 100 ms windows, 8
seeded trials per condition (seeds 4000–4007). Per condition only the candidate's own cells get a Poisson target's
zero refractory period; the rest keep the model's default. Script `probe.py`, every number in `probe.json`.

Sign convention: turn = (DNa02 + DNa01 + DNg13) right − the same on the left; positive means turn right. A gap on
the left should give a positive turn, a gap on the right a negative one. Values are Hz, mean ± sd over the trials.

## Each channel alone

| candidate | channel | 100 Hz | 300 Hz | 500 Hz | Giant Fiber at 500 Hz |
| --- | --- | --- | --- | --- | --- |
| M1 | centre (LPLC2, both eyes) | −4 ± 5 | −3 ± 7 | +8 ± 8 | 221 |
| M1 | left (LC4 left) | +40 ± 11 | +79 ± 16 | +91 ± 11 | 130 |
| M1 | right (LC4 right) | −43 ± 4 | −69 ± 11 | −70 ± 9 | 116 |
| M2 | left eye (LPLC2 + LC4) | +66 ± 26 | +91 ± 18 | +109 ± 22 | 182 |
| M2 | right eye | −76 ± 11 | −59 ± 8 | −68 ± 11 | 179 |
| M3 | centre (LPLC2 + LC4, both eyes) | −3 ± 4 | +1 ± 9 | +16 ± 10 | 258 |
| M3 | left (LPLC4 + LC22 left) | +29 ± 23 | +99 ± 22 | +121 ± 34 | **0** |
| M3 | right (LPLC4 + LC22 right) | −45 ± 35 | −158 ± 21 | −181 ± 21 | **0** |

Every one-sided channel turns the fly away from its own side. The centre channels turn little (a small rightward
bias at 500 Hz, +8 and +16) and drive the Giant Fiber hard. M3's side channel drives no Giant Fiber at all.

## Strong centre plus one uneven side (the gate)

Centre 500 Hz for M1 and M3. M2 has no centre channel: a centre gap drives both eyes, so its condition is both eyes
at 250 Hz with the side added on top, capped at 500 Hz (so its +300 and +500 rows are the same input; ours, not
in the spec's wording).

| candidate | gap side, extra Hz | turn | turn without DNa02 | DNa02 R−L | Giant Fiber |
| --- | --- | --- | --- | --- | --- |
| M1 | none | +8 ± 8 | +5 ± 7 | +2 ± 4 | 221 |
| M1 | left 100 / 300 / 500 | +9 ± 11 / +31 ± 9 / +28 ± 10 | +6 / +19 / +16 | +2 ± 4 / **+12 ± 8** / **+11 ± 6** | 226–243 |
| M1 | right 100 / 300 / 500 | −3 ± 4 / −16 ± 13 / −15 ± 9 | −1 / −14 / −13 | −1 ± 3 / −2 ± 4 / −2 ± 4 | 226–238 |
| M2 | none | 0 ± 9 | 0 | 0 ± 0 | 214 |
| M2 | left 100 / 300 | +16 ± 7 / +31 ± 12 | +16 / +29 | 0 ± 0 / +2 ± 7 | 228–234 |
| M2 | right 100 / 300 | −3 ± 8 / −6 ± 7 | −3 / −6 | 0 ± 0 / 0 ± 0 | 226–235 |
| M3 | none | +16 ± 10 | +15 ± 9 | +1 ± 3 | 258 |
| M3 | left 100 / 300 / 500 | +31 ± 12 / +79 ± 20 / +113 ± 33 | +20 / +38 / +60 | +11 ± 11 / **+41 ± 21** / **+53 ± 25** | 256–258 |
| M3 | right 100 / 300 / 500 | −9 ± 11 / −61 ± 15 / −93 ± 23 | −11 / −44 / −73 | +2 ± 10 / **−18 ± 8** / −20 ± 20 | 254–256 |

## Findings

- **The gate passes.** Under a strong centre every candidate still turns away from the side of the extra gap, so
  the update goes on. How well differs a lot:
  - **M3** keeps a large, two-sided turn (+113 and −93 at 500 Hz, 3.4 and 4.0 trial sd from zero), and its side
    channel never drives the Giant Fiber: "where to dodge" and "whether to jump" arrive on separate cells. That is
    the fly's wiring doing what the rule needs, not our rule.
  - **M1** keeps it, but weakly and lopsided: +28 for a left gap, −15 for a right one (1.7 sd).
  - **M2** barely does: +31 for a left gap, −6 for a right one (under one sd). Narrow eyes under a strong centre
    lose the right side almost entirely.
- **M3's direction** (the spec's admission test): the left LPLC4 + LC22 alone turns the fly right, away from the
  left, at every rate. **M3 is admitted.**
- **DNa02 does not cancel the same way everywhere.** By the spec's test (DNa02's right−left within one trial sd in
  the uneven-with-strong-centre conditions):
  - M2: within noise in every condition (it barely fires). It cancels.
  - M1: within noise for every right-side gap and at 100 Hz; above it for a left gap at 300 and 500 Hz.
  - M3: above noise at 300 and 500 Hz on both sides except right 500 (−20 ± 20), where it is borderline; it adds to
    the turn.
  - Leaving DNa02 out never lowers the turn's distance from zero in trial sd and raises it for M3 (left 500:
    3.4 → 4.0 sd; right 500: 4.0 → 4.8 sd). DNa02 is the noisiest of the three.
- **A left–right asymmetry:** the right eye has fewer input cells (LPLC2 102 against 108, LC4 50 against 54), and
  M1 and M2 turn less for a right gap. M3 does not show it. The rule has one turn threshold for both sides.
- **A rightward bias under centre drive:** DNg13 fires a little more on the right when both eyes are driven (+5 to
  +16 Hz), so a lone centre gap leans the turn right (M3: +16 ± 10). With a turn threshold of 0 or 10 Hz the fly
  would sometimes dodge right on a centre-only gap; the calibration sees this and so will the controls.
- Logged only, not in the readout: DNb05 swings hard with M3's side channels (up to 258 Hz right−left), on the
  side of the gap; DNa04 follows the gap side in M1 and M3.

## What this leaves for the user

The gate passes and M3 stays, so all three candidates go on to the surfaces. One call is needed first: the spec's
DNa02 test gives a different answer per candidate (it cancels in M2, partly in M1, not in M3). The options:

1. **Leave DNa02 out for every candidate** (turn = DNa01 + DNg13). One readout for all, it is the spec's fall-back,
   and by the numbers above it costs nothing: the turn is as far or farther from zero without it.
2. **Decide per candidate** by the test as measured: out for M2 (and M1?), in for M3.
3. **Keep DNa02 in everywhere**, as the spec's default readout.
