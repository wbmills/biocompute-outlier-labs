import hashlib, importlib.util, inspect
from pathlib import Path
import numpy as np
import pytest
from backend.acquisition.simulator_adapter import ReactiveSimBackend
from backend.encoding.encoders import CANDIDATES, encode
from backend.schema import StimPulse
from backend.simulations.tissue_model import TissueConfig, TissueModel

# sha256 of spikes + raw for seed 123, recorded BEFORE plasticity was added to the model.
# Floating-point results differ across numpy versions, so one golden per recorded version.
GOLDEN = {"2.5.4": "46432ece3906ba11f082467f8ab91e6973fe97b5e5a51ffb4eaf4c1ee9259e13",
          "1.24.3": "a8920721a8fe34d421c7c8abc66e67051988626806397bdf1b55354199581206"}

def _demo():
    path = Path(__file__).resolve().parents[1] / "scripts" / "learning_demo.py"
    spec = importlib.util.spec_from_file_location("learning_demo", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def test_plasticity_off_output_is_bitwise_unchanged():
    if np.__version__ not in GOLDEN:
        pytest.skip(f"no pre-change golden recorded for numpy {np.__version__}")
    b = ReactiveSimBackend(seed=123, raw=True)
    h = hashlib.sha256()
    for _ in range(2):
        for spec in CANDIDATES:
            for label in ("YES", "NO"):
                a = b.run_trial(encode(label, spec))
                h.update(np.ascontiguousarray(a.spikes).tobytes()); h.update(np.ascontiguousarray(a.raw_samples).tobytes())
    assert h.hexdigest() == GOLDEN[np.__version__]

def test_plasticity_never_takes_a_label():
    for fn in (TissueModel._stdp_update, TissueModel.simulate, TissueModel.rate):
        assert not any("label" in p for p in inspect.signature(fn).parameters)
    assert not any("label" in f for f in TissueConfig.__dataclass_fields__)

def test_rule_changes_gains_only_when_on_and_unfrozen():
    pulses = [StimPulse(18, 0.0, 160, 1.0), StimPulse(34, 4.0, 160, 1.0)]
    for plastic, frozen, changes in ((False, False, False), (True, True, False), (True, False, True)):
        m = TissueModel(TissueConfig(seed=1, plasticity=plastic))
        m.freeze_plasticity(frozen)
        m._gains(18); m._gains(34); before = m.gain_snapshot()
        for k in range(5):
            m.simulate(pulses, trial_index=k)
        after = m.gain_snapshot()
        assert any(not np.array_equal(before[c], after[c]) for c in before) == changes

def test_sham_pairing_stays_near_chance():
    L = _demo()
    last = np.mean([L.run_condition("sham", s)[-1] for s in L.SEEDS])
    assert abs(last - 0.5) <= 0.15, last
