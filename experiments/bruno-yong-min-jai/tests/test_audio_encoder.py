import numpy as np
from backend.encoding import audio
from backend.encoding.safety import SafetyGate

SR = 16_000

def _utterance(f0, f1, seed):
    """Synthetic 'word': silence, a tone gliding f0 -> f1 with noise, silence."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.4 * SR)) / SR
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, len(t))) / SR)
    x = np.concatenate([np.zeros(SR // 5), 8000 * tone + 300 * rng.normal(size=len(t)), np.zeros(SR // 5)])
    return x + 30 * rng.normal(size=len(x))

def test_every_utterance_gets_the_same_budget_and_timing():
    gate = SafetyGate(live=False, limits=None)
    for k, (f0, f1) in enumerate([(200, 300), (300, 4000), (3000, 500), (800, 800)]):
        pulses, pat = audio.encode_audio(_utterance(f0, f1, k), SR)
        gate.validate(pulses)
        assert len(pulses) == audio.N_STEPS * audio.N_PER_STEP
        assert {p.channel for p in pulses} <= set(audio.AUDIO_CHANNELS)
        assert sorted({p.offset_ms for p in pulses}) == [s * audio.STEP_MS for s in range(audio.N_STEPS)]
        assert pat.sum(0).tolist() == [audio.N_PER_STEP] * audio.N_STEPS

def test_encoding_is_deterministic_and_ignores_loudness():
    x = _utterance(300, 3000, 7)
    a, _ = audio.encode_audio(x, SR)
    b, _ = audio.encode_audio(x.copy(), SR)
    c, _ = audio.encode_audio(0.25 * x, SR)
    assert a == b == c
    d, _ = audio.encode_audio(_utterance(3000, 300, 7), SR)
    assert d != a   # different sound, different pattern
