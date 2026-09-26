"""Two renames: Claude Haiku's players `llm*` -> `haiku*` (decision 39), then the question sets
(decision 44): the one-shot is `plain`, `choice` is `guided`, `composed` is `step1`, `two_step` is `step2`
and `reader` is `map`. Nothing recorded before either rename may be lost or double-counted by it, and a
command someone saved must still work."""

from __future__ import annotations

import json

import pytest

from bakeoff.bench import parse_source
from bakeoff.players import PAID, REGISTRY, make_player
from bakeoff.players.names import RENAMED, canonical
from bakeoff.replay import build_replay
from bakeoff.report import load_meta, load_steps
from bakeoff.session import answered_models, played_before
from tests.test_replay import record, write_run

V2 = {"name": "v2", "version": "v2", "max_rows": 150, "lanes": 12, "lookahead": 6, "window": 3,
      "start_gap_rate": 0.04, "end_gap_rate": 0.16, "difficulty_rows": 100, "runway_rows": 5, "max_gap_width": 3}

# every pair, written out: what a reader of an old command, run or doc needs to look up
PAIRS = {
    "llm": "haiku_plain", "llm_composed": "haiku_step1", "llm_choice": "haiku_guided",
    "llm_two_step": "haiku_step2", "llm_reader": "haiku_map",
    "jev": "jev_plain", "jev_composed": "jev_step1", "jev_choice": "jev_guided",
    "jev_two_step": "jev_step2", "jev_reader": "jev_map",
    "haiku": "haiku_plain", "haiku_composed": "haiku_step1", "haiku_choice": "haiku_guided",
    "haiku_two_step": "haiku_step2", "haiku_reader": "haiku_map",
    "glm": "glm_plain", "glm_composed": "glm_step1", "glm_choice": "glm_guided",
    "glm_two_step": "glm_step2", "glm_reader": "glm_map",
}


def test_every_old_name_maps_straight_to_the_name_it_has_now():
    assert RENAMED == PAIRS
    for old, new in RENAMED.items():
        assert canonical(old) == new
        assert new not in RENAMED, f"{old} -> {new} must not need a second lookup"


def test_every_old_name_maps_to_a_player_that_exists():
    for old, new in RENAMED.items():
        assert old not in REGISTRY, f"{old} was renamed and must not be a player again"
        assert new in REGISTRY
        assert new in PAID


def test_no_player_goes_by_an_old_name():
    """`jev`, `haiku` and `glm` are old names now: nothing may still make a player called that."""
    for name, factory in REGISTRY.items():
        assert name not in RENAMED and getattr(factory, "name", name) == name


@pytest.mark.parametrize("old", sorted(PAIRS))
def test_an_old_name_still_makes_the_player_it_was_renamed_to(old):
    """A saved command or script that says jev_composed or llm_reader keeps working."""
    assert make_player(old).name == PAIRS[old]


def test_an_unknown_name_is_still_refused():
    with pytest.raises(KeyError):
        make_player("llm_nonsense")


def test_a_bench_source_accepts_an_old_name():
    assert parse_source("runs/x:llm_reader,jev_composed,jev").players == ("haiku_map", "jev_step1", "jev_plain")


def test_a_run_recorded_before_the_rename_reads_back_under_the_new_name(tmp_path):
    """The file on disk keeps its old name; what comes out of it is the player as it is called now."""
    run = write_run(tmp_path, "old", [record(player="llm", seed=1000, row=0),
                                      record(player="llm_composed", seed=1000, row=0),
                                      record(player="jev", seed=1000, row=0),
                                      record(player="jev_composed", seed=1000, row=0)],
                    {"players": ["llm", "llm_composed", "jev", "jev_composed"], "game": V2})
    assert (run / "llm.jsonl").exists() and (run / "jev_composed.jsonl").exists()  # nothing is rewritten
    assert {s["player"] for s in load_steps(run)} == {"haiku_plain", "haiku_step1", "jev_plain", "jev_step1"}
    assert load_meta(run)["players"] == ["haiku_plain", "haiku_step1", "jev_plain", "jev_step1"]
    assert json.loads((run / "llm.jsonl").read_text().splitlines()[0])["player"] == "llm"


def test_an_old_run_and_a_new_one_merge_as_one_player(tmp_path):
    """The whole point: recorded answers must not become a second contestant."""
    older = write_run(tmp_path, "older", [record(player="llm_composed", seed=1000, row=0)],
                      {"players": ["llm_composed"], "game": V2})
    old = write_run(tmp_path, "old", [record(player="haiku_composed", seed=1001, row=0)],
                    {"players": ["haiku_composed"], "game": V2})
    new = write_run(tmp_path, "new", [record(player="haiku_step1", seed=1002, row=0)],
                    {"players": ["haiku_step1"], "game": V2})
    replay = build_replay([older, old, new])
    assert replay["players"] == ["haiku_step1"]
    assert sorted(e["seed"] for e in replay["episodes"]) == [1000, 1001, 1002]


def test_the_same_player_from_two_names_on_one_seed_is_still_refused(tmp_path):
    """Merging must not let one episode in twice under two of its names."""
    old = write_run(tmp_path, "old", [record(player="jev", seed=1000, row=0)], {"players": ["jev"], "game": V2})
    new = write_run(tmp_path, "new", [record(player="jev_plain", seed=1000, row=0)],
                    {"players": ["jev_plain"], "game": V2})
    with pytest.raises(ValueError, match="jev_plain on seed 1000"):
        build_replay([old, new])


def test_the_lobby_reads_old_runs_under_the_new_names(tmp_path):
    """What the lobby says was played, and which model answered, counts an old run as the new name's."""
    write_run(tmp_path, "20260101-000000", [record(player="jev_composed", seed=1000, row=0, info={"model": "jev-1"})],
              {"players": ["jev_composed", "llm"], "seeds": [1000], "game": V2})
    assert played_before(tmp_path, "v2") == {"jev_step1": [1000], "haiku_plain": [1000]}
    assert answered_models(tmp_path) == {"jev_step1": "jev-1"}


def test_canonical_leaves_every_other_name_alone():
    for name in ("fly", "fly2", "solver", "random", "always_jump", "jev_plain", "jev_step1", "glm_step1",
                 "haiku_map", "haiku_guided"):
        assert canonical(name) == name
