"""The GLM client: one OpenAI-compatible chat completion per decision. No test touches the network."""

import json

import pytest

from bakeoff.clients.core import DiskCache, ProviderError, RequestBudget
from bakeoff.clients.glm import DEFAULT_BASE_URL, GlmClient, HttpTransport, base_url
from tests.fakes import FakeHttp, glm_reply

SENSES = {"lane": 3, "ahead": []}
QUESTIONS = {"system": "you are a runner", "max_tokens": 300, "questions": {"gap_stay": {"type": "noul"}},
             "schema": {"type": "object", "properties": {"gap_stay": {"type": "number"}},
                        "required": ["gap_stay"], "additionalProperties": False}}


def client(tmp_path, reply, max_requests=1):
    http = FakeHttp(reply)
    return GlmClient(DiskCache(tmp_path / "cache"), RequestBudget(max_requests), sdk=http), http


def test_one_request_carries_the_system_prompt_the_senses_and_asks_for_json(tmp_path):
    glm, http = client(tmp_path, glm_reply(text='{"gap_stay": 0.1}'))
    reply = glm.ask(SENSES, QUESTIONS)
    (body,) = http.calls
    assert body["model"] == "glm-4.5-flash" and body["temperature"] == 0 and body["max_tokens"] == 300
    assert body["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "answers", "strict": True, "schema": QUESTIONS["schema"]}}  # the schema Claude Haiku gets
    assert body["thinking"] == {"type": "disabled"}  # Haiku does not think here either
    assert body["messages"] == [{"role": "system", "content": "you are a runner"},
                                {"role": "user", "content": json.dumps(SENSES)}]
    assert reply.payload["text"] == '{"gap_stay": 0.1}' and reply.payload["stop_reason"] == "end_turn"
    assert reply.payload["usage"] == {"input_tokens": 480, "output_tokens": 7}
    assert reply.payload["model"] == "glm-4.5-flash" and not reply.cache_hit


def test_a_cut_off_reply_keeps_its_own_finish_reason(tmp_path):
    glm, _ = client(tmp_path, glm_reply(finish_reason="length"))
    payload = glm.ask(SENSES, QUESTIONS).payload
    assert payload["stop_reason"] == "length" and payload["finish_reason"] == "length"


def test_the_second_ask_comes_from_the_cache_and_spends_nothing(tmp_path):
    glm, http = client(tmp_path, glm_reply(), max_requests=1)
    glm.ask(SENSES, QUESTIONS)
    again = glm.ask(SENSES, QUESTIONS)
    assert again.cache_hit and len(http.calls) == 1 and glm.budget.used == 1


def test_an_unreadable_reply_is_a_provider_error(tmp_path):
    for broken in ({"choices": []}, {"error": {"message": "bad key"}}, {"choices": [{"message": {}}]}):
        glm, _ = client(tmp_path, broken)
        with pytest.raises(ProviderError, match="unreadable reply"):
            glm.ask(SENSES, QUESTIONS)


def test_a_transport_failure_is_a_provider_error(tmp_path):
    glm, _ = client(tmp_path, ProviderError("HTTP 400: bad request"))  # a queue failure is retried: see below
    with pytest.raises(ProviderError, match="400"):
        glm.ask(SENSES, QUESTIONS)


def test_the_base_url_is_a_setting_and_the_key_never_appears_in_a_failure(monkeypatch):
    monkeypatch.delenv("GLM_BASE_URL", raising=False)
    assert base_url() == DEFAULT_BASE_URL
    monkeypatch.setenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    assert base_url() == "https://open.bigmodel.cn/api/paas/v4"
    import urllib.error

    def refuse(*args, **kwargs):  # no test touches the network
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    transport = HttpTransport("https://example.invalid/chat/completions", "secret-key")
    with pytest.raises(ProviderError) as failure:
        transport.post({"model": "glm-4.5-flash"})
    assert "secret-key" not in str(failure.value) and "URLError" in str(failure.value)


def test_reasoning_content_is_logged_if_the_model_sends_any(tmp_path):
    reply = glm_reply(text='{"gap_stay": 0.1}')
    reply["choices"][0]["message"]["reasoning_content"] = "first I look at the tiles"
    glm, _ = client(tmp_path, reply)
    payload = glm.ask(SENSES, QUESTIONS).payload
    assert payload["reasoning_content"] == "first I look at the tiles" and payload["text"] == '{"gap_stay": 0.1}'


def test_changing_how_the_request_is_made_does_not_replay_the_old_answers(tmp_path):
    """The knobs the client adds are part of the cache key: the first GLM run cached empty replies made with
    thinking on, and those must never come back once thinking is off."""
    glm, http = client(tmp_path, glm_reply(text='{"gap_stay": 0.1}'), max_requests=2)
    glm.ask(SENSES, QUESTIONS)
    glm.request_options = {**GlmClient.request_options, "thinking": {"type": "enabled"}}
    again = glm.ask(SENSES, QUESTIONS)
    assert not again.cache_hit and len(http.calls) == 2


def test_an_overloaded_free_tier_is_retried_once_and_the_retry_spends_from_the_cap(tmp_path, monkeypatch):
    import bakeoff.clients.glm as glm_module
    from bakeoff.clients.core import BudgetExhausted

    monkeypatch.setattr(glm_module, "RETRY_PAUSES_S", (0, 0, 0))
    replies = [ProviderError("HTTP 429: overloaded"), glm_reply(text='{"gap_stay": 0.2}')]

    class Flaky(FakeHttp):
        def post(self, body):
            self.calls.append(body)
            reply = replies[len(self.calls) - 1]
            if isinstance(reply, Exception):
                raise reply
            return reply

    http = Flaky(None)
    glm = GlmClient(DiskCache(tmp_path / "cache"), RequestBudget(2), sdk=http)
    payload = glm.ask(SENSES, QUESTIONS).payload
    assert payload["text"] == '{"gap_stay": 0.2}' and payload["attempts"] == 2
    assert len(http.calls) == 2 and glm.budget.used == 2  # both HTTP requests counted

    tight = GlmClient(DiskCache(tmp_path / "cache2"), RequestBudget(1), sdk=Flaky(None))
    replies[:] = [ProviderError("HTTP 429: overloaded"), glm_reply()]
    with pytest.raises(BudgetExhausted):  # no room for the retry: the cap wins
        tight.ask(SENSES, QUESTIONS)


def test_a_failure_that_is_not_the_queue_is_not_retried(tmp_path):
    glm, http = client(tmp_path, ProviderError("HTTP 401: bad key"), max_requests=5)
    with pytest.raises(ProviderError, match="401"):
        glm.ask(SENSES, QUESTIONS)
    assert len(http.calls) == 1 and glm.budget.used == 1
