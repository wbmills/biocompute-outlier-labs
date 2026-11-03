import json, pytest
from backend.schema import StimPulse
from backend.encoding.safety import SafetyGate, OperatorLimits, StimRejected

P = [StimPulse(8, 0.0, 160, 1.0)]
LIM = OperatorLimits(allowed_channels=[8, 9], max_current_uA=1.0, max_phase_us=200,
                     max_pulses_per_trial=4, min_inter_trial_s=0.0, max_session_stims=3, approved_by="op")

@pytest.mark.parametrize("bad", [
    StimPulse(99, 0, 160, 1.0),      # channel not allowed
    StimPulse(8, 0, 150, 1.0),       # not multiple of 20
    StimPulse(8, 0, 160, 3.5),       # current
    StimPulse(8, 0, 0, 1.0),         # zero width
    StimPulse(8, -1, 160, 1.0),      # negative offset
])
def test_sim_gate_rejects_invalid(bad):
    with pytest.raises(StimRejected):
        SafetyGate(live=False, limits=None).authorise([bad])

def test_rate_limit():
    with pytest.raises(StimRejected):
        SafetyGate(live=False, limits=None).authorise([StimPulse(8, 0, 160, 1), StimPulse(8, 2, 160, 1)])

def test_live_fails_closed_without_env(monkeypatch):
    monkeypatch.delenv("LIVE_STIM_ENABLED", raising=False)
    g = SafetyGate(live=True, limits=LIM)
    with pytest.raises(StimRejected):
        g.authorise(P)
    with pytest.raises(StimRejected):
        g.approve("op")

def test_live_fails_closed_without_limits(monkeypatch):
    monkeypatch.setenv("LIVE_STIM_ENABLED", "true")
    g = SafetyGate(live=True, limits=None)
    with pytest.raises(StimRejected):
        g.approve("op")
    with pytest.raises(StimRejected):
        g.authorise(P)

def test_live_requires_operator_approval_and_audits(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_STIM_ENABLED", "true")
    g = SafetyGate(live=True, limits=LIM, audit_path=tmp_path / "a.jsonl")
    with pytest.raises(StimRejected):
        g.authorise(P)
    g.approve("op")
    g.authorise(P)
    with pytest.raises(StimRejected):           # operator limit tighter than SDK
        g.authorise([StimPulse(8, 0, 160, 2.0)])
    g.authorise(P); g.authorise(P)
    with pytest.raises(StimRejected):           # session budget (3) exhausted
        g.authorise(P)
    g.stop()
    with pytest.raises(StimRejected):
        g.authorise(P)
    events = [json.loads(l)["event"] for l in (tmp_path / "a.jsonl").read_text().splitlines()]
    assert events.count("authorised") == 3 and events.count("rejected") == 4 and "STOP" in events
