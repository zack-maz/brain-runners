"""The Writeup page's source (bakeoff/writeup.py)."""

import pytest

from bakeoff.players import REGISTRY
from bakeoff.writeup import STAT_FIELDS, WRITEUP, stats_in, writeup_of


def test_the_draft_is_marked_and_cites_only_real_players_and_fields():
    out = writeup_of()
    assert out["why"] is None and out["draft"] is True and out["source"] == "WRITEUP.html"
    for player, field, _ in stats_in(WRITEUP.read_text()):
        assert player in REGISTRY and field in STAT_FIELDS


def test_a_citation_names_a_player_and_a_known_field():
    assert stats_in('<span data-stat="jev_step2 mean_rows"></span> and <span data-stat="fly usd_per_track"></span>') == [
        ("jev_step2", "mean_rows", "held_out"), ("fly", "usd_per_track", "held_out")]
    for bad in ('data-stat="jev_step2"', 'data-stat="jev_step2 mean_rows extra"', 'data-stat="jev_step2 bogus"'):
        with pytest.raises(ValueError, match="must be"):
            stats_in(bad)


def test_the_writeup_says_why_instead_of_failing(tmp_path):
    assert writeup_of(tmp_path / "missing.html")["why"].startswith("the writeup could not be read")
    wrong = tmp_path / "w.html"
    wrong.write_text('<span data-stat="fly rows"></span>')
    assert writeup_of(wrong)["why"].startswith("the writeup cites a number wrongly")
    shown = tmp_path / "shown.html"  # a comment may show the syntax without citing anything or marking a draft
    shown.write_text('<!-- <span data-stat="PLAYER FIELD"> and data-draft="true" --><article></article>')
    assert writeup_of(shown)["why"] is None and writeup_of(shown)["draft"] is False
    mine = tmp_path / "mine.html"
    mine.write_text("<article><p>In my own words.</p></article>")
    assert writeup_of(mine) == {"html": "<article><p>In my own words.</p></article>", "source": "mine.html",
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
        page.write_text(f"<article>{bad}</article>")
        out = writeup_of(page)
        assert out["html"] is None and out["why"].startswith("the writeup would load from the network"), bad
    fine = tmp_path / "fine.html"
    fine.write_text('<article><a href="#method">Method</a> <!-- <img src="https://x"> --></article>')
    assert writeup_of(fine)["why"] is None
