"""The Brain Battle roster: the characters, their skins, and what each skin is called and looks like
(docs/history/superpowers/specs/2026-09-25-brain-battle-design.md, section A; colours from docs/history/FRONTEND.md).

A skin is a player: the character is who plays, the skin is how (a question set and its rule, a fly's
input, a yardstick). Every registered player is exactly one skin, and a test keeps it so. The page gets
this as JSON (`roster_json`, embedded by `bakeoff/view.py`) and colours a runner by its skin in the
tunnel, the mind strip and every screen. The drawing itself, the grids and the inks they start from, is
the viewer's (`viewer/sprites.js`); a skin names its sprite, the colour of the sprite's body, and any
other cell it recolours."""

from __future__ import annotations

# the question sets as skins, in the select screen's order (decision 44); plain is the default skin. Each
# line ends with what is ours about it (the honesty rule, CLAUDE.md): the wording of the questions, and the
# code's rule for turning the answers into a move.
SETS = (
    ("plain", "Plain", "One broad question: “Which move?”, asked once. The question is ours."),
    ("guided", "Guided", "One question over the four moves, naming the tile each would land on. Code takes its "
                         "favourite. The question and the rule are ours."),
    ("step1", "Step 1", "Four yes/no questions: would each move land on a gap? Code picks the move least likely "
                        "to. The questions and the rule are ours."),
    ("step2", "Step 2", "Eight questions, two moves ahead. Code takes the lowest combined risk. The questions "
                        "and the rule are ours."),
    ("map", "Map", "One question per visible tile, then code plans a path through what it read. The questions "
                   "and the planner are ours."),
)
# per model, one look per set in the order above: plain is the character's own colour; guided green, step1
# yellow, step2 red, map black with its eyes (or visor) lit blue, which the user chose (docs/history/FRONTEND.md)
SET_LOOKS = {
    "jev": ({"color": "#B9BEC4"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
            {"color": "#1E2227", "inks": {"V": "#7AA2F7"}}),
    "haiku": ({"color": "#D97757"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
              {"color": "#1E2227", "inks": {"k": "#7AA2F7"}}),
    "glm": ({"color": "#9AA0A6"}, {"color": "#5FA35A"}, {"color": "#E6B422"}, {"color": "#B8404F"},
            {"color": "#1E2227", "inks": {"n": "#3A4046", "k": "#7AA2F7"}}),
}


def _skin(player: str, name: str, about: str, color: str, inks: dict | None = None) -> dict:
    return {"player": player, "name": name, "about": about, "color": color, "inks": dict(inks or {})}


def _model(character_id: str, name: str, sprite: str) -> dict:
    skins = [_skin(f"{character_id}_{suffix}", skin_name, about, **look)
             for (suffix, skin_name, about), look in zip(SETS, SET_LOOKS[character_id])]
    return {"id": character_id, "name": name, "sprite": sprite, "skins": skins}


# in the select screen's order; each character's first skin is its default
ROSTER = (
    {"id": "fly", "name": "Fly", "sprite": "fly", "skins": [
        _skin("fly", "Looming", "Looming → escape reflex. Untrained, innate wiring; how gaps become input, which "
                         "neurons we read and the thresholds are ours.", "#AEB4BA"),
        _skin("fly2", "Sideways", "Side-lane gaps drive a sideways channel; dodge before jump. Untrained; its input, "
                                  "read-out, rule and thresholds are ours.", "#F7768E", {"e": "#AEB4BA"}),
    ]},
    _model("jev", "Jev", "visor"),
    _model("haiku", "Haiku", "chat"),
    _model("glm", "GLM Flash", "ox"),
    {"id": "bot", "name": "Bot", "sprite": "bot", "skins": [
        _skin("random", "Random", "A coin: any move. A yardstick, not a contestant.", "#8A9097"),
        _skin("solver", "Solver", "A perfect search: what the track allows. A yardstick, not a contestant.", "#7AA2F7"),
        _skin("always_jump", "Always jump", "Jumps every row. A yardstick, not a contestant.", "#E8EBED"),
    ]},
)


def roster_json() -> list[dict]:
    """The roster as the page reads it: a fresh copy, so nothing a caller does can change the table."""
    return [{**character, "skins": [{**skin, "inks": dict(skin["inks"])} for skin in character["skins"]]}
            for character in ROSTER]


def players() -> list[str]:
    """Every skin's player, in the roster's order."""
    return [skin["player"] for character in ROSTER for skin in character["skins"]]
