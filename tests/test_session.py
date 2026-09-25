"""The session behind `bakeoff live`: what it lets the page start, and what the ceiling does.

Free players only, so nothing here touches a provider."""

import json

import pytest

from bakeoff.clients.core import RequestBudget, SharedBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.rules import rules_for
from bakeoff.players import PAID, REGISTRY
from bakeoff.session import PRICE_USD, LiveSession, LobbyError, answered_models, model_of, played_before
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
    assert by_name["haiku"]["paid"] is True and by_name["haiku"]["price_usd"] == 0.0006
    assert by_name["glm_composed"]["price_usd"] == 0.0  # the free tier costs nothing while it lasts
    assert by_name["haiku"]["requests_left"] == 0  # the default cap spends nothing


def test_every_paid_player_says_which_model_it_asks(tmp_path):
    """The page prints this in its column headers, so it must be what a run really asks for, not a
    name typed by hand. No command overrides a model, so the client's default is the whole truth."""
    by_name = {p["name"]: p for p in session(tmp_path).state()["players"]}
    assert by_name["haiku"]["model"] == "claude-haiku-4-5-20251001"
    assert by_name["haiku_reader"]["model"] == "claude-haiku-4-5-20251001"
    assert by_name["glm"]["model"] == "glm-4.5-flash" and by_name["glm_composed"]["model"] == "glm-4.5-flash"
    assert by_name["jev"]["model"] == "jev-latest" and by_name["jev_composed"]["model"] == "jev-latest"
    assert by_name["fly"]["model"] is None and by_name["solver"]["model"] is None  # nothing is asked
    assert all(p["model"] == model_of(p["name"]) for p in session(tmp_path).state()["players"] if p["paid"])
    assert all(p["model_answered"] is None for p in session(tmp_path).state()["players"])  # nothing recorded yet


def test_a_player_also_says_which_version_it_last_answered_as(tmp_path):
    """Jev's client asks for `jev-latest`, so only an answer knows the version. It comes from the newest
    run that recorded the player, under the name that run filed it under (an old `llm*` file counts)."""
    out = tmp_path / "runs"
    for name, run, model in [("jev.jsonl", "20260101-000000", "jev-1.12.0"),
                             ("jev.jsonl", "20260202-000000", "jev-1.13.0"),
                             ("llm.jsonl", "20260101-000000", "claude-haiku-4-5-20251001")]:
        (out / run).mkdir(parents=True, exist_ok=True)
        (out / run / name).write_text(json.dumps({"player": name[:-6], "info": {"model": model}}) + "\n")
    models = answered_models(out)
    assert models["jev"] == "jev-1.13.0"                       # the newest run wins
    assert models["haiku"] == "claude-haiku-4-5-20251001"      # recorded before the rename, as llm.jsonl
    assert "glm" not in models                                 # never played
    by_name = {p["name"]: p for p in session(tmp_path).state()["players"]}
    assert by_name["jev"]["model_answered"] == "jev-1.13.0" and by_name["jev"]["model"] == "jev-latest"
    assert by_name["solver"]["model_answered"] is None


def test_the_contestants_come_first_in_the_pages_own_order_and_the_yardsticks_last(tmp_path):
    names = [p["name"] for p in session(tmp_path).state()["players"]]
    assert names[:5] == ["fly", "jev_composed", "haiku", "jev", "glm"]  # the demo's three, then the other one-shots
    assert names[-3:] == ["always_jump", "random", "solver"]  # the free yardsticks
    assert set(names) == set(REGISTRY)


