"""What one decision window of a brain yields. No heavy imports: the runner and the stand-in use it."""

from __future__ import annotations

from dataclasses import dataclass

WINDOW_MS = 100.0  # simulated time per decision


@dataclass(frozen=True)
class Reading:
    rates_hz: dict[str, float]  # "DNa01_left" -> mean rate per neuron of the group over the window
    spike_counts: dict[str, int]
    spike_times_ms: dict[str, list[float]]  # from the start of the window
    total_spikes: int  # the whole brain
    wall_ms: float
