"""Charts, for the Brain Run charts screen (decision 53, docs/superpowers/specs/2026-09-28-study-design.md,
section 4): every recorded episode of this game, each player and track once from the newest run that completed
it, scored by the benchmark. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here
adds a statistic.

All the data, as the user asked: the held-out tracks and the practice tracks alike. Every pair is compared only
on the tracks both players ran; a player's own mean is over whatever tracks it ran, so the screen says how many
and which."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import benchmark, load
from bakeoff.fly.fly2_rule import PRACTICE_SEEDS  # cheap: no brian2 (bakeoff/fly/__init__.py imports nothing)
from bakeoff.game.rules import Rules
from bakeoff.records import pick

# the study's own tracks (decision 53): no player was tuned on them, none played them before the study
HELD_OUT = (100, 199)

# fly2's frozen numbers were fitted on these seeds (calibration/FLY2_REPORT.md, decision 43): a mean over them is
# in-sample for fly2 in a way it is not for anyone else, so `charts_of` counts them.
TUNED_ON = {"fly2": [min(PRACTICE_SEEDS), max(PRACTICE_SEEDS)]}


def charts_of(out_root: Path | str, rules: Rules) -> dict:
    """{game, max_rows, tracks, held_out, bench (bench.benchmark's numbers, or None), why, left_out, unreadable,
    tuned_on, tuned_tracks}. Like `benchmark_of`, it answers with a reason instead of failing. `tracks` is the
    first and last track scored; `tuned_tracks` is, per frozen player, how many of its tracks here are ones its
    numbers were fitted on."""
    about = {"held_out": list(HELD_OUT), "tuned_on": TUNED_ON}
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "tracks": None, "bench": None,
                "why": "no run has been recorded yet.", "left_out": 0, "unreadable": [], "tuned_tracks": {}, **about}
    sources, left_out, unreadable = pick(out_root, rules)
    seeds = [seed for source in sources for _, seed in source.episodes]
    tuned = {player: sum(1 for source in sources for p, seed in source.episodes if p == player and lo <= seed <= hi)
             for player, (lo, hi) in TUNED_ON.items()}
    numbers, why = None, None
    if not sources:
        why = f"no completed track of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(sources))
        except (OSError, ValueError) as e:
            why = f"the charts could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "tracks": [min(seeds), max(seeds)] if seeds else None,
            "bench": numbers, "why": why, "left_out": left_out, "unreadable": unreadable,
            "tuned_tracks": {p: n for p, n in tuned.items() if n}, **about}
