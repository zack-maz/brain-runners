"""The Writeup page's source (bakeoff/writeup.py): docs/WRITEUP.html, its two tabs and its figure slots, and
docs/STUDY.json, the numbers the figures are drawn from (decision 62)."""

import json
import re

import pytest

from bakeoff.players import REGISTRY
from bakeoff.writeup import (COMMENT, FIG_KEYS, STAT_FIELDS, STUDY, STUDY_PAIR_FIELDS, STUDY_PLAYER_FIELDS, TABS, WRITEUP,
                             figs_in, icon_of, in_study, stats_in, structure_why, study_charts, study_of, writeup_of)
from tests.test_bench import V2 as V2_BLOCK
from tests.test_bench import episode
from tests.test_replay import write_run

FRAME = ('<article class="writeup"><section data-tab="competitors" aria-label="Competitors"></section>'
         '<section data-tab="results" aria-label="Results">{}</section></article>')


def test_the_writeup_is_zacks_two_tabs_with_known_figure_slots_only():
    out = writeup_of()
    assert out["why"] is None and out["draft"] is False and out["source"] == "WRITEUP.html"
    html = COMMENT.sub("", WRITEUP.read_text())  # the header comment shows the contract's syntax
    assert re.findall(r'<section data-tab="([a-z]+)" aria-label="([A-Za-z]+)">', html) == [
        ("competitors", "Competitors"), ("results", "Results")]
    assert html.count('<article class="writeup">') == 1
    # every generated figure once, in Zack's order, all of them on Results; the leaderboard first
    assert figs_in(html) == ["leaderboard", "rows", "jev-vs-haiku", "finished", "cost-time", "scores"]
    assert html.index('data-tab="results"') < html.index('data-fig="leaderboard"')
    for key in figs_in(html):
        assert re.search(rf'<figure data-fig="{key}"><div class="fig-body">.*?</div><figcaption>', html, re.DOTALL), key
    for n in range(1, 7):
        assert f'<span class="label">table {n}</span>' in html
    assert "<script" not in html and "<style" not in html
    for player, field, _ in stats_in(html):  # data-stat still works for whoever uses it
        assert player in REGISTRY and field in STAT_FIELDS


def test_a_writeup_that_breaks_the_contract_says_why(tmp_path):
    assert structure_why(FRAME.format("")) is None
    assert structure_why(FRAME.format('<figure data-fig="rows"><div class="fig-body"></div><figcaption>x'
                                      '</figcaption></figure>')) is None
    assert "data-fig" in structure_why(FRAME.format('<figure data-fig="survival"></figure>'))
    assert "two sections" in structure_why(FRAME.replace("competitors", "players"))
    assert "two sections" in structure_why("<article class=\"writeup\"></article>")
    assert "article" in structure_why(FRAME.replace('class="writeup"', 'class="post"'))
    assert "script" in structure_why(FRAME.format("<script>alert(1)</script>"))
    assert "style" in structure_why(FRAME.format("<style>p{}</style>"))
    page = tmp_path / "w.html"
    page.write_text(FRAME.format('<figure data-fig="bogus"></figure>'))
    assert writeup_of(page)["html"] is None and writeup_of(page)["why"].startswith("the writeup is not in its shape")
    shown = tmp_path / "shown.html"  # a comment may show the syntax without citing anything or marking a draft
    shown.write_text('<!-- <span data-stat="PLAYER FIELD"> data-fig="KEY" data-draft="true" -->' + FRAME.format(""))
    assert writeup_of(shown)["why"] is None and writeup_of(shown)["draft"] is False


def test_a_citation_names_a_player_and_a_known_field():
    assert stats_in('<span data-stat="jev_step2 mean_rows"></span> and <span data-stat="fly usd_per_track"></span>') == [
        ("jev_step2", "mean_rows", "held_out"), ("fly", "usd_per_track", "held_out")]
    for bad in ('data-stat="jev_step2"', 'data-stat="jev_step2 mean_rows extra"', 'data-stat="jev_step2 bogus"'):
        with pytest.raises(ValueError, match="must be"):
            stats_in(bad)


def test_the_writeup_says_why_instead_of_failing(tmp_path):
    assert writeup_of(tmp_path / "missing.html")["why"].startswith("the writeup could not be read")
    wrong = tmp_path / "w.html"
    wrong.write_text(FRAME.format('<span data-stat="fly rows"></span>'))
    assert writeup_of(wrong)["why"].startswith("the writeup cites a number wrongly")
    mine = tmp_path / "mine.html"
    mine.write_text(FRAME.format("<p>In my own words.</p>"))
    assert writeup_of(mine) == {"html": FRAME.format("<p>In my own words.</p>"), "source": "mine.html",
                                "draft": False, "why": None}


def test_a_citation_may_add_all_to_cite_every_track_instead_of_the_held_out_ones():
    assert stats_in('<span data-stat="fly2 mean_rows all"></span><span data-stat="fly2 mean_rows"></span>') == [
        ("fly2", "mean_rows", "all"), ("fly2", "mean_rows", "held_out")]
    with pytest.raises(ValueError, match="must be"):
        stats_in('data-stat="fly2 mean_rows practice"')


