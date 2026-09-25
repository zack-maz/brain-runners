"""fly2, the second pure fly: the same untrained wiring as fly, a richer input and a readout of its steering neurons.

Design: docs/superpowers/specs/2026-09-24-fly2-design.md (decisions 41 and 42). The fly's own part is the wiring
and the model, which cells get input and which cells are read. OURS, and labelled as ours everywhere:
- the input mapping (bakeoff/fly/channels.py): which gaps drive which cells, and how hard;
- the readout: turn = (right - left) of the mapping's steering neurons, jump = the Giant Fiber's mean;
- the rule: dodge before jump. A turn beyond its threshold goes left or right; otherwise a Giant Fiber above
  its threshold jumps; otherwise stay (fly lets the jump win);
- the numbers below, fixed on practice seeds by bakeoff/fly/fly2_rule.py and then frozen.
"""

from __future__ import annotations

import zlib
from typing import Callable

from bakeoff.fly import shared
from bakeoff.fly.channels import MAPPINGS, rates
from bakeoff.game.engine import Game
from bakeoff.players.base import Decision
from bakeoff.players.fly import jump_signal_hz

# Frozen by the calibration on practice seeds 1000-1199 (calibration/FLY2_REPORT.md, decision 43). Never retune:
# tournament seeds must never influence these numbers.
MAPPING = "M3"
GAIN_HZ = 250.0
FALLOFF = 2.0
TURN_THRESHOLD_HZ = 40.0
JUMP_THRESHOLD_HZ = 175.0
CALIBRATED = True
# Copied from calibration/FLY2_REPORT.md's Controls table (mean rows on the held-out seeds, stand-in brain);
# tests/test_fly2_player.py checks every value against the report. "candidates" is how many mappings were measured.
CONTROLS = {"seeds": "1200-1399", "practice_seeds": "1000-1199", "candidates": 3,
            "fly2": 82.34, "no_brain": 74.05, "shuffled": 27.84, "fly": 65.98}


def about() -> str:
    """One line for the lobby: what fly2 is, from the frozen mapping (never typed into the page)."""
    return f"{MAPPINGS[MAPPING].summary}, walking-steering neurons, dodge before jump"


def turn_signal_hz(rates_hz: dict[str, float], turn_types: tuple[str, ...]) -> float:
    """(right - left) summed over `turn_types`. Each of these turns the fly toward its own side (Rayshubskiy 2025,
    Yang 2024) and fires on the side away from a one-sided threat (spike 04), so positive means turn right."""
    return sum(rates_hz[f"{t}_right"] - rates_hz[f"{t}_left"] for t in turn_types)


def choose(turn_hz: float, jump_hz: float, turn_threshold_hz: float, jump_threshold_hz: float) -> tuple[str, str]:
    """(action, branch): dodge before jump."""
    if abs(turn_hz) > turn_threshold_hz:
        return ("right" if turn_hz > 0 else "left"), "dodge"
    if jump_hz > jump_threshold_hz:
        return "jump", "jump"
    return "stay", "stay"


def no_brain_signals(channel_hz: dict[str, float]) -> tuple[float, float]:
    """The no-brain control's (turn, jump): a gap on the left turns right, and every channel adds to the jump."""
    return channel_hz.get("left", 0.0) - channel_hz.get("right", 0.0), sum(channel_hz.values())


def noise_seed(seed: int, row: int) -> int:
    return zlib.crc32(f"fly2:{seed}:{row}".encode())


def _real_brain(mapping_name: str):
    return shared.acquire(mapping_name, MAPPINGS[mapping_name].cells)


class Fly2Player:
    name = "fly2"

    def __init__(self, brain_factory: Callable[[str], object] = _real_brain, mapping: str = MAPPING,
                 gain_hz: float = GAIN_HZ, falloff: float = FALLOFF, turn_threshold_hz: float = TURN_THRESHOLD_HZ,
                 jump_threshold_hz: float = JUMP_THRESHOLD_HZ):
        self.mapping = MAPPINGS[mapping]
        self._brain_factory = brain_factory
        self._brain = None  # the process's one brain, taken on the first reset()
        self._seed = 0
        self.gain_hz, self.falloff = gain_hz, falloff
        self.turn_threshold_hz, self.jump_threshold_hz = turn_threshold_hz, jump_threshold_hz
        if brain_factory is _real_brain:
            shared.want(self.mapping.name, self.mapping.cells)

    def preflight(self) -> None:
        """A real fly2 plays only once its numbers are frozen; calibration uses the stand-in brain."""
        if self._brain_factory is _real_brain:
            if not CALIBRATED:
                raise ValueError("fly2 is not calibrated yet: run python -m bakeoff.fly.calibrate2 first "
                                 "(calibration/FLY2_REPORT.md)")
            from bakeoff.fly import data

            data.require()

    def reset(self, game: Game, seed: int) -> None:
        self._seed = seed
        if self._brain is None:
            self._brain = self._brain_factory(self.mapping.name)

    def act(self, senses: dict) -> Decision:
        channel_hz = rates(senses, self.mapping, self.gain_hz, self.falloff)
        seed = noise_seed(self._seed, senses["rows_survived"])
        reading = self._brain.window_of(self.mapping.name, channel_hz, noise_seed=seed)
        turn = turn_signal_hz(reading.rates_hz, self.mapping.turn_types)
        jump = jump_signal_hz(reading.rates_hz)
        action, branch = choose(turn, jump, self.turn_threshold_hz, self.jump_threshold_hz)
        return Decision(action, info={
            "mapping": self.mapping.name, "channels_hz": channel_hz, "noise_seed": seed,
            "rates_hz": reading.rates_hz, "spike_counts": reading.spike_counts,
            "spike_times_ms": reading.spike_times_ms, "total_spikes": reading.total_spikes,
            "turn_types": list(self.mapping.turn_types), "turn_signal_hz": turn, "jump_signal_hz": jump,
            "turn_threshold_hz": self.turn_threshold_hz, "jump_threshold_hz": self.jump_threshold_hz,
            "branch": branch, "wall_ms": reading.wall_ms,
        })

    def observe(self, executed_action: str) -> None:
        pass

    def close(self) -> None:
        if self._brain is not None:
            self._brain.close()
            self._brain = None


class NoBrainPlayer:
    """The no-brain control (calibration only, never registered): fly2's channel rates put through fly2's rule
    with the brain skipped. If it plays as well as fly2, the gain came from our mapping and rule."""

    name = "fly2_no_brain"

    def __init__(self, mapping: str, gain_hz: float, falloff: float, turn_threshold_hz: float,
                 jump_threshold_hz: float):
        self.mapping = MAPPINGS[mapping]
        self.gain_hz, self.falloff = gain_hz, falloff
        self.turn_threshold_hz, self.jump_threshold_hz = turn_threshold_hz, jump_threshold_hz

    def reset(self, game: Game, seed: int) -> None:
        pass

    def act(self, senses: dict) -> Decision:
        channel_hz = rates(senses, self.mapping, self.gain_hz, self.falloff)
        turn, jump = no_brain_signals(channel_hz)
        action, branch = choose(turn, jump, self.turn_threshold_hz, self.jump_threshold_hz)
        return Decision(action, info={"channels_hz": channel_hz, "branch": branch})

    def observe(self, executed_action: str) -> None:
        pass
