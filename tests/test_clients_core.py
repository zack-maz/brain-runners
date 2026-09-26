import json

import pytest

from bakeoff.clients.core import (DiskCache, PaidClient, ProviderError, Reply, RequestBudget, SharedBudget,
                                  UncappedBudget, cache_key,
                                  cached_request)
from bakeoff.errors import BudgetExhausted

SENSES = {"lane": 4, "lanes": 12, "rows_survived": 0, "ahead": [{"row": 1, "gaps_relative": [0]}]}
QUESTIONS = {"action": {"type": "choice"}}


def test_cache_key_covers_provider_model_senses_and_questions_and_ignores_dict_order():
    base = cache_key("jev", "jev-latest", SENSES, QUESTIONS)
    assert len(base) == 64
    assert cache_key("jev", "jev-latest", dict(reversed(SENSES.items())), QUESTIONS) == base
    assert cache_key("llm", "jev-latest", SENSES, QUESTIONS) != base
    assert cache_key("jev", "jev-2", SENSES, QUESTIONS) != base
    assert cache_key("jev", "jev-latest", {**SENSES, "lane": 5}, QUESTIONS) != base
    assert cache_key("jev", "jev-latest", SENSES, {"action": {"type": "noul"}}) != base


def test_disk_cache_round_trip_keeps_the_request_beside_the_response(tmp_path):
    cache = DiskCache(tmp_path)
    assert cache.get("jev", "ab" * 32) is None
    cache.put("jev", "ab" * 32, {"model": "jev-latest"}, {"answers": {}})
    assert cache.get("jev", "ab" * 32) == {"answers": {}}
    path = tmp_path / "jev" / "ab" / f"{'ab' * 32}.json"
    assert json.loads(path.read_text()) == {"request": {"model": "jev-latest"}, "payload": {"answers": {}}}
    assert [p.name for p in path.parent.iterdir()] == [path.name]  # no partial file left


def test_a_damaged_cache_file_is_a_miss(tmp_path):
    cache = DiskCache(tmp_path)
    cache.put("jev", "cd" * 32, {}, {"ok": True})
    (tmp_path / "jev" / "cd" / f"{'cd' * 32}.json").write_text('{"payl')
    assert cache.get("jev", "cd" * 32) is None


def test_budget_raises_at_the_cap_and_counts_what_was_spent():
    budget = RequestBudget(2)
    budget.spend()
    budget.spend()
    with pytest.raises(BudgetExhausted, match="request cap of 2 reached"):
        budget.spend()
    assert budget.used == 2 and budget.max_requests == 2


def test_a_budget_of_zero_allows_no_live_request_and_a_negative_one_is_refused():
    with pytest.raises(BudgetExhausted):
        RequestBudget(0).spend()
    with pytest.raises(ValueError):
        RequestBudget(-1)


def test_a_miss_spends_calls_live_and_stores_and_a_hit_does_none_of_that(tmp_path):
    cache, budget, calls = DiskCache(tmp_path), RequestBudget(5), []

    def live():
        calls.append(1)
        return {"answer": "stay"}

    first = cached_request(cache, budget, "jev", "jev-latest", SENSES, QUESTIONS, live)
    assert first.payload == {"answer": "stay"} and not first.cache_hit and first.latency_ms >= 0
    second = cached_request(cache, budget, "jev", "jev-latest", SENSES, QUESTIONS, live)
    assert second == Reply({"answer": "stay"}, latency_ms=None, cache_hit=True)
    assert len(calls) == 1 and budget.used == 1


def test_the_cap_stops_a_miss_before_the_live_call_but_never_a_hit(tmp_path):
    cache, calls = DiskCache(tmp_path), []
    cached_request(cache, RequestBudget(1), "jev", "m", SENSES, QUESTIONS, lambda: {"a": 1})
    broke = RequestBudget(0)
    assert cached_request(cache, broke, "jev", "m", SENSES, QUESTIONS, lambda: calls.append(1)).cache_hit
    with pytest.raises(BudgetExhausted):
        cached_request(cache, broke, "jev", "m", {**SENSES, "lane": 5}, QUESTIONS, lambda: calls.append(1))
    assert calls == []


def test_a_failed_request_is_spent_but_not_cached(tmp_path):
    cache, budget = DiskCache(tmp_path), RequestBudget(3)

    def failing():
        raise ProviderError("503")

    with pytest.raises(ProviderError):
        cached_request(cache, budget, "jev", "m", SENSES, QUESTIONS, failing)
    assert budget.used == 1
    assert not cached_request(cache, budget, "jev", "m", SENSES, QUESTIONS, lambda: {"a": 1}).cache_hit
    assert budget.used == 2


class Echo(PaidClient):
    provider, key_name, default_model = "echo", "ECHO_KEY", "echo-1"

    def _live(self, senses, questions):
        return {"lane": senses["lane"]}


def test_a_paid_client_asks_through_the_cache_and_the_cap(tmp_path):
    client = Echo(DiskCache(tmp_path), RequestBudget(1), sdk=object())
    assert client.model == "echo-1" and Echo(DiskCache(tmp_path), RequestBudget(1), model="echo-2").model == "echo-2"
    assert client.ask(SENSES, QUESTIONS).payload == {"lane": 4}
    assert client.ask(SENSES, QUESTIONS).cache_hit
    with pytest.raises(BudgetExhausted):
        client.ask({**SENSES, "lane": 5}, QUESTIONS)


def test_paid_client_preflight_wants_the_key_only_when_it_may_go_live_with_its_own_sdk(tmp_path, monkeypatch):
    monkeypatch.setattr("bakeoff.clients.keys.ENV_FILE", tmp_path / "absent")
    monkeypatch.delenv("ECHO_KEY", raising=False)
    Echo(DiskCache(tmp_path), RequestBudget(0)).preflight()
    Echo(DiskCache(tmp_path), RequestBudget(3), sdk=object()).preflight()
    with pytest.raises(ValueError, match="ECHO_KEY is not set"):
        Echo(DiskCache(tmp_path), RequestBudget(3)).preflight()
    monkeypatch.setenv("ECHO_KEY", "k")
    Echo(DiskCache(tmp_path), RequestBudget(3)).preflight()


def test_an_uncapped_budget_counts_every_live_request_but_never_stops_one():
    budget = UncappedBudget()  # Jev: its requests cost the user nothing (decision 50), but they are still counted
    for _ in range(1000):
        budget.spend()
    assert (budget.used, budget.max_requests, budget.remaining) == (1000, None, None)


def test_a_run_s_view_of_an_uncapped_budget_never_stops_and_counts_on_both():
    shared = UncappedBudget()
    run = SharedBudget(shared)
    for _ in range(5):
        run.spend()
    assert (run.used, shared.used, run.max_requests, run.remaining) == (5, 5, None, None)


def test_an_uncapped_client_asks_for_its_key_only_when_it_goes_live(tmp_path, monkeypatch):
    monkeypatch.setattr("bakeoff.clients.keys.ENV_FILE", tmp_path / "absent")
    monkeypatch.delenv("ECHO_KEY", raising=False)
    Echo(DiskCache(tmp_path), UncappedBudget()).preflight()  # a replay of the cache needs no key
