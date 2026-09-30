# Spike 01 report: can the untrained fly-brain model steer, and how fast does it run?

Run 2026-09-19 on a MacBook (Apple M1, 8 cores, 8 GB RAM, heavily loaded with other apps:
swap was ~9.8 of 10 GB used the whole time). Shiu et al. model, FlyWire v783 connectivity,
default parameters, Brian2 2.10 via `uv`. Wall-clock used: about 45 of the 60 minutes.
Everything below was actually run unless marked **NOT RUN**.

## 1. Verdict: **weakly** (yes for fleeing, no for approaching)

The pure, untrained fly can steer a snake **away from a threat**, and does it well: when the
looming detectors of one eye (LPLC2 and/or LC4) are stimulated, the steering descending
neurons DNa01, DNa02 and DNb01 fire **only on the opposite side**, in 36 of 36 one-sided
trials, with exactly zero spikes on the stimulated side, within 15–35 ms of simulated time,
and they cancel out when both eyes are stimulated. Since activity in these neurons turns a
real fly toward the active side, this is a turn away from the threat, which is what real
flies do. The Giant Fiber also fires, more on the threatened side, graded with intensity.
But the fly **cannot steer toward food**: left-vs-right smell produces no left/right
difference at all in any steering neuron (fly smell neurons project to both brain halves),
and left-vs-right sugar taste does not drive the steering neurons in a lateralized way
either. Both food channels instead flip the network into one fixed state in which the *left*
DNa02 fires whatever side was stimulated, so a snake wired that way would circle left
forever. Food-side information does exist in other descending neurons (taste: DNg35,
DNge031, DNg60, DNp58; antennal wind: DNp18, DNb06), but those are feeding/grooming-type
outputs, not known turning neurons, so reading them as "turn" is our relabelling, not the
fly's biology. Speed is fine: about 0.35–0.7 s of wall-clock per decision.

## 2. Q1 speed

One network (138,639 neurons, 15.1 M synapses) built once; each decision = `restore()` a
stored clean state, set new input rates, run a short window. Times are single-process.

| Item | numpy target | cython target |
|---|---|---|
| Build network (load CSV/parquet + create_model) | 2.1 s | 8.4 s (ran while machine was swapping) |
| First run (codegen; cython compile is cached on disk afterwards) | 0.3 s | 15.2 s first ever, then seconds |
| `restore()` to clean state | 0.04 s | 0.04 s |
| 20 ms simulated window | not measured | 0.21 ± 0.01 s |
| 50 ms window | 0.87 s | 0.33 ± 0.01 s |
| 100 ms window | 1.63 s | 0.59–0.72 s |
| 200 ms window | 2.74 s | 1.14–1.22 s |
| 1 s window | 12.4 s | 4.2 s |
| Continuous run, rates changed every 100 ms, no restore | 1.4–1.9 s per 100 ms | 0.52–0.65 s per 100 ms |
| Peak memory (one process) | ~0.9 GB | similar, not separately measured |

- **Rebuilding per decision is unnecessary.** Restore costs 0.04 s; rebuilding costs 2–8 s.
  Continuous running with changing rates also works and costs the same per 100 ms, but then
  state carries over between decisions (a design choice, not a cost one).
- cython is about 3× faster than numpy. Cost scales with simulated time (10,000 steps per
  simulated second at dt = 0.1 ms) plus about 0.1–0.15 s fixed overhead per `run()` call, and
  only mildly with activity: the smell experiment (195k spikes per 400 ms) ran 2–3× slower
  per window than the looming one (19k spikes).
- **One game decision:** 100 ms window ≈ **0.6–0.7 s**; 50 ms window ≈ **0.33 s**.
  **300-decision match:** ≈ **3–3.5 min** at 100 ms, ≈ **1.7 min** at 50 ms, plus ~10–25 s
  one-off start-up. Under memory pressure on this 8 GB machine I saw the same windows take
  3–10× longer (three parallel processes pushed it into swap; 400 ms windows took 2–7 s
  serially depending on what else the laptop was doing). Run one fly process at a time.
