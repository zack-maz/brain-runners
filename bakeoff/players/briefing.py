"""What the two paid players are told about the game: the same words for both. OURS, written once
before any paid request and never tuned on tournament seeds (the text is part of the cache key)."""

RULES = (
    "A runner moves through a tunnel made of a ring of lanes, one row per turn. `ahead` lists the next rows, "
    "nearest first: `row` 1 is the row the runner enters next. `gaps_relative` lists where the floor of that row "
    "is missing, as lane offsets from the runner's current lane: negative is to the runner's left, 0 is the "
    "runner's own lane, positive is to the right. Only offsets from -3 to 3 are visible. `left` and `right` move "
    "one lane sideways while entering row 1, so they land on offset -1 or 1 of row 1. `stay` lands on offset 0 of "
    "row 1. `jump` passes over row 1 and lands on offset 0 of row 2. Landing on a gap ends the run. The goal is "
    "to survive as many rows as possible."
)
