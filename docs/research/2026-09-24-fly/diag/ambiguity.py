"""How ambiguous is each input? For every (row, lane) state of v2 practice tracks 1000-1199 (rows 30-149, where
gaps are dense enough to matter), the share of states of each input key where each action lands on a gap.

    PYTHONPATH=. uv run python .superpowers/research/2026-09-24-fly/diag/ambiguity.py
"""
import collections
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ceiling as C
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track

tracks = [generate_track(s, V2) for s in range(1000, 1200)]
for name in ("A today", "A5", "B ", "E "):
    feat = next(f for n, f in C.INPUTS.items() if n.startswith(name))
    stats = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for t in tracks:
        for row in range(30, t.max_rows):
            for lane in range(t.lanes):
                if t.is_gap(row, lane):
                    continue
                k = feat(C.senses_of(t, row, lane))
                st = stats[k]
                st[4] += 1
                for i, a in enumerate(C.ACTS):
                    adv, sh = C.MOVES[a]
                    st[i] += t.is_gap(row + adv, lane + sh)
    total = sum(s[4] for s in stats.values())
    risk = sum(min(s[:4]) for s in stats.values()) / total
    print(f"\n{name}: {len(stats)} keys; best-single-action gap rate over all floor states = {100*risk:.2f}% per decision"
          f" (a 150-row game ~ {100*(1-(1-risk)**120):.0f}% chance to die in rows 30-149)")
    for k, s in sorted(stats.items(), key=lambda kv: -min(kv[1][:4]))[:6]:
        print(f"   key {k}: share of states {100*s[4]/total:.1f}%, gap rate stay/left/right/jump = "
              + "/".join(f"{100*x/s[4]:.0f}%" for x in s[:4]))