- The steering signal is already correct in the first 50 ms (first spikes: Giant Fiber 5 ms,
  DNa01 14 ms, DNa02 23 ms, DNb01 34 ms) but at 50 ms it is 1–2 spikes per neuron; 100 ms is
  the sensible decision window.
- Mechanics note: the repo's `poi()` makes one `PoissonInput` object per neuron with a fixed
  rate, which is slow with hundreds of neurons and cannot change rate. I kept `create_model`
  and all default parameters, and replaced only the input mechanics with one `PoissonGroup`
  wired one-to-one to the sensory neurons with the same 68.75 mV kick and zero refractory
  period. `validate_poi.py` shows the two give the same downstream rates within trial noise
  (e.g. DNg35 72–95 Hz vs 85–88 Hz, MN9 15–30 vs 20–30 Hz).

## 3. Q2 lateralized steering

Method: 6 trials × 400 ms per condition (2 for baseline), fresh Poisson noise each trial.
Conditions: none, left-only and right-only at 50 / 150 / 250 Hz, both sides at 150 Hz. Rates
are Hz per neuron, mean ± sd across trials, for the left (L) and right (R) members of each
cell type. "ipsi − contra" pools left-only and right-only trials (12 per rate): positive
means more firing on the stimulated side. Sides are the FlyWire annotation `side` column.
Baseline (no input) is exactly 0 Hz everywhere: the model has no spontaneous activity.
Full tables for all 13 read-out types and the top-15 data-driven lists: `results/analysis_*.md`.

**ID coverage:** 138,625 of 139,248 annotated neurons are in the v783 model (the v630 files
match only 106k, so v783 it is). Of my chosen neurons: every output type 100 % present
(DNa01 2+2, DNa02 1+1, DNa03 1+1, DNb01 2+2, DNb02 2+2, DNg13 1+1, DNae003 1+1, DNp09 2+2,
MDN 2+2, Giant Fiber DNp01 1+1, DNp02, DNp04, DNp11 1+1 each); sensory sets 903 of 904
present (one left ORN missing).

### a. Attractive smell (ORNs of glomeruli DM1, VA2, DM4, DM2; 118 left, 111 right) — **no**

| | L150 | R150 | both150 |
|---|---|---|---|
| DNa01 | L 20.8±5.5 R 6.2±3.8 | L 18.3±3.7 R 9.2±1.9 | L 22.1±3.4 R 5.4±2.7 |
| DNa02 | L 55.0±6.9 R 0.4±0.9 | L 50.0±4.6 R 0.0±0.0 | L 53.8±3.5 R 0.4±0.9 |
| DNg13 | L 71.2±4.0 R 44.6±4.2 | L 72.1±3.7 R 41.7±2.8 | L 70.4±2.2 R 41.7±6.2 |

- Output is the same whichever antenna is stimulated. ipsi − contra for DNa02: +2.3 ± 52.6 Hz
  (the huge sd is the fixed left bias flipping sign when pooled); asymmetry index (R−L)/(R+L)
  is about −1.0 for DNa02 in every condition. Best of 92 active DN types: 3.5 ± 7.3 Hz. Nothing.
- Not graded: 50, 150 and 250 Hz give identical outputs (network saturated: ~8,400 neurons
  active, ~190k spikes per 400 ms at every rate).
- Why: most fly olfactory receptor neurons send axons to both antennal lobes, so "left
  antenna" and "right antenna" are nearly the same input in the connectome. Real flies use a
  small ipsilateral release asymmetry that this model does not capture.

### b. Sugar taste (gustatory, sub-class sugar/water; 67 left, 62 right) — **not with steering neurons**

