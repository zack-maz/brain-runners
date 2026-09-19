"""The untrained whole-brain model (Shiu et al. 2024): built once, restored per 100 ms decision window.

The network is built by the authors' own `create_model` with their `default_params`. Ours is only
the input mechanics: one PoissonGroup wired one-to-one onto the looming detectors, with the same
kick (w_syn * f_poi) and zero refractory period that the authors' `poi()` gives stimulated
neurons, so the rates can change between decisions without a rebuild.
"""

from __future__ import annotations

import importlib.util
import time

import numpy as np

from bakeoff.fly import data
from bakeoff.fly.neurons import SIDES, Selection, load_selection
from bakeoff.fly.reading import WINDOW_MS, Reading


def _upstream_model():
    spec = importlib.util.spec_from_file_location("shiu_model", data.MODEL_CODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Brain:
    def __init__(self, selection: Selection | None = None, window_ms: float = WINDOW_MS, target: str = "cython"):
        found = data.problems()
        if found:
            raise FileNotFoundError("fly data unusable (run `uv run python -m scripts.fetch_fly_data`): "
                                    + "; ".join(found))
        import brian2 as b2

        self._b2 = b2
        b2.prefs.codegen.target = target
        upstream = _upstream_model()
        self.selection = selection or load_selection(data.ANNOTATIONS, data.COMPLETENESS)
        self.window_ms = window_ms
        params = dict(upstream.default_params)
        self._neurons, synapses, self._monitor = upstream.create_model(
            str(data.COMPLETENESS), str(data.CONNECTIVITY), params)
        stimulated = np.array([i for side in SIDES for i in self.selection.inputs[side]], dtype=int)
        self._n_left = len(self.selection.inputs["left"])
        self._poisson = b2.PoissonGroup(len(stimulated), rates=np.zeros(len(stimulated)) * b2.Hz, name="looming")
        kick_mv = float(params["w_syn"] * params["f_poi"] / b2.mV)
        wiring = b2.Synapses(self._poisson, self._neurons, on_pre=f"v_post += {kick_mv!r}*mV", name="looming_wiring")
        wiring.connect(i=np.arange(len(stimulated)), j=stimulated)
        self._neurons.rfc[stimulated] = 0 * b2.ms  # as upstream poi(): no refractory period for Poisson targets
        self._net = b2.Network(self._neurons, synapses, self._monitor, self._poisson, wiring)
        self._net.run(0.1 * b2.ms)  # compiles the code once
        self._net.store("clean")
        self._t0_ms = float(self._net.t / b2.ms)

    def window(self, left_hz: float, right_hz: float, noise_seed: int | None = None) -> Reading:
        b2 = self._b2
        started = time.perf_counter()
        self._net.restore("clean")
        if noise_seed is not None:
            b2.seed(noise_seed)
        hz = np.full(len(self._poisson), float(right_hz))  # not named `rates`: brian2 would warn
        hz[:self._n_left] = float(left_hz)
        self._poisson.rates = hz * b2.Hz
        self._net.run(self.window_ms * b2.ms)
        who = np.asarray(self._monitor.i)
        when_ms = np.asarray(self._monitor.t / b2.ms) - self._t0_ms
        rates_hz, counts, times = {}, {}, {}
        for name, members in self.selection.readouts.items():
            mask = np.isin(who, members)
            counts[name] = int(mask.sum())
            rates_hz[name] = counts[name] / len(members) / (self.window_ms / 1000.0)
            times[name] = [round(float(t), 1) for t in when_ms[mask]]
        return Reading(rates_hz=rates_hz, spike_counts=counts, spike_times_ms=times,
                       total_spikes=int(len(who)), wall_ms=(time.perf_counter() - started) * 1000.0)

    def close(self) -> None:
        self._net = self._neurons = self._monitor = self._poisson = None
