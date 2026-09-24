"""The fly must be buildable from a worker thread, because that is where a live run plays.

brian2 installs a SIGINT handler as it is imported, which CPython allows only on the main thread, so
`import brian2` inside the run's thread raised and the page reported "interrupted" with no reason
(2026-09-24). These tests are fast: they do not build a brain, they only exercise the import rule.
"""

from __future__ import annotations

import signal
import sys
import threading
import types

import pytest

from bakeoff.fly.brain import import_brian2


def _fake_brian2(monkeypatch):
    """A stand-in for brian2 that does what the real one does at import: install a SIGINT handler."""
    module = types.ModuleType("brian2")

    def install():
        signal.signal(signal.SIGINT, signal.default_int_handler)  # raises off the main thread
        module.installed = True

    module.install = install
    monkeypatch.delitem(sys.modules, "brian2", raising=False)
    monkeypatch.setitem(sys.modules, "brian2", module)
    return module


def test_the_import_rule_runs_on_a_worker_thread(monkeypatch):
    """The real symptom: a signal handler installed off the main thread is a ValueError."""
    def on_thread(fn):
        out = {}
        def target():
            try:
                out["value"] = fn()
            except BaseException as e:  # noqa: BLE001 - the test wants whatever it raised
                out["error"] = e
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        return out

    with pytest.raises(ValueError, match="main thread"):
        raise on_thread(lambda: signal.signal(signal.SIGINT, signal.default_int_handler))["error"]

    _fake_brian2(monkeypatch)
    assert "error" not in on_thread(import_brian2), "importing brian2 must work off the main thread"


def test_the_shim_puts_signal_handling_back(monkeypatch):
    """Only the import is unhooked: everything after it installs handlers as usual."""
    _fake_brian2(monkeypatch)
    installed = signal.signal
    done = threading.Event()

    def target():
        import_brian2()
        done.set()

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    assert done.is_set()
    assert signal.signal is installed


def test_the_main_thread_imports_brian2_untouched(monkeypatch):
    """On the main thread nothing is shimmed: brian2 keeps its own Ctrl-C handler."""
    module = _fake_brian2(monkeypatch)
    calls = []
    monkeypatch.setattr(signal, "signal", lambda *args: calls.append(args))
    assert import_brian2() is module
    module.install()
    assert calls, "the main thread must let brian2 install its handler"
