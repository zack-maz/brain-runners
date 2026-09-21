import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import Game
from bakeoff.game.track import generate_track
from bakeoff.players import PAID, make_player
from bakeoff.players.jev_composed import ORDER, QUESTIONS, JevComposedPlayer, pick
from bakeoff.runner import Runner
from bakeoff.senses import LANDS, compute_senses, lands_on_gap
from tests.fakes import FakeTypeSafe, jev_composed_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return JevComposedPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_four_pointed_nouls_one_per_action_worded_as_in_the_spike():
    assert list(QUESTIONS) == ["gap_left", "gap_stay", "gap_right", "gap_jump"]
    assert all(q["type"] == "noul" for q in QUESTIONS.values())
    assert QUESTIONS["gap_left"]["instructions"] == (
        "Would the action `left` land the runner on a gap, that is, does `ahead[0].gaps_relative` contain -1?")
    assert QUESTIONS["gap_stay"]["instructions"].endswith("does `ahead[0].gaps_relative` contain 0?")
    assert QUESTIONS["gap_right"]["instructions"].endswith("does `ahead[0].gaps_relative` contain 1?")
    assert QUESTIONS["gap_jump"]["instructions"] == (
        "Would the action `jump` land the runner on a gap, that is, does `ahead[1].gaps_relative` contain 0?")


def test_it_is_a_paid_player_in_the_registry(tmp_path):
    assert "jev_composed" in PAID
    made = make_player("jev_composed", cache=DiskCache(tmp_path), budget=RequestBudget(0))
    assert isinstance(made, JevComposedPlayer) and made.name == "jev_composed" and made.model == "jev-latest"


def test_the_sdk_gets_the_senses_and_four_typed_nouls_in_one_request(tmp_path):
    from typesafe_sdk import Noul

    jev, sdk = player(tmp_path, jev_composed_reply())
    senses = senses_for()
    jev.act(senses)
    (call,) = sdk.calls
    assert call["state"] == senses and call["model"] == "jev-latest"
    assert set(call["questions"]) == set(QUESTIONS)
    assert all(isinstance(q, Noul) for q in call["questions"].values())
    assert call["questions"]["gap_jump"].instructions == QUESTIONS["gap_jump"]["instructions"]


def test_the_move_is_the_action_least_likely_to_land_on_a_gap(tmp_path):
    jev, _ = player(tmp_path, jev_composed_reply(left=0.9, stay=0.8, right=0.03, jump=0.4))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "right" and not decision.needs_fallback and not decision.gated
    assert decision.questions == QUESTIONS
    assert {k: v["noul"] for k, v in decision.answers.items()} == {
        "gap_left": 0.9, "gap_stay": 0.8, "gap_right": 0.03, "gap_jump": 0.4}
    assert decision.usage == {"input_tokens": 300, "output_tokens": 4}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "jev-latest", "rule": "lowest_gap_probability",
                             "order": ["stay", "left", "right", "jump"]}


def test_ties_after_rounding_to_two_decimals_go_in_the_solvers_order():
    assert ORDER == ("stay", "left", "right", "jump")
    assert pick({"left": 0.1, "stay": 0.1, "right": 0.1, "jump": 0.1}) == "stay"
    assert pick({"left": 0.012, "stay": 0.5, "right": 0.008, "jump": 0.014}) == "left"  # all three round to 0.01
    assert pick({"left": 0.5, "stay": 0.5, "right": 0.021, "jump": 0.019}) == "right"  # both round to 0.02
    assert pick({"left": 0.5, "stay": 0.5, "right": 0.03, "jump": 0.02}) == "jump"


def test_it_is_never_gated_even_when_every_action_looks_fatal(tmp_path):
    jev, _ = player(tmp_path, jev_composed_reply(left=0.99, stay=0.98, right=0.99, jump=0.99))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "stay" and not decision.gated and not decision.needs_fallback


@pytest.mark.parametrize("broken", [None, "0.2", True, float("nan"), {"type": "noul"}])
def test_a_missing_or_non_numeric_noul_is_invalid_never_half_a_judgment(tmp_path, broken):
    jev, _ = player(tmp_path, jev_composed_reply())
    answers = jev_composed_reply(right=0.0)["answers"]
    answers["gap_jump"] = broken if isinstance(broken, dict) else {"type": "noul", "noul": broken}
    action, invalid, logged = jev.read({"answers": answers})
    assert action is None and invalid and logged == answers
    assert jev.read({}) == (None, True, {})


def test_an_invalid_answer_is_logged_and_left_to_the_runners_fallback(tmp_path):
    reply = jev_composed_reply(right=0.0)
    del reply["answers"]["gap_jump"]
    jev, _ = player(tmp_path, reply)
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.invalid and decision.needs_fallback
    assert set(decision.answers) == {"gap_left", "gap_stay", "gap_right"}
    assert decision.info["rule"] == "lowest_gap_probability"


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    jev, sdk = player(tmp_path, jev_composed_reply(left=0.0))
    senses = senses_for()
    jev.act(senses)
    again = jev.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and jev.budget.used == 1


def test_the_one_shot_jev_never_answers_from_the_composed_jevs_cache(tmp_path):
    from bakeoff.players.jev import JevPlayer
    from tests.fakes import jev_reply

    composed, _ = player(tmp_path, jev_composed_reply())
    senses = senses_for()
    composed.act(senses)
    one_shot = JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(0), sdk=FakeTypeSafe(jev_reply()))
    with pytest.raises(BudgetExhausted):  # same provider, model and senses, other questions: another key
        one_shot.act(senses)


def test_a_provider_error_becomes_a_logged_error_and_the_cap_ends_the_run(tmp_path):
    from typesafe_sdk import TypeSafeAPIConnectionError

    jev, _ = player(tmp_path, TypeSafeAPIConnectionError("connection refused"))
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.error == "TypeSafeAPIConnectionError: connection refused"
    assert decision.info is None and decision.questions == QUESTIONS
    capped, sdk = player(tmp_path / "other", jev_composed_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        capped.act(senses_for())
    assert sdk.calls == []


class TruthfulTypeSafe(FakeTypeSafe):
    """Answers the four questions from the state it is sent, as a Jev that reads the track perfectly would."""

    def system_one(self, state, questions, model=None):
        self.reply = jev_composed_reply(**{action: float(lands_on_gap(state, action)) for action in LANDS})
        return super().system_one(state, questions, model)


def test_with_perfect_answers_it_runs_a_practice_track_through_the_runner(tmp_path):
    sdk = TruthfulTypeSafe(None)
    jev = JevComposedPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(100), sdk=sdk)
    records = Runner(tmp_path / "runs").run_seed(jev, 1001, "r", max_rows=60)
    assert records[-1]["finished"] and records[-1]["rows_survived"] == 60
    assert all(r["executed_action"] == r["chosen_action"] and not r["invalid"] for r in records)
    assert {r["executed_action"] for r in records} > {"stay"}  # it had to dodge or jump on the way
    assert jev.budget.used == len(records) == len(sdk.calls)
    assert set(records[0]["answers"]) == set(QUESTIONS) and records[0]["info"]["rule"] == "lowest_gap_probability"
