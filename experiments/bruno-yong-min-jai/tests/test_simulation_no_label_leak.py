import inspect
import numpy as np
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.encoding.encoders import CANDIDATE_BY_ID, encode
from backend.simulations.tissue_model import TissueModel

def test_backend_interface_has_no_label():
    params = inspect.signature(ReactiveSimBackend.run_trial).parameters
    assert list(params) == ["self", "pulses"]
    for name in ("simulate", "rate"):
        sig = str(inspect.signature(getattr(TissueModel, name))).lower()
        assert "label" not in sig and "encoder" not in sig and "score" not in sig

def test_bitwise_reproducible():
    p = encode("YES", CANDIDATE_BY_ID["B_order_ipi20"])
    a = TissueModel(seed=5).simulate(p, trial_index=3, raw=True)
    b = TissueModel(seed=5).simulate(p, trial_index=3, raw=True)
    assert np.array_equal(a["spikes"], b["spikes"]) and np.array_equal(a["raw"], b["raw"])

def test_same_schedule_same_response_whatever_the_label():
    # identical pulses requested under different 'labels' -> backend can't tell
    p = encode("YES", CANDIDATE_BY_ID["A_rate"])
    b1, b2 = ReactiveSimBackend(seed=1, raw=False), ReactiveSimBackend(seed=1, raw=False)
    assert np.array_equal(b1.run_trial(p).spikes, b2.run_trial(list(p)).spikes)

def test_response_depends_on_delivered_stim():
    m = TissueModel(seed=2)
    y = encode("YES", CANDIDATE_BY_ID["B_order_ipi60"]); n = encode("NO", CANDIDATE_BY_ID["B_order_ipi60"])
    import numpy as np
    t = np.arange(0, 700.0) + 0.5
    ev = lambda ps: [(100 + q.offset_ms, q.channel, q.current_uA, q.phase_us) for q in sorted(ps, key=lambda q: q.offset_ms)]
    assert not np.allclose(m.rate(t, ev(y), 0), m.rate(t, ev(n), 0))

def test_gain_zero_removes_stimulus_dependence():
    m = TissueModel(seed=2, gain_scale=0.0)
    y = encode("YES", CANDIDATE_BY_ID["B_order_ipi60"]); n = encode("NO", CANDIDATE_BY_ID["B_order_ipi60"])
    t = np.arange(0, 700.0) + 0.5
    ev = lambda ps: [(100 + q.offset_ms, q.channel, q.current_uA, q.phase_us) for q in ps]
    assert np.allclose(m.rate(t, ev(y), 0), m.rate(t, ev(n), 0))
