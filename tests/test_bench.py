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


def episodes_of(*spec):
    """(player, seed, rows[, finished]) tuples -> complete Episodes, via load() on a written run."""
    from bakeoff.bench import Episode
    return [Episode(p, s, "r", tuple(episode(p, s, rows, *rest)), None) for p, s, rows, *rest in spec]


def test_a_players_rows_and_its_interval():
    from bakeoff.bench import player_numbers
    eps = episodes_of(("jev", 1000, 10), ("jev", 1001, 20), ("jev", 1002, 150, True), ("jev", 1003, 20), ("jev", 1004, 50))
    n = player_numbers(eps, 150)
    assert (n["seeds"], n["mean_rows"], n["median_rows"], n["finished"]) == (5, 50.0, 20.0, 1 / 5)
    # t interval 50 +- 2.776 * sd / sqrt(5) = -21.9 to 121.9, clipped to the rows a track can have
    assert n["ci_low"] == 0.0 and n["ci_high"] == pytest.approx(121.855, abs=1e-3)
    assert n == player_numbers(eps, 150)  # the same numbers every time
    assert n["survival"][0] == 1.0 and n["survival"][10] == 1.0 and n["survival"][11] == 4 / 5
    assert n["survival"][150] == 1 / 5 and len(n["survival"]) == 151
    four = player_numbers(eps[:4], 150)
    assert four["ci_low"] is None and four["ci_high"] is None  # below 5 seeds: no interval
    same = player_numbers(episodes_of(*[("jev", s, 7) for s in range(5)]), 150)
    assert same["ci_low"] == same["ci_high"] == 7.0


def test_time_comes_from_live_decisions_and_the_flys_simulation():
    from bakeoff.bench import Episode, player_numbers
    live = [record(player="llm", seed=1000, row=r, latency_ms=ms, usage={"input_tokens": 1000, "output_tokens": 100})
            for r, ms in enumerate([500, 700, 900])]
    cached = [record(player="llm", seed=1000, row=3, cache_hit=True, **DIED)]
    n = player_numbers([Episode("llm", 1000, "r", tuple(live + cached), "claude-haiku-4-5-20251001")], 150)
    assert (n["s_per_decision_median"], n["live_decisions"], n["cache_hits"]) == (0.7, 3, 1)
    assert n["s_per_decision_p90"] == pytest.approx(0.86)
    assert n["decisions_per_row"] == 1.0 and n["s_per_row"] == pytest.approx(0.7)
    assert n["usd_per_decision"] == pytest.approx((1000 * 1.0 + 100 * 5.0) / 1e6)  # the live ones only
    fly = [record(player="fly", seed=1000, row=r, info={"wall_ms": 600.0}) for r in range(2)]
    fly[-1].update(DIED)
    f = player_numbers([Episode("fly", 1000, "r", tuple(fly), None)], 150)
    assert f["s_per_decision_median"] == 0.6 and f["usd_per_decision"] is None and f["usd_per_row"] is None
    assert f["live_decisions"] == 2
    free = player_numbers(episodes_of(("solver", 1000, 5)), 150)
    assert free["s_per_decision_median"] is None and free["s_per_row"] is None and free["usd_per_row"] is None
    unpriced = player_numbers([Episode("jev", 1000, "r", tuple(live + cached), "jev-1.13.0")], 150)
    assert unpriced["usd_per_decision"] is None and unpriced["s_per_decision_median"] == 0.7


def test_a_jump_makes_fewer_decisions_than_rows():
    from bakeoff.bench import Episode, player_numbers
    steps = [record(player="p", seed=1, row=0, rows_survived=2), record(player="p", seed=1, row=2, rows_survived=4, **DIED)]
    assert player_numbers([Episode("p", 1, "r", tuple(steps), None)], 150)["decisions_per_row"] == 0.5


def test_pairs_say_who_is_ahead_only_when_the_interval_excludes_zero():
    from bakeoff.bench import pair_numbers
    a = episodes_of(("a", 1, 100), ("a", 2, 110), ("a", 3, 120), ("a", 4, 90), ("a", 5, 100))
    b = episodes_of(("b", 1, 50), ("b", 2, 60), ("b", 3, 55), ("b", 4, 40), ("b", 5, 45), ("b", 9, 3))
    p = pair_numbers(a, b)
    assert (p["common_seeds"], p["wins"], p["ties"], p["losses"], p["verdict"]) == (5, 5, 0, 0, "a ahead")
    assert p["mean_diff"] == 54.0 and p["ci_low"] == pytest.approx(45.907, abs=1e-3) and p["seeds_needed"] == 5
    assert pair_numbers(b, a)["verdict"] == "a ahead"
    close = pair_numbers(episodes_of(*[("a", s, r) for s, r in enumerate([100, 80, 100, 80, 100])]),
                         episodes_of(*[("b", s, r) for s, r in enumerate([90, 85, 90, 85, 90])]))
    assert close["verdict"] == "can't tell yet" and close["mean_diff"] == 4.0
    assert close["seeds_needed"] == 34  # differences 10, -5, 10, -5, 10: sd 8.22, ((1.96 + 0.842) * 8.22 / 4) ** 2
    assert close["ci_low"] == pytest.approx(-6.200, abs=1e-3)
    few = pair_numbers(episodes_of(("a", 1, 100), ("a", 2, 110)), episodes_of(("b", 1, 50), ("b", 2, 60)))
    assert (few["verdict"], few["ci_low"], few["seeds_needed"]) == ("too few tracks (2)", None, None)
    tied = pair_numbers(episodes_of(*[("a", s, 30) for s in range(5)]), episodes_of(*[("b", s, 30) for s in range(5)]))
    assert (tied["ties"], tied["verdict"], tied["seeds_needed"]) == (5, "can't tell yet", None)
    apart = pair_numbers(episodes_of(("a", 1, 30)), episodes_of(("b", 2, 40)))
    assert (apart["common_seeds"], apart["mean_diff"], apart["verdict"]) == (0, None, "too few tracks (0)")


