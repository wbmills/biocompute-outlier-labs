"""cl-sdk custom simulator data source wrapping the NeuroHear tissue model.

Register (done by cl1_adapter when source='cl_sdk_sim'):

    cl.sim.set_simulator_data_source(
        "backend.simulations.reactive_source:create_source",
        config={"seed": 123},
        metadata=cl.sim.SimulatorDataSourceMetadata(channel_count=64))

The source sees ONLY committed stim events (timestamp, channel, phase widths,
phase currents) via on_stim(). It never sees labels, encoder ids or scores.
Rehearsal / software integration only; NOT a model of any real culture.

Written against cl-sdk 1.0.0 (github.com/Cortical-Labs/cl-sdk, src/cl/sim).
Verify signatures at the event: `python -c "import cl.sim; help(cl.sim.SimulatorDataSource)"`.
"""
from __future__ import annotations

import numpy as np

from backend.schema import FS_HZ, N_CHANNELS
from backend.simulations.tissue_model import TissueModel, TissueConfig

try:  # import-safe when cl-sdk is absent
    from cl.sim import (DataSourceBatch, DataSourceSpike, SimulatorDataSource,
                        SimulatorDataSourceMetadata)
    HAVE_CL = True
except Exception:  # pragma: no cover - exercised when cl-sdk missing
    HAVE_CL = False
    SimulatorDataSource = object  # type: ignore


HISTORY_MS = 700.0
UV_PER_UNIT = 0.195   # cl-sdk default-ish scaling; read from metadata if it differs


class ReactiveTissueSource(SimulatorDataSource):  # type: ignore[misc]
    def __init__(self, seed: int = 123, gain_scale: float = 1.0, artifact_scale: float = 1.0):
        self.model = TissueModel(TissueConfig(seed=seed, gain_scale=gain_scale,
                                              artifact_scale=artifact_scale))
        self.seed = seed
        self._events: list[tuple] = []   # (t_ms, ch, current_uA, phase_us)

    @property
    def metadata(self):
        return SimulatorDataSourceMetadata(channel_count=N_CHANNELS, frames_per_second=FS_HZ,
                                           duration_frames=None, seekable=True)

    def open(self) -> None:
        self._events = []

    def close(self) -> None:
        pass

    def on_stim(self, stim) -> None:
        cur = max((abs(c) for c in stim.phase_currents_uA), default=1.0)
        ph = int(stim.phase_durations_us[0]) if stim.phase_durations_us else 160
        self._events.append((stim.timestamp * 1000.0 / FS_HZ, int(stim.channel), float(cur), ph))
        self._events.sort()

    def read(self, from_timestamp: int, frame_count: int):
        t0_ms = from_timestamp * 1000.0 / FS_HZ
        t1_ms = (from_timestamp + frame_count) * 1000.0 / FS_HZ
        g0 = np.floor(t0_ms - HISTORY_MS)
        grid = np.arange(g0, np.ceil(t1_ms) + 1.0) + 0.5
        ev = [e for e in self._events if g0 - 400 <= e[0] < t1_ms]
        rate = self.model.rate(grid, ev, trial_index=t0_ms / 1000.0)
        keep = grid >= np.floor(t0_ms)
        rate, grid = rate[keep], grid[keep]
        rng = np.random.default_rng([self.seed, 3, int(from_timestamp)])
        counts = rng.poisson(np.clip(rate, 0, None) / 1000.0)
        ti, ci = np.nonzero(counts)
        st = grid[ti] - 0.5 + rng.random(len(ti))
        m = (st >= t0_ms) & (st < t1_ms)
        st, ci = st[m], ci[m]
        frames = rng.normal(0, 6.0 / UV_PER_UNIT, (frame_count, N_CHANNELS))
        spikes = []
        for t, c in zip(st, ci):
            ts = int(t * FS_HZ / 1000.0)
            i = ts - from_timestamp
            if 0 <= i < frame_count and not self.model.silent[c]:
                frames[i:i + 8, c] -= self.model.spike_amp_uV[c] / UV_PER_UNIT
                spikes.append(DataSourceSpike(timestamp=ts, channel=int(c)))
        frames[:, self.model.silent] = 0.0
        return DataSourceBatch(frames=np.clip(frames, -32768, 32767).astype(np.int16), spikes=spikes)


def create_source(seed: int = 123, gain_scale: float = 1.0, artifact_scale: float = 1.0):
    if not HAVE_CL:
        raise RuntimeError("cl-sdk is not installed")
    return ReactiveTissueSource(seed=seed, gain_scale=gain_scale, artifact_scale=artifact_scale)
