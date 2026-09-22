import json

import pytest

from bakeoff.bench import Source, load, parse_source
from tests.test_replay import DIED, record, write_run

V2 = {"version": "v2", "lanes": 12, "max_rows": 150, "lookahead": 6, "window": 3, "runway_rows": 4,
      "start_gap_rate": 0.04, "end_gap_rate": 0.16, "difficulty_rows": 100, "max_gap_width": 3}


def episode(player, seed, rows, finished=False, **extra):
    """Records of one episode: `rows` rows, then death (or the finish line)."""
    recs = [record(player=player, seed=seed, row=r, **extra) for r in range(rows - 1)]
    end = {"finished": True} if finished else DIED
    return recs + [record(player=player, seed=seed, row=rows - 1, **end, **extra)]


def test_a_source_is_a_directory_with_or_without_players():
    assert parse_source("runs/a") == Source(runs := __import__("pathlib").Path("runs/a"), None)
    assert parse_source("runs/a:llm, jev_composed") == Source(runs, ("llm", "jev_composed"))
    with pytest.raises(ValueError, match="no players after ':'"):
        parse_source("runs/a:")


def test_load_merges_directories_and_takes_only_the_named_players(tmp_path):
    a = write_run(tmp_path, "a", episode("fly", 1000, 3) + episode("llm", 1000, 2), {"game": V2, "models": {"llm": "m"}})
    b = write_run(tmp_path, "b", episode("llm", 1001, 4), {"game": V2, "models": {"llm": "m"}})
    loaded = load([Source(a, ("fly",)), Source(b)])
    assert [(e.player, e.seed, e.rows, e.run_id) for e in loaded.episodes] == [("fly", 1000, 3, "a"), ("llm", 1001, 4, "b")]
    assert loaded.game.version == "v2" and loaded.run_ids == ("a", "b") and loaded.episodes[1].model == "m"


def test_an_episode_that_neither_died_nor_finished_is_set_aside(tmp_path):
    stopped = [record(player="llm", seed=1000, row=r) for r in range(5)]  # alive at its last record
    run = write_run(tmp_path, "a", stopped + episode("llm", 1001, 3) + episode("solver", 1000, 150, finished=True))
    loaded = load([Source(run)])
    assert [(e.player, e.seed) for e in loaded.incomplete] == [("llm", 1000)]
    assert [(e.player, e.seed) for e in loaded.episodes] == [("llm", 1001), ("solver", 1000)]


def test_merge_errors_name_what_is_wrong(tmp_path):
    a = write_run(tmp_path, "a", episode("llm", 1000, 2), {"game": V2})
    b = write_run(tmp_path, "b", episode("llm", 1000, 3), {"game": V2})
    with pytest.raises(ValueError, match="llm on seed 1000 is in both a and b"):
        load([Source(a), Source(b)])
    with pytest.raises(ValueError, match="has no jev; it has llm"):
        load([Source(a, ("jev",))])
    c = write_run(tmp_path, "c", episode("fly", 1000, 2), {"game": {**V2, "version": "v1", "max_rows": 300,
                                                                     "difficulty_rows": 300}})
    with pytest.raises(ValueError, match="a is game v2 but c is game v1"):
        load([Source(a), Source(c)])
    d = write_run(tmp_path, "d", episode("fly", 1001, 2), {"schema_version": 99})
    with pytest.raises(ValueError, match="schema_version 99"):
        load([Source(d)])
    with pytest.raises(FileNotFoundError):
        load([Source(tmp_path / "nope")])
