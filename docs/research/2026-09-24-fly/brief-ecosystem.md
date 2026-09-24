# Brief: the fly-model ecosystem and the trained fly (track 2), plus speed

Read `COMMON.md` in this directory first.

Research deeply (web, GitHub, papers, 2024-2026):
- Projects that made the Shiu / FlyWire LIF brain play games or drive agents (e.g. the "fly plays Doom" and
  Chrome-dino repos, anything indexed at https://github.com/cobanov/awesome-fly): what input neurons, what readout,
  trained or not, what results, how honest the claims are. What worked that we could reuse.
- Newer or better whole-brain / whole-CNS models: BANC (brain + nerve cord), male CNS connectome, updated FlyWire
  versions, models with better neuron parameters (graded vs spiking, cell-type-specific), and whether any has a
  runnable package on Python 3.13 / Apple silicon / 8 GB RAM.
- Visual front ends: flyvis (Lappalainen et al. 2024, TuragaLab) -- licence, Python version constraints, can its
  T4/T5/LC outputs be computed for a simple rendered tunnel image and fed into the Shiu model's matching neurons;
  NeuroMechFly v2 / flygym (vision + connectome-constrained controllers), flybody.
- The trained fly: honest designs of "connectome + small learned part" (learned readout on DN spike rates, learned
  input encoder, connectome-constrained RNN trained end to end), what the literature does, how many training
  episodes / how much compute it needs, how to keep it clearly separate from the pure fly.
- Speed: GPU / MLX / PyTorch / JAX ports of the Shiu model (claims of large speedups) -- which are real, maintained,
  licenced, and produce the same spikes as Brian2 (validation). Today one 100 ms decision costs ~1.2 s on this M1.
  A faster simulator would make recalibration and training cheaper.

Deliverable: `ecosystem-report.md` in this directory: a 10-line summary first; then (a) prior art table (project,
input, readout, trained?, result, licence, activity, credibility); (b) 2-4 concrete trained-fly designs ranked, with
cost estimates on this machine; (c) simulator options ranked; (d) sources with URLs. Mark unverified claims.
