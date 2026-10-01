# Addendum (from the user, 2026-09-24): use the FlyWire viewer project as a mapping tool

The user asks that you use `/Users/zackmaz/Documents/PROJECTS/LEARN/flywire/motg-flywire` ("Visualising Fruit Fly Neurons",
the user's own FlyWire 783 viewer; read its README.md) to help map neurons and synapses. Read-only: do not modify it.

What it has that our Shiu data does not:
- `data/raw/fafb_783_split_edgelist.feather` (532 MB): synapse counts per (pre, post, compartment) -- whether a
  connection lands on axon or dendrite. Load only the columns you need (pyarrow), mind the 8 GB machine.
- `data/raw/neuron_neuropil_counts.parquet`: synapses per neuron per neuropil, input vs output role -- tells where a
  neuron receives and sends (e.g. which LC types output in which optic glomeruli, which DNs take input in the
  posterior slope / GNG).
- `data/raw/fafb_783_meta.feather`, `data/raw/neuron_annotations.tsv`: the same annotations (cell_type, side, flow,
  super_class, positions).
- `public/data/flow_rank.bin` (uint8 per neuron in annotations order: sensory->motor traversal step, Schlegel 2021),
  `public/data/connections.bin` (CSR, pairs >= 5 synapses; layout in `scripts/build_connectome.py`),
  `public/data/groupings.*` (Leiden brain modules, Infomap flow modules, connectivity types, hub level; see
  `scripts/build_clusters.py`). Flow modules are a quick way to see which visual inputs share a module with which DNs.
- The viewer itself (`npm run dev`, or `npx vite --port 5199 --strictPort`) shows a neuron's strongest inputs and
  outputs; use it only if a picture helps the report (screenshots go in this research directory, not the repo).
Note: FAFB coordinates are mirrored; FlyWire's `side` annotation is corrected, the coordinates are not (see its README).

Use it for the pathway analysis (input types -> output types, 1-2 hops, by compartment and neuropil), and say in
the report which numbers came from which source. The Shiu model's own connectivity
(`data/Drosophila_brain_model/Connectivity_783.parquet`) stays the ground truth for what the simulation will do.
