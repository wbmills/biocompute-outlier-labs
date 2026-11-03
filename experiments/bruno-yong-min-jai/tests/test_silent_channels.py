import numpy as np
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.encoding.encoders import CANDIDATES, encode
from backend.experiment import feature_extract as fx
from backend.schema import SILENT_CHANNELS

def test_simulator_records_nothing_on_grounded_or_reference_channels():
    b = ReactiveSimBackend(seed=123, raw=True)          # full response + artifact
    for spec in CANDIDATES:
        for label in ("YES", "NO"):
            a = b.run_trial(encode(label, spec))         # group A (8, 9) neighbours channels 0 and 4
            assert not np.isin(a.spikes[:, 1].astype(int), SILENT_CHANNELS).any()
            assert not a.raw_samples[:, list(SILENT_CHANNELS)].any()

def test_features_ignore_grounded_and_reference_channels():
    sp = np.array([[300.0 + k, ch] for k in range(20) for ch in SILENT_CHANNELS] + [[50.0, 0]])
    f = fx.spike_features(sp, (250.0, 650.0), 100.0).reshape(-1, fx.N_BINS)
    assert not f[list(SILENT_CHANNELS)].any()
    raw = np.random.default_rng(0).normal(0, 6, (int(0.4 * 25_000), 64))
    p = fx.psd_features(raw, (0.0, 400.0)).reshape(64, -1)
    assert not p[list(SILENT_CHANNELS)].any() and p[[1, 2, 3]].all()