def test_the_benchmark_ranks_players_pairs_them_and_lists_what_it_left_out(tmp_path):
    from bakeoff.bench import JEV_PRICE_NOTE, benchmark
    stopped = [record(player="llm", seed=1002, row=r) for r in range(5)]
    run = write_run(tmp_path, "a", episode("solver", 1000, 150, finished=True) + episode("jev", 1000, 40)
                    + episode("llm", 1000, 90) + stopped, {"game": V2})
    out = benchmark(load([Source(run)]))
    assert [p["player"] for p in out["players"]] == ["solver", "llm", "jev"]
    assert [(p["a"], p["b"]) for p in out["pairs"]] == [("solver", "llm"), ("solver", "jev"), ("llm", "jev")]
    assert out["incomplete"] == [{"player": "llm", "seed": 1002, "run_id": "a", "rows": 5}]
    assert (out["game"], out["max_rows"], out["runs"]) == ("v2", 150, ["a"])
    assert JEV_PRICE_NOTE in out["notes"] and len(out["players"][0]["survival"]) == 151
    json.dumps(out)  # JSON-ready


def test_with_no_real_difference_a_verdict_comes_about_1_time_in_20():
    """The reason for t intervals (final review of item 7): at 5 tracks a percentile bootstrap gave a verdict
    about 1 time in 7 when the two players were equal."""
    from bakeoff.bench import _t_interval
    rng = __import__("numpy").random.default_rng(7)
    trials = 4000
    verdicts = sum((lambda ci: ci[0] > 0 or ci[1] < 0)(_t_interval(list(rng.normal(0, 20, 5)))) for _ in range(trials))
    assert 0.03 < verdicts / trials < 0.065


def test_the_t_quantile_uses_the_next_lower_degrees_of_freedom():
    from bakeoff.bench import t975
    assert (t975(4), t975(30), t975(35), t975(1000)) == (2.776, 2.042, 2.042, 1.980)


def test_players_with_too_few_tracks_are_not_ranked_and_many_pairs_get_a_warning(tmp_path):
    from bakeoff.bench import benchmark
    recs = episode("few", 1000, 150, finished=True)
    for seed in range(1000, 1005):
        recs += episode("a", seed, 100 + seed - 1000) + episode("b", seed, 50) + episode("c", seed, 60)
    out = benchmark(load([Source(write_run(tmp_path, "r", recs, {"game": V2}))]))
    assert [(p["player"], p["ranked"]) for p in out["players"]] == [("a", True), ("c", True), ("b", True), ("few", False)]
    assert any(n.startswith("3 pairs are compared at 95% each") for n in out["notes"])


def test_cost_says_free_priced_or_no_price():
    from bakeoff.bench import Episode, player_numbers
    live = record(player="p", seed=1, row=0, latency_ms=500, usage={"input_tokens": 10, "output_tokens": 1}, **DIED)
    assert player_numbers([Episode("p", 1, "r", (live,), "claude-haiku-4-5-20251001")], 150)["cost"] == "priced"
    assert player_numbers([Episode("p", 1, "r", (live,), "jev-latest")], 150)["cost"] == "no price"
    assert player_numbers(episodes_of(("fly", 1, 3)), 150)["cost"] == "free"
    free_tier = record(player="p", seed=1, row=0, latency_ms=300,
                       usage={"input_tokens": 500, "output_tokens": 20}, **DIED)
    assert player_numbers([Episode("p", 1, "r", (free_tier,), "glm-4.5-flash")], 150)["cost"] == "free"


def test_load_refuses_what_would_score_wrong(tmp_path):
    short = write_run(tmp_path, "short", episode("a", 1000, 50, finished=True), {"game": {**V2, "max_rows": 50}})
    full = write_run(tmp_path, "full", episode("b", 1000, 120), {"game": V2})
    with pytest.raises(ValueError, match="short has tracks of 50 rows but full of 150"):
        load([Source(short), Source(full)])
    m1 = write_run(tmp_path, "m1", episode("llm", 1000, 5), {"game": V2, "models": {"llm": "one"}})
    m2 = write_run(tmp_path, "m2", episode("llm", 1001, 5), {"game": V2, "models": {"llm": "two"}})
    with pytest.raises(ValueError, match="llm is one in m1 but two in m2"):
        load([Source(m1), Source(m2)])
    twice = write_run(tmp_path, "twice", episode("a", 1000, 3) + episode("a", 1000, 3), {"game": V2})
    with pytest.raises(ValueError, match="a on seed 1000 appears more than once in twice"):
        load([Source(twice)])


def test_a_colon_in_a_directory_path_is_not_a_player_list():
    from pathlib import Path
    assert parse_source("runs/a:b/c") == Source(Path("runs/a:b/c"), None)
    assert parse_source("runs/a:b/c:llm") == Source(Path("runs/a:b/c"), ("llm",))
