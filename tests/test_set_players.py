import json

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import Game
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players import PAID, make_player
from bakeoff.players.briefing import RULES as BRIEFING
from bakeoff.players.question_sets import CHOICE, READER, TWO_STEP
from bakeoff.players.set_players import (CHAT_SYSTEM, JevReaderPlayer, JevTwoStepPlayer, HaikuChoicePlayer,
                                         HaikuComposedPlayer, HaikuReaderPlayer, SET_PLAYERS)
from bakeoff.runner import Runner
from bakeoff.senses import compute_senses, truth_of
from tests.fakes import FakeAnthropic, FakeTypeSafe, jev_set_reply, llm_reply

SENSES = compute_senses(Game(generate_track(1000)))


def jev(tmp_path, cls, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return cls(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def haiku(tmp_path, cls, text, stop_reason="end_turn", cap=10):
    sdk = FakeAnthropic(llm_reply(text, stop_reason))
    return cls(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def safe(questions, value=0.1):
    return {qid: value for qid in questions}


def test_one_paid_player_per_model_and_set():
    names = [p.name for p in SET_PLAYERS]
    assert names == ["jev_choice", "jev_two_step", "jev_reader", "haiku_composed", "haiku_choice", "haiku_two_step",
                     "haiku_reader", "glm_composed", "glm_choice", "glm_two_step", "glm_reader"]
    assert all(name in PAID for name in names)


def test_a_jev_set_player_asks_its_questions_and_its_rule_picks(tmp_path):
    from typesafe_sdk import Noul

    values = {**safe(TWO_STEP.build(V2)), "gap_stay": 0.9}
    player, sdk = jev(tmp_path, JevTwoStepPlayer, jev_set_reply(values))
    decision = player.act(SENSES)
    (call,) = sdk.calls
    assert set(call["questions"]) == set(TWO_STEP.build(V2)) and all(isinstance(q, Noul) for q in call["questions"].values())
    assert decision.chosen_action == "left" and not decision.invalid
    assert decision.info == {"model": "jev-latest", "set": "two_step", "rule": "lowest_two_step_risk",
                             "order": ["stay", "left", "right", "jump"]}
    assert decision.questions == TWO_STEP.build(V2) and decision.answers["gap_stay"]["noul"] == 0.9


def test_a_missing_or_impossible_answer_is_invalid_and_logged(tmp_path):
    values = safe(TWO_STEP.build(V2))
    del values["trapped_jump"]
    player, _ = jev(tmp_path, JevTwoStepPlayer, jev_set_reply(values))
    decision = player.act(SENSES)
    assert decision.invalid and decision.chosen_action is None and "gap_left" in decision.answers


def test_the_reader_asks_about_every_tile_of_the_games_view(tmp_path):
    player, sdk = jev(tmp_path, JevReaderPlayer, jev_set_reply(safe(READER.build(V2.variant(lookahead=3)), 0.0)))
    player.reset(Game(generate_track(1000, V2.variant(lookahead=3))), 1000)
    assert len(player.questions) == 3 * 7
    assert player.act(compute_senses(Game(generate_track(1000, V2.variant(lookahead=3))))).chosen_action == "stay"


def test_a_jev_set_player_with_perfect_answers_plays_its_rules_ceiling(tmp_path):
    class Oracle(FakeTypeSafe):  # answers the truth, read from the senses it is sent
        def system_one(self, state, questions, model=None):
            self.reply = jev_set_reply({qid: float(truth_of(state, qid)) for qid in questions})
            return super().system_one(state, questions, model)

    player = JevReaderPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(1000), sdk=Oracle(None))
    records = Runner(tmp_path / "runs").run_seed(player, 1000, "r")
    assert records[-1]["finished"] and records[-1]["rows_survived"] == 150


def test_the_llm_twin_gets_the_same_questions_in_one_structured_request(tmp_path):
    values = {**safe(TWO_STEP.build(V2)), "gap_stay": 0.9}
    player, sdk = haiku(tmp_path, HaikuComposedPlayer, json.dumps({k: v for k, v in values.items() if k.startswith("gap_")}))
    decision = player.act(SENSES)
    (call,) = sdk.calls
    assert call["system"].startswith(CHAT_SYSTEM) and call["system"].startswith(BRIEFING)
    assert "- `gap_left` (yes/no): Would the action `left` land the runner on a gap" in call["system"]
    schema = call["output_config"]["format"]["schema"]
    assert schema["required"] == ["gap_left", "gap_stay", "gap_right", "gap_jump"]
    assert schema["properties"]["gap_left"] == {"type": "number"} and schema["additionalProperties"] is False
    assert json.loads(call["messages"][0]["content"]) == SENSES
    assert decision.chosen_action == "left" and not decision.invalid
    assert decision.answers["gap_stay"] == {"noul": 0.9} and decision.answers["stop_reason"] == "end_turn"
    assert decision.questions["questions"] == {k: v for k, v in TWO_STEP.build(V2).items() if k.startswith("gap_")}


def test_the_llm_choice_twin_names_the_options_once_and_not_the_briefing_twice(tmp_path):
    player, sdk = haiku(tmp_path, HaikuChoicePlayer, '{"action": "jump"}')
    assert player.act(SENSES).chosen_action == "jump"
    system = sdk.calls[0]["system"]
    assert system.count(BRIEFING) == 1
    assert "Options: `stay`: run straight; lands on offset 0 of `ahead[0]`" in system
    assert sdk.calls[0]["output_config"]["format"]["schema"]["properties"]["action"] == {
        "type": "string", "enum": ["stay", "left", "right", "jump"]}


@pytest.mark.parametrize("text, stop_reason", [
    ("not json", "end_turn"), ('["a list"]', "end_turn"), ('{"gap_left": 0.1}', "end_turn"),
    ('{"gap_left": 2, "gap_stay": 0, "gap_right": 0, "gap_jump": 0}', "end_turn"),
    ('{"gap_left": 0.1, "gap_stay": 0, "gap_right": 0, "gap_jump": 0}', "max_tokens")])
def test_an_llm_answer_that_is_not_every_usable_number_is_invalid(tmp_path, text, stop_reason):
    player, _ = haiku(tmp_path, HaikuComposedPlayer, text, stop_reason)
    decision = player.act(SENSES)
    assert decision.invalid and decision.chosen_action is None and decision.answers["text"] == text


def test_the_reader_twin_leaves_room_for_42_answers(tmp_path):
    player, sdk = haiku(tmp_path, HaikuReaderPlayer, json.dumps(safe(READER.build(V2), 0.0)))
    assert player.act(SENSES).chosen_action == "stay"
    assert sdk.calls[0]["max_tokens"] == 256 + 12 * 42


def test_set_players_spend_nothing_without_a_budget_and_stop_at_the_cap(tmp_path):
    player = make_player("haiku_choice", cache=DiskCache(tmp_path))
    with pytest.raises(BudgetExhausted):
        player.act(SENSES)
    capped, _ = jev(tmp_path, JevReaderPlayer, jev_set_reply(safe(READER.build(V2))), cap=1)
    capped.act(SENSES)
    game = Game(generate_track(1000))
    for _ in range(12):  # past the empty runway, so the senses differ and the cache cannot answer
        game.step("jump")
    with pytest.raises(BudgetExhausted):
        capped.act(compute_senses(game))


def test_both_chat_models_are_sent_the_same_request_and_differ_only_in_the_provider(tmp_path):
    from bakeoff.clients.core import DiskCache, RequestBudget
    from bakeoff.players.set_players import GlmComposedPlayer
    from tests.fakes import FakeHttp, glm_reply

    cache = DiskCache(tmp_path / "cache")
    haiku = HaikuComposedPlayer(cache=cache, budget=RequestBudget(1), sdk=FakeAnthropic(llm_reply()))
    glm = GlmComposedPlayer(cache=cache, budget=RequestBudget(1), sdk=FakeHttp(glm_reply()))
    assert glm.questions == haiku.questions  # same system prompt, same question lines, same JSON shape
    assert glm.client.provider == "glm" and glm.client.model == "glm-4.5-flash"


def test_a_glm_player_reads_its_answers_like_the_haiku_twin(tmp_path):
    import json

    from bakeoff.clients.core import DiskCache, RequestBudget
    from bakeoff.players.set_players import GlmTwoStepPlayer
    from tests.fakes import FakeHttp, glm_reply

    player = GlmTwoStepPlayer(cache=DiskCache(tmp_path / "cache"), budget=RequestBudget(1), sdk=FakeHttp(None))
    answers = {**safe(player.set_questions, 0.9), "gap_left": 0.01, "trapped_left": 0.01}
    player.client._sdk.reply = glm_reply(text=json.dumps(answers))
    decision = player.act(SENSES)
    assert decision.chosen_action == "left" and not decision.invalid
    assert decision.info["set"] == "two_step" and decision.answers["gap_left"] == {"noul": 0.01}


def test_a_cut_off_glm_reply_is_invalid_and_the_runner_falls_back(tmp_path):
    from bakeoff.clients.core import DiskCache, RequestBudget
    from bakeoff.players.set_players import GlmReaderPlayer
    from tests.fakes import FakeHttp, glm_reply

    player = GlmReaderPlayer(cache=DiskCache(tmp_path / "cache"), budget=RequestBudget(1),
                             sdk=FakeHttp(glm_reply(text='{"tile_r1_c": 0.1', finish_reason="length")))
    decision = player.act(SENSES)
    assert decision.chosen_action is None and decision.invalid


def test_a_fenced_json_answer_is_read_by_both_chat_models():
    from bakeoff.players.paid import unfenced

    assert unfenced('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert unfenced('```\n{"a": 1}```') == '{"a": 1}'
    assert unfenced('{"a": 1}') == '{"a": 1}'  # Claude Haiku's structured output is unchanged
    assert unfenced("  ") == ""
