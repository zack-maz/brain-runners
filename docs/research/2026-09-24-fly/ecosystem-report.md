# The fly-model ecosystem, the trained fly (track 2), and speed

Research brief: `brief-ecosystem.md` (context `COMMON.md`). Written 2026-09-24. Sources were read on GitHub (READMEs,
research logs, licence and last-push metadata through `gh api`) and on the web. "(unverified)" marks claims taken
from a project's own text that I did not reproduce, and estimates that I did not measure. No code was run and no
paid call was made.

## Summary (10 lines)

1. About 60 community projects have wired the Shiu LIF model (FlyWire v783) or the new MaleCNS v1.0 connectome (June 2026) into games. Nearly all appeared in the last three weeks, and few are rigorous.
2. The closest prior art is **tairqaldy/dino-fly** (MIT). It drives LPLC2/LC4 with a looming signal (θ, θ̇ of the nearest obstacle), and a single Giant Fiber (DNp01) spike means jump. The frozen fly scores 83 against 40 for never jumping, but **a bare threshold on its own transducer scores 281**. The brain works as a noisy threshold, and a degree-preserving shuffle of the connectome drops it to the floor.
3. The honest projects agree on one lesson: **a flexible trained part can play without the brain.** fly-craftax's PPO readout on 1,314 descending-neuron (DN) rates ended as "a clock with a small drive-dependent jitter" that ignored vision. The Digital Sphinx paper (2026) walked a fly body with a worm connectome. doomfly-rl found the wiring made training 22× slower "and buys nothing".
4. For us this means the controls matter more than the learner. Any trained fly must be compared against the same learner fed the **input without the brain**, a blind brain and a shuffled connectome.
5. Our input is two eye totals quantized to 11 levels each, so at most 121 distinct stimuli. With it, no readout can beat the best lookup table on those 121 cells. That ceiling can be computed without the brain. A useful trained fly needs **retinotopic input** first.
6. The top-ranked trained-fly design keeps the brain frozen, feeds retinotopic input (each LPLC2/LC4 cell lit by the part of the tunnel in its receptive field) and adds a **small linear readout on DN spike counts**, learned by imitating the solver (DAgger), not by RL. Cost: about 15k decisions, roughly 5 h at today's 1.2 s per decision or under 1 h on a faster engine.
7. flyvis (TuragaLab, MIT) is the credible visual front end, but it needs Python <3.13 (a separate uv venv). It models 64 optic-lobe cell types on 721 columns and stops before LC/LPLC2. Using it would mean mapping T4/T5 onto FlyWire cells by column: a project of its own. It ranks third.
8. Speed: our 1.2 s per 100 ms decision is mostly Brian2's fixed per-run cost; cython Brian2 costs about 2 s per *biological second*. A spike-exact event-driven NumPy engine written in the repo, checked against Brian2 on identical input spikes, is the best option.
9. **Kisame76/drosophila-brain-mlx** (MIT, Python 3.13, Apple Metal) is the best ready-made port: 0.29 s per biological second on an M4 Pro, about 7× faster than Brian2. It covers FlyWire v630 and MaleCNS but not v783 (unverified), it is ten days old, and it has not been measured on an M1.
10. Newer connectomes exist: MaleCNS v1.0 (166,700 neurons, brain and nerve cord, CC BY 4.0) and BANC v888 (female, brain and nerve cord). Shiu's constants were fitted to FlyWire only, and no validated whole-brain model on either is ready to adopt. Stay on FlyWire v783 for both tracks.

---

## (a) Prior art

"Credibility" is my judgement of how honestly the project separates what the fly does from what the authors built, and
whether it reports controls. Activity is the last push date (all 2026).

