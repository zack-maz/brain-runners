"""Opt-in: one real request per provider. Costs money. Run with `uv run pytest -m live -q`.
Each test has a budget of exactly one request and its own empty cache."""

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.clients.keys import require_key
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players.jev import JevPlayer
from bakeoff.players.haiku import HaikuPlayer
from bakeoff.senses import compute_senses

pytestmark = pytest.mark.live
PRACTICE_SEED = 1000  # never a tournament seed


def one_decision(player_class, key_name, tmp_path):
    try:
        require_key(key_name)
    except ValueError as e:
        pytest.skip(str(e))
    player = player_class(cache=DiskCache(tmp_path), budget=RequestBudget(1))
    try:
        decision = player.act(compute_senses(Game(generate_track(PRACTICE_SEED))))
    finally:
        player.close()
    assert player.budget.used == 1
    assert decision.error is None, decision.error
    assert decision.chosen_action in ACTIONS and not decision.invalid
    assert decision.latency_ms > 0 and not decision.cache_hit
    assert decision.usage["input_tokens"] > 0
    return decision


def test_jev_answers_one_real_request(tmp_path):
    decision = one_decision(JevPlayer, "TYPESAFE_API_KEY", tmp_path)
    assert set(decision.answers) == {"action", "gap_ahead", "left_safe"}
    assert set(decision.answers["action"]["probabilities"]) == set(ACTIONS)
    assert 0.0 <= decision.answers["gap_ahead"]["noul"] <= 1.0


def test_the_llm_answers_one_real_request(tmp_path):
    decision = one_decision(HaikuPlayer, "ANTHROPIC_API_KEY", tmp_path)
    assert decision.answers["stop_reason"] == "end_turn"
    assert decision.info["model"].startswith("claude-haiku-4-5")