| | L150 | R150 | both150 |
|---|---|---|---|
| DNa01 | 0 / 0 | L 14.2±2.8 R 7.9±3.4 | L 15.8±4.7 R 6.2±1.9 |
| DNa02 | 0 / 0 | L 47.1±5.1 R 1.2±1.9 | L 45.4±6.2 R 0.0±0.0 |
| DNg13 | 0 / 0 | L 55.4±5.8 R 31.2±2.4 | L 55.8±3.7 R 20.0±2.5 |

- Left sugar never drives the steering neurons (0 Hz at all three rates). Right sugar at
  ≥150 Hz switches on the same fixed "left DNa02 + left DNg13 + right DNp02" pattern that
  smell produces. That is an all-or-none network state with a built-in left bias, not a
  steering signal. At 50 Hz everything is silent.
- Sugar *does* lateralize strongly elsewhere (ipsi − contra at 50 / 150 / 250 Hz, same sign
  in 12 of 12 trials): DNg35 +16.5±16.0 / +56.0±11.7 / +74.8±5.7; DNge031 +41±28 / +73±23 /
  +79±24; DNg60 +28.8±5.1 at 150; DNp58 +24.8±4.3; DNge023 +23.3±2.8. Graded, and present in
  the first 100 ms. These are gnathal (mouthpart/foreleg region) descending neurons, not
  known turning neurons.
- The repo's demo "right hemisphere" sugar IDs are annotated `left` in FlyWire (the FlyWire
  volume is mirror-flipped relative to the fly). Harmless for the game; just be consistent.

### c. Threat: looming detectors (LPLC2 108 L / 102 R, LC4 54 L / 50 R) — **yes, strong**

LPLC2 + LC4 together:

| | L50 | R50 | L150 | R150 | L250 | R250 | both150 |
|---|---|---|---|---|---|---|---|
| DNa01 | L 0 R 33.8±3.8 | L 21.2±1.2 R 0 | L 0 R 40.4±5.7 | L 38.3±1.2 R 0 | L 0 R 47.9±3.9 | L 45.0±3.2 R 0 | L 1.7±1.9 R 0.4±0.9 |
| DNa02 | L 0 R 20.4±1.7 | L 29.2±4.2 R 0 | L 0 R 10.8±4.7 | L 27.1±6.8 R 0 | L 0 R 3.8±1.2 | L 15.4±4.4 R 0 | 0 / 0 |
| DNb01 | L 0 R 17.1±3.0 | L 7.1±0.9 R 0 | L 0 R 55.0±2.5 | L 41.7±1.2 R 0 | L 0 R 66.2±1.9 | L 52.9±2.7 R 0 | L 12.5±4.6 R 24.2±3.4 |
| Giant Fiber | L 101±6 R 90±4 | L 75±5 R 120±3 | L 170±3 R 109±1 | L 98±2 R 187±3 | L 203±4 R 115±4 | L 102±3 R 220±2 | L 178±4 R 193±3 |

- **Sign: away.** Steering neurons fire only on the side opposite the threat; asymmetry index
  is exactly ±1 in all 36 one-sided trials. DNa01/DNa02 activity turns a fly toward the
  active side, so the snake turns away from the threat. Symmetric threat → steering cancels.
- **Graded:** DNa01 ipsi − contra −27.5±6.8 / −39.4±4.2 / −46.5±3.9 Hz and DNb01 −12.1±5.5 /
  −48.3±6.9 / −59.6±7.1 Hz at 50 / 150 / 250 Hz. DNa02 is *inversely* graded (−24.8 / −19.0 /
  −9.6): do not use DNa02 alone as an intensity signal.
- **Giant Fiber:** spikes in every threat trial, on both sides, more on the threatened side
  (ipsi − contra +28±19 / +75±14 / +103±16 Hz) and graded with rate. 100–200 Hz is not
  realistic (a real Giant Fiber fires about one spike per escape), but as a graded "boost"
  signal it works. DNp02, DNp04, DNp11 are even cleaner same-side threat reporters (DNp04:
  222±1 vs 0 Hz at 150 Hz; +146 / +216 / +248 Hz across rates).
