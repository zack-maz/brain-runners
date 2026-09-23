"""The session behind `bakeoff live`: what it lets the page start, and what the ceiling does.

Free players only, so nothing here touches a provider."""

import json

import pytest

from bakeoff.clients.core import RequestBudget, SharedBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.rules import rules_for
from bakeoff.players import REGISTRY
from bakeoff.session import LiveSession, LobbyError, played_before
from tests.fakes import slow_player

RULES = rules_for("v2").variant(max_rows=12)


def session(tmp_path, **options):
    return LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", **options)


def play(session, seed=1001, players=("solver", "random")):
    started = session.start(seed, list(players))
    session.wait(30)
    return started


def test_a_fresh_session_is_in_the_lobby_and_lists_every_player_with_its_price(tmp_path):
    state = session(tmp_path).state(seed=1001)
    assert state["status"] == "lobby" and state["run"] is None
    assert state["game"]["version"] == "v2" and state["max_rows"] == 12 and state["requests_per_row"] == 1
    by_name = {p["name"]: p for p in state["players"]}
    assert by_name["solver"]["paid"] is False and by_name["solver"]["requests_left"] is None
    assert by_name["llm"]["paid"] is True and by_name["llm"]["price_usd"] == 0.0006
    assert by_name["glm_composed"]["price_usd"] == 0.0  # the free tier costs nothing while it lasts
    assert by_name["llm"]["requests_left"] == 0  # the default cap spends nothing


def test_the_contestants_come_first_in_the_pages_own_order_and_the_yardsticks_last(tmp_path):
    names = [p["name"] for p in session(tmp_path).state()["players"]]
    assert names[:4] == ["fly", "jev_composed", "llm", "jev"]  # the demo's three, then the one-shot Jev
    assert names[-3:] == ["always_jump", "random", "solver"]  # the free yardsticks
    assert set(names) == set(REGISTRY)


def test_the_cap_the_command_set_is_per_paid_player_for_the_whole_session(tmp_path):
    state = session(tmp_path, max_requests=40).state()
    left = {p["name"]: p["requests_left"] for p in state["players"] if p["paid"]}
    assert set(left.values()) == {40} and state["max_requests"] == 40


def test_a_run_from_the_lobby_is_a_normal_run_directory_and_the_session_returns_to_it(tmp_path):
    lobby = session(tmp_path)
    started = play(lobby, seed=1001)
    assert lobby.status == "finished" and started.run.status == "completed"
    meta = json.loads((started.run.run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["seeds"] == [1001] and meta["players"] == ["solver", "random"]
    assert meta["args"]["seed"] == 1001 and meta["args"]["players"] == "solver,random"
    assert started.replay["seeds"] == [1001] and started.replay["episodes"] == []
    state = lobby.state(seed=1001)
    assert state["status"] == "finished" and state["run"]["run_id"] == started.run.run_id
    play(lobby, seed=1002, players=["solver"])  # and another track can be set up without restarting
    assert len(lobby.finished) == 2 and lobby.run.seed == 1002


def test_a_track_that_was_played_before_is_marked_so_the_page_knows_it_replays_for_free(tmp_path):
    lobby = session(tmp_path)
    play(lobby, seed=1001, players=["solver"])
    assert played_before(tmp_path / "runs", "v2") == {"solver": [1001]}
    assert played_before(tmp_path / "runs", "v1") == {}  # another game is another set of answers
    by_name = {p["name"]: p for p in lobby.state(seed=1001)["players"]}
    assert by_name["solver"]["played_before"] is True and by_name["random"]["played_before"] is False
    assert {p["name"] for p in lobby.state()["players"] if p["played_before"]} == set()  # no track, nothing to say


@pytest.mark.parametrize("seed, players, reason", [
    (1001, ["nobody"], "unknown player 'nobody'"),
    (1001, ["solver", "solver"], "duplicate player names"),
    (1001, [], "choose at least one player"),
    (-3, ["solver"], "must not be negative"),
    ("1001", ["solver"], "must be a whole number"),
    (7, ["solver", "llm"], "paid players may not play seeds below 1000"),
])
def test_every_refusal_names_its_reason(tmp_path, seed, players, reason):
    with pytest.raises(LobbyError, match=reason):
        session(tmp_path).check(seed, players)


def test_a_free_player_may_play_a_tournament_seed_and_a_paid_one_may_with_the_flag(tmp_path):
    session(tmp_path).check(7, ["solver"])  # nothing is spent, so nothing is at stake
    session(tmp_path, tournament=True).check(7, ["solver", "llm"])


def test_a_paid_player_with_no_request_left_of_the_session_cap_is_refused(tmp_path):
    lobby = session(tmp_path, max_requests=2)
    lobby.budgets["llm"].spend()
    lobby.check(1001, ["llm"])  # one left
    lobby.budgets["llm"].spend()
    with pytest.raises(LobbyError, match="llm has no requests left of this session's cap of 2"):
        lobby.check(1001, ["llm"])
    lobby.check(1001, ["jev"])  # the other paid players keep their own budget
    session(tmp_path).check(1001, ["llm"])  # a cap of 0 still replays the cache, as the command does


def test_only_one_run_at_a_time(tmp_path):
    lobby = session(tmp_path)
    lobby.start(1001, ["solver"])
    with pytest.raises(LobbyError, match="a run is already going"):
        lobby.check(1002, ["solver"])
    lobby.wait(30)
    lobby.check(1002, ["solver"])


def test_cancelling_closes_the_run_as_a_normal_interrupted_directory(tmp_path, monkeypatch):
    lobby = session(tmp_path)
    with pytest.raises(LobbyError, match="no run is going"):
        lobby.cancel()
    started = lobby.start(1001, [slow_player(monkeypatch)])
    lobby.cancel()
    lobby.wait(30)
    assert started.run.status == "interrupted"
    meta = json.loads((started.run.run_dir / "meta.json").read_text())
    assert meta["status"] == "interrupted" and meta["finished_at"]


def test_a_question_set_that_needs_more_vision_than_the_game_gives_is_refused_before_anything_exists(tmp_path):
    narrow = LiveSession(rules_for("v2").variant(lookahead=2), out_root=tmp_path / "runs",
                         cache_dir=tmp_path / "cache")
    with pytest.raises(LobbyError, match="jev_two_step"):
        narrow.start(1001, ["jev_two_step"])
    assert not (tmp_path / "runs").exists()


def test_a_run_spends_from_the_session_budget_but_records_only_its_own_requests():
    session_budget = RequestBudget(5)
    first, second = SharedBudget(session_budget), None
    first.spend()
    first.spend()
    second = SharedBudget(session_budget)
    second.spend()
    assert (first.max_requests, first.used) == (5, 2)  # what the first run could spend, and did
    assert (second.max_requests, second.used) == (3, 1)  # the second one starts from what was left
    assert session_budget.used == 3 and session_budget.remaining == 2
    for _ in range(2):
        second.spend()
    with pytest.raises(BudgetExhausted):
        second.spend()  # the ceiling the command set holds across the session
