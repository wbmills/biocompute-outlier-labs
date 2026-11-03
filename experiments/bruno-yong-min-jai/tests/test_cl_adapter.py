import sys, types
import numpy as np
from dataclasses import dataclass, field

def test_imports_without_cl_sdk():
    import backend.acquisition.cl1_adapter as m
    import backend.simulations.reactive_source as rs
    ok, _ = m.cl_available()
    if not ok:
        import pytest
        with pytest.raises(RuntimeError):
            rs.create_source()

def test_threshold_detector():
    from backend.acquisition.cl1_adapter import detect_spikes
    x = np.random.default_rng(0).normal(0, 5, (5000, 2)).astype(np.float32)
    x[1000, 0] = -200; x[3000, 1] = -200
    sp = detect_spikes(x)
    assert {(1000, 0), (3000, 1)} <= {(int(a), int(b)) for a, b in sp}

def test_reactive_source_against_stub_sdk(monkeypatch):
    """Exercise the cl-sdk data-source wrapper with a stub cl.sim module."""
    @dataclass
    class Meta:
        channel_count: int = 64; frames_per_second: int = 25000; duration_frames: int | None = None; seekable: bool = True
    @dataclass
    class Spike:
        timestamp: int; channel: int
    @dataclass
    class Batch:
        frames: object = None; spikes: list = field(default_factory=list)
    @dataclass
    class Stim:
        timestamp: int; channel: int; phase_durations_us: tuple = (160, 160); phase_currents_uA: tuple = (-1.0, 1.0)
    sim = types.ModuleType("cl.sim")
    sim.DataSourceBatch, sim.DataSourceSpike, sim.SimulatorDataSource, sim.SimulatorDataSourceMetadata = Batch, Spike, object, Meta
    cl = types.ModuleType("cl"); cl.sim = sim
    monkeypatch.setitem(sys.modules, "cl", cl); monkeypatch.setitem(sys.modules, "cl.sim", sim)
    import importlib, backend.simulations.reactive_source as rs
    rs = importlib.reload(rs)
    try:
        def count(stim):
            s = rs.create_source(seed=4); s.open()
            if stim:
                for ch in (8, 9):
                    s.on_stim(Stim(timestamp=25000 * 1, channel=ch))
            b = s.read(25000 * 1, 25000 // 4)    # 250 ms after the stim time
            assert b.frames.shape == (6250, 64) and b.frames.dtype == np.int16
            return len(b.spikes)
        assert count(True) > count(False) + 10
    finally:
        monkeypatch.delitem(sys.modules, "cl"); monkeypatch.delitem(sys.modules, "cl.sim")
        importlib.reload(rs)


def test_repeat_pulses_keep_intended_timing_under_sdk_scheduling(monkeypatch):
    """cl-sdk schedules each stim at max(now, channel_free) + lead, and syncs the
    channels of a multi-channel stim. Encoders pulse each group twice, so the
    adapter must aim at absolute frames or A-A-B-B arrives as A-B-A-B."""
    from backend.acquisition.cl1_adapter import CLBackend, PRE_MS
    from backend.encoding.encoders import encode, CANDIDATE_BY_ID
    from backend.schema import FS_HZ

    class ChannelSet:
        def __init__(self, *c): self.c = c
    class StimDesign:
        def __init__(self, *a): self.a = a

    class FakeNeurons:            # mirrors cl-sdk Neurons._queue_stims semantics
        def __init__(self): self.now, self.free, self.starts = 1000, {}, []
        def timestamp(self): self.now += 1; return self.now   # time passes while issuing
        def stim(self, cs, sd, lead_time_us=80):
            assert lead_time_us >= 80 and lead_time_us % 40 == 0
            chans = cs.c
            if len(chans) > 1:    # sync to latest availability
                m = max(self.free.get(c, -1) for c in chans)
                for c in chans: self.free[c] = m
            for c in chans:
                f = self.free.get(c, -1)
                s = (self.now if self.now > f else f) + lead_time_us // 40
                self.starts.append((s, c))
                self.free[c] = s + int((sd.a[0] * 2 + 80) / 40 + 0.5) - 2
        def read(self, n, ts, analysis=False):
            if analysis: raise RuntimeError("no analysis in fake")
            return np.zeros((n, 64), dtype=np.int16)

    cl = types.ModuleType("cl"); cl.ChannelSet, cl.StimDesign = ChannelSet, StimDesign
    monkeypatch.setitem(sys.modules, "cl", cl)

    class Gate:
        live = False; limits = None
        def authorise(self, pulses, ctx=None): pass
        def status(self): return {}

    for enc_id in ("B_order_ipi5", "B_order_ipi20", "B_order_ipi60", "A_rate"):
        for label in ("YES", "NO"):
            b = CLBackend(Gate()); b.neurons = FakeNeurons()
            start = b.neurons.now + 1
            pulses = encode(label, CANDIDATE_BY_ID[enc_id])
            acq = b.run_trial(pulses)
            got = sorted(b.neurons.starts)
            want = sorted((start + round((PRE_MS + p.offset_ms) * FS_HZ / 1000), p.channel) for p in pulses)
            assert [c for _, c in got] == [c for _, c in want], (enc_id, label)
            assert all(abs(g - w) <= 1 for (g, _), (w, _) in zip(got, want)), (enc_id, label, got, want)
            assert acq.metadata["scheduled_lateness_ms"] <= 0.04