- LPLC2 alone and LC4 alone each reproduce the result (DNa01 ipsi − contra at 150 Hz:
  −30.2±3.6 and −38.3±5.0). LC4 alone barely drives DNb01; LPLC2 alone does not drive
  DNp02/DNp11. Same picture in only the first 100 ms and the first 50 ms.

### d. Johnston's organ, wind-sensitive JO-C and JO-E (229 left, 204 right) — **no for steering neurons**

DNa01, DNa02, DNb01 stay at 0–5 Hz in every condition; DNg13 right fires 6–16 Hz for *left*
stimulation only. Strong same-side, graded responses exist in other descending neurons (12 of
12 trials): DNp18 +29±15 / +80±9 / +113±8 Hz, DNb06 +56 / +64 / +78, DNbe001 +27 / +40 / +54.
Their behavioural role is not something I checked.

## 4. What I could not do, and problems hit

- **NOT RUN:** moonwalker (MDN) as a deliberate output (it only reached 1–14 Hz under looming);
  other JO subtypes (A/B sound, F); bitter or other aversive taste; mixed food + threat input
  in one window; silencing experiments; decision windows shorter than 50 ms for the signal;
  the MLX/GPU ports mentioned in RESEARCH.md; more than 6 trials per condition.
- One animal, one fixed wiring, no spontaneous activity: trial-to-trial spread comes only from
  input Poisson noise, so the small sds overstate how robust this would be in a noisier model.
- Left/right are not mirror images: e.g. left DNa02 responds more than right (27 vs 11 Hz at
  150 Hz looming), and sugar on the left vs right behaves completely differently. Expect a
  mild built-in turning bias even in the channel that works.
- Whole-eye stimulation (all ~160 looming cells of one eye at once) is cruder than a real
  looming object. I did not test partial-field stimulation.
- Time lost: a wait loop watching for the wrong string, and a first attempt at 3 parallel
  processes that pushed the 8 GB machine into swap (20 s per window) and had to be restarted
  serially.
- I did not check the functional literature for the data-driven "best lateralizers"
  (DNg35, DNp18, DNb06 …). The ipsilateral-turn role I assume for DNa01/DNa02/DNb01 comes from
  the published steering literature, not from anything verified here.

## 5. Recommended sensory → fly → button mapping

- **Threat on the left/right → turn:** stimulate LPLC2 + LC4 of that eye at 50–250 Hz scaled
  by threat proximity (both eyes if both sides are threatened). Turn signal =
  (DNa01 + DNb01, right) − (DNa01 + DNb01, left), 100 ms window; positive = turn right. Optionally
  include DNa02 for sign only. This is the fly's own biology and needs no relabelling.
- **Boost:** Giant Fiber (DNp01) mean rate over both sides, with a threshold around 150 Hz
  (it is ~100 Hz even for weak threats), or DNp04 if a cleaner graded signal is wanted.
- **Food:** no honest steering mapping exists in this model. Options, in order of purity:
  (1) accept that the pure fly only flees and never seeks food, consistent with DECISIONS #2
  ("it will lose games that match no reflex"); (2) read MN9 (proboscis extension) as an "eat"
  button when sugar is sensed, without steering; (3) relabel a lateralized taste output
  (DNg35 right − left, graded, 12/12 trials) as "turn toward food" and say clearly on screen
  that this is our mapping, not a known fly turning circuit. Do not use smell: it carries no
  side information here and locks DNa02 to the left.
- **Engine:** cython target, build once, `restore()` + 100 ms window per decision, one process.
  Budget ~0.7 s per decision, ~3.5 min per 300-decision match; replays make that a non-issue.

## Files
`flysim.py` (shared: ID selection, build-once network, window runner), `bench.py`, `bench2.py`
(Q1), `run_set.py` (Q2 runs), `analyze.py` (tables), `validate_poi.py` (input-method check),
`explore*.py` (ID hunting), `results/` (per-trial DN/motor spikes as parquet, run metadata,
analysis tables). Model repo and annotations live in git-ignored `data/`.
