import pytest

from bakeoff.game.rules import V2
from bakeoff.game.track import Track


PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "ZHIPU_API_KEY", "TYPESAFE_API_KEY")


@pytest.fixture(autouse=True)
def no_provider_keys(request, monkeypatch, tmp_path_factory):
    """No test but a `live` one can find a provider key, so none can reach a provider. A cap of 0 is
    enough today (decision 58), but an uncapped player, as Jev was under decision 50, would otherwise go live with
    the key in .env."""
    if "live" in request.keywords:
        return
    monkeypatch.setattr("bakeoff.clients.keys.ENV_FILE", tmp_path_factory.mktemp("nokeys") / ".env")
    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_track():
    """Hand-made track: make_track({1: [6], 3: [5, 6, 7]}) puts gaps in those lanes of rows 1 and 3."""

    def _make(gap_rows: dict[int, list[int]], max_rows: int = 10, lookahead: int | None = None,
              window: int | None = None) -> Track:
        rules = V2.variant(max_rows=max_rows, lookahead=lookahead, window=window)
        length = max_rows + rules.lookahead + 2
        gaps = tuple(tuple(sorted(gap_rows.get(row, ()))) for row in range(length))
        return Track(seed=0, rules=rules, gaps=gaps)

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
    """The real fly brain, built once per test session (about 1 GB, half a minute). Slow tests only.
    Every fly2 candidate's input is registered beside fly's, so fly's slow tests run on the shared brain."""
    from bakeoff.fly.brain import Brain
    from bakeoff.fly.channels import FLY_CELLS, MAPPINGS

    brain = Brain(inputs={"fly": FLY_CELLS, **{name: mapping.cells for name, mapping in MAPPINGS.items()}})
    yield brain
    brain.close()
