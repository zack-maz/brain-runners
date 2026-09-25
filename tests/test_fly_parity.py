"""The parity gate of fly2 (spec, "Code"): fly on the shared brain, with every fly2 input registered beside its own,
replays its recorded v2 run window for window. A failure stops the work and goes to the user; drift is never
accepted silently. Slow: about 320 windows plus a window of M3 between every ten, on the session's one brain."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

RUN = Path(__file__).resolve().parents[1] / "runs" / "20260921-192037" / "fly.jsonl"  # fly, v2 seeds 1000-1004


def test_fly_replays_its_recorded_v2_run_exactly_on_the_shared_brain(brain):
    if not RUN.exists():
        pytest.fail("the parity gate needs runs/20260921-192037/fly.jsonl, "
                    "fly's recorded v2 run (git-ignored, on the machine that recorded it)")
    records = [json.loads(line) for line in RUN.read_text().splitlines()]
    assert {r["seed"] for r in records} == {1000, 1001, 1002, 1003, 1004}
    drift = []
    for n, record in enumerate(records):
        if n % 10 == 5:  # another fly's window in between must change nothing
            brain.window_of("M3", {"centre": 500.0, "left": 300.0, "right": 0.0}, noise_seed=n)
        info = record["info"]
        reading = brain.window(info["left_hz"], info["right_hz"], noise_seed=info["noise_seed"])
        counts = {name: reading.spike_counts[name] for name in info["spike_counts"]}
        times = {name: reading.spike_times_ms[name] for name in info["spike_times_ms"]}
        if (counts, times, reading.total_spikes) != (info["spike_counts"], info["spike_times_ms"], info["total_spikes"]):
            drift.append((record["seed"], record["row"]))
    assert drift == [], f"fly's spikes drifted at (seed, row) {drift[:10]}"
