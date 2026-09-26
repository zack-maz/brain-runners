import pytest

from bakeoff.game.engine import Game
from bakeoff.game.rules import V2
from bakeoff.game.track import generate_track
from bakeoff.players.jev_step1 import QUESTIONS as STEP1_QUESTIONS
from bakeoff.players.question_sets import GUIDED, STEP1, MAP, SETS, STEP2, values_of
from bakeoff.senses import compute_senses, truth_of


def noul(p):
    return {"type": "noul", "noul": p}


def test_the_four_sets():
    assert list(SETS) == ["step1", "guided", "step2", "map"]
    assert all(SETS[name].name == name for name in SETS)


def test_step1_asks_exactly_what_jev_step1_asks_so_its_cache_replays():
    assert STEP1.build(V2) == STEP1_QUESTIONS


def test_choice_is_one_choice_that_names_each_landing_tile():
    questions = GUIDED.build(V2)
    assert list(questions) == ["action"] and questions["action"]["type"] == "choice"
    criteria = questions["action"]["criteria"]
    assert list(criteria) == ["stay", "left", "right", "jump"]
    assert criteria["left"] == ("move one lane left; lands on offset -1 of `ahead[0]`, a gap if "
                                "`ahead[0].gaps_relative` contains -1")
    assert criteria["jump"].endswith("lands on offset 0 of `ahead[1]`, a gap if `ahead[1].gaps_relative` contains 0")
    assert questions["action"]["instructions"].endswith("Choose one whose landing tile is not a gap.")


def test_step2_adds_a_trapped_question_per_move():
    questions = STEP2.build(V2)
    assert list(questions) == [*STEP1_QUESTIONS, "trapped_stay", "trapped_left", "trapped_right", "trapped_jump"]
    assert questions["trapped_jump"]["instructions"] == (
        "After the action `jump` (landing on offset 0 of `ahead[1]`), would every next move land on a gap, that is, "
        "does `ahead[2].gaps_relative` contain all of -1, 0 and 1, and does `ahead[3].gaps_relative` contain 0?")
    with pytest.raises(ValueError, match="need 4 rows and 2 lanes"):
        STEP2.build(V2.variant(lookahead=3))


def test_reader_asks_one_question_per_visible_tile():
    questions = MAP.build(V2)
    assert len(questions) == 6 * 7 and all(q["type"] == "noul" for q in questions.values())
    assert questions["tile_r2_l3"]["instructions"] == (
        "Is offset -3 of `ahead[1]` a gap, that is, does `ahead[1].gaps_relative` contain -3?")
    assert len(MAP.build(V2.variant(lookahead=3, window=2))) == 3 * 5


def test_values_of_wants_every_answer_usable():
    questions = STEP2.build(V2)
    good = {q: noul(0.25) for q in questions}
    assert values_of(questions, good) == {q: 0.25 for q in questions}
    for bad in (None, 1.5, -0.1, float("nan"), True, "0.2"):
        assert values_of(questions, {**good, "trapped_jump": noul(bad)}) is None
    assert values_of(questions, {q: a for q, a in good.items() if q != "gap_left"}) is None
    assert values_of(GUIDED.build(V2), {"action": {"choice": "jump"}}) == {"action": "jump"}
    assert values_of(GUIDED.build(V2), {"action": {"choice": "fly"}}) is None


def test_the_rules_on_hand_made_answers():
    assert STEP1.pick({"gap_stay": 0.4, "gap_left": 0.1, "gap_right": 0.1, "gap_jump": 0.3}) == "left"
    assert GUIDED.pick({"action": "right"}) == "right"
    safe_but_trapped = {"gap_stay": 0.0, "trapped_stay": 0.9, "gap_left": 0.2, "trapped_left": 0.0,
                        "gap_right": 0.6, "trapped_right": 0.0, "gap_jump": 0.9, "trapped_jump": 0.0}
    assert STEP2.pick(safe_but_trapped) == "left"  # stay's landing is floor, but a dead end
    tied = {f"{kind}_{a}": 0.0 for kind in ("gap", "trapped") for a in ("stay", "left", "right", "jump")}
    assert STEP2.pick(tied) == "stay"
    tiles = {q: 0.0 for q in MAP.build(V2)}
    assert MAP.pick(tiles) == "stay"
    assert MAP.pick({**tiles, "tile_r1_c": 0.9}) == "left"
    assert MAP.pick({**tiles, "tile_r1_c": 0.4}) == "stay"  # read as floor: 0.5 or less


@pytest.mark.parametrize("name, floor", [("step1", 60), ("step2", 100), ("map", 140)])
def test_perfect_answers_reach_each_rules_ceiling(name, floor):
    # free and exact: the answers are the truth; a real model can only do worse
    question_set = SETS[name]
    questions, rows = question_set.build(V2), []
    for seed in range(1000, 1010):
        game = Game(generate_track(seed))
        while not game.over:
            senses = compute_senses(game)
            game.step(question_set.pick({q: float(truth_of(senses, q)) for q in questions}))
        rows.append(game.rows_survived)
    assert sum(rows) / len(rows) >= floor
