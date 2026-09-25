"""The fly's measured response to every input it can get, and a stand-in brain that replays it.

Looming rates come in steps of LOOMING_STEP_HZ, so an eye has 11 levels and the brain has
11 x 11 possible inputs. Measuring each one a few times with fresh input noise gives a table from
which thousands of practice games can be played in seconds (the real brain needs about 0.7 s per
decision). The stand-in is a calibration tool only: tournament runs always use the real brain.

    uv run python -m bakeoff.fly.surface calibration/response_surface.json

Schema 2 is fly2's (bakeoff/fly/channels.py): any number of named channels, each with its own levels, every
combination measured. `--mapping M1` measures a candidate; `--shuffle-seed N` measures it on shuffled wiring
(the control, never a player):

    uv run python -m bakeoff.fly.surface --mapping M1 calibration/fly2_surface_M1.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import zlib
from pathlib import Path

from bakeoff.fly import data
from bakeoff.fly.reading import WINDOW_MS, Reading
from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ

SURFACE_SCHEMA = 1
CHANNELS_SCHEMA = 2
TRIALS = 8
LEVELS_HZ = tuple(i * LOOMING_STEP_HZ for i in range(int(MAX_HZ / LOOMING_STEP_HZ) + 1))


def _trial_seed(left_hz: float, right_hz: float, trial: int) -> int:
    return zlib.crc32(f"surface:{left_hz}:{right_hz}:{trial}".encode())


def _one_neuron_per_group(brain) -> None:
    selection = getattr(brain, "selection", None)
    if selection is not None:
        for name, members in selection.readouts.items():
            if len(members) != 1:
                raise ValueError("the surface stores spike counts and assumes one neuron per read-out group; "
                                 f"{name} has {len(members)}")


def measure_surface(brain, levels_hz=LEVELS_HZ, trials: int = TRIALS, progress=None) -> dict:
    _one_neuron_per_group(brain)
    cells = []
    for left_hz in levels_hz:
        for right_hz in levels_hz:
            readings = [brain.window(left_hz, right_hz, noise_seed=_trial_seed(left_hz, right_hz, t))
                        for t in range(trials)]
            cells.append({"left_hz": left_hz, "right_hz": right_hz,
                          "spike_counts": [r.spike_counts for r in readings]})
            if progress is not None:
                progress(len(cells), len(levels_hz) ** 2)
    return {"schema": SURFACE_SCHEMA, "window_ms": brain.window_ms, "levels_hz": list(levels_hz),
            "trials": trials, "model_commit": data.MODEL_REPO_COMMIT,
            "annotations_commit": data.ANNOTATIONS_COMMIT, "cells": cells}


def _channels_seed(input_name: str, rates: tuple[float, ...], trial: int) -> int:
    return zlib.crc32(f"surface2:{input_name}:{':'.join(map(str, rates))}:{trial}".encode())


def measure_mapping(brain, mapping, trials: int = TRIALS, progress=None) -> dict:
    """Schema 2: every combination of the mapping's channel levels, `trials` windows each, on the brain's input
    named after the mapping. Channels vary in the mapping's order, the last one fastest."""
    _one_neuron_per_group(brain)
    channels, cells = mapping.channels, []
    total = len(mapping.levels_hz) ** len(channels)
    for combo in itertools.product(mapping.levels_hz, repeat=len(channels)):
        rates = dict(zip(channels, combo))
        readings = [brain.window_of(mapping.name, rates, noise_seed=_channels_seed(mapping.name, combo, t))
                    for t in range(trials)]
        cells.append({"rates_hz": rates, "spike_counts": [r.spike_counts for r in readings]})
        if progress is not None:
            progress(len(cells), total)
    return {"schema": CHANNELS_SCHEMA, "input": mapping.name, "channels": list(channels),
            "levels_hz": {channel: list(mapping.levels_hz) for channel in channels},
            "shuffle_seed": getattr(brain, "shuffle_seed", None), "window_ms": brain.window_ms, "trials": trials,
            "model_commit": data.MODEL_REPO_COMMIT, "annotations_commit": data.ANNOTATIONS_COMMIT, "cells": cells}


