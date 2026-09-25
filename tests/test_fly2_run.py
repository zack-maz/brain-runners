"""fly and fly2 in one run on one real brain (slow: about 150 windows of each, on the session's brain)."""

import json

import pytest

from bakeoff.fly import shared
from bakeoff.game.rules import V2
from bakeoff.players import fly2, make_player
from bakeoff.runner import Runner

pytestmark = pytest.mark.slow


def test_fly_and_fly2_play_a_v2_practice_track_on_one_shared_brain(brain, tmp_path, monkeypatch):
    monkeypatch.setattr(fly2, "CALIBRATED", True)  # the provisional numbers: this checks the plumbing, not the score
    built = []
    monkeypatch.setattr(shared, "_real_brain", lambda inputs: built.append(set(inputs)) or brain)
    monkeypatch.setattr(brain, "close", lambda: None)  # the session's brain outlives this run
    shared._wanted.clear()
    run_dir = Runner(out_root=tmp_path).run([make_player("fly"), make_player("fly2")], seeds=[1000], rules=V2,
                                            run_id="r")
    assert built[0] == {"fly", fly2.MAPPING}  # both flies were registered before the first window
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["fly2"]["mapping"] == fly2.MAPPING
    records = [json.loads(line) for line in (run_dir / "fly2.jsonl").read_text().splitlines()]
    assert records and all(r["info"]["mapping"] == fly2.MAPPING for r in records)
    assert all(r["info"]["branch"] in ("dodge", "jump", "stay") for r in records)
    assert sum(r["info"]["total_spikes"] for r in records) > 0
    assert records[-1]["finished"] or not records[-1]["alive"]
