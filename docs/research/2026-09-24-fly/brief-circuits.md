# Brief: innate fly circuits for a gap-avoiding runner (track 1, the pure fly)

Read `COMMON.md` in this directory first.

Question: which innate Drosophila circuits, present in FlyWire v783 and in the Shiu model, fit what this game asks
(see a gap in the floor ahead, go around it or over it, keep running), better than "looming -> turn away / Giant
Fiber"? Research deeply (web: papers 2005-2026, FlyWire/Codex, reviews) and check against the local data.

Cover at least:
- Gap crossing and the visual cliff: Pick & Strauss 2005 and later work on how walking flies judge gap width
  (parallax), decide to climb, and the circuits known for it (e.g. protocerebral bridge / central complex).
- Walking-direction and speed outputs: forward walking (DNp09, oDN1), backward walking (MDN / moonwalker), stopping
  (DNa02? "stop" DNs), turning DNs beyond DNa01/DNb01 (DNa02, DNa03, DNg13, DNb05/06, DNae...), and what the
  2024-2026 descending-neuron connectome work says (e.g. Cheong et al., Braun/Sapkal et al. on distributed DN
  control, BANC / male CNS brain+nerve-cord connectomes).
- Escape that is not a Giant Fiber jump: non-GF takeoffs, takeoff direction control (Card & Dickinson), freezing,
  backing away; which visual projection neurons drive them (LC4, LPLC2, LPLC1, LC6, LC9, LC11, LC15, LC16, LC18...;
  Klapoetke 2022, Cowley 2024 and others on LC feature selectivity).
- Obstacle/collision avoidance while walking, edge and ground/horizon detection, optic flow (HS/VS, T4/T5,
  LPLC1/LPLC2), object vs. background.
- For each candidate input set and output set: are the cell types in `data/neuron_annotations.tsv` (count per side)?
  Using the connectivity in `data/Drosophila_brain_model/Connectivity_783.parquet` (pre/post model indices + weights;
  `Completeness_783.csv` gives root ids in model order), what is the shortest / strongest path from candidate inputs
  to candidate outputs (direct synapses, 2-hop weighted)? Pure pandas/numpy only; do NOT build the Brian2 model.
- Memory between decisions: is running continuously (not restoring state) defensible biologically and likely to
  help (e.g. integration, adaptation)?

Deliverable: `circuits-report.md` in this directory: (a) a ranked list of 3-6 concrete pure-fly designs (input
neurons + our signal mapping, readout neurons + our rule, what is ours vs biology, why it could beat 68 rows on v2,
the main risk), each with its evidence; (b) the pathway analysis tables; (c) sources. Start with a 10-line summary.
