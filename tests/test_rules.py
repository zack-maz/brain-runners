import json

import pytest

from bakeoff.game.rules import DEFAULT, RULES, V1, V2, Rules, resolve, rules_for


def test_the_two_versions():
    assert DEFAULT == "v2" and RULES == {"v1": V1, "v2": V2}
    assert (V1.max_rows, V1.difficulty_rows, V1.lookahead, V1.window) == (300, 300, 6, 3)
    assert (V2.max_rows, V2.difficulty_rows, V2.lookahead, V2.window) == (150, 100, 6, 3)
    assert (V2.lanes, V2.runway_rows, V2.start_gap_rate, V2.end_gap_rate, V2.max_gap_width) == (12, 4, 0.04, 0.16, 3)


def test_rules_for_names_the_known_versions():
    assert rules_for("v1") is V1
    with pytest.raises(ValueError, match="unknown game version 'v9'; known: v1, v2"):
        rules_for("v9")


def test_a_different_vision_is_named_and_a_different_length_is_not():
    assert V2.variant(lookahead=3).version == "v2+look3"
    assert V2.variant(lookahead=8, window=4).version == "v2+look8+win4"
    assert V2.variant(lookahead=6, window=3) == V2  # unchanged values leave the version alone
    assert V2.variant(max_rows=40) == Rules(**{**V2.to_json(), "max_rows": 40})


def test_chained_variants_are_named_from_the_base_version():
    # back to the base version's own lookahead: named plain V2, not v2+look3+look6
    assert V2.variant(lookahead=3).variant(lookahead=6) == V2
    assert V2.variant(lookahead=3).variant(lookahead=6).version == "v2"
    assert V2.variant(lookahead=3).variant(window=2).version == "v2+look3+win2"
    assert V2.variant(lookahead=3).variant(lookahead=6).same_game(V2)


def test_resolve_defaults_to_the_current_version():
    assert resolve() == V2 and resolve(V1) == V1
    assert resolve(max_rows=20).max_rows == 20 and resolve(V1, 20).version == "v1"


def test_json_round_trip():
    rules = V2.variant(lookahead=3)
    assert Rules.from_json(json.loads(json.dumps(rules.to_json()))) == rules


def test_a_game_block_from_before_versions_is_v1():
    old = {"lanes": 12, "max_rows": 40, "lookahead": 6, "window": 3, "looming": {"gain_hz": 250.0}}
    assert Rules.from_json(old) == V1.variant(max_rows=40)


def test_a_recorded_block_may_carry_more_than_the_rules():
    assert Rules.from_json({**V2.to_json(), "looming": {"gain_hz": 250.0}}) == V2


def test_a_versioned_block_missing_a_field_is_filled_from_its_named_base_version():
    block = V2.to_json()
    del block["max_gap_width"]
    assert Rules.from_json(block) == V2


def test_a_versioned_variant_block_missing_a_field_is_filled_from_its_base_version():
    block = V2.variant(lookahead=3).to_json()
    del block["max_gap_width"]
    assert Rules.from_json(block) == V2.variant(lookahead=3)


def test_a_versioned_block_missing_a_field_with_an_unknown_base_version_raises():
    block = {**V2.to_json(), "version": "v9"}
    del block["max_gap_width"]
    with pytest.raises(ValueError, match=r"cannot read game 'v9'"):
        Rules.from_json(block)


def test_same_game_ignores_length_only():
    assert V2.same_game(V2.variant(max_rows=40))
    assert not V2.same_game(V1)
    assert not V2.same_game(V2.variant(lookahead=3))


def test_every_landing_tile_must_be_in_sight():
    with pytest.raises(ValueError, match="lookahead must be at least 2"):
        V2.variant(lookahead=1)
    with pytest.raises(ValueError, match="window must be 1 to 5 lanes, not 0"):
        V2.variant(window=0)
    with pytest.raises(ValueError, match="window must be 1 to 5 lanes, not 6"):
        V2.variant(window=6)
