"""Information ceiling: the best fixed lookup table (input key -> action) for several inputs, on v2.

For every practice track every (row, lane) state is encoded once; a table policy is then played by table
lookups alone. The table is optimised by coordinate ascent (start from the myopic table, try every action
for every visited key, keep a change only if the mean rows on the practice seeds rise; repeat until no key
changes; three restarts). What it finds is a LOWER bound on the best table for that input; the best table in
turn bounds every memoryless deterministic readout of that input (the fly's brain only adds noise between the
input and the readout). Held-out seeds 1200-1399 are played once by the table found.

    PYTHONPATH=. uv run python .superpowers/research/2026-09-24-fly/diag/ceiling.py
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track, start_lane
from bakeoff.senses import LOOMING_STEP_HZ, MAX_HZ, lands_on_gap

ACTS = ("stay", "left", "right", "jump")
MOVES = {"stay": (1, 0), "left": (1, -1), "right": (1, 1), "jump": (2, 0)}
PRACTICE = range(1000, 1200)
HELD_OUT = range(1200, 1400)
OUT = Path(__file__).with_name("ceiling.json")


class _G:  # the fields compute_senses reads
    def __init__(self, track, row, lane):
        self.track, self.row, self.lane, self.rows_survived = track, row, lane, row


def senses_of(track, row, lane):
    rules = track.rules
    ahead = []
    for d in range(1, rules.lookahead + 1):
        ahead.append({"row": d, "gaps_relative": [o for o in range(-rules.window, rules.window + 1)
                                                  if track.is_gap(row + d, lane + o)]})
    return {"ahead": ahead}


def level(hz):
    return math.floor(min(hz, MAX_HZ) / LOOMING_STEP_HZ + 0.5) * LOOMING_STEP_HZ


# ---------- inputs (all OURS) ----------

def eyes(gain=250.0, falloff=3.0, rows=range(1, 7), offsets=None, quantize=True, cap=True):
    """Two eyes as today: offset <= 0 -> left, >= 0 -> right; optional row/offset restriction."""
    def f(s):
        l = r = 0.0
        for e in s["ahead"]:
            if e["row"] not in rows:
                continue
            w = gain / e["row"] ** falloff
            for o in e["gaps_relative"]:
                if offsets is not None and o not in offsets:
                    continue
                if o <= 0:
                    l += w
                if o >= 0:
                    r += w
        if quantize:
            return (level(l), level(r)) if cap else (round(l / LOOMING_STEP_HZ), round(r / LOOMING_STEP_HZ))
        return (round(l, 3), round(r, 3))
    return f


def combine(*fs):
    return lambda s: tuple(x for f in fs for x in f(s))


def tiles(cells):
    return lambda s: tuple(o in s["ahead"][r - 1]["gaps_relative"] for r, o in cells)


LANDING = [(1, -1), (1, 0), (1, 1), (2, 0)]
INPUTS = {
    "A today: 2 eyes (gain 250, falloff 3, 11 levels)": eyes(),
    "A1 2 eyes, falloff 1": eyes(falloff=1.0),
    "A2 2 eyes, falloff 2": eyes(falloff=2.0),
    "A3 2 eyes, falloff 4": eyes(falloff=4.0),
    "A4 2 eyes, uncapped (levels keep counting past 250)": eyes(cap=False),
    "A5 2 eyes, only offsets -1..1 (narrow eyes)": eyes(offsets={-1, 0, 1}),
    "B 2 eyes + straight-ahead channel (offset 0 only)": combine(eyes(), eyes(offsets={0})),
    "C 2 eyes split near (row 1) / far (rows 2-6)": combine(eyes(rows={1}), eyes(rows=range(2, 7))),
    "D 2 narrow eyes split near/far (offsets -1..1)": combine(eyes(rows={1}, offsets={-1, 0, 1}),
                                                             eyes(rows=range(2, 7), offsets={-1, 0, 1})),
    "E 4 landing tiles (L1 C1 R1 C2), 1 bit each": tiles(LANDING),
    "F landing tiles + row-2 and row-3 3x3 (L1 C1 R1 L2 C2 R2 L3 C3 R3)": tiles(
        [(r, o) for r in (1, 2, 3) for o in (-1, 0, 1)]),
    "G 5x3 patch rows 1-3, offsets -2..2": tiles([(r, o) for r in (1, 2, 3) for o in range(-2, 3)]),
}


# ---------- simulation ----------

def encode(tracks, feature):
    """keys[t][(row, lane)] = input key; also each action's immediate outcome (dead or next state)."""
    enc = []
    for track in tracks:
        k = {}
        for row in range(track.max_rows):
            for lane in range(track.lanes):
                k[(row, lane)] = feature(senses_of(track, row, lane))
        enc.append(k)
    return enc


