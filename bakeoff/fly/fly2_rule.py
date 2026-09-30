"""The rule that picks fly2's input mapping and fixes its numbers: written before any surface was measured.

Design: docs/history/superpowers/specs/2026-09-24-fly2-design.md, "Order and gates", step 3 (decision 41). Everything
this rule chooses is OURS, not the fly's biology: which mapping turns gaps into input, the gain and falloff of
that mapping, and the two thresholds on the fly's read-out neurons.

- For each candidate mapping (M1, M2, M3) every point of GRID (gain x falloff x turn threshold x jump threshold,
  in that nesting order) plays the practice seeds with the stand-in brain made from that candidate's measured
  surface.
- The highest mean rows survived wins. Ties go to the candidate listed first in CANDIDATE_ORDER, then to the
  first point in grid order.
- The winner plays HELD_OUT_SEEDS once. Its numbers are then frozen in bakeoff/players/fly2.py.
- The no-brain control has its own grid (NO_BRAIN_GRID) over the winner's gain and falloff, and is judged by
  the same rule. The shuffled-wiring control reuses GRID.
- Tournament seeds (below 1000) are never played.
"""

from __future__ import annotations

import itertools

PRACTICE_SEEDS = range(1000, 1200)
HELD_OUT_SEEDS = range(1200, 1400)
CHECK_SEEDS = range(1000, 1020)  # what the real brain replays afterwards, to see how far the stand-in holds
CANDIDATE_ORDER = ("M1", "M2", "M3")

GAINS_HZ = (100.0, 250.0, 500.0)
FALLOFFS = (2.0, 3.0, 4.0)
TURN_THRESHOLDS_HZ = (0.0, 10.0, 20.0, 40.0)
JUMP_THRESHOLDS_HZ = tuple(100.0 + 25.0 * i for i in range(9))  # 100 to 300 Hz
NO_BRAIN_TURN_THRESHOLDS_HZ = (0.0, 50.0, 100.0, 200.0)
NO_BRAIN_JUMP_THRESHOLDS_HZ = tuple(100.0 * i for i in range(1, 16))  # 100 to 1,500 Hz


def grid(gains_hz=GAINS_HZ, falloffs=FALLOFFS, turn_thresholds_hz=TURN_THRESHOLDS_HZ,
         jump_thresholds_hz=JUMP_THRESHOLDS_HZ) -> list[dict]:
    """Every configuration, in grid order: gain outermost, jump threshold innermost."""
    return [{"gain_hz": g, "falloff": f, "turn_threshold_hz": t, "jump_threshold_hz": j}
            for g, f, t, j in itertools.product(gains_hz, falloffs, turn_thresholds_hz, jump_thresholds_hz)]


GRID = grid()
NO_BRAIN_GRID = grid(turn_thresholds_hz=NO_BRAIN_TURN_THRESHOLDS_HZ, jump_thresholds_hz=NO_BRAIN_JUMP_THRESHOLDS_HZ)


def pick_winner(scored: dict[str, list[dict]]) -> dict:
    """`scored`: candidate -> its results in grid order, each with `mean_rows`. Returns the winning result with
    its `candidate` added: the highest mean rows, ties to CANDIDATE_ORDER, then to grid order. A candidate
    that is not in CANDIDATE_ORDER, or no result at all, is an error."""
    unknown = sorted(set(scored) - set(CANDIDATE_ORDER))
    if unknown:
        raise ValueError(f"unknown candidates {unknown}; the order is {CANDIDATE_ORDER}")
    ranked = [(-result["mean_rows"], CANDIDATE_ORDER.index(name), i, name)
              for name, results in scored.items() for i, result in enumerate(results)]
    if not ranked:
        raise ValueError("nothing was scored")
    _, _, i, name = min(ranked)
    return {"candidate": name, **scored[name][i]}
