"""Pure-Python simulated backends (no cl-sdk required).

ReactiveSimBackend  -> source 'reactive_sim'  (stimulation-responsive model)
RandomSimBackend    -> source 'sdk_random'    (stimulus-independent spikes; mirrors
                       the cl-sdk default random source; negative control)

Both receive pulses only. Labels never enter this module.
"""
from __future__ import annotations

import threading

from backend.schema import Acquisition, StimPulse, PROVENANCE, IS_LIVING_TISSUE
from backend.encoding.safety import SafetyGate
from backend.simulations.tissue_model import TissueModel, TissueConfig


class ReactiveSimBackend:
    source = "reactive_sim"

    def __init__(self, seed: int = 123, *, raw: bool = True, gate: SafetyGate | None = None,
                 **model_kw):
        self.seed = seed
        self.raw = raw
        self.model_kw = model_kw
        self.model = TissueModel(TissueConfig(seed=seed, **model_kw))
        self.gate = gate or SafetyGate(live=False, limits=None)
        self._trial_counter = 0
        self._lock = threading.Lock()
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def get_status(self) -> dict:
        return {
            "source": self.source, "provenance": PROVENANCE[self.source],
            "is_living_tissue": IS_LIVING_TISSUE[self.source], "connected": self.connected,
            "ready": self.connected, "seed": self.seed, "trials_acquired": self._trial_counter,
            "model": {k: v for k, v in vars(self.model.cfg).items()},
            "disclosure": "Mathematical model. Encoding preferences exist by model construction.",
            "safety": self.gate.status(),
        }

    def record_spontaneous(self, duration_ms: float = 500.0) -> Acquisition:
        with self._lock:
            idx = self._trial_counter
            self._trial_counter += 1
        r = self.model.simulate([], trial_index=idx, pre_ms=0.0, post_ms=duration_ms, raw=False)
        return Acquisition(spikes=r["spikes"], duration_ms=r["duration_ms"], stim_onset_ms=0.0,
                           metadata={"trial_index": idx, "seed": self.seed, "spontaneous": True})

    def run_trial(self, pulses: list[StimPulse]) -> Acquisition:
        self.gate.authorise(pulses, {"source": self.source})
        with self._lock:
            idx = self._trial_counter
            self._trial_counter += 1
        r = self.model.simulate(pulses, trial_index=idx, raw=self.raw)
        return Acquisition(spikes=r["spikes"], duration_ms=r["duration_ms"],
                           stim_onset_ms=r["stim_onset_ms"], raw_samples=r["raw"],
                           delivered=list(pulses),
                           metadata={"trial_index": idx, "seed": self.seed,
                                     "gain_scale": self.model.cfg.gain_scale})

    def control_clone(self, **overrides) -> "ReactiveSimBackend":
        """Same seed/tissue, different settings (e.g. gain_scale=0 for NO_RESPONSE)."""
        kw = dict(self.model_kw)
        kw.update(overrides)
        b = ReactiveSimBackend(self.seed, raw=self.raw, gate=SafetyGate(live=False, limits=None), **kw)
        b._trial_counter = 100_000      # independent noise stream from main run
        b.connect()
        return b


class RandomSimBackend(ReactiveSimBackend):
    source = "sdk_random"

    def __init__(self, seed: int = 123, **kw):
        kw.setdefault("gain_scale", 0.0)
        kw.setdefault("artifact_scale", 0.0)
        super().__init__(seed, **kw)
