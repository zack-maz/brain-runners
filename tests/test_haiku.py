import json

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players import jev
from bakeoff.players.briefing import RULES
from bakeoff.players.haiku import QUESTIONS, HaikuPlayer
from bakeoff.senses import compute_senses
from tests.fakes import FakeAnthropic, llm_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeAnthropic(reply)
    return HaikuPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_both_paid_players_are_told_the_same_rules():
    assert QUESTIONS["system"].startswith(RULES) and jev.QUESTIONS["action"]["instructions"].startswith(RULES)


def test_the_request_is_haiku_with_the_senses_as_the_user_message_and_an_action_schema(tmp_path):
    haiku, sdk = player(tmp_path, llm_reply())
    senses = senses_for()
    haiku.act(senses)
    (call,) = sdk.calls
    assert call["model"] == "claude-haiku-4-5-20251001" and call["max_tokens"] == 256
    assert call["system"] == QUESTIONS["system"]
    assert call["messages"] == [{"role": "user", "content": json.dumps(senses)}]
    schema = call["output_config"]["format"]["schema"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert schema["properties"]["action"]["enum"] == list(ACTIONS) and schema["additionalProperties"] is False


def test_a_live_decision_logs_the_answer_and_the_usage(tmp_path):
    haiku, _ = player(tmp_path, llm_reply('{"action": "jump"}'))
    decision = haiku.act(senses_for())
    assert decision.chosen_action == "jump" and not decision.needs_fallback
    assert decision.questions == QUESTIONS
    assert decision.answers == {"text": '{"action": "jump"}', "stop_reason": "end_turn"}
    assert decision.usage == {"input_tokens": 520, "output_tokens": 9}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "claude-haiku-4-5-20251001"}


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    haiku, sdk = player(tmp_path, llm_reply('{"action": "left"}'))
    senses = senses_for()
    haiku.act(senses)
    again = haiku.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and haiku.budget.used == 1


@pytest.mark.parametrize("reply, chosen", [
    (llm_reply("I would jump"), None),
    (llm_reply('{"move": "jump"}'), None),
    (llm_reply('{"action": 3}'), None),
    (llm_reply('["jump"]'), None),
    (llm_reply('{"action": "fly"}'), "fly"),
    (llm_reply('{"action": "jump"}', stop_reason="max_tokens"), "jump"),
    (llm_reply('{"action": "jump"}', stop_reason="refusal"), "jump"),
])
def test_anything_but_one_known_action_from_a_finished_turn_is_invalid(tmp_path, reply, chosen):
    haiku, _ = player(tmp_path, reply)
    decision = haiku.act(senses_for())
    assert decision.invalid and decision.needs_fallback and decision.chosen_action == chosen
    assert decision.answers["text"] == reply["content"][0]["text"]


def test_a_provider_error_becomes_a_logged_error_not_an_exception(tmp_path):
    import anthropic
    import httpx2

    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    haiku, _ = player(tmp_path, error)
    decision = haiku.act(senses_for())
    assert decision.chosen_action is None and decision.error.startswith("APIConnectionError: ")
    assert haiku.budget.used == 1


def test_the_cap_ends_the_run_instead_of_becoming_a_fallback(tmp_path):
    haiku, sdk = player(tmp_path, llm_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        haiku.act(senses_for())
    assert sdk.calls == []


def test_preflight_names_the_anthropic_key(tmp_path, monkeypatch):
    import bakeoff.clients.core as core

    def no_key(name):
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not set"):
        HaikuPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5)).preflight()
