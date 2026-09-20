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


def pytest_collection_modifyitems(config, items):
    """`slow` tests run the real fly brain; they are skipped when its data has not been fetched."""
    from bakeoff.fly.data import data_available

    if data_available():
        return
    skip = pytest.mark.skip(reason="fly data absent: uv run python -m scripts.fetch_fly_data")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def brain():
    """The real fly brain, built once per test session (about 1 GB, half a minute). Slow tests only."""
    from bakeoff.fly.brain import Brain

    brain = Brain()
    yield brain
    brain.close()
