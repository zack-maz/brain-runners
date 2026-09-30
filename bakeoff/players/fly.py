"""The fly player: looming rates in, the brain's read-out neurons out, two thresholds between."""

from __future__ import annotations

import zlib
from typing import Callable

from bakeoff.fly import shared
from bakeoff.fly.channels import FLY_CELLS
from bakeoff.game.engine import Game
from bakeoff.players.base import Decision
from bakeoff.senses import LOOMING_FALLOFF, LOOMING_GAIN_HZ, looming_rates

# The fly's only tuning, and OURS: fixed once on practice seeds 1000-1199 together with the looming
# gain and falloff in bakeoff/senses.py (docs/calibration/REPORT.md). Do not retune: tournament seeds
# must never influence these numbers. A turn threshold of 0 means any net steering spike turns.
TURN_THRESHOLD_HZ = 0.0
JUMP_THRESHOLD_HZ = 200.0
CALIBRATED = True


def turn_signal_hz(rates_hz: dict[str, float]) -> float:
    """(DNa01 + DNb01, right) - (DNa01 + DNb01, left). These neurons fire on the side opposite a
    one-sided threat and turn the fly toward the active side, so positive means turn right."""
    return (rates_hz["DNa01_right"] + rates_hz["DNb01_right"]) - (rates_hz["DNa01_left"] + rates_hz["DNb01_left"])


def jump_signal_hz(rates_hz: dict[str, float]) -> float:
    """Giant Fiber (DNp01) mean rate over both sides."""
    return (rates_hz["DNp01_left"] + rates_hz["DNp01_right"]) / 2.0


def choose(rates_hz: dict[str, float], turn_threshold_hz: float, jump_threshold_hz: float) -> str:
    if jump_signal_hz(rates_hz) > jump_threshold_hz:
        return "jump"  # jump wins over a turn
    turn = turn_signal_hz(rates_hz)
    if turn > turn_threshold_hz:
        return "right"
    if turn < -turn_threshold_hz:
        return "left"
    return "stay"


def noise_seed(seed: int, row: int) -> int:
    """Input noise is the model's only randomness; seeding it per decision makes a run repeatable."""
    return zlib.crc32(f"fly:{seed}:{row}".encode())


def _real_brain():
    from bakeoff.fly import shared  # the brain itself imports brian2 only when a fly actually plays

    return shared.acquire("fly", FLY_CELLS)


class FlyPlayer:
    name = "fly"

    def __init__(self, brain_factory: Callable[[], object] = _real_brain,
                 turn_threshold_hz: float = TURN_THRESHOLD_HZ, jump_threshold_hz: float = JUMP_THRESHOLD_HZ,
                 gain_hz: float = LOOMING_GAIN_HZ, falloff: float = LOOMING_FALLOFF):
        self._brain_factory = brain_factory
        self._brain = None  # about 1 GB: built on the first reset(), not when the CLI lists players
        if brain_factory is _real_brain:
            shared.want("fly", FLY_CELLS)  # one brain per process, shared with any other fly of the run
        self._seed = 0
        self.turn_threshold_hz, self.jump_threshold_hz = turn_threshold_hz, jump_threshold_hz
        self.gain_hz, self.falloff = gain_hz, falloff

    def preflight(self) -> None:
        """Called by Runner.run before the run directory exists: a fly without its data is a usage error."""
        if self._brain_factory is _real_brain:
            from bakeoff.fly import data  # light: no brian2 import until a fly actually plays

            data.require()

    def reset(self, game: Game, seed: int) -> None:
        self._seed = seed
        if self._brain is None:
            self._brain = self._brain_factory()

    def act(self, senses: dict) -> Decision:
        left_hz, right_hz = looming_rates(senses, self.gain_hz, self.falloff)
        # senses["rows_survived"] is the runner's row at decision time (Game._cleared == row while alive), so this is the
        # documented crc32("fly:{seed}:{row}"). If the engine ever changes that, pass the row in explicitly.
        seed = noise_seed(self._seed, senses["rows_survived"])
        reading = self._brain.window(left_hz, right_hz, noise_seed=seed)
        action = choose(reading.rates_hz, self.turn_threshold_hz, self.jump_threshold_hz)
        return Decision(action, info={
            "left_hz": left_hz, "right_hz": right_hz, "noise_seed": seed,
            "rates_hz": reading.rates_hz, "spike_counts": reading.spike_counts,
            "spike_times_ms": reading.spike_times_ms, "total_spikes": reading.total_spikes,
            "turn_signal_hz": turn_signal_hz(reading.rates_hz), "jump_signal_hz": jump_signal_hz(reading.rates_hz),
            "turn_threshold_hz": self.turn_threshold_hz, "jump_threshold_hz": self.jump_threshold_hz,
            "wall_ms": reading.wall_ms,
        })

    def observe(self, executed_action: str) -> None:
        pass

    def close(self) -> None:
        if self._brain is not None:
            self._brain.close()
            self._brain = None
