"""cl API backend: works against the cl-sdk in-process simulator ('cl_sdk_sim')
or real CL1 hardware ('live_cl1'), decided by cl.is_simulator().

READ-ONLY BY DEFAULT on hardware: every stim goes through SafetyGate, which on
live hardware requires LIVE_STIM_ENABLED=true, operator limits loaded from a
file, and a runtime operator approval. Without those, run_trial() raises
StimRejected and nothing is sent. record_spontaneous() (no stimulation) is
always allowed.

Written against cl-sdk 1.0.0 docs (stim(channel_set, stim_design, burst_design,
lead_time_us), read(frame_count, from_timestamp, analysis=...), timestamp(),
interrupt()). NOT tested on physical hardware. Verify at the event.
"""
from __future__ import annotations

import os
from collections import defaultdict

import numpy as np

from backend.schema import Acquisition, FS_HZ, StimPulse, PROVENANCE, IS_LIVING_TISSUE
from backend.encoding.safety import SafetyGate, StimRejected

PRE_MS = 100.0
POST_MS = 480.0
FRAME_US = 40          # one 25 kHz frame
MIN_LEAD_FRAMES = 2    # cl-sdk minimum lead time: 80 us


def _busy_frames(phase_us: int) -> int:
    """Frames a channel stays busy after a single biphasic pulse starts, as in
    cl-sdk Neurons._compute_burst_schedule (duration + 80 us, rounded to a
    frame) minus the minimum lead time."""
    interval_frames = int((2 * phase_us + 80) / FRAME_US + 0.5)
    return interval_frames - MIN_LEAD_FRAMES


def cl_available() -> tuple[bool, str]:
    try:
        import cl  # noqa: F401
        from importlib.metadata import version   # cl-sdk 1.0.0 has no cl.__version__
        return True, getattr(cl, "__version__", None) or version("cl-sdk")
    except Exception as e:  # ImportError or broken install
        return False, f"{type(e).__name__}: {e}"


def detect_spikes(frames: np.ndarray, k: float = 5.0, refractory: int = 25) -> np.ndarray:
    """Fallback threshold detector (negative crossings below -k*MAD). Returns
    (n,2) [sample_index, channel]."""
    x = frames.astype(np.float32)
    x = x - np.median(x, 0)
    thr = -k * (np.median(np.abs(x), 0) / 0.6745 + 1e-6)
    out = []
    for c in range(x.shape[1]):
        idx = np.flatnonzero((x[1:, c] < thr[c]) & (x[:-1, c] >= thr[c])) + 1
        lastk = -10**9
        for i in idx:
            if i - lastk >= refractory:
                out.append((i, c))
                lastk = i
    return np.array(out, dtype=float).reshape(-1, 2)


