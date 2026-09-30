"""Fix fly2's input mapping and numbers on practice seeds, and score its controls: step 3 and 4 of the fly2 spec.

The rule is bakeoff/fly/fly2_rule.py, written before any surface was measured. Every candidate plays the practice
tracks of game v2 with the stand-in brain made from its own measured surface; the winner plays the held-out
seeds once. The controls are scored on the same seeds by the same rule:
- no brain: the winner's channel rates through fly2's rule with the brain skipped (its own grid);
- shuffled wiring: the winner's mapping on a surface measured on shuffled wiring (`--shuffled`, measured once the
  winner is known: python -m bakeoff.fly.surface --mapping <winner> --shuffle-seed 1 <out>);
- fly itself, with its frozen numbers, on its own stand-in brain.
Tournament seeds (below 1000) are never played.

    uv run python -m bakeoff.fly.calibrate2 --surface M1=docs/calibration/fly2_surface_M1.json \\
        --surface M2=docs/calibration/fly2_surface_M2.json --surface M3=docs/calibration/fly2_surface_M3.json \\
        [--shuffled docs/calibration/fly2_surface_shuffled.json] docs/calibration/FLY2_REPORT.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bakeoff.fly.calibrate import FLOORS, SCORE_COLUMNS, _table, score, search_configs
from bakeoff.fly.channels import MAPPINGS
from bakeoff.fly.fly2_rule import (CANDIDATE_ORDER, CHECK_SEEDS, GRID, HELD_OUT_SEEDS, NO_BRAIN_GRID, PRACTICE_SEEDS,
                                   pick_winner)
from bakeoff.fly.surface import SurrogateBrain, load_surface
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players import make_player
from bakeoff.players.fly import FlyPlayer
from bakeoff.players.fly2 import Fly2Player, NoBrainPlayer

FLY_SURFACE = Path(__file__).resolve().parents[2] / "docs" / "calibration" / "response_surface.json"
CONFIG_COLUMNS = ("gain_hz", "falloff", "turn_threshold_hz", "jump_threshold_hz")
REPORT_COLUMNS = SCORE_COLUMNS + ("deaths",)


def fly2_on(surface: dict, mapping: str):
    brain = SurrogateBrain(surface)
    if brain.input != mapping:
        raise ValueError(f"the surface was measured for {brain.input!r}, not {mapping!r}")
    return lambda config: Fly2Player(brain_factory=lambda _name: brain, mapping=mapping, **config)


def no_brain_on(mapping: str):
    return lambda config: NoBrainPlayer(mapping=mapping, **config)


def best(results: list[dict]) -> dict:
    """The rule for a control: the highest mean rows, ties to grid order (`results` in grid order)."""
    return max(results, key=lambda r: r["mean_rows"])  # max keeps the first of equals


def calibrate(surfaces: dict[str, dict], shuffled: dict | None = None, practice_seeds=PRACTICE_SEEDS,
              held_out_seeds=HELD_OUT_SEEDS, check_seeds=CHECK_SEEDS, grid=GRID, no_brain_grid=NO_BRAIN_GRID,
              fly_surface: dict | None = None) -> dict:
    if min(practice_seeds) < 1000 or min(held_out_seeds) < 1000 or min(check_seeds) < 1000:
        raise ValueError("tournament seeds (below 1000) may not be used to calibrate fly2")
    for name, surface in surfaces.items():
        if surface.get("shuffle_seed") is not None:
            raise ValueError(f"the surface for {name} was measured on shuffled wiring; "
                              "it is a control, not a candidate")
    missing = [name for name in CANDIDATE_ORDER if name not in surfaces]
    practice = [generate_track(seed, V2) for seed in practice_seeds]
    held_out = [generate_track(seed, V2) for seed in held_out_seeds]
    scored = {name: search_configs(fly2_on(surfaces[name], name), practice, grid, sort=False, deaths=True)
              for name in CANDIDATE_ORDER if name in surfaces}
    winner = pick_winner(scored)
    mapping, config = winner["candidate"], {k: winner[k] for k in CONFIG_COLUMNS}
    make_winner = fly2_on(surfaces[mapping], mapping)
    out = {
        "missing": missing, "scored": scored, "winner": winner,
        "held_out": score(make_winner(config), held_out, deaths=True),
        "check": score(make_winner(config), [generate_track(seed, V2) for seed in check_seeds], deaths=True),
        "best_per_candidate": {name: best(results) for name, results in scored.items()},
    }
    no_brain = search_configs(no_brain_on(mapping), practice, no_brain_grid, sort=False)
    no_brain_best = best(no_brain)
    no_brain_config = {k: no_brain_best[k] for k in CONFIG_COLUMNS}
    out["no_brain"] = {"practice": no_brain_best,
                       "held_out": score(NoBrainPlayer(mapping=mapping, **no_brain_config), held_out, deaths=True)}
    if shuffled is not None:
        if shuffled.get("shuffle_seed") is None:
            raise ValueError("the --shuffled surface was not measured on shuffled wiring")
        make_shuffled = fly2_on(shuffled, mapping)
        shuffled_best = best(search_configs(make_shuffled, practice, grid, sort=False))
        out["shuffled"] = {"practice": shuffled_best, "shuffle_seed": shuffled["shuffle_seed"],
                           "held_out": score(make_shuffled({k: shuffled_best[k] for k in CONFIG_COLUMNS}), held_out,
                                             deaths=True)}
    if fly_surface is not None:
        fly_brain = SurrogateBrain(fly_surface)
        out["fly"] = {"practice": score(FlyPlayer(brain_factory=lambda: fly_brain), practice, deaths=True),
                      "held_out": score(FlyPlayer(brain_factory=lambda: fly_brain), held_out, deaths=True)}
    out["floors"] = [{"player": name, **score(make_player(name), practice)} for name in FLOORS]
    return out


def _seeds(seeds: range) -> str:
    return f"{seeds.start}-{seeds.stop - 1}"


def _deaths(row: dict) -> dict:
    return {**row, "deaths": ", ".join(f"{k} {v}" for k, v in sorted(row["deaths"].items())) or "none"}


def report(result: dict, practice_seeds=PRACTICE_SEEDS, held_out_seeds=HELD_OUT_SEEDS, check_seeds=CHECK_SEEDS) -> str:
    winner = result["winner"]
    mapping = MAPPINGS[winner["candidate"]]
    parts = [
        "# fly2 calibration",
        "Generated by `python -m bakeoff.fly.calibrate2`; do not edit by hand. Everything here is OUR tuning, not "
        "the fly's biology: the input mapping (which gaps drive which cells, `gain_hz / row ** falloff`), the "
        "readout (which steering neurons make the turn) and the two thresholds of the rule, dodge before jump. "
        "The rule was fixed before any surface was measured (`bakeoff/fly/fly2_rule.py`).",
        f"Game v2, stand-in brains from the measured surfaces, practice seeds {_seeds(practice_seeds)}. "
        f"{sum(len(r) for r in result['scored'].values())} configurations over "
        f"{len(result['scored'])} candidates. Highest mean rows wins; ties to M1, M2, M3, then grid order.",
        f"The held-out seeds {_seeds(held_out_seeds)} were used earlier by the research that chose the three "
        "candidates (their best-table scores on these seeds), so they are not wholly unseen; the rule itself "
        "never looked at them before scoring the winner.",
    ]
    if result["missing"]:
        parts.append(f"Not measured, so not in the running: {', '.join(result['missing'])}.")
    parts += [
        f"## Winner: {mapping.name}, {mapping.summary}\n\nTurn = (right - left) of "
        f"{' + '.join(mapping.turn_types)}; jump = the Giant Fiber (DNp01) mean.\n\n"
        + _table([_deaths(winner)], CONFIG_COLUMNS + REPORT_COLUMNS),
        f"## Winner on held-out seeds {_seeds(held_out_seeds)} (played once)\n\n"
        + _table([_deaths(result["held_out"])], REPORT_COLUMNS),
        f"## Winner on check seeds {_seeds(check_seeds)}, stand-in brain\n\n"
        + _table([_deaths(result["check"])], REPORT_COLUMNS)
        + f"\n\nCompare with the real brain: `uv run python -m bakeoff run --players fly,fly2 --seeds "
          f"{len(check_seeds)} --seed-start {check_seeds.start}`.",
        "## Best of each candidate on the practice seeds\n\n"
        + _table([{"candidate": name, **row} for name, row in result["best_per_candidate"].items()],
                 ("candidate",) + CONFIG_COLUMNS + SCORE_COLUMNS),
    ]
    controls = [{"player": "fly2 (winner)", "practice": winner["mean_rows"],
                 "held_out": result["held_out"]["mean_rows"]},
                {"player": "no brain", "practice": result["no_brain"]["practice"]["mean_rows"],
                 "held_out": result["no_brain"]["held_out"]["mean_rows"]}]
    if "shuffled" in result:
        controls.append({"player": f"shuffled wiring (seed {result['shuffled']['shuffle_seed']})",
                         "practice": result["shuffled"]["practice"]["mean_rows"],
                         "held_out": result["shuffled"]["held_out"]["mean_rows"]})
    if "fly" in result:
        controls.append({"player": "fly (frozen, stand-in brain)", "practice": result["fly"]["practice"]["mean_rows"],
                         "held_out": result["fly"]["held_out"]["mean_rows"]})
    parts.append(
        "## Controls\n\nMean rows survived, each control at its own best configuration on the practice seeds "
        "(the same rule), then played once on the held-out seeds. If the no-brain control plays as well as fly2, "
        "the gain came from our mapping and rule, not from the wiring.\n\n"
        + _table(controls, ("player", "practice", "held_out"))
        + ("" if "shuffled" in result else "\n\nThe shuffled-wiring control is not measured yet.")
        + "\n\nNo brain, best configuration: "
        + ", ".join(f"{k} {result['no_brain']['practice'][k]}" for k in CONFIG_COLUMNS) + "."
        + "\n\nThe shuffle keeps each neuron's in- and out-degree by sign and every connection's presynaptic sign "
          "and synapse count; it loses which neuron talks to which and each neuron's summed input weight (a "
          "permutation can also create a self-connection or repeat a pair). Like fly2 itself, the shuffled control "
          "searches the whole grid, gain and falloff included, rather than only its own thresholds as the spec "
          "allows for a control — more generous to the control, the conservative direction.")
    parts.append("## Floors on the practice seeds\n\n" + _table(result["floors"], ("player",) + SCORE_COLUMNS))
    top = sorted(((name, r) for name, rows in result["scored"].items() for r in rows),
                 key=lambda item: -item[1]["mean_rows"])[:10]
    parts.append("## Top 10 configurations\n\n"
                 + _table([{"candidate": name, **r} for name, r in top], ("candidate",) + CONFIG_COLUMNS + SCORE_COLUMNS))
    return "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bakeoff.fly.calibrate2", description=__doc__.split("\n\n")[0])
    parser.add_argument("--surface", action="append", required=True, metavar="NAME=PATH",
                        help="a candidate's measured surface (schema 2); give each candidate once")
    parser.add_argument("--shuffled", metavar="PATH", help="the winner's surface on shuffled wiring")
    parser.add_argument("report", help="where to write the report (Markdown)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    surfaces = {}
    for item in args.surface:
        name, _, path = item.partition("=")
        if name not in CANDIDATE_ORDER or not path:
            parser.error(f"--surface wants NAME=PATH with NAME one of {CANDIDATE_ORDER}, not {item!r}")
        if name in surfaces:
            parser.error(f"--surface {name} was given twice")
        surfaces[name] = load_surface(path)
    shuffled = load_surface(args.shuffled) if args.shuffled else None
    text = report(calibrate(surfaces, shuffled, fly_surface=load_surface(FLY_SURFACE)))
    Path(args.report).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
