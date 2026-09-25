"""Failure anatomy of the recorded fly runs (seeds >= 1000 only; tournament seeds are never read).

    uv run python .superpowers/research/2026-09-24-fly/diag/anatomy.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from bakeoff.senses import lands_on_gap

ACTS = ("stay", "left", "right", "jump")
ROOT = Path(__file__).resolve().parents[4]


def runs():
    for meta_path in sorted((ROOT / "runs").glob("*/meta.json")):
        fly = meta_path.parent / "fly.jsonl"
        if not fly.exists():
            continue
        meta = json.loads(meta_path.read_text())
        game = meta.get("game", {}).get("version", "v1")
        yield meta_path.parent.name, game, meta["status"], fly


def tile_code(s):
    """The four landing tiles as a string: L1 C1 R1 C2, 'X' = gap."""
    return "".join("X" if lands_on_gap(s, a) else "." for a in ("left", "stay", "right", "jump"))


def situation(s):
    ahead = s["ahead"]
    c1, l1, r1 = (o in ahead[0]["gaps_relative"] for o in (0, -1, 1))
    c2 = 0 in ahead[1]["gaps_relative"]
    if c1 and l1 and r1:
        base = "wall row1 (L1 C1 R1 gaps)"
    elif c1 and (l1 or r1):
        base = "gap ahead + one side"
    elif c1:
        base = "gap straight ahead only"
    elif l1 and r1:
        base = "gaps both sides, centre open"
    elif l1 or r1:
        base = "gap one side, centre open"
    else:
        base = "row1 clear"
    return base + (", C2 gap" if c2 else ", C2 open")


def main():
    seen = set()
    per_game = collections.defaultdict(lambda: collections.Counter())
    deaths = collections.defaultdict(list)
    for run_id, game, status, path in runs():
        recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        recs = [r for r in recs if r["seed"] >= 1000]
        by_seed = collections.defaultdict(list)
        for r in recs:
            by_seed[r["seed"]].append(r)
        for seed, rs in by_seed.items():
            key = (game, seed, rs[-1]["rows_survived"], len(rs))
            dup = key in seen  # identical replays of the same seed (live runs repeat 1001)
            seen.add(key)
            if dup:
                continue
            c = per_game[game]
            for r in rs:
                s = r["senses"]
                act = r["executed_action"]
                unsafe = lands_on_gap(s, act)
                safe_exists = any(not lands_on_gap(s, a) for a in ACTS)
                c["decisions"] += 1
                c[f"act_{act}"] += 1
                c["unsafe"] += unsafe
                c["unsafe_with_safe_alt"] += unsafe and safe_exists
                c["solver_agree"] += act == r["solver_action"]
                d = r["solver_depths"]
                c["subopt_depth"] += d[act] < max(d.values())
                if act == "jump":
                    c["jumps"] += 1
                    c["jump_unsafe"] += unsafe
                    c["jump_when_stay_safe"] += not lands_on_gap(s, "stay")
                    c["jump_when_c1_c2_both_gap"] += lands_on_gap(s, "stay") and unsafe
            last = rs[-1]
            if not last["alive"]:
                deaths[game].append((run_id, seed, rs))
    for game in sorted(per_game):
        c = per_game[game]
        n = c["decisions"]
        print(f"\n=== {game}: {len(deaths[game])} deaths, {n} decisions")
        print({k: v for k, v in sorted(c.items())})
        print(f"unsafe with a safe alternative: {c['unsafe_with_safe_alt']} of {n} decisions"
              f" ({100*c['unsafe_with_safe_alt']/n:.2f}%); jumps {c['jumps']}, of them onto a gap {c['jump_unsafe']}"
              f"; solver agreement {c['solver_agree']/n:.3f}; action with shorter solver depth {c['subopt_depth']}")
        sits = collections.Counter()
        alt = collections.Counter()
        causes = collections.Counter()
        for run_id, seed, rs in deaths[game]:
            last = rs[-1]
            s = last["senses"]
            sits[situation(s)] += 1
            causes[last["death_cause"]] += 1
            safe = [a for a in ACTS if not lands_on_gap(s, a)]
            alt["safe alternative existed" if safe else "no safe landing tile"] += 1
            alt[f"solver said {last['solver_action']} (depth {last['solver_depths'][last['solver_action']]})"] += 0
        print("causes", dict(causes))
        print("fatal situations", dict(sits))
        print("safe alternative at fatal decision", {k: v for k, v in alt.items() if v})
        print("\nlast 5 decisions of every death (tiles = L1 C1 R1 C2 landing tiles, X = gap):")
        for run_id, seed, rs in deaths[game]:
            print(f"-- {run_id} seed {seed}: died at row {rs[-1]['rows_survived']} ({rs[-1]['death_cause']})")
            for r in rs[-5:]:
                s, i = r["senses"], r["info"]
                rows = " | ".join(",".join(str(o) for o in e["gaps_relative"]) or "-" for e in s["ahead"][:3])
                print(f"   row {r['row']:3d} tiles {tile_code(s)} rows1-3 [{rows}] in=({i['left_hz']:.0f},{i['right_hz']:.0f}) "
                      f"turn={i['turn_signal_hz']:+.0f} GF={i['jump_signal_hz']:.0f} did={r['executed_action']:5s} "
                      f"solver={r['solver_action']:5s} depths={r['solver_depths']}")


if __name__ == "__main__":
    main()
