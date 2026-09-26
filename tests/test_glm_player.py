"""`glm_plain`, the plain twin of `haiku_plain`: the same briefing, the same one-action schema, GLM Flash instead of
Claude Haiku. No test touches the network."""

import json

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players import make_player
from bakeoff.players.glm import GlmPlayer
from bakeoff.players.haiku import QUESTIONS
from bakeoff.senses import compute_senses
from tests.fakes import FakeHttp, glm_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    http = FakeHttp(reply)
    return GlmPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=http), http


def test_it_is_sent_exactly_what_claude_haiku_is_sent():
    assert GlmPlayer.questions is QUESTIONS and GlmPlayer.name == "glm_plain"


def test_the_request_carries_the_briefing_the_senses_and_the_action_schema(tmp_path):
    glm, http = player(tmp_path, glm_reply())
    senses = senses_for()
    glm.act(senses)
    (body,) = http.calls
    assert body["model"] == "glm-4.5-flash" and body["max_tokens"] == 256
    assert body["messages"] == [{"role": "system", "content": QUESTIONS["system"]},
                                {"role": "user", "content": json.dumps(senses)}]
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["action"]["enum"] == list(ACTIONS) and schema["additionalProperties"] is False


def test_a_live_decision_logs_the_answer_and_the_usage(tmp_path):
    glm, _ = player(tmp_path, glm_reply('{"action": "jump"}'))
    decision = glm.act(senses_for())
    assert decision.chosen_action == "jump" and not decision.needs_fallback
    assert decision.questions == QUESTIONS
    assert decision.answers == {"text": '{"action": "jump"}', "stop_reason": "end_turn"}
    assert decision.usage == {"input_tokens": 480, "output_tokens": 7}
    assert decision.info == {"model": "glm-4.5-flash"} and not decision.cache_hit


def test_a_fenced_answer_is_read_and_logged_as_it_came(tmp_path):
    """GLM wraps its JSON in ```json ... ```; the move is read all the same, and the log keeps the raw text."""
    glm, _ = player(tmp_path, glm_reply('```json\n{"action": "left"}\n```'))
    decision = glm.act(senses_for())
    assert decision.chosen_action == "left" and not decision.needs_fallback
    assert decision.answers["text"] == '```json\n{"action": "left"}\n```'


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    glm, http = player(tmp_path, glm_reply('{"action": "left"}'))
    senses = senses_for()
    glm.act(senses)
    again = glm.act(senses)
    assert again.chosen_action == "left" and again.cache_hit
    assert len(http.calls) == 1 and glm.budget.used == 1


@pytest.mark.parametrize("reply, chosen", [
    (glm_reply("I would jump"), None),
    (glm_reply('{"move": "jump"}'), None),
    (glm_reply('{"action": 3}'), None),
    (glm_reply('```json\n["jump"]\n```'), None),
    (glm_reply('{"action": "fly"}'), "fly"),
    (glm_reply('{"action": "jump"}', finish_reason="length"), "jump"),
])
def test_anything_but_one_known_action_from_a_finished_turn_is_invalid(tmp_path, reply, chosen):
    glm, _ = player(tmp_path, reply)
    decision = glm.act(senses_for())
    assert decision.invalid and decision.needs_fallback and decision.chosen_action == chosen


def test_a_provider_error_becomes_a_logged_error_not_an_exception(tmp_path):
    from bakeoff.clients.core import ProviderError

    glm, _ = player(tmp_path, ProviderError("HTTP 400: bad request"))
    decision = glm.act(senses_for())
    assert decision.chosen_action is None and decision.error.startswith("HTTP 400")


def test_the_cap_ends_the_run_instead_of_becoming_a_fallback(tmp_path):
    glm, http = player(tmp_path, glm_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        glm.act(senses_for())
    assert http.calls == []


def test_preflight_names_the_zhipu_key(tmp_path, monkeypatch):
    import bakeoff.clients.core as core

    def no_key(name):
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    with pytest.raises(ValueError, match="ZHIPU_API_KEY is not set"):
        GlmPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5)).preflight()


def test_the_factory_makes_it_and_it_spends_nothing_without_a_budget():
    made = make_player("glm_plain")
    assert made.name == "glm_plain" and made.budget.remaining == 0
