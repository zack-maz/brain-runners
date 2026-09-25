"""The untrained whole-brain model (Shiu et al. 2024): built once, restored per 100 ms decision window.

The network is built by the authors' own `create_model` with their `default_params`. Ours is only
the input mechanics: one PoissonGroup per registered input wired one-to-one onto its cells, with the
same kick (w_syn * f_poi) and zero refractory period that the authors' `poi()` gives stimulated
neurons, so the rates can change between decisions without a rebuild.

Several flies can share one brain (fly2 spec): each registers an input (a name and its channels'
cells) before the brain is built. A window turns on only that input's group: every other group is
inactive, so it runs no code and draws no random numbers, and only that input's cells lose their
refractory period. A brain with fly's input alone is the network fly has always played on.
"""

from __future__ import annotations

import importlib.util
import signal
import tempfile
import threading
import time
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from bakeoff.fly import data
from bakeoff.fly.channels import FLY_CELLS
from bakeoff.fly.neurons import Selection, load_tables, select_channels, select_neurons
from bakeoff.fly.reading import WINDOW_MS, Reading

Cells = Mapping[str, Sequence[tuple[str, str]]]  # channel -> (cell type, side) groups


def import_brian2():
    """`import brian2`, from any thread.

    brian2 installs its own SIGINT handler while it is being imported, so that Ctrl-C can stop a
    simulation, and CPython allows a signal handler to be installed only from the main thread. A live
    run plays in a worker thread (the page starts it), so importing brian2 there raised
    `ValueError: signal only works in main thread of the main interpreter` and took the whole run
    down — the page showed "interrupted" with no reason. Off the main thread we let the import happen
    without that handler: it only exists to interrupt a simulation from the keyboard, and a live run
    is cancelled between decisions instead. Nothing about the simulation changes.
    """
    if threading.current_thread() is threading.main_thread():
        import brian2 as b2

        return b2
    installed = signal.signal
    signal.signal = lambda *args, **kwargs: None  # only for the length of the import
    try:
        import brian2 as b2
    finally:
        signal.signal = installed
    return b2


