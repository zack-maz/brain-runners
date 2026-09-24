"""Claude Haiku's players were renamed `llm*` -> `haiku*` (decision 39). Nothing recorded before the
rename may be lost or double-counted by it, and a command someone saved must still work."""

from __future__ import annotations

import json

import pytest

from bakeoff.bench import parse_source
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.players.names import RENAMED, canonical
from bakeoff.replay import build_replay
from bakeoff.report import load_meta, load_steps
from tests.test_replay import record, write_run

V2 = {"name": "v2", "version": "v2", "max_rows": 150, "lanes": 12, "lookahead": 6, "window": 3,
      "start_gap_rate": 0.04, "end_gap_rate": 0.16, "difficulty_rows": 100, "runway_rows": 5, "max_gap_width": 3}


def test_every_old_name_maps_to_a_player_that_exists():
    for old, new in RENAMED.items():
        assert old not in REGISTRY, f"{old} was renamed and must not be a player again"
        assert new in REGISTRY
        assert new in PAID


def test_an_old_name_still_makes_the_player_it_was_renamed_to():
    """A saved command or script that says llm_composed keeps working."""
    assert make_player("llm_composed").name == "haiku_composed"
    assert make_player("llm").name == "haiku"
    with pytest.raises(KeyError):
        make_player("llm_nonsense")


def test_a_bench_source_accepts_an_old_name():
    assert parse_source("runs/x:llm_reader,jev_composed").players == ("haiku_reader", "jev_composed")


def test_a_run_recorded_before_the_rename_reads_back_under_the_new_name(tmp_path):
    """The file on disk keeps its old name; what comes out of it is the player as it is called now."""
    run = write_run(tmp_path, "old", [record(player="llm", seed=1000, row=0),
                                      record(player="llm_composed", seed=1000, row=0)],
                    {"players": ["llm", "llm_composed"], "game": V2})
    assert (run / "llm.jsonl").exists()  # nothing is rewritten
    assert {s["player"] for s in load_steps(run)} == {"haiku", "haiku_composed"}
    assert load_meta(run)["players"] == ["haiku", "haiku_composed"]
    assert json.loads((run / "llm.jsonl").read_text().splitlines()[0])["player"] == "llm"


def test_an_old_run_and_a_new_one_merge_as_one_player(tmp_path):
    """The whole point: 3.85 USD of recorded Haiku answers must not become a second contestant."""
    old = write_run(tmp_path, "old", [record(player="llm_composed", seed=1000, row=0)],
                    {"players": ["llm_composed"], "game": V2})
    new = write_run(tmp_path, "new", [record(player="haiku_composed", seed=1001, row=0)],
                    {"players": ["haiku_composed"], "game": V2})
    replay = build_replay([old, new])
    assert replay["players"] == ["haiku_composed"]
    assert sorted(e["seed"] for e in replay["episodes"]) == [1000, 1001]


def test_the_same_player_from_both_names_on_one_seed_is_still_refused(tmp_path):
    """Merging must not let one episode in twice under its two names."""
    old = write_run(tmp_path, "old", [record(player="llm", seed=1000, row=0)], {"players": ["llm"], "game": V2})
    new = write_run(tmp_path, "new", [record(player="haiku", seed=1000, row=0)], {"players": ["haiku"], "game": V2})
    with pytest.raises(ValueError, match="haiku on seed 1000"):
        build_replay([old, new])


def test_canonical_leaves_every_other_name_alone():
    for name in ("fly", "jev", "jev_composed", "glm_composed", "solver", "random", "haiku_reader"):
        assert canonical(name) == name
