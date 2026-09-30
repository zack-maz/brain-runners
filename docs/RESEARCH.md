# Fly-brain resources: what a research pass found (2026-09-19)

This is a research pass from 2026-09-19; it is not kept current. The project uses FlyWire v783 connectivity
(138,639 neurons in the model) and steers with DNa01 + DNb01 (DNa02 is logged only, never decides). For current
facts about the fly, see `docs/FORMATS.md` and the fly code (`bakeoff/fly/`).

Gathered by a web-research agent; items marked (unverified) are its claims about very
recent material that nobody here has checked by running code.

## The contestant: Shiu et al. whole-brain model
- Repo: https://github.com/philshiu/Drosophila_brain_model — MIT, Brian2, last push 2024-09.
  Paper: "A Drosophila computational brain model reveals sensorimotor processing", Nature 2024.
- Data ships in the repo (FlyWire v630 and v783 connectivity, about 185 MB total). No FlyWire
  account needed. About 127k neurons.
- Drive it by giving a list of FlyWire neuron IDs to Poisson-activate at a chosen rate (and
  optionally a list to silence); read spike rates of any neurons by ID.
- Demonstrated in the paper/repo: sugar and bitter taste neurons → MN9 (proboscis extension
  motor neuron, ID 720575940660219265); antennal mechanosensory → grooming circuit.
- No learning, no plasticity, no state carried between runs.
- No visual front end in the tooling. Optic-lobe neurons exist as nodes, but nothing turns
  pixels into photoreceptor input.
- Brian2 2.10.1 has macOS ARM64 wheels and supports Python 3.12–3.14.
- Speed: the repo says 30 one-second trials take about 20 minutes on Colab. No laptop
  benchmark published. Must be measured here (first spike).

## Not used for the pure-wiring contestant
- flyvis (https://github.com/TuragaLab/flyvis): connectome-constrained fly visual system,
  MIT, maintained, needs Python <3.13, no motor output. Would need a trained decoder.
- flygym / NeuroMechFly and Janelia "flybody": detailed bodies, but controllers are trained
  by RL or imitation, not derived from the connectome.

## Neurons that map to game buttons
Present as nodes in the connectome, addressable by ID. Only the first two are demonstrated
in the published model; the rest would be our own untested extension and must be labelled so.
- Feeding: MN9 (demonstrated).
- Antennal grooming, left vs right (demonstrated).
- Escape jump: looming detectors LPLC2 / LC4 → Giant Fiber (untested in this model).
- Steering: DNa01 / DNa02 (untested; no visual input to drive them).
- Backward walking: moonwalker MDN (untested).

## Recent ecosystem (unverified)
The agent reports a Janelia male CNS connectome release (brain + nerve cord, 2026) and a
wave of days-old hobby repos ("fly plays Doom", a Chrome-dino clone with a trained readout,
GPU and Apple-MLX ports of the Shiu model claiming large speedups), indexed at
https://github.com/cobanov/awesome-fly and covered sceptically by Hackaday. Treat as
inspiration and leads to test, not as precedent.

## 2026-09-24: research for fly2

Three research agents answered briefs before the design of `fly2`
(`docs/history/superpowers/specs/2026-09-24-fly2-design.md`): why `fly` dies, which inborn circuits fit the game, and what
other projects did with this model. Their reports and the briefs they were given are in
`docs/research/2026-09-24-fly/`. Spike 04, the probe that followed, is on branch `spike/fly2-probe`,
`docs/spikes/04-fly2-probe/REPORT.md`.
