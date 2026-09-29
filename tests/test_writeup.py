"""The Writeup page's source (bakeoff/writeup.py)."""

import pytest

from bakeoff.players import REGISTRY
from bakeoff.writeup import STAT_FIELDS, WRITEUP, stats_in, writeup_of


def test_the_draft_is_marked_and_cites_only_real_players_and_fields():
    out = writeup_of()
    assert out["why"] is None and out["draft"] is True and out["source"] == "WRITEUP.html"
    for player, field in stats_in(WRITEUP.read_text()):
        assert player in REGISTRY and field in STAT_FIELDS


def test_a_citation_names_a_player_and_a_known_field():
    assert stats_in('<span data-stat="jev_step2 mean_rows"></span> and <span data-stat="fly usd_per_track"></span>') == [
        ("jev_step2", "mean_rows"), ("fly", "usd_per_track")]
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