def play(track, keys, table, default="stay"):
    row, lane, cleared, visited = 0, start_lane(track.lanes), 0, set()
    n = track.max_rows
    while row < n:
        key = keys[(row, lane)]
        visited.add(key)
        adv, sh = MOVES[table.get(key, default)]
        nrow, nlane = row + adv, (lane + sh) % track.lanes
        if nrow <= n and track.is_gap(nrow, nlane):
            return nrow - 1, visited
        row, lane, cleared = nrow, nlane, nrow
    return min(cleared, n), visited


def evaluate(tracks, enc, table):
    res = [play(t, k, table) for t, k in zip(tracks, enc)]
    return [r for r, _ in res], [v for _, v in res]


def myopic_table(tracks, enc):
    """Per key, the action that lands on a gap least often over every state with that key."""
    bad = {}
    for track, keys in zip(tracks, enc):
        for (row, lane), key in keys.items():
            b = bad.setdefault(key, [0, 0, 0, 0, 0])
            b[4] += 1
            for i, a in enumerate(ACTS):
                adv, sh = MOVES[a]
                if row + adv <= track.max_rows and track.is_gap(row + adv, lane + sh):
                    b[i] += 1
    return {k: ACTS[min(range(4), key=lambda i: (b[i], i))] for k, b in bad.items()}


def ascend(tracks, enc, table, max_passes=8, rng=None):
    rows, visits = evaluate(tracks, enc, table)
    total = sum(rows)
    for _ in range(max_passes):
        changed = False
        keys = sorted({k for v in visits for k in v}, key=repr)
        if rng is not None:
            rng.shuffle(keys)
        for key in keys:
            users = [i for i, v in enumerate(visits) if key in v]
            base = sum(rows[i] for i in users)
            best_a, best_gain, best_res = table.get(key, "stay"), 0, None
            for a in ACTS:
                if a == table.get(key, "stay"):
                    continue
                trial = dict(table)
                trial[key] = a
                res = [play(tracks[i], enc[i], trial) for i in users]
                gain = sum(r for r, _ in res) - base
                if gain > best_gain:
                    best_a, best_gain, best_res = a, gain, res
            if best_res is not None:
                table[key] = best_a
                for i, (r, v) in zip(users, best_res):
                    rows[i], visits[i] = r, v
                total += best_gain
                changed = True
        if not changed:
            break
    return table, total / len(tracks)


def main():
    only = sys.argv[1:]
    practice = [generate_track(s, V2) for s in PRACTICE]
    held = [generate_track(s, V2) for s in HELD_OUT]
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name, feature in INPUTS.items():
        if only and not any(name.startswith(o) for o in only):
            continue
        t0 = time.time()
        enc_p, enc_h = encode(practice, feature), encode(held, feature)
        n_keys = len({k for e in enc_p for k in e.values()})
        start = myopic_table(practice, enc_p)
        myopic_rows = statistics.mean(evaluate(practice, enc_p, start)[0])
        best, best_mean = None, -1
        for restart in range(3):
            rng = None if restart == 0 else random.Random(restart)
            table, mean = ascend(practice, enc_p, dict(start), rng=rng)
            if mean > best_mean:
                best, best_mean = table, mean
        held_rows = evaluate(held, enc_h, best)[0]
        results[name] = {"keys_seen": n_keys, "myopic_practice": myopic_rows, "best_practice": best_mean,
                         "best_held_out": statistics.mean(held_rows),
                         "held_out_finished": sum(r >= 150 for r in held_rows),
                         "table": {repr(k): v for k, v in sorted(best.items(), key=lambda kv: repr(kv[0]))},
                         "seconds": round(time.time() - t0, 1)}
        print(f"{name}: keys {n_keys}, myopic {myopic_rows:.1f}, best {best_mean:.1f}, "
              f"held-out {statistics.mean(held_rows):.1f} ({time.time()-t0:.0f}s)", flush=True)
        OUT.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
