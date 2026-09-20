import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.clients.jev import JevClient
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players.jev import QUESTIONS, JevPlayer
from bakeoff.senses import compute_senses
from tests.fakes import FakeTypeSafe, jev_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_questions_are_a_choice_over_the_four_actions_and_two_nouls_named_like_the_ground_truth():
    assert set(QUESTIONS) == {"action", "gap_ahead", "left_safe"}
    assert QUESTIONS["action"]["type"] == "choice" and set(QUESTIONS["action"]["criteria"]) == set(ACTIONS)
    assert QUESTIONS["gap_ahead"]["type"] == QUESTIONS["left_safe"]["type"] == "noul"


def test_the_sdk_gets_the_senses_as_state_and_typed_questions(tmp_path):
    from typesafe_sdk import Choice, Noul

    jev, sdk = player(tmp_path, jev_reply())
    senses = senses_for()
    jev.act(senses)
    (call,) = sdk.calls
    assert call["state"] == senses and call["model"] == "jev-latest"
    assert isinstance(call["questions"]["action"], Choice) and isinstance(call["questions"]["gap_ahead"], Noul)
    assert dict(call["questions"]["action"].criteria) == QUESTIONS["action"]["criteria"]
    assert call["questions"]["left_safe"].instructions == QUESTIONS["left_safe"]["instructions"]


def test_a_live_decision_logs_the_choice_the_probabilities_the_nouls_and_the_usage(tmp_path):
    jev, _ = player(tmp_path, jev_reply("jump", gap_ahead=0.97))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "jump" and not decision.needs_fallback
    assert decision.questions == QUESTIONS
    assert decision.answers["action"]["probabilities"] == {"left": 0.1, "right": 0.1, "jump": 0.7, "stay": 0.1}
    assert decision.answers["gap_ahead"]["noul"] == 0.97
    assert decision.usage == {"input_tokens": 400, "output_tokens": 3}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "jev-latest"}


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    jev, sdk = player(tmp_path, jev_reply("left"))
    senses = senses_for()
    jev.act(senses)
    again = jev.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and jev.budget.used == 1
    fresh, fresh_sdk = player(tmp_path, jev_reply("right"), cap=0)  # a later run, no budget at all
    assert fresh.act(senses).chosen_action == "left" and fresh_sdk.calls == []


def test_a_provider_error_becomes_a_logged_error_not_an_exception(tmp_path):
    from typesafe_sdk import TypeSafeAPIConnectionError

    jev, _ = player(tmp_path, TypeSafeAPIConnectionError("connection refused"))
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.needs_fallback
    assert decision.error == "TypeSafeAPIConnectionError: connection refused"
    assert decision.questions == QUESTIONS and jev.budget.used == 1


def test_the_cap_ends_the_run_instead_of_becoming_a_fallback(tmp_path):
    jev, sdk = player(tmp_path, jev_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        jev.act(senses_for())
    assert sdk.calls == []


def test_a_bug_is_not_swallowed(tmp_path):
    jev, _ = player(tmp_path, RuntimeError("our bug"))
    with pytest.raises(RuntimeError, match="our bug"):
        jev.act(senses_for())


def test_an_unknown_or_missing_choice_is_invalid(tmp_path):
    jev, _ = player(tmp_path, jev_reply("fly"))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "fly" and decision.invalid
    missing, _ = player(tmp_path / "other", {"model": "jev-latest", "usage": {}, "answers": {}})
    assert missing.act(senses_for()).invalid


def test_without_a_budget_the_player_can_only_replay(tmp_path):
    jev = JevPlayer(cache=DiskCache(tmp_path), sdk=FakeTypeSafe(jev_reply()))
    assert jev.budget.max_requests == 0 and jev.model == "jev-latest"


def test_preflight_needs_the_key_only_for_a_live_run_with_the_real_sdk(tmp_path, monkeypatch):
    import bakeoff.clients.core as core

    asked = []

    def no_key(name):
        asked.append(name)
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(0)).preflight()  # replay only
    JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5), sdk=FakeTypeSafe(jev_reply())).preflight()
    assert asked == []
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY is not set"):
        JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5)).preflight()


def test_close_closes_only_an_sdk_the_client_built_itself(tmp_path):
    jev, sdk = player(tmp_path, jev_reply())
    jev.close()
    assert not sdk.closed
    client = JevClient(DiskCache(tmp_path), RequestBudget(1))
    client._sdk = owned = FakeTypeSafe(jev_reply())
    client.close()
    assert owned.closed and client._sdk is None