def test_every_paid_player_has_its_own_measured_price_and_none_of_them_is_understated():
    """The page asks the user to agree to this number, so it must not be lower than the real cost.
    The prices are the measured ones in docs/COSTS.md (update 2a), rounded up; a question set that
    reads more costs more, so a price belongs to a player, not to a provider."""
    assert set(PRICE_USD) == set(PAID)
    assert PRICE_USD["haiku_reader"] > PRICE_USD["haiku"] * 10  # 0.970 USD over 150 requests, COSTS.md
    assert PRICE_USD["haiku_two_step"] > PRICE_USD["haiku_composed"] > PRICE_USD["haiku"]
    assert PRICE_USD["jev_reader"] > PRICE_USD["jev_composed"]
    assert all(PRICE_USD[name] > 0 for name in PAID if not name.startswith("glm"))
    assert all(PRICE_USD[name] == 0.0 for name in PAID if name.startswith("glm"))  # the free tier


def test_a_run_cancelled_before_it_begins_stops_waiting_and_closes_as_interrupted(tmp_path, monkeypatch):
    """`--start` holds the first decision until a browser is listening. Cancelling while it waits must
    close the run at once: a directory left saying `running` would be a record that is not true."""
    lobby = session(tmp_path)
    started = lobby.start(1001, [slow_player(monkeypatch)], wait_for_page=True)
    assert started.run.status == "running" and not started.run.broadcast.listeners
    lobby.cancel()
    lobby.wait(10)
    assert started.run.status == "interrupted"
    meta = json.loads((started.run.run_dir / "meta.json").read_text())
    assert meta["status"] == "interrupted" and meta["finished_at"]
    assert not (started.run.run_dir / f"{slow_player(monkeypatch)}.jsonl").exists()  # nothing was decided


def test_the_history_of_a_run_that_is_over_is_dropped_when_the_next_one_starts(tmp_path):
    """Every frame of a track is kept for the page that watches it; a session plays run after run, and
    only the newest is still watched, so the older histories must not pile up on an 8 GB machine."""
    lobby = session(tmp_path)
    first = play(lobby, seed=1001, players=["solver"]).run
    assert first.broadcast._events  # kept while it is the run on screen
    play(lobby, seed=1002, players=["solver"])
    assert first.broadcast._events == []


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
    (7, ["solver", "haiku"], "paid players may not play seeds below 1000"),
])
def test_every_refusal_names_its_reason(tmp_path, seed, players, reason):
    with pytest.raises(LobbyError, match=reason):
        session(tmp_path).check(seed, players)


def test_a_free_player_may_play_a_tournament_seed_and_a_paid_one_may_with_the_flag(tmp_path):
    session(tmp_path).check(7, ["solver"])  # nothing is spent, so nothing is at stake
    session(tmp_path, tournament=True).check(7, ["solver", "haiku"])


def test_a_paid_player_with_no_request_left_of_the_session_cap_is_refused(tmp_path):
    lobby = session(tmp_path, max_requests=2)
    lobby.budgets["haiku"].spend()
    lobby.check(1001, ["haiku"])  # one left
    lobby.budgets["haiku"].spend()
    with pytest.raises(LobbyError, match="haiku has no requests left of this session's cap of 2"):
        lobby.check(1001, ["haiku"])
    lobby.check(1001, ["jev"])  # the other paid players keep their own budget
    session(tmp_path).check(1001, ["haiku"])  # a cap of 0 still replays the cache, as the command does


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


def test_an_uncalibrated_fly2_is_shown_with_its_reason_and_cannot_be_started(tmp_path, monkeypatch):
    from bakeoff.players import fly2

    monkeypatch.setattr(fly2, "CALIBRATED", False)
    live = session(tmp_path)
    by_name = {p["name"]: p for p in live.state(seed=1001)["players"]}
    assert by_name["fly2"]["why_not"] == "fly2 is not calibrated yet (calibration/FLY2_REPORT.md)"
    assert by_name["fly2"]["paid"] is False and by_name["fly"]["why_not"] is None
    with pytest.raises(LobbyError, match="fly2 is not calibrated yet"):
        live.start(1001, ["fly2"])
    monkeypatch.setattr(fly2, "CALIBRATED", True)
    assert live.why_not("fly2", 1001) is None