class CLBackend:
    def __init__(self, gate: SafetyGate, *, use_reactive_source: bool = True, seed: int = 123):
        self.gate = gate
        self.use_reactive_source = use_reactive_source
        self.seed = seed
        self.neurons = None
        self._ctx = None
        self.source = "cl_sdk_sim"
        self.sdk_version = cl_available()[1]
        self.last_error: str | None = None
        self.uV_per_unit = None

    def connect(self) -> None:
        import cl
        if cl.is_simulator():
            # cl-sdk's visualiser binds the first free port from 8000, which would
            # take the dashboard's port before uvicorn starts. Opt back in with =1.
            os.environ.setdefault("CL_SDK_VISUALISATION", "0")
            # The wall-clock producer reads the source 5 frames per tick, which the
            # reactive model cannot keep up with; accelerated time reads on demand.
            os.environ.setdefault("CL_SDK_ACCELERATED_TIME", "1")
            self.source = "cl_sdk_sim"
            if self.use_reactive_source:
                cl.sim.set_simulator_data_source(
                    "backend.simulations.reactive_source:create_source",
                    config={"seed": self.seed},
                    metadata=cl.sim.SimulatorDataSourceMetadata(channel_count=64))
            else:
                self.source = "sdk_random"
        else:
            self.source = "live_cl1"
            if not self.gate.live:
                raise StimRejected("Hardware detected but gate not in live mode; refusing to connect")
        self._ctx = cl.open()
        self.neurons = self._ctx.__enter__()

    def close(self) -> None:
        if self._ctx is not None:
            try:
                self._ctx.__exit__(None, None, None)
            finally:
                self._ctx, self.neurons = None, None

    def get_status(self) -> dict:
        return {"source": self.source, "provenance": PROVENANCE.get(self.source, self.source),
                "is_living_tissue": IS_LIVING_TISSUE.get(self.source), "connected": self.neurons is not None,
                "ready": self.neurons is not None, "cl_sdk_version": self.sdk_version,
                "last_error": self.last_error, "safety": self.gate.status()}

    def stop(self) -> None:
        self.gate.stop()
        if self.neurons is not None and self.gate.limits is not None:
            from cl import ChannelSet
            try:
                self.neurons.interrupt(ChannelSet(*self.gate.limits.allowed_channels))
            except Exception as e:  # pragma: no cover
                self.last_error = f"interrupt failed: {e}"

    def _read_window(self, start_ts: int, n_frames: int):
        frames = self.neurons.read(n_frames, start_ts)
        spikes = None
        try:
            det = self.neurons.read(n_frames, start_ts, analysis=True)
            spikes = np.array([((s.timestamp - start_ts) * 1000.0 / FS_HZ, s.channel) for s in det.spikes],
                              dtype=float).reshape(-1, 2)
            stims = [((s.timestamp - start_ts) * 1000.0 / FS_HZ, s.channel) for s in getattr(det, "stims", [])]
        except Exception as e:
            self.last_error = f"analysis read unavailable ({e}); using threshold detector"
            stims = []
        if spikes is None:
            sp = detect_spikes(frames)
            sp[:, 0] = sp[:, 0] * 1000.0 / FS_HZ
            spikes = sp
        return frames, spikes, stims

    def record_spontaneous(self, duration_ms: float = 500.0) -> Acquisition:
        n = int(duration_ms * FS_HZ / 1000)
        start = self.neurons.timestamp()
        frames, spikes, _ = self._read_window(start, n)
        return Acquisition(spikes=spikes, duration_ms=duration_ms, stim_onset_ms=0.0,
                           raw_samples=frames.astype(np.float32),
                           metadata={"spontaneous": True, "start_ts": int(start), "units": "raw_sample_units"})

    def run_trial(self, pulses: list[StimPulse]) -> Acquisition:
        from cl import ChannelSet, StimDesign
        self.gate.authorise(pulses, {"source": self.source})
        span = max(p.offset_ms for p in pulses)
        start = self.neurons.timestamp()
        groups: dict[tuple, list[int]] = defaultdict(list)
        for p in pulses:
            groups[(p.offset_ms, p.phase_us, p.current_uA)].append(p.channel)
        # cl-sdk counts lead_time_us from max(now, time the channel is next free),
        # and a multi-channel stim first syncs its channels to the latest of them.
        # Our encoders pulse each group twice, so a lead measured from "now" would
        # push repeat pulses late and scramble A-A-B-B into A-B-A-B. Track each
        # channel's busy-until timestamp and aim at absolute target frames instead.
        free_until: dict[int, int] = {}
        schedule = []
        for (off, ph, cur), chans in sorted(groups.items()):
            target = start + int(round((PRE_MS + off) * FS_HZ / 1000.0))
            base = max([self.neurons.timestamp()] + [free_until.get(c, -1) for c in chans])
            lead_frames = max(MIN_LEAD_FRAMES, target - base)
            self.neurons.stim(ChannelSet(*chans), StimDesign(int(ph), -float(cur), int(ph), float(cur)),
                              lead_time_us=lead_frames * FRAME_US)
            actual = base + lead_frames
            busy = _busy_frames(int(ph))
            for c in chans:
                free_until[c] = actual + busy
            schedule.append({"offset_ms": off, "channels": list(chans),
                             "late_ms": round((actual - target) * 1000.0 / FS_HZ, 3)})
        dur = PRE_MS + span + POST_MS
        n = int(dur * FS_HZ / 1000)
        frames, spikes, stims = self._read_window(start, n)
        align_err = None
        if stims:
            first_actual = min(t for t, _ in stims)
            align_err = round(first_actual - PRE_MS, 3)
        return Acquisition(spikes=spikes, duration_ms=dur, stim_onset_ms=PRE_MS,
                           raw_samples=frames.astype(np.float32), delivered=list(pulses),
                           metadata={"start_ts": int(start), "observed_stims_ms": stims[:64],
                                     "stim_alignment_error_ms": align_err, "units": "raw_sample_units",
                                     "scheduled_lateness_ms": max((s["late_ms"] for s in schedule), default=0.0),
                                     "cl_sdk_version": self.sdk_version})
