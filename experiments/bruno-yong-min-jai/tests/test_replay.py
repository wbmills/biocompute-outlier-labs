import pytest
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.acquisition.replay_adapter import ReplayBackend, ReplayUnavailable
from backend.encoding.encoders import CANDIDATE_BY_ID, encode
from backend.experiment.scheduler import Experiment

def test_replay_only_serves_recorded_schedules(tmp_path):
    b = ReactiveSimBackend(seed=3, raw=False); b.connect()
    e = Experiment(b, runs_root=tmp_path, seed=3, n_train=2, n_val=1, n_test=2)
    e.run_baseline()
    r = ReplayBackend(e.store.dir); r.connect()
    st = r.get_status()
    assert st["is_living_tissue"] is False and "SIMULATED" in st["provenance"]
    acq = r.run_trial(encode("YES", CANDIDATE_BY_ID["A_rate"]))
    assert acq.metadata["replay_of"] == "reactive_sim"
    with pytest.raises(ReplayUnavailable):            # protocol never delivered in the recording
        r.run_trial(encode("YES", CANDIDATE_BY_ID["B_order_ipi20"]))
    with pytest.raises(ReplayUnavailable):            # recordings are not reused / fabricated
        for _ in range(100):
            r.run_trial(encode("NO", CANDIDATE_BY_ID["A_rate"]))
