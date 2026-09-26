import re

from bakeoff.players import REGISTRY
from bakeoff.roster import ROSTER, players, roster_json

HEX = re.compile(r"#[0-9A-F]{6}")


def test_every_registered_player_is_exactly_one_skin():
    assert sorted(players()) == sorted(REGISTRY)
    assert len(players()) == len(set(players()))


def test_the_characters_and_their_default_skins_in_the_select_screens_order():
    assert [c["name"] for c in ROSTER] == ["Fly", "Jev", "Haiku", "GLM Flash", "Bot"]
    assert [c["skins"][0]["player"] for c in ROSTER] == ["fly", "jev_plain", "haiku_plain", "glm_plain", "random"]
    jev = next(c for c in ROSTER if c["id"] == "jev")
    assert [s["name"] for s in jev["skins"]] == ["Plain", "Guided", "Step 1", "Step 2", "Map"]
    assert [s["player"] for s in jev["skins"]] == ["jev_plain", "jev_guided", "jev_step1", "jev_step2", "jev_map"]


def test_the_skin_colours_the_user_settled():
    colour = {s["player"]: s["color"] for c in ROSTER for s in c["skins"]}
    assert [colour[f"jev_{k}"] for k in ("plain", "guided", "step1", "step2", "map")] == \
        ["#B9BEC4", "#5FA35A", "#E6B422", "#B8404F", "#1E2227"]
    assert colour["haiku_plain"] == "#D97757" and colour["glm_plain"] == "#9AA0A6"
    assert colour["haiku_guided"] == colour["glm_guided"] == colour["jev_guided"]
    assert (colour["fly"], colour["fly2"]) == ("#AEB4BA", "#F7768E")
    assert (colour["random"], colour["solver"], colour["always_jump"]) == ("#8A9097", "#7AA2F7", "#E8EBED")


def test_every_colour_is_a_hex_colour_and_every_skin_says_what_it_does():
    for character in ROSTER:
        assert character["sprite"] in ("fly", "visor", "chat", "ox", "bot")
        for skin in character["skins"]:
            assert HEX.fullmatch(skin["color"]), skin
            assert all(len(k) == 1 and HEX.fullmatch(v) for k, v in skin["inks"].items()), skin
            assert skin["about"].endswith("."), skin


def test_every_skin_but_the_yardsticks_says_what_is_ours():
    for character in ROSTER:
        for skin in character["skins"]:
            if character["id"] == "bot":
                assert "ours" not in skin["about"], skin  # a yardstick, not a contestant: nothing here is ours
            else:
                assert "ours" in skin["about"], skin


def test_the_json_is_a_copy():
    data = roster_json()
    data[0]["skins"][0]["inks"]["x"] = "#000000"
    data[0]["name"] = "changed"
    assert ROSTER[0]["name"] == "Fly" and "x" not in ROSTER[0]["skins"][0]["inks"]
