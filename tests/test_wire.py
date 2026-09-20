"""Offline tests against the real provider SDKs, over a mock HTTP transport. No network: `tests/fakes.py`
stands in at the SDK-client level, so this is the only coverage of the real request building and response
parsing outside the opt-in live tests."""

from __future__ import annotations

import json

import httpx2

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.game.engine import Game
from bakeoff.game.track import generate_track
from bakeoff.players.jev import JevPlayer
from bakeoff.players.llm import LlmPlayer
from bakeoff.senses import compute_senses
from tests.fakes import jev_reply, llm_reply

SENSES = compute_senses(Game(generate_track(1000)))


def test_the_real_jev_sdk_sends_the_documented_request_and_parses_the_reply(tmp_path):
    from typesafe_sdk import RetryPolicy, TypeSafeClient

    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json=jev_reply("jump"))

    sdk = TypeSafeClient(api_key="k", retry=RetryPolicy(max_retries=0), transport=httpx2.MockTransport(handler))
    player = JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(1), sdk=sdk)
    decision = player.act(SENSES)

    assert len(requests) == 1
    (request,) = requests
    assert str(request.url) == "https://api.typesafe.ai/v1/systemone"
    body = json.loads(request.content)
    assert body["state"] == SENSES and body["model"] == "jev-latest"
    assert [q["type"] for q in body["questions"].values()] == ["choice", "noul", "noul"]
    assert decision.chosen_action == "jump" and decision.error is None
    assert decision.usage == {"input_tokens": 400, "output_tokens": 3}


def test_the_real_anthropic_sdk_sends_the_documented_request_and_parses_the_reply(tmp_path):
    import anthropic

    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json=llm_reply('{"action": "left"}'))

    sdk = anthropic.Anthropic(api_key="k", max_retries=0, timeout=60.0,
                              http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))
    player = LlmPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(1), sdk=sdk)
    decision = player.act(SENSES)

    assert len(requests) == 1
    (request,) = requests
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    body = json.loads(request.content)
    assert body["model"] == "claude-haiku-4-5-20251001" and body["max_tokens"] == 256
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["messages"][0]["content"] == json.dumps(SENSES)
    assert decision.chosen_action == "left"


def test_a_jev_503_is_one_request_a_spent_budget_and_a_logged_error(tmp_path):
    from typesafe_sdk import RetryPolicy, TypeSafeClient

    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(503, json={"error": "down"})

    sdk = TypeSafeClient(api_key="k", retry=RetryPolicy(max_retries=0), transport=httpx2.MockTransport(handler))
    budget = RequestBudget(1)
    player = JevPlayer(cache=DiskCache(tmp_path), budget=budget, sdk=sdk)
    decision = player.act(SENSES)

    assert len(requests) == 1 and budget.used == 1
    assert decision.chosen_action is None
    assert decision.error.startswith("TypeSafeInternalServerError")


def test_an_anthropic_503_is_one_request_a_spent_budget_and_a_logged_error(tmp_path):
    import anthropic

    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(503, json={"error": "down"})

    sdk = anthropic.Anthropic(api_key="k", max_retries=0, timeout=60.0,
                              http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))
    budget = RequestBudget(1)
    player = LlmPlayer(cache=DiskCache(tmp_path), budget=budget, sdk=sdk)
    decision = player.act(SENSES)

    assert len(requests) == 1 and budget.used == 1
    assert decision.chosen_action is None
    assert decision.error.startswith("InternalServerError")
