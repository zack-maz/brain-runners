# Spike 01: can the untrained fly-brain model steer, and how fast does it run?

THROWAWAY experiment. Its output is an answer, not code we keep. Work on git branch
`spike/fly-steering` (create it), commit your scripts and REPORT.md there, do not push,
do not touch `main`. Do everything yourself; do not dispatch subagents.

## Background
brain-bakeoff pits an LLM, a small decision model and a fruit fly brain against each other
in a slither.io-style arena. The fly contestant is the published whole-brain leaky
integrate-and-fire model built from the FlyWire connectome (Shiu et al., Nature 2024;
https://github.com/philshiu/Drosophila_brain_model, MIT, Brian2), used UNTRAINED: we
Poisson-stimulate chosen sensory neurons by FlyWire root ID and read firing rates of chosen
output neurons. The game would give the fly egocentric senses ("food smell stronger on the
left", "threat on the right") as left/right sensory-neuron stimulation, and read left/right
steering neurons to turn, plus an escape neuron as "boost". Nobody has shown this model
produces lateralized steering output from lateralized sensory input. Read
`docs/RESEARCH.md` and `docs/DECISIONS.md` first.

## Questions to answer
Q1 Speed. On this Mac: time to build the network; wall-clock per 100 ms and per 1 s of
   simulated time; whether one built network can serve many short decision windows cheaply
   (Brian2 store/restore, or continuous run with changing input rates) versus rebuilding;
   numpy vs cython codegen targets if both work. Give the realistic wall-clock cost of ONE
   game decision (suggest 50–200 ms simulated windows) and of a 300-decision match.
Q2 Lateralized steering. Stimulate LEFT-side sensory neurons only, then RIGHT only, then
   both, then none (baseline), several trials each (Poisson noise differs per trial).
   Measure firing of left vs right steering descending neurons (DNa01, DNa02; add other
   steering/turning DNs you can identify) and report an asymmetry index with spread across
   trials. Is there a reliable left/right difference? Which sign (toward or away from the
   stimulated side)? Is it graded with stimulation rate (try ~3 rates)?
   Sensory sets to try, in this order, stopping early if time runs out:
   a. attractive olfactory receptor neurons, left vs right antenna (real flies turn toward
      the more strongly stimulated antenna);
   b. sugar gustatory neurons left vs right (the published, demonstrated input);
   c. a threat channel: looming detectors LPLC2 and/or LC4 left vs right, reading steering
      DNs AND the Giant Fiber (does it spike at all? is it graded with rate?);
   d. antennal mechanosensory (Johnston's organ) left vs right.
Q3 Anything that makes the idea unworkable or suggests a better output readout (for example
   a different descending neuron pair that lateralizes much more strongly).

## How
- Clone the Shiu repo into `data/` (git-ignored). It ships connectivity for FlyWire v630 and
  v783. Neuron IDs by cell type and side are NOT in that repo: get them from the public
  FlyWire annotations (https://github.com/flyconnectome/flywire_annotations, the
  supplemental neuron annotations TSV with root_id, cell_type, side, super_class). Use the
  connectivity version whose IDs match the annotations (v783) and check how many of your
  chosen IDs are actually present in the model's neuron list; report the coverage.
- Python via `uv` only, inside `spikes/01-fly-steering/` (its own pyproject is fine). No
  global installs. Brian2 2.10+ supports Apple Silicon and Python 3.12–3.14.
- Read the repo's `model.py`/`example.ipynb` for how stimulation and readout work; reuse its
  functions rather than rewriting the model. Keep its default parameters.
- Do not read, print or need any `.env` file or API key.
- Time-box: about 60 minutes of wall-clock including downloads. Prefer fewer, well-chosen
  simulations over a big sweep. If something blocks you for more than 10 minutes, write down
  what and move on.

## Deliverable
`spikes/01-fly-steering/REPORT.md`, plain language first, numbers after:
1. One-paragraph verdict: can the pure fly plausibly steer a snake? (yes / weakly / no)
2. Q1 numbers in a small table. 3. Q2 results per sensory set: neuron counts used, mean ±
sd firing per condition for left and right output neurons, asymmetry, sign, gradedness.
4. What you could not do and why. 5. Recommended sensory→fly→button mapping if any.
Be honest: a clear "no" is a useful result. Mark anything you did not actually run.
Finish your turn with a summary under 15 lines.
