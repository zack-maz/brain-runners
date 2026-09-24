"""Re-fix the fly's thresholds on v2 with the stand-in brain (report only; nothing is written to calibration/).

Rule fixed beforehand (the same as bakeoff/fly/calibrate.py): highest mean rows on v2 practice seeds 1000-1199
wins, ties to the first in grid order; the winner plays held-out seeds 1200-1399 once.
(1) the two thresholds only, gain 250 / falloff 3 kept; (2) the whole 768-candidate calibrate grid.
Also: floors and solver on the same seeds, and the best table for today's input (ceiling.json, "A") played
THROUGH the brain: the table is indexed by the input a nearest-centroid decoder recovers from the fly's eight
DN spike counts, so it is what a perfect memoryless readout of these neurons could do with that table.

    PYTHONPATH=. uv run python .superpowers/research/2026-09-24-fly/diag/refix_v2.py
"""
from __future__ import annotations

import ast
import json
import random
import statistics
from pathlib import Path

from bakeoff.fly.calibrate import (FALLOFFS, GAINS_HZ, JUMP_THRESHOLDS_HZ, TURN_THRESHOLDS_HZ, play, score,
                                   search)
from bakeoff.fly.surface import SurrogateBrain, load_surface
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.players.fly import FlyPlayer, noise_seed
from bakeoff.senses import looming_rates

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
PRACTICE, HELD_OUT = range(1000, 1200), range(1200, 1400)


class DecodedTablePlayer:
    """Input -> the fly's DN counts (a measured trial, chosen by the same noise seed as the fly) -> nearest
    input cell by the DN vector -> the table's action. Ours end to end except the brain."""
    name = "decoded_table"

    def __init__(self, surface, table):
        self.brain = SurrogateBrain(surface)
        self.table = table
        cells = {}
        for c in surface["cells"]:
            trials = c["spike_counts"]
            names = sorted(trials[0])
            cells[(c["left_hz"], c["right_hz"])] = [sum(t[n] for t in trials) / len(trials) for n in names]
        self.names, self.centroids = names, cells

    def reset(self, game, seed):
        self.seed = seed

    def decode(self, counts):
        v = [counts[n] for n in self.names]
        return min(self.centroids, key=lambda k: sum((a - b) ** 2 for a, b in zip(v, self.centroids[k])))

    def act(self, senses):
        l, r = looming_rates(senses)
        reading = self.brain.window(l, r, noise_seed=noise_seed(self.seed, senses["rows_survived"]))
        key = self.decode(reading.spike_counts)
        self.hits = getattr(self, "hits", [0, 0])
        self.hits[0] += key == (l, r)
        self.hits[1] += 1
        return Decision(self.table.get(key, "stay"))

    def observe(self, a):
        pass


class TablePlayer(DecodedTablePlayer):
    def act(self, senses):
        return Decision(self.table.get(looming_rates(senses), "stay"))


def main():
    surface = load_surface(ROOT / "calibration/response_surface.json")
    practice = [generate_track(s, V2) for s in PRACTICE]
    held = [generate_track(s, V2) for s in HELD_OUT]
    brain = SurrogateBrain(surface)
    out = {}

    def fly(**cfg):
        return FlyPlayer(brain_factory=lambda: brain, **cfg)

    out["current_practice"] = score(fly(), practice)
    out["current_held_out"] = score(fly(), held)
    out["current_seeds_1000_1004"] = [play(fly(), t)[0].rows_survived for t in practice[:5]]
    for name in ("random", "always_jump", "solver"):
        out[f"{name}_practice"] = score(make_player(name), practice)
        out[f"{name}_held_out"] = score(make_player(name), held)

    thr = search(surface, practice, gains_hz=(250.0,), falloffs=(3.0,))
    out["thresholds_top"] = thr[:8]
    w = {k: thr[0][k] for k in ("gain_hz", "falloff", "turn_threshold_hz", "jump_threshold_hz")}
    out["thresholds_winner_held_out"] = score(fly(**w), held)
    out["thresholds_grid"] = [{k: r[k] for k in ("turn_threshold_hz", "jump_threshold_hz", "mean_rows")} for r in thr]

    full = search(surface, practice)
    out["full_top"] = full[:10]
    w = {k: full[0][k] for k in ("gain_hz", "falloff", "turn_threshold_hz", "jump_threshold_hz")}
    out["full_winner_held_out"] = score(fly(**w), held)

    ceiling = json.loads((HERE / "ceiling.json").read_text())
    table = {ast.literal_eval(k): v for k, v in
             ceiling["A today: 2 eyes (gain 250, falloff 3, 11 levels)"]["table"].items()}
    for label, player_cls in (("table_A_direct", TablePlayer), ("table_A_through_brain", DecodedTablePlayer)):
        p = player_cls(surface, table)
        out[f"{label}_practice"] = score(p, practice)
        out[f"{label}_held_out"] = score(p, held)
        if hasattr(p, "hits"):
            out[f"{label}_decode_accuracy"] = p.hits[0] / p.hits[1]
    (HERE / "refix_v2.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        if k != "thresholds_grid":
            print(k, v if not isinstance(v, list) else v[:3])


if __name__ == "__main__":
    main()
