"""fly2's candidate input mappings: which gaps drive which of the fly's cells, and how hard. Pure; no brain.

Everything here is OURS, not the fly's biology (decision 41): which lanes a channel shows, which cell types of
which eye it drives, and the rate a gap adds (gain / row ** falloff). The fly's own part is what the wiring does
with that input. The turn read-out of each candidate was chosen by spike 04 (decision 42).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_HZ = 500.0  # every channel is capped here; lifting fly's 250 Hz cap lets a side gap add to a centre gap

# fly's own input, as channels: each eye's LPLC2 + LC4 (bakeoff/senses.py:looming_rates feeds it)
FLY_CELLS = {"left": (("LPLC2", "left"), ("LC4", "left")), "right": (("LPLC2", "right"), ("LC4", "right"))}

STEERING_ALL = ("DNa02", "DNa01", "DNg13")
STEERING_NO_DNA02 = ("DNa01", "DNg13")


@dataclass(frozen=True)
class Mapping:
    name: str
    summary: str  # one line for the lobby and the page
    cells: dict[str, tuple[tuple[str, str], ...]]  # channel -> (cell type, side) it drives, in channel order
    sees: dict[str, tuple[int, ...]]  # channel -> the lane offsets whose gaps it adds up
    step_hz: float  # levels are 0 to MAX_HZ in these steps
    turn_types: tuple[str, ...]  # read-out: (right - left) of these; decision 42

    @property
    def channels(self) -> tuple[str, ...]:
        return tuple(self.cells)

    @property
    def levels_hz(self) -> tuple[float, ...]:
        return tuple(i * self.step_hz for i in range(int(MAX_HZ / self.step_hz) + 1))


LEFT_SIDE, RIGHT_SIDE = (-3, -2, -1), (1, 2, 3)

MAPPINGS = {
    "M1": Mapping(
        name="M1", summary="a straight-ahead channel",
        cells={"centre": (("LPLC2", "left"), ("LPLC2", "right")), "left": (("LC4", "left"),),
               "right": (("LC4", "right"),)},
        sees={"centre": (0,), "left": LEFT_SIDE, "right": RIGHT_SIDE}, step_hz=100.0, turn_types=STEERING_ALL),
    "M2": Mapping(
        name="M2", summary="narrow eyes",
        cells=dict(FLY_CELLS), sees={"left": (-1, 0), "right": (0, 1)}, step_hz=50.0,
        turn_types=STEERING_NO_DNA02),
    "M3": Mapping(
        name="M3", summary="a sideways channel",
        cells={"centre": tuple((t, s) for t in ("LPLC2", "LC4") for s in ("left", "right")),
               "left": (("LPLC4", "left"), ("LC22", "left")), "right": (("LPLC4", "right"), ("LC22", "right"))},
        sees={"centre": (0,), "left": LEFT_SIDE, "right": RIGHT_SIDE}, step_hz=100.0, turn_types=STEERING_ALL),
}


def to_level(hz: float, step_hz: float) -> float:
    return math.floor(min(hz, MAX_HZ) / step_hz + 0.5) * step_hz


def rates(senses: dict, mapping: Mapping, gain_hz: float, falloff: float) -> dict[str, float]:
    """Each channel's input rate: the sum of gain / row ** falloff over the gaps it sees, capped and quantized
    to the mapping's levels, so every rate is one the measured surface holds."""
    total = {channel: 0.0 for channel in mapping.channels}
    for entry in senses["ahead"]:
        intensity = gain_hz / entry["row"] ** falloff
        for offset in entry["gaps_relative"]:
            for channel, offsets in mapping.sees.items():
                if offset in offsets:
                    total[channel] += intensity
    return {channel: to_level(hz, mapping.step_hz) for channel, hz in total.items()}
