import numpy as np
from sklearn.metrics import balanced_accuracy_score
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.encoding.encoders import CANDIDATE_BY_ID, encode
from backend.experiment import feature_extract as fx
from backend.experiment.decoder import Decoder

def test_intervals_cover_every_pulse_and_window_is_clean():
    for cid in CANDIDATE_BY_ID:
        p = encode("YES", CANDIDATE_BY_ID[cid])
        iv = fx.artifact_intervals(p, 100.0)
        for q in p:
            t = 100.0 + q.offset_ms
            assert any(a <= t and t + fx.BLANK_MS <= b + 1e-9 for a, b in iv)
        assert not fx.overlaps(fx.response_window(p, 100.0), iv)

def _decode(feature, seed):
    b = ReactiveSimBackend(seed=seed, gain_scale=0.0, raw=False)   # NO neural response, artifact only
    spec = CANDIDATE_BY_ID["A_rate"]                                # class-correlated artifact timing
    rng = np.random.default_rng(seed); labs = np.array(["YES", "NO"] * 25); rng.shuffle(labs)
    X = []
    for l in labs:
        p = encode(l, spec); a = b.run_trial(p)
        X.append(fx.unmasked_spike_features(a.spikes, p, a.stim_onset_ms) if feature == "unmasked"
                 else fx.spike_features(a.spikes, fx.response_window(p, a.stim_onset_ms), a.stim_onset_ms))
    X = np.array(X); d = Decoder().fit(X[:30], list(labs[:30]), [])
    return balanced_accuracy_score(labs[30:], d.predict(X[30:])[0])

def test_artifact_inflates_unmasked_but_mask_removes_it():
    un = [_decode("unmasked", s) for s in range(4)]
    ma = [_decode("masked", s) for s in range(4)]
    assert np.mean(un) > 0.9, un
    assert 0.3 < np.mean(ma) < 0.7, ma

def test_artifact_only_trial_fails_quality_gate():
    sp = np.array([[100.5, 8], [101.0, 9]])
    flags = fx.quality_flags(sp, (300, 700), [(100, 105)], 800)
    assert "too_few_spikes" in flags
