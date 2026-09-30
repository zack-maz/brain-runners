"""Charts, for the Brain Runners charts screen (decision 53, docs/superpowers/specs/2026-09-28-study-design.md,
section 4): every recorded episode of this game, each player and track once from the newest run that completed
it, scored by the benchmark. Reads files only, spends nothing. The numbers are `bakeoff bench`'s; nothing here
adds a statistic.

All the data, as the user asked: the held-out tracks and the practice tracks alike. Every pair is compared only
on the tracks both players ran; a player's own mean is over whatever tracks it ran, so the screen says how many
and which. The Writeup asks for the held-out tracks alone (`tracks=HELD_OUT`), since its Method promises them."""

from __future__ import annotations

from pathlib import Path

from bakeoff.bench import Source, benchmark, load
from bakeoff.fly.fly2_rule import PRACTICE_SEEDS  # cheap: no brian2 (bakeoff/fly/__init__.py imports nothing)
from bakeoff.game.rules import Rules
from bakeoff.records import pick

# the study's own tracks (decision 53): no player was tuned on them, none played them before the study
HELD_OUT = (100, 199)

# fly2's frozen numbers were fitted on these seeds (docs/calibration/FLY2_REPORT.md, decision 43): a mean over them is
# in-sample for fly2 in a way it is not for anyone else, so `charts_of` counts them.
TUNED_ON = {"fly2": [min(PRACTICE_SEEDS), max(PRACTICE_SEEDS)]}


def _merged(sources: list[Source], stopped: list[Source]) -> list[Source]:
    """One source per run directory, its complete and its stopped episodes together, so `load` reads each run once
    and names it once."""
    episodes: dict = {}
    for source in [*sources, *stopped]:
        episodes[source.run_dir] = episodes.get(source.run_dir, frozenset()) | source.episodes
    return [Source(run_dir, episodes=pairs) for run_dir, pairs in episodes.items()]


def charts_of(out_root: Path | str, rules: Rules, tracks: tuple[int, int] | None = None) -> dict:
    """{game, max_rows, scope, tracks, track_count, held_out, bench (bench.benchmark's numbers, or None), why,
    left_out, unreadable, tuned_on, tuned_tracks}. Like `benchmark_of`, it answers with a reason instead of
    failing. `tracks` narrows it to those seeds (first and last): `HELD_OUT` is the scope "held_out", None is "all".
    In the answer, `tracks` is the first and last track scored and `track_count` how many different ones;
    `tuned_tracks` is, per frozen player, how many of its tracks here are ones its numbers were fitted on."""
    about = {"held_out": list(HELD_OUT), "tuned_on": TUNED_ON,
             "scope": "all" if tracks is None else "held_out" if tuple(tracks) == HELD_OUT else "tracks"}
    out_root = Path(out_root)
    if not out_root.is_dir():
        return {"game": rules.version, "max_rows": rules.max_rows, "tracks": None, "track_count": 0, "bench": None,
                "why": "no run has been recorded yet.", "left_out": 0, "unreadable": [], "tuned_tracks": {}, **about}
    sources, left_out, unreadable, stopped = pick(out_root, rules, tracks)
    seeds = {seed for source in sources for _, seed in source.episodes}
    tuned = {player: sum(1 for source in sources for p, seed in source.episodes if p == player and lo <= seed <= hi)
             for player, (lo, hi) in TUNED_ON.items()}
    numbers, why = None, None
    if not sources:
        within = "" if tracks is None else f" {tracks[0]}–{tracks[1]}"
        why = f"no completed track{within} of game {rules.version} has been recorded yet."
    else:
        try:
            numbers = benchmark(load(_merged(sources, stopped)))
        except (OSError, ValueError) as e:
            why = f"the charts could not be scored: {e}"
    return {"game": rules.version, "max_rows": rules.max_rows, "tracks": [min(seeds), max(seeds)] if seeds else None,
            "track_count": len(seeds), "bench": numbers, "why": why, "left_out": left_out, "unreadable": unreadable,
            "tuned_tracks": {p: n for p, n in tuned.items() if n}, **about}