def test_a_writeup_may_cite_the_price_and_the_seconds_spec_section_2_lists():
    assert {"price_usd", "s_per_decision_mean", "s_per_track"} <= set(STAT_FIELDS)


def test_a_writeup_that_would_load_from_the_network_is_refused(tmp_path):
    """The page never loads anything from the network, and the writeup is put in as written."""
    for bad in ('<img src="https://example.com/a.png">', "<a href='http://example.com'>x</a>",
                '<img SRC = "//example.com/a.png">', '<link href="HTTPS://example.com/x.css">'):
        page = tmp_path / "w.html"
        page.write_text(FRAME.format(bad))
        out = writeup_of(page)
        assert out["html"] is None and out["why"].startswith("the writeup would load from the network"), bad
    fine = tmp_path / "fine.html"
    fine.write_text(FRAME.format('<a href="#method">Method</a> <!-- <img src="https://x"> -->'))
    assert writeup_of(fine)["why"] is None


# ---- the study's numbers ---------------------------------------------------------------------------------------

def _charts(tmp_path):
    from bakeoff.game.rules import V2
    rows = {"jev_step1": [120, 130, 140, 100, 90], "haiku_step1": [100, 140, 120, 80, 95],
            "jev_plain": [10, 20, 15, 30, 25], "haiku_plain": [40, 30, 35, 45, 20], "fly2": [70, 60, 80, 75, 65],
            "solver": [150, 150, 150, 150, 150], "jev_map": [40, 50, 30, 45, 35],
            "glm_step1": [149, 149, 149, 149, 149]}  # GLM Flash left the study (decision 56)
    tmp_path.mkdir(parents=True, exist_ok=True)
    records = [r for player, rs in rows.items() for seed, n in zip(range(100, 105), rs) for r in episode(player, seed, n)]
    write_run(tmp_path, "20260928-100000", records, {"game": V2_BLOCK})
    return study_charts(tmp_path, V2)


def test_the_study_is_the_held_out_charts_cut_to_what_the_figures_read(tmp_path):
    study = study_of(_charts(tmp_path))
    assert set(study) == {"players", "pairs", "notes"}
    assert [p["player"] for p in study["players"]][0] == "solver"  # the benchmark's order: ranked by mean rows
    assert all(set(p) == set(STUDY_PLAYER_FIELDS) for p in study["players"])
    assert all(set(q) == set(STUDY_PAIR_FIELDS) for q in study["pairs"])
    # only the Jev and Claude Haiku twins, Jev always first, in the order of the sets
    assert [(q["a"], q["b"]) for q in study["pairs"]] == [("jev_step1", "haiku_step1"), ("jev_plain", "haiku_plain")]
    plain = study["pairs"][1]
    assert plain["mean_diff"] == pytest.approx(-14.0) and plain["mean_a_shared"] == 20 and plain["mean_b_shared"] == 34
    assert plain["wins"] + plain["ties"] + plain["losses"] == plain["common_seeds"] == 5
    assert (plain["wins"], plain["losses"]) == (1, 4) and plain["ci_low"] < -14 < plain["ci_high"]
    assert "glm_step1" not in {p["player"] for p in study["players"]} and not in_study("glm_plain")
    assert any("21 pairs" in note for note in study["notes"])  # the study's 7 players, not GLM Flash's 8th
    assert study["notes"] and all(isinstance(n, str) for n in study["notes"])
    assert study_of({"bench": None, "why": "nothing yet"}) is None


def test_a_players_icon_is_its_skin_from_the_roster():
    from bakeoff.roster import ROSTER
    for character in ROSTER:
        for skin in character["skins"]:
            icon = icon_of(skin["player"])
            assert (icon["sprite"], icon["color"], icon["inks"]) == (character["sprite"], skin["color"], skin["inks"])
            assert set(icon["palette"]) == {c for row in icon["rows"] for c in row} - {"."}
    assert icon_of("nobody")["sprite"] == "block"


def test_the_committed_study_is_in_the_shape_the_figures_read():
    study = json.loads(STUDY.read_text())
    assert set(study) == {"players", "pairs", "notes"}
    assert study["players"] and all(set(p) == set(STUDY_PLAYER_FIELDS) for p in study["players"])
    assert study["pairs"] and all(set(q) == set(STUDY_PAIR_FIELDS) for q in study["pairs"])
    assert all(q["a"].startswith("jev_") and q["b"] == "haiku_" + q["a"][4:] for q in study["pairs"])
    assert {p["player"] for p in study["players"]} <= set(REGISTRY)


def test_study_json_writes_the_study_from_the_recorded_runs_and_spends_nothing(tmp_path, capsys):
    from bakeoff.__main__ import main
    _charts(tmp_path / "runs")
    out = tmp_path / "STUDY.json"
    assert main(["study-json", "--out", str(tmp_path / "runs"), "--output", str(out)]) == 0
    assert "7 players, 2 pairs, 5 tracks" in capsys.readouterr().out
    assert json.loads(out.read_text()) == json.loads(json.dumps(study_of(_charts(tmp_path / "again"))))
    assert main(["study-json", "--out", str(tmp_path / "none"), "--output", str(out)]) == 2
    assert "no numbers over the held-out tracks" in capsys.readouterr().err