class SurrogateBrain:
    """Same windows as the real Brain, answered from the table: the noise seed picks one of the
    measured trials of that input. Every read-out neuron group has one neuron, so rate = count / window.
    A schema 1 surface answers `window(left_hz, right_hz)` (fly's); schema 2 answers `window_of(input, rates)`."""

    def __init__(self, surface: dict):
        if surface.get("schema") not in (SURFACE_SCHEMA, CHANNELS_SCHEMA):
            raise ValueError(f"unknown response surface schema: {surface.get('schema')!r}")
        for key, current in (("model_commit", data.MODEL_REPO_COMMIT),
                             ("annotations_commit", data.ANNOTATIONS_COMMIT), ("window_ms", WINDOW_MS)):
            if surface[key] != current:
                raise ValueError(f"response surface was measured on a different fly "
                                 f"({key}: {surface[key]} != {current}); "
                                 "measure it again with python -m bakeoff.fly.surface")
        self.window_ms = surface["window_ms"]
        self.schema = surface["schema"]
        if self.schema == SURFACE_SCHEMA:
            self.input, self.channels = "fly", ("left", "right")
            self._cells = {(c["left_hz"], c["right_hz"]): c["spike_counts"] for c in surface["cells"]}
        else:
            self.input, self.channels = surface["input"], tuple(surface["channels"])
            self._levels = surface["levels_hz"]
            self._cells = {tuple(c["rates_hz"][ch] for ch in self.channels): c["spike_counts"] for c in surface["cells"]}
        self.shuffle_seed = surface.get("shuffle_seed")

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        if self.schema != SURFACE_SCHEMA:
            raise ValueError(f"this surface is input {self.input!r} with channels {list(self.channels)}; use window_of")
        # count / window == count / len(members) / window only when every read-out group has one
        # neuron; measure_surface's guard enforces that when the surface is written.
        trials = self._cells.get((left_hz, right_hz))
        if trials is None:
            raise KeyError(f"input ({left_hz}, {right_hz}) Hz was not measured; levels are steps of {LOOMING_STEP_HZ} Hz")
        return self._reading(trials, noise_seed)

    def window_of(self, input_name: str, rates_hz: dict, noise_seed: int | None = None) -> Reading:
        if input_name != self.input:
            raise KeyError(f"this surface was measured for input {self.input!r}, not {input_name!r}")
        if set(rates_hz) != set(self.channels):
            raise ValueError(f"input {self.input!r} has channels {list(self.channels)}, got rates for {sorted(rates_hz)}")
        key = tuple(float(rates_hz[ch]) for ch in self.channels)
        trials = self._cells.get(key)
        if trials is None:
            if self.schema == CHANNELS_SCHEMA:
                for channel, hz in zip(self.channels, key):
                    if hz not in self._levels[channel]:
                        raise KeyError(f"{channel} at {hz} Hz was not measured; its levels are {self._levels[channel]}")
            raise KeyError(f"input {dict(zip(self.channels, key))} Hz was not measured")
        return self._reading(trials, noise_seed)

    def _reading(self, trials: list, noise_seed: int | None) -> Reading:
        counts = trials[random.Random(noise_seed).randrange(len(trials))]
        seconds = self.window_ms / 1000.0
        return Reading(rates_hz={name: n / seconds for name, n in counts.items()}, spike_counts=dict(counts),
                       spike_times_ms={}, total_spikes=0, wall_ms=0.0)

    def close(self) -> None:
        pass


def load_surface(path: Path | str) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bakeoff.fly.surface",
                                     description="Measure the fly's response surface on the real brain.")
    parser.add_argument("out", help="where to write the surface (JSON)")
    parser.add_argument("--mapping", help="a fly2 candidate (M1, M2, M3): schema 2; without it, fly's two eyes")
    parser.add_argument("--shuffle-seed", type=int, help="measure on wiring shuffled with this seed (the control)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    from bakeoff.fly.channels import MAPPINGS

    if args.mapping is not None and args.mapping not in MAPPINGS:
        parser.error(f"unknown mapping {args.mapping!r}; choose from {sorted(MAPPINGS)}")
    if args.mapping is None and args.shuffle_seed is not None:
        parser.error("--shuffle-seed is for a fly2 mapping only")
    from bakeoff.fly.brain import Brain

    progress = lambda done, total: print(f"\r{done}/{total} inputs", end="", flush=True)
    if args.mapping is None:
        brain = Brain()
        measure = lambda: measure_surface(brain, progress=progress)
    else:
        mapping = MAPPINGS[args.mapping]
        brain = Brain(inputs={mapping.name: mapping.cells}, shuffle_seed=args.shuffle_seed)
        measure = lambda: measure_mapping(brain, mapping, progress=progress)
    try:
        surface = measure()
    finally:
        brain.close()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(surface, separators=(",", ":")) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
