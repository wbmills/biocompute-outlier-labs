import pytest
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.experiment.scheduler import Experiment

@pytest.fixture(scope="module")
def exp(tmp_path_factory):
    b = ReactiveSimBackend(seed=7, raw=False); b.connect()
    e = Experiment(b, runs_root=tmp_path_factory.mktemp("runs"), seed=7, n_train=4, n_val=2, n_test=4, n_preflight=2)
    calls = []
    orig = e._acquire
    def spy(item, backend=None):
        calls.append((item.split, e.locked))
        return orig(item, backend)
    e._acquire = spy
    e.run_all()
    e._calls = calls
    return e

def test_completes(exp):
    assert exp.state == "REPORT_READY", exp.error

def test_splits_disjoint_whole_trials(exp):
    ids = {s: {t.trial_id for t in exp.trials.values() if t.split == s} for s in ("train", "val", "test")}
    assert not (ids["train"] & ids["val"]) and not (ids["train"] & ids["test"]) and not (ids["val"] & ids["test"])
    assert exp.report["controls"]["TRAIN_TEST_SEPARATION"]["disjoint"]

def test_decoders_fit_on_train_only(exp):
    train = {t.trial_id for t in exp.trials.values() if t.split == "train"}
    for d in exp.decoders.values():
        assert set(d.train_ids) <= train and d.frozen

def test_no_test_trial_before_lock(exp):
    for split, locked in exp._calls:
        if split == "test":
            assert locked
    assert any(s == "test" for s, _ in exp._calls)

def test_winner_selected_on_validation(exp):
    best = max(exp.val_scores.values(), key=lambda r: r["objective"])["objective"]
    assert exp.val_scores[exp.winner_id]["objective"] == best

def test_report_provenance(exp):
    r = exp.report
    assert r["provenance"] == "SIMULATED MODEL" and r["is_living_tissue"] is False and r["is_live"] is False
    for res in r["test_results"].values():
        assert res["n"] > 0
    assert (exp.store.dir / "report.json").exists() and (exp.store.dir / "evidence.md").exists()
    assert "SIMULATED" in (exp.store.dir / "evidence.md").read_text()

def test_cannot_reoptimise_after_lock(exp):
    from backend.experiment.scheduler import ProtocolError
    w = exp.winner_id
    with pytest.raises(ProtocolError):
        exp.run_optimise()
    assert exp.winner_id == w and exp.state == "REPORT_READY"