| Project | Brain | Input (ours/theirs) | Readout | Trained? | Result as claimed | Licence | Activity | Credibility |
|---|---|---|---|---|---|---|---|---|
| [tairqaldy/dino-fly](https://github.com/tairqaldy/dino-fly) (Chrome Dino) | Shiu LIF, FlyWire v783, own PyTorch engine | analytic θ, θ̇ of nearest obstacle → Poisson into all 104 LC4 + 210 LPLC2, gain frozen (G = 3 Hz) before play | any GF (DNp01) spike in a frame = JUMP | No (plus a mushroom-body plasticity phase, pre-registered, **no learning effect**) | 83 vs 40 (never jump) on 200 held-out seeds; bare transducer threshold 281; GF-ablated and 20+5 shuffles = 40 | MIT | 09-21 | **High**: pre-registered, reports unflattering numbers, spike-identical to Brian2 |
| [seowol-dev/flybrain-dino](https://github.com/seowol-dev/flybrain-dino) (Chrome Dino) | Shiu LIF v783, own numpy + MLX engines | rendered first-person view → R1-6 photoreceptors via recovered retinotopic map | optic-lobe population decoder (central 25° lamina − 35–75° lamina), *not* GF | No | 17.9 s of 20 s, 5/6 trials; blind and R1-6-silenced 2.85 s | none stated (NOASSERTION) | 09-24 | Medium-high: key negative finding: **LIF optic lobe has no direction selectivity** (median \|DSI\| 0.002), LPLC2 silent, DNp01 fires 34–47 Hz regardless |
| [cobanov/flyjump](https://github.com/cobanov/flyjump) "Fly Dino" | 80-cell MaleCNS subgraph, leaky tanh (not LIF) | 8 engineered observations | 16 DN activities → 16-12-3 MLP (243 params) | Yes, CEM, 15,680 episodes (~7.6 min, Mac mini) | 99/100 held-out courses; silenced circuit 0/100 | custom attribution licence | 09-12 | Medium: says itself "not superiority of biological topology" |
| [webergithub/fruitfly-lab](https://github.com/webergithub/fruitfly-lab) (Doom aim) | 3,963-neuron FlyWire v783 subgraph, Shiu constants, numba | target bearing → LC10a of matching eye (≤150 Hz) | steer = (DNa02 R−L) + (AOTU019 R−L); fire on AOTU019 | No (one calibration sweep) | 10.2 kills/episode vs 0.7 scrambled, oracle 11.5 (n = 10) | none | 09-15 | Medium-high: validated subgraph against full brain, scrambled + lesion controls; small n |
| [nftechie/doomfly](https://github.com/nftechie/doomfly) | whole MaleCNS v1.0 (166,700 n, 25.6 M edges), C++ event-driven | 3,335 R1–R6 + 811 R8 from frames | DNp20 R−L = turn, DNpe017 = move/fire ("engineered, not natural function") | Experimental dopamine rule on KC→MBON11 | **"failed its visual, conditioning and survival validation gates"** | MIT | 09-09 | High honesty, no positive result |
| [eganeganegan/flydoom](https://github.com/eganeganegan/flydoom) | MaleCNS subgraph (1k–10k) as sparse leaky rate RNN | CNN or "fly-inspired" features | policy/value heads on DN nodes | Yes, PPO; fixed / readout-only / trainable-internal modes | framework only; controls ER, degree-rewired, MLP, GRU, LSTM | none | 09-14 | Good design, no results published |
| [nonatofabio/doomfly-rl](https://github.com/nonatofabio/doomfly-rl) | connectome-wired network | pixels | trained | Yes, gradient descent | **two negative results**: gaps within one SD; wiring 22× slower to train | MIT | 09-22 | High |
| [liuzihe02/fly-craftax](https://github.com/liuzihe02/fly-craftax) | MaleCNS LIF in JAX | retina (lamina drive) + interoception | zero-shot fixed groups; then **linear readout on 1,314 DN rates, PPO** | Yes (readout only) | zero-shot: pure no-op out-survives the fly; PPO (76,800 steps, 59 min on a 4090): black-out vision leaves policy unchanged, "a clock" | MIT | 09-10 | **High**: the clearest warning for track 2 |
| [MarkUnthank/flyhard](https://github.com/MarkUnthank/flyhard) (CARLA wheel) | MaleCNS 165,122 n, trainable | camera | leg actuation via body | Yes (connection strengths) | 100/100 held-out steering targets after 600 updates, 186 s on an A6000 | MIT | 09-15 | Medium: trains the connectome's weights, so it is a connectome-shaped network, not the fly |
| [seanphan/flyt3](https://github.com/seanphan/flyt3) (tic-tac-toe) | MaleCNS full graph | board → sensory | linear readout on DN + VNC motor rates | Yes, self-play REINFORCE | (not quantified in README) | none | 09-14 | Low-medium |
| [ns2250225/fly-flappy](https://github.com/ns2250225/fly-flappy) | MaleCNS, 50 Hz | — | — | Yes ("训练", trained) | (unverified) | none | 09-16 | Low (no method details read) |
| [erojasoficial-byte/fly-brain](https://github.com/erojasoficial-byte/fly-brain) | FlyWire v783 LIF, PyTorch CUDA, NeuroMechFly body | vision/smell/taste/touch | ~1,100 DNs → hand-built mode bridge (walk/escape/groom/feed/flight) | Hebbian drift only | "individuality": 81% vs 47% escape after 24 h | MIT | 03-21 | Low-medium (over-claims per fly-craftax review) |
| [Eon Systems embodied fly](https://eon.systems/updates/embodied-brain-emulation) | Shiu LIF + Lappalainen visual model + NeuroMechFly v2 | taste, JO, vision (vision "decorative") | DNa01/DNa02 steer, oDN1 forward, MN9, escape | Body controllers by imitation learning; DN→motor mapping by hand | demo; "not validated" | (site) | 2026 | Medium: honest about gaps |
| [FlyGM, arXiv 2602.17997](https://arxiv.org/abs/2602.17997) (NeurIPS 2025) | whole-brain connectome as GNN (fixed signed weights, learned per-node MLPs) | 2 × 32×32 RGB eyes (flybody) | efferent nodes → joints | Yes, imitation then PPO | better sample efficiency than random/rewired/MLP graphs | paper | 2026 | Medium: the "GNN inductive bias vs connectome" question stays open |
| [NeuroMechFly v2](https://www.nature.com/articles/s41592-024-02497-y) (Wang-Chen et al., Nat. Methods 2024) | flyvis for vision + hand/RL controllers | rendered compound-eye view → flyvis | T1–T5, Tm, TmY activities → learned object-detection decoder | Yes (decoder, RL for navigation) | fly–fly following in closed loop | Apache-2.0 | active | **High** (peer-reviewed); the direct precedent for "flyvis + small learned part" |
| [Cowley et al. 2024, Nature](https://www.nature.com/articles/s41586-024-07451-8) | CNN → 23-unit LC bottleneck → decision net | male's reconstructed visual stream | behaviour | Yes, "knockout training" against LC silencing data | one-to-one units ↔ LC types | paper | 2024 | High; a method for making learned units mean fly cell types |
| [Digital Sphinx](https://elifesciences.org/reviewed-preprints/111516) (Brunton/Tuthill labs, 2026) | *C. elegans* 302-neuron graded model | fly body sensors | **DRL-trained interface** to fly legs | Yes (interface) | realistic fly walking, "biologically meaningless" | paper | 2026 | High; the cautionary paper for track 2 |

What we could reuse (ideas only; licences noted per repo):

- **From dino-fly, looming as θ and θ̇ over time, not a one-shot drive.** Their LPLC2/LC4 rates follow the obstacle's
  angular size and its expansion as it approaches, and the GF integrates this over hundreds of ms. A GF spike appears
  at a median 40° angular size, 510 ms after the obstacle appears. Our fly gets a fresh 100 ms window from a clean state
  per decision, with no carried state (`bakeoff/fly/brain.py:75,81`). Two of their findings bear on track 1:
  1. LC4 alone never fired the GF; LPLC2 alone did (0.66).
  2. Their jump is *one GF spike*, where ours is a mean above 200 Hz.
  Both belong to the pure-fly brief but are worth noting.
- **From dino-fly and fruitfly-lab, the control battery.** They run a degree-preserving shuffle (keeping signs, and
  optionally keeping the LC→GF edges), a lesion of the key cell (GF-ablated), a jump-rate-matched random player, and
  "the transducer alone, no brain". The last one is the control that caught dino-fly's own brain adding nothing.
- **From fruitfly-lab, a validated subgraph for speed.** Their 3,963-neuron circuit reproduced the full brain's
  lateralized DNa02 response for the left eye but was weak for the right. A subgraph has to be validated per side
  against the full brain before it replaces it.
- **From fly-craftax, the readout recipe and its failure.** Features are spike counts per window of all DNs
  (superclass `descending_neuron`, 1,314 in MaleCNS; about 1,300 in FlyWire v783), and all parameters start at zero.
  Its failure mode: the policy learned the action prior, not the stimulus.
- **From Cowley et al., making learned units carry a cell-type name.** If a learned part has units, tie each one to
  a named cell type and train with knockouts, so that "unit = LPLC2" is testable.

## (b) Trained-fly designs, ranked

Common frame for all four: a **separate player** (for example `fly_trained`), its own name and colour on the page, and
the label "connectome + learned readout (ours, trained on practice seeds ≥ 1000)". It is never mixed into the pure
fly's calibration. It is trained **only on v2 practice seeds ≥ 1000**, with the training seeds and evaluation seeds
disjoint and fixed beforehand. Every design reports the same four controls on the same evaluation seeds:

- **no-brain:** the same learner fed the encoded input directly.
- **blind brain:** input zeroed, readout kept.
- **shuffled brain:** degree- and sign-preserving shuffle, readout retrained.
- **pure fly:** today's player.

The trained fly only counts as "the brain helps" if it beats no-brain. Otherwise the write-up says what dino-fly's
says: the wiring is necessary but adds no skill.

Costs assume this M1 (8 GB), one fly process at a time, and a v2 track of 150 rows, which is at most 150 decisions.
They are given at today's Brian2 speed (1.2 s per decision) and at a fast engine's (0.15 s per decision, an estimate
from section (c), unverified).

### 1. Retinotopic eyes + frozen brain + linear DN readout, learned by imitation (recommended)

- **Input (ours, labelled):** give each LPLC2 and LC4 cell its own receptive-field centre, from its dendrite position
  in the lobula mapped to the eye's hex columns. Candidate sources are FlyWire optic-lobe column assignments
  ([flyconnectome/ol_annotations](https://github.com/flyconnectome/ol_annotations); Matsliah et al. 2024, the FlyWire
  optic-lobe column map). The "is this available per LPLC2 cell" question is unverified. Light each cell by the
  gaps in its part of the rendered tunnel, weighted by looming (angular size and its growth, as dino-fly does). The
  brain then receives *where* a gap is, not two scalar totals. This removes the 121-state ceiling of the current
  encoding.
  The same input could also serve track 1 (pure fly with a better, ours-labelled mapping), so the work is shared.
- **Brain:** Shiu LIF v783, untouched.
- **Readout (learned):** spike counts of every DN in the window (~1,300 features) → 4 logits (stay, left, right,
  jump). Multinomial logistic regression with L2 regularization, weights starting at zero. About 5k parameters,
  plain NumPy, no new dependency. A sparsity penalty (L1) additionally shows *which* DNs the readout leans on, which
  can be compared against DNa01/DNa02/DNb01/DNp01.
- **Learning:** behaviour cloning from the solver (it knows the right action on any row), with DAgger. Play the
  current readout, label every visited state with the solver's action, refit, and repeat. This is supervised
  learning, far cheaper and steadier than PPO on this budget. fly-craftax needed 76,800 steps and an RTX 4090 hour,
  and still learned a clock.
- **Cost:** 5 DAgger rounds × 20 practice tracks × up to 150 decisions ≈ 15k decisions. That is **~5 h at 1.2 s**
  (overnight, one process) or **~40 min at 0.15 s**. Fitting takes seconds. Evaluation on 5 held-out practice tracks
  is 750 decisions, ~15 min now. Memory: the brain (~1 GB) plus a 15k × 1,300 float32 matrix (~80 MB).
- **Risks:**
  - DN activity is sparse: in dino-fly only 18 of 1,299 DNs fired under looming. The features may be nearly all
    zero, and the readout would then fall back to the action prior. Mitigations are averaging more than one window
    per decision and measuring feature coverage first.
  - Poisson noise makes the same state give different features, so each state needs a few samples.

### 2. Learned readout on today's input: the one-day diagnostic

- The same readout and learning as design 1, but with the current two-eye, 11-level input. It is cheap because the
  input has only 121 cells: **precompute DN features once per cell** (121 cells × ~10 Poisson samples = 1,210
  decisions ≈ 25 min at today's speed). Every later decision is then a table lookup plus the logistic readout. Its
  purpose is to measure two numbers before anything bigger is built:
  1. **The ceiling:** the best policy on those 121 input cells with no brain. This is pure Python, seconds.
  2. How close the DN readout gets to that ceiling.

  If the ceiling itself is poor (spike 03 says the input does not know where a jump lands), that is the argument
  for design 1.
- **Cost:** under 1 h in total. It should not ship as the trained player: it cannot beat its no-brain control by
  construction.

### 3. flyvis front end → FlyWire optic-lobe neurons → brain → learned readout

- **Front end:** [flyvis](https://github.com/TuragaLab/flyvis) (MIT, v. active 2026-08), a pretrained ensemble of
  connectome-constrained graded networks: 64 cell types on a hexagonal lattice of extent 15 (721 columns), R1–R8
  through L, Mi, Tm, TmY, T4a–d and T5a–d. **It has no LC/LPLC2/LC4 cells**, and the NeuroMechFly v2 decoder read
  T1–T5, Tm and TmY. Render the tunnel as a luminance movie on the hex lattice, run flyvis, and take T4/T5 (motion)
  plus Tm/TmY activity.
- **Bridge (ours):**
  - Option (a): drive FlyWire's own T4/T5 cells column by column as Poisson rates proportional to flyvis output.
    This needs the FlyWire column map, and it pushes graded signals into spiking neurons that, per seowol-dev,
    do not reproduce direction selectivity themselves.
  - Option (b): skip the LIF optic lobe and map flyvis T4/T5 output onto LPLC2 input by the LPLC2 cells' lobula-plate
    connectivity (Klapoetke et al. 2017 describe LPLC2 as integrating outward motion from T4/T5 in four lobula-plate
    layers).

  Option (b) is more faithful to known physiology but more of it is ours.
- **Constraints:** flyvis declares `requires-python >=3.9,<3.13`, so it needs a separate Python 3.12 environment
  (uv can manage it) and a cache of its outputs per rendered frame. Tracks are deterministic, so the front end can
  run once per track offline. flyvis runtime on CPU for a 721-column movie is unverified.
- **Cost:** mostly engineering (column mapping, rendering, validation: does a looming gap drive T4/T5 outward motion
  in the right columns?), several days. Compute after caching is the same as design 1.
- **Why third:** it is the most biological route, but with the column mapping it has the most parts that are ours,
  and design 1 answers the main question first.

### 4. Connectome-constrained rate network trained end to end (FlyDoom / FlyGM style)

- Take a k-hop subgraph (LC4/LPLC2 → … → DNs, a few thousand neurons, from v783) as a sparse leaky rate RNN in
  PyTorch (MPS or CPU). Fix signs, learn per-synapse gains (train-your-fly style) or per-node descriptors (FlyGM
  style), then behaviour cloning from the solver followed by optional RL.
- **Why last:** it is no longer "the fly". It is a network in the fly's shape, as flyhard and doomfly-rl say of
  themselves. doomfly-rl measured no benefit and 22× slower training. It also leaves the Shiu model and Brian2
  behind, adds PyTorch (~1 GB wheel) to an 8 GB machine, and the Digital Sphinx critique applies in full. Worth doing
  only as its own labelled experiment ("does fly topology help this game?"), with Erdős–Rényi and degree-rewired
  controls as in FlyDoom.
- **Cost:** 1–3 days of work. Training a 5k-neuron rate net on 50k solver-labelled frames on CPU/MPS takes minutes to
  an hour (unverified).

## (c) Simulator options, ranked

Today: Brian2 2.10 with the cython target (`bakeoff/fly/brain.py:55,59`). It uses `store`/`restore` and `run` for
100 ms per decision, costing ~1.2 s, i.e. ~12 s per biological second. The same model in cython Brian2 runs about
2 s per biological second on an M4 Pro. Brian2's cost per `run()` call is largely fixed: 7.9 s per biological second
for a 200-tick run against 2.07 s for 10,000 ticks
([drosophila-brain-mlx measurements](https://github.com/Kisame76/drosophila-brain-mlx)). So most of our 1.2 s is
overhead, not integration.

| Rank | Option | Licence | Platform | Speed | Same spikes as Brian2? | Activity | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Own event-driven NumPy/SciPy engine in the repo** (ideas from dino-fly's "exact active set" and seowol-dev's `lif.py`) | ours | CPU, Python 3.13, no new dependency | est. 0.05–0.3 s per decision (unverified). seowol-dev numpy: 2.17 s per biological s, single core, M5, whole brain. From a clean state only a few hundred neurons are active, which an active-set update exploits | Achievable **exactly** given identical input spikes. dino-fly reports zero mismatches over ~10,000 spikes per trial. One trap both ports found: input arriving during the refractory period is *dropped* (`g` is `unless refractory`) | — | **Best.** Validate by feeding the same pre-generated Poisson trains to Brian2 (SpikeGeneratorGroup) and requiring identical spike trains on a few hundred recorded decisions; keep Brian2 as the slow reference test (`-m slow`) |
| 2 | [Kisame76/drosophila-brain-mlx](https://github.com/Kisame76/drosophila-brain-mlx) | MIT | Apple silicon only (Metal), Python 3.13 | fused lane 0.29 s per biological s on an M4 Pro (Brian2 cython 2.07). MaleCNS 1.17. Peak memory 665 MB (273 MB with blocking eval) | All its lanes give a bit-identical spike-count SHA-256 against its own naive lane. Against Brian2: 13,594 spikes vs Brian2's 13,448–14,239 on the same drive (stochastic, not spike-exact) | created 09-14, pushed 09-22, 2 stars | Strong candidate *to borrow from* (MIT). Unknowns: v783 support (README lists v630 and MaleCNS; unverified), M1 speed (M1 has less GPU bandwidth), and adds `mlx` |
| 3 | [tairqaldy/dino-fly](https://github.com/tairqaldy/dino-fly) `brain/` engine | MIT | PyTorch; benchmarked on an NVIDIA RTX 5060 laptop (0.27–0.6 biological s per wall s per brain); CPU path for tests | on M1: unverified | **Yes, identical spike trains** given identical input (their claim; unverified by me); sugar→MN9 within 0.9 Hz | 09-21 | Best reference for *how* to prove parity; adds PyTorch |
| 4 | [mehrantsi/flyBrain](https://github.com/mehrantsi/flyBrain) (Rust/Metal) | MIT | Apple silicon | 0.38 s per biological s, 94 MB | **No**: different refractory semantics, 16,796 vs 13,594 spikes | 09-05 | Fast and light, but not the same model |
| 5 | [seowol-dev/flybrain-dino](https://github.com/seowol-dev/flybrain-dino) `lif_mlx.py` | none stated | Apple Metal | 0.46–0.50 s per biological s on an M5 | r = 0.9988 in rates vs Brian2; 407 vs 413 active neurons | 09-24 | Read for ideas only: no licence |
| 6 | [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain) | **GPL-2.0-or-later** | Brian2CUDA / PyTorch CUDA / NEST GPU / GeNN; NVIDIA | GPU benchmarks; a "Nature" benchmark run labelled 2026_07 | Ships a ground-truth comparison against Brian2 (Jaccard, rate correlation) | 08-29, 915 stars | Maintained and serious, but CUDA-first and GPL: do not copy code in |
| 7 | [eonfathom/FastFly](https://github.com/eonfathom/FastFly), [seohyunjun/mps-malecns-model](https://github.com/seohyunjun/mps-malecns-model), [ruvnet/Connectome-OS](https://github.com/ruvnet/Connectome-OS) | none | CUDA / MPS / Rust | — | FastFly uses FP16 weights; the MPS port uses its own LIF assumptions (not Shiu's) | — | Not usable (no licence, or not the same model) |

Also in the ecosystem, not needed for us: JAX (fly-craftax, MIT), GeNN, and a 2024 result arguing that
network structure matters more than the choice of neuron model
([Zhang et al., arXiv:2404.17128](https://arxiv.org/abs/2404.17128)).

### Newer or better whole-brain / whole-CNS models

- **FlyWire v783** is still the dataset the Shiu model and its constants were fitted and validated on. It is what we
  run.
- **MaleCNS v1.0** (Berg et al., *Cell* 189(18), Sept 2026; 166,700 neurons, brain + optic lobes + VNC, 11,710
  types; CC BY 4.0). Most community games now use it. The MLX author warns that Shiu's constants "were fitted to
  FlyWire only", and on MaleCNS some stimuli drive self-sustained abdominal-VNC states. Its advantage for us would be
  real leg/wing motor neurons, which a 4-action game does not need. Not recommended now.
- **BANC v888** (female brain + nerve cord, ~188,000 neurons per its README; data CC BY 4.0 on Harvard Dataverse).
  Its paper describes whole-network LIF tests. No maintained runnable simulator package was found (unverified).
- **Graded / fitted parameters:**
  - flyvis (optic lobe, graded, task-trained time constants and gains).
  - A 2026 bioRxiv preprint fitting a connectome-constrained whole-brain rate model to spontaneous calcium activity
    ([10.64898/2026.08.21.745055](https://www.biorxiv.org/content/10.64898/2026.08.21.745055v1.full); code
    availability unverified).
  - seowol-dev's finding that uniform LIF time constants kill T4/T5 direction selectivity is the strongest argument
    for a graded front end if we ever feed images rather than looming signals.
- **Bodies:** flygym 2.1 (Apache-2.0, Python 3.12–3.14, pins mujoco 3.9 and mujoco_warp) and flybody (Apache-2.0).
  The tunnel game has no body, so neither is needed.

## Recommendation, in order

1. Build the in-repo fast engine (rank 1) with a spike-exact parity test against Brian2. Every later step becomes
   5–20× cheaper, and recalibrating the pure fly benefits too.
2. Run design 2 (1 h): measure the 121-cell ceiling and whether a DN readout reaches it.
3. Build the retinotopic LPLC2/LC4 input. It is a candidate for the pure fly as well.
4. Then design 1 as the trained fly, with the four controls, trained on practice seeds ≥ 1000 only.

## (d) Sources

Lists and articles
- awesome-fly list: https://github.com/cobanov/awesome-fly
- IBM article, "Scientists mapped a fruit fly's brain. The internet made it play Doom": https://www.ibm.com/think/news/fruit-fly-connectome-brain-map-minecraft-doom

Game and agent projects (READMEs read 2026-09-24)
- https://github.com/tairqaldy/dino-fly (and its `docs/RESEARCH.md`, `docs/ARCHITECTURE.md`)
- https://github.com/seowol-dev/flybrain-dino
- https://github.com/cobanov/flyjump
- https://github.com/webergithub/fruitfly-lab
- https://github.com/nftechie/doomfly
- https://github.com/eganeganegan/flydoom
- https://github.com/nonatofabio/doomfly-rl
- https://github.com/liuzihe02/fly-craftax (`tracker.md`, `context/prior_art.md`, `docs/plans/2026-09-10-m4-ppo.md`)
- https://github.com/MarkUnthank/flyhard
- https://github.com/seanphan/flyt3
- https://github.com/ns2250225/fly-flappy
- https://github.com/erojasoficial-byte/fly-brain
- Eon Systems embodied fly write-up: https://eon.systems/updates/embodied-brain-emulation

Simulators
- Shiu model: https://github.com/philshiu/Drosophila_brain_model (MIT); Shiu et al. 2024, *Nature* 634:210, https://doi.org/10.1038/s41586-024-07763-9
- https://github.com/Kisame76/drosophila-brain-mlx
- https://github.com/mehrantsi/flyBrain
- https://github.com/eonsystemspbc/fly-brain
- https://github.com/eonfathom/FastFly
- https://github.com/seohyunjun/mps-malecns-model
- Zhang et al. 2024, network structure vs neuron model: https://arxiv.org/abs/2404.17128

Visual front ends and bodies
- flyvis: https://github.com/TuragaLab/flyvis; docs https://turagalab.github.io/flyvis/; Lappalainen et al. 2024, *Nature*, https://www.nature.com/articles/s41586-024-07939-3
- NeuroMechFly v2 / flygym: https://github.com/NeLy-EPFL/flygym; Wang-Chen et al. 2024, *Nat. Methods*, https://www.nature.com/articles/s41592-024-02497-y
- flybody: https://github.com/TuragaLab/flybody; Vaxenburg et al. 2025, *Nature*, https://www.nature.com/articles/s41586-025-09029-4
- train-your-fly: https://github.com/eudald-seeslab/train-your-fly

Trained-connectome literature
- FlyGM: https://arxiv.org/abs/2602.17997
- Digital Sphinx: https://elifesciences.org/reviewed-preprints/111516; The Transmitter coverage, https://www.thetransmitter.org/systems-neuroscience/digital-sphinx-raises-questions-about-connectome-models/
- Cowley et al. 2024, knockout training: https://www.nature.com/articles/s41586-024-07451-8
- Whole-brain rate model fitted to spontaneous activity (2026 preprint): https://www.biorxiv.org/content/10.64898/2026.08.21.745055v1.full

Connectomes
- MaleCNS: https://male-cns.janelia.org/; Berg et al. 2026, *Cell*, https://www.cell.com/cell/fulltext/S0092-8674(26)00942-6
- BANC: https://github.com/htem/BANC-project; data https://doi.org/10.7910/DVN/7WTH1N
- FlyWire annotations: https://github.com/flyconnectome/flywire_annotations
- Optic-lobe annotations and column matches: https://github.com/flyconnectome/ol_annotations

Not verified by me: every speed figure (each is the project's own measurement), dino-fly's spike-exact parity, the
M1 speed of any port, whether drosophila-brain-mlx loads v783, whether per-cell LPLC2 receptive-field positions can
be derived from `ol_annotations`, flyvis CPU runtime, and fly-flappy's and flyt3's results.
