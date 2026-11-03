import numpy as np
from backend.experiment.controls import permutation_control
from backend.experiment.metrics import score, clopper_pearson
from backend.acquisition.simulator_adapter import RandomSimBackend
from backend.encoding.encoders import CANDIDATE_BY_ID, encode
from backend.experiment import feature_extract as fx
from backend.experiment.decoder import Decoder
from sklearn.metrics import balanced_accuracy_score

def test_permutation_null_is_chance_on_informative_data():
    rng = np.random.default_rng(0)
    y = np.array(["YES", "NO"] * 20)
    X = rng.normal(size=(40, 10)); X[y == "YES", 0] += 3
    r = permutation_control(X[:20], y[:20], X[20:], y[20:], observed=1.0, n_perm=100)
    assert 0.35 < r["null_mean"] < 0.65 and r["p_value"] < 0.05

def test_random_source_is_chance_over_seeds():
    accs = []
    for seed in range(6):
        b = RandomSimBackend(seed=seed, raw=False)
        rng = np.random.default_rng(seed); labs = np.array(["YES", "NO"] * 20); rng.shuffle(labs)
        X = []
        for l in labs:
            p = encode(l, CANDIDATE_BY_ID["B_order_ipi60"]); a = b.run_trial(p)
            X.append(fx.spike_features(a.spikes, fx.response_window(p, a.stim_onset_ms), a.stim_onset_ms))
        X = np.array(X); d = Decoder().fit(X[:20], list(labs[:20]), [])
        accs.append(balanced_accuracy_score(labs[20:], d.predict(X[20:])[0]))
    assert 0.35 < np.mean(accs) < 0.65, accs

def test_metrics_insufficient_evidence():
    assert score([], [])["status"] == "insufficient_evidence"
    assert score(["YES", "YES"], ["YES", "YES"])["status"] == "insufficient_evidence"
    lo, hi = clopper_pearson(10, 20)
    assert lo < 0.5 < hi

def test_decoder_needs_two_classes():
    import pytest
    with pytest.raises(ValueError):
        Decoder().fit(np.zeros((4, 3)), ["YES"] * 4, [])