def _upstream_model():
    spec = importlib.util.spec_from_file_location("shiu_model", data.MODEL_CODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Brain:
    def __init__(self, selection: Selection | None = None, window_ms: float = WINDOW_MS, target: str = "cython",
                 inputs: Mapping[str, Cells] | None = None, shuffle_seed: int | None = None):
        """`inputs`: name -> channel -> cells; the default is fly's two eyes alone. The first input is built
        active, as fly's always was. `shuffle_seed` wires the brain at random (the shuffled-wiring control,
        bakeoff/fly/shuffle.py); never for a player."""
        data.require()
        b2 = import_brian2()  # from a worker thread too: a live run plays in one
        self._b2 = b2
        b2.prefs.codegen.target = target
        upstream = _upstream_model()
        tables = load_tables(data.ANNOTATIONS, data.COMPLETENESS)
        self.selection = selection or select_neurons(*tables)
        self.inputs = {name: select_channels(*tables, cells) for name, cells in (inputs or {"fly": FLY_CELLS}).items()}
        self.shuffle_seed = shuffle_seed
        self.window_ms = window_ms
        params = dict(upstream.default_params)
        with tempfile.TemporaryDirectory() as tmp:
            connectivity = data.CONNECTIVITY if shuffle_seed is None else _shuffled_file(shuffle_seed, Path(tmp))
            self._neurons, synapses, self._monitor = upstream.create_model(
                str(data.COMPLETENESS), str(connectivity), params)
        kick_mv = float(params["w_syn"] * params["f_poi"] / b2.mV)
        self._rfc = params["t_rfc"]
        self._groups = {}
        objects = []
        # The order inputs are registered in here does not change a window's outcome. With more than one
        # input, `rfc` and `active` are set fresh for every window in window_of() below, so which group is
        # active depends on the name asked for, not on registration order; an inactive group runs no code
        # and draws no random numbers; and b2.seed() runs after restore(), resetting the device's random
        # buffers regardless of how many (inactive) objects sit in the network alongside the active one.
        for name, channels in self.inputs.items():
            cells = np.array([i for members in channels.values() for i in members], dtype=int)
            label = "looming" if name == "fly" else f"looming_{name}"  # fly's objects keep their names
            group = b2.PoissonGroup(len(cells), rates=np.zeros(len(cells)) * b2.Hz, name=label)
            wiring = b2.Synapses(group, self._neurons, on_pre=f"v_post += {kick_mv!r}*mV", name=f"{label}_wiring")
            wiring.connect(i=np.arange(len(cells)), j=cells)
            slices, start = {}, 0
            for channel, members in channels.items():
                slices[channel] = slice(start, start + len(members))
                start += len(members)
            self._groups[name] = (group, wiring, cells, slices)
            objects += [group, wiring]
        self._all_cells = np.unique(np.concatenate([cells for _, _, cells, _ in self._groups.values()]))
        first = next(iter(self._groups))
        self._neurons.rfc[self._groups[first][2]] = 0 * b2.ms  # as upstream poi(): no refractory period for Poisson targets
        for name, (group, wiring, _, _) in self._groups.items():
            group.active = wiring.active = name == first
        self._net = b2.Network(self._neurons, synapses, self._monitor, *objects)
        self._net.run(0.1 * b2.ms)  # compiles the code once
        self._net.store("clean")
        self._t0_ms = float(self._net.t / b2.ms)

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        """fly's window: its two eyes."""
        return self.window_of("fly", {"left": left_hz, "right": right_hz}, noise_seed)

    def window_of(self, input_name: str, rates_hz: Mapping[str, float], noise_seed: int | None = None) -> Reading:
        """One decision window with `input_name`'s channels at `rates_hz` and every other input silent."""
        b2 = self._b2
        if input_name not in self._groups:
            raise KeyError(f"no input {input_name!r} was registered on this brain; it has {sorted(self._groups)}")
        group, wiring, cells, slices = self._groups[input_name]
        if set(rates_hz) != set(slices):
            raise ValueError(f"input {input_name!r} has channels {sorted(slices)}, got rates for {sorted(rates_hz)}")
        started = time.perf_counter()
        self._net.restore("clean")
        if noise_seed is not None:
            b2.seed(noise_seed)
        if len(self._groups) > 1:  # a brain of one input is left exactly as fly's always was
            self._neurons.rfc[self._all_cells] = self._rfc
            self._neurons.rfc[cells] = 0 * b2.ms
            for name, (other, other_wiring, _, _) in self._groups.items():
                other.active = other_wiring.active = name == input_name
        hz = np.zeros(len(group))  # not named `rates`: brian2 would warn
        for channel, members in slices.items():
            hz[members] = float(rates_hz[channel])
        group.rates = hz * b2.Hz
        self._net.run(self.window_ms * b2.ms)
        who = np.asarray(self._monitor.i)
        when_ms = np.asarray(self._monitor.t / b2.ms) - self._t0_ms
        rates, counts, times = {}, {}, {}
        for name, members in self.selection.readouts.items():
            mask = np.isin(who, members)
            counts[name] = int(mask.sum())
            rates[name] = counts[name] / len(members) / (self.window_ms / 1000.0)
            times[name] = [round(float(t), 1) for t in when_ms[mask]]
        return Reading(rates_hz=rates, spike_counts=counts, spike_times_ms=times,
                       total_spikes=int(len(who)), wall_ms=(time.perf_counter() - started) * 1000.0)

    def close(self) -> None:
        self._net = self._neurons = self._monitor = self._groups = None


def _shuffled_file(seed: int, directory: Path) -> Path:
    import pandas as pd

    from bakeoff.fly.shuffle import shuffled_connectivity

    path = directory / f"connectivity_shuffled_{seed}.parquet"
    shuffled_connectivity(pd.read_parquet(data.CONNECTIVITY), seed).to_parquet(path)
    return path
