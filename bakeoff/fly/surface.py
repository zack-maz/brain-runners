"""The fly's measured response to every input it can get, and a stand-in brain that replays it.

Looming rates come in steps of LOOMING_STEP_HZ, so an eye has 11 levels and the brain has
11 x 11 possible inputs. Measuring each one a few times with fresh input noise gives a table from
which thousands of practice games can be played in seconds (the real brain needs about 0.7 s per
decision). The stand-in is a calibration tool only: tournament runs always use the real brain.

    uv run python -m bakeoff.fly.surface calibration/response_surface.json
"""

from __future__ import annotations

import json
import random
import sys
import zlib
from pathlib import Path

from bakeoff.fly import data
from bakeoff.fly.reading import WINDOW_MS, Reading
from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ

SURFACE_SCHEMA = 1
TRIALS = 8
LEVELS_HZ = tuple(i * LOOMING_STEP_HZ for i in range(int(MAX_HZ / LOOMING_STEP_HZ) + 1))


def _trial_seed(left_hz: float, right_hz: float, trial: int) -> int:
    return zlib.crc32(f"surface:{left_hz}:{right_hz}:{trial}".encode())


def measure_surface(brain, levels_hz=LEVELS_HZ, trials: int = TRIALS, progress=None) -> dict:
    selection = getattr(brain, "selection", None)
    if selection is not None:
        for name, members in selection.readouts.items():
            if len(members) != 1:
                raise ValueError("the surface stores spike counts and assumes one neuron per read-out group; "
                                 f"{name} has {len(members)}")
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


class SurrogateBrain:
    """Same `window()` as the real Brain, answered from the table: the noise seed picks one of the
    measured trials of that input. Every read-out neuron group has one neuron, so rate = count / window."""

    def __init__(self, surface: dict):
        if surface.get("schema") != SURFACE_SCHEMA:
            raise ValueError(f"unknown response surface schema: {surface.get('schema')!r}")
        for key, current in (("model_commit", data.MODEL_REPO_COMMIT),
                             ("annotations_commit", data.ANNOTATIONS_COMMIT), ("window_ms", WINDOW_MS)):
            if surface[key] != current:
                raise ValueError(f"response surface was measured on a different fly "
                                 f"({key}: {surface[key]} != {current}); "
                                 "measure it again with python -m bakeoff.fly.surface")
        self.window_ms = surface["window_ms"]
        self._cells = {(c["left_hz"], c["right_hz"]): c["spike_counts"] for c in surface["cells"]}

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        # count / window == count / len(members) / window only when every read-out group has one
        # neuron; measure_surface's guard enforces that when the surface is written.
        trials = self._cells.get((left_hz, right_hz))
        if trials is None:
            raise KeyError(f"input ({left_hz}, {right_hz}) Hz was not measured; levels are steps of {LOOMING_STEP_HZ} Hz")
        counts = trials[random.Random(noise_seed).randrange(len(trials))]
        seconds = self.window_ms / 1000.0
        return Reading(rates_hz={name: n / seconds for name, n in counts.items()}, spike_counts=dict(counts),
                       spike_times_ms={}, total_spikes=0, wall_ms=0.0)

    def close(self) -> None:
        pass


def load_surface(path: Path | str) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m bakeoff.fly.surface <out.json>", file=sys.stderr)
        return 2
    from bakeoff.fly.brain import Brain

    brain = Brain()
    try:
        surface = measure_surface(brain, progress=lambda done, total: print(f"\r{done}/{total} inputs", end="", flush=True))
    finally:
        brain.close()
    out = Path(argv[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(surface, separators=(",", ":")) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
