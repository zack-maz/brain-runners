"""One real brain per process, shared by every fly that plays in it (about 1 GB each: never two).

A fly player registers its input when it is made (`want`) and takes the brain when it first resets
(`acquire`). The brain is built by the first `acquire`, with every input registered by then, so all flies of a
run must be made before the first one resets; the runner and the live loop both make every player first. The
brain is closed when the last holder closes, and the registry is emptied with it, so the next run starts over.
"""

from __future__ import annotations

import gc
import threading
from typing import Callable, Mapping

_lock = threading.Lock()
_wanted: dict[str, Mapping] = {}
_brain = None
_holders = 0


def _real_brain(inputs: dict):
    from bakeoff.fly.brain import Brain  # imports brian2: only when a fly actually plays

    return Brain(inputs=inputs)


def want(name: str, cells: Mapping) -> None:
    with _lock:
        _wanted.setdefault(name, cells)


def acquire(name: str, cells: Mapping, build: Callable[[dict], object] | None = None) -> "Holder":
    """`build(inputs)` makes the brain; the real one when None (looked up at call time, so a test can swap it)."""
    global _brain, _holders
    with _lock:
        _wanted.setdefault(name, cells)
        if _brain is None:
            _brain = (build or _real_brain)(dict(_wanted))
        elif name not in _brain.inputs:
            raise RuntimeError(f"the fly brain of this process was built without {name}'s input "
                               f"(it has {sorted(_brain.inputs)}); make every fly before the first one plays")
        _holders += 1
        return Holder(_brain)


def _release() -> None:
    global _brain, _holders
    with _lock:
        _holders -= 1
        if _holders == 0:
            _brain.close()
            _brain = None
            _wanted.clear()
            gc.collect()  # brian2's objects hold cycles: free this brain before a next one is built beside it


class Holder:
    """What a fly player holds: the shared brain's windows, and a close() that lets go of it once."""

    def __init__(self, brain):
        self._brain = brain
        self.window_ms, self.selection, self.inputs = brain.window_ms, brain.selection, brain.inputs

    def window(self, *args, **kwargs):
        return self._brain.window(*args, **kwargs)

    def window_of(self, *args, **kwargs):
        return self._brain.window_of(*args, **kwargs)

    def close(self) -> None:
        if self._brain is not None:
            self._brain = None
            _release()
