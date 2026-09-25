import pytest

from bakeoff.fly import shared


class FakeBrain:
    window_ms, selection = 100.0, None

    def __init__(self, inputs):
        self.inputs, self.closed = inputs, False

    def window(self, left_hz, right_hz, noise_seed=None):
        return ("fly", left_hz, right_hz, noise_seed)

    def window_of(self, name, rates, noise_seed=None):
        return (name, rates, noise_seed)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def empty_registry():
    shared._wanted.clear()
    shared._brain, shared._holders = None, 0
    yield
    shared._wanted.clear()
    shared._brain, shared._holders = None, 0


def test_the_first_acquire_builds_one_brain_with_every_input_wanted_so_far():
    built = []
    build = lambda inputs: built.append(FakeBrain(inputs)) or built[-1]
    shared.want("fly", {"left": ()})
    shared.want("fly2", {"centre": ()})
    first = shared.acquire("fly", {"left": ()}, build)
    second = shared.acquire("fly2", {"centre": ()}, build)
    assert len(built) == 1 and set(built[0].inputs) == {"fly", "fly2"}
    assert first.window(1.0, 2.0, noise_seed=3) == ("fly", 1.0, 2.0, 3)
    assert second.window_of("fly2", {"centre": 5.0}, noise_seed=4) == ("fly2", {"centre": 5.0}, 4)


def test_the_brain_closes_with_its_last_holder_and_the_next_run_starts_over():
    built = []
    build = lambda inputs: built.append(FakeBrain(inputs)) or built[-1]
    a, b = shared.acquire("fly", {}, build), shared.acquire("fly", {}, build)
    a.close()
    a.close()  # closing twice lets go once
    assert not built[0].closed
    b.close()
    assert built[0].closed and shared._wanted == {}
    shared.acquire("fly2", {}, build)
    assert len(built) == 2 and set(built[1].inputs) == {"fly2"}


def test_an_input_that_arrives_after_the_brain_is_built_is_an_error():
    shared.acquire("fly", {}, FakeBrain)
    with pytest.raises(RuntimeError, match="built without fly2's input"):
        shared.acquire("fly2", {}, FakeBrain)
