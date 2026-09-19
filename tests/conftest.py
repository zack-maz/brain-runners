import pytest

from bakeoff.game.track import LOOKAHEAD, Track


@pytest.fixture
def make_track():
    """Hand-made track: make_track({1: [6], 3: [5, 6, 7]}) puts gaps in those lanes of rows 1 and 3."""

    def _make(gap_rows: dict[int, list[int]], max_rows: int = 10, lanes: int = 12) -> Track:
        length = max_rows + LOOKAHEAD + 2
        gaps = tuple(tuple(sorted(gap_rows.get(row, ()))) for row in range(length))
        return Track(seed=0, lanes=lanes, max_rows=max_rows, gaps=gaps)

    return _make
