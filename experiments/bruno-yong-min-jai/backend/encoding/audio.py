"""Audio -> stimulation encoder: the reservoir's input layer.

A recorded utterance (not a label) is compiled into pulses. The voiced part is
cut into N_STEPS equal time slices; in each slice the N_PER_STEP frequency bands
that stand out most from that slice's average spectrum are pulsed, one electrode
per band (a tonotopic row). Every utterance therefore gets the same number of
pulses, at the same times, with the same charge: only WHICH electrodes fire
carries information, and the response window starts at the same time for all.

Pure function of the audio: no label, no fitted parameters, no state.
"""
from __future__ import annotations

import numpy as np
from scipy.io import wavfile

from backend.schema import SILENT_CHANNELS, StimPulse

AUDIO_CHANNELS = (8, 9, 10, 11, 12, 13, 14, 15)   # one MEA row, low -> high band
N_BANDS = len(AUDIO_CHANNELS)
N_STEPS = 5
N_PER_STEP = 2
STEP_MS = 40.0
PHASE_US = 160
CURRENT_UA = 1.0
BAND_LO_HZ, BAND_HI_HZ = 100.0, 6000.0
FRAME_MS = 20.0
assert not set(AUDIO_CHANNELS) & set(SILENT_CHANNELS)


def load_wav(path) -> tuple[np.ndarray, int]:
    sr, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    return x, int(sr)


def voiced_region(x: np.ndarray, sr: int) -> np.ndarray:
    """Trim leading/trailing silence: keep frames louder than both 10% of the
    peak frame and 3x the quietest-fifth noise floor."""
    n = max(1, int(sr * FRAME_MS / 1000))
    k = len(x) // n
    if k < N_STEPS:
        return x
    rms = np.sqrt((x[: k * n].reshape(k, n) ** 2).mean(1))
    thr = max(0.1 * rms.max(), 3.0 * np.percentile(rms, 20))
    on = np.flatnonzero(rms > thr)
    if len(on) < N_STEPS:
        return x
    return x[on[0] * n:(on[-1] + 1) * n]


def band_energies(x: np.ndarray, sr: int) -> np.ndarray:
    """(N_BANDS, N_STEPS) log band energy of the pre-emphasised voiced region."""
    v = voiced_region(x, sr)
    v = np.append(v[0], v[1:] - 0.97 * v[:-1])          # standard speech pre-emphasis
    hi = min(BAND_HI_HZ, sr / 2 * 0.95)
    edges = np.geomspace(BAND_LO_HZ, hi, N_BANDS + 1)
    out = np.zeros((N_BANDS, N_STEPS))
    for s, seg in enumerate(np.array_split(v, N_STEPS)):
        P = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1.0 / sr)
        for b in range(N_BANDS):
            m = (f >= edges[b]) & (f < edges[b + 1])
            out[b, s] = np.log10(P[m].sum() + 1e-12)
    return out


def pulse_pattern(x: np.ndarray, sr: int) -> np.ndarray:
    """(N_BANDS, N_STEPS) 0/1 matrix: which band electrodes fire in each slice."""
    e = band_energies(x, sr)
    rel = e - e.mean(0, keepdims=True)                   # spectral shape, loudness-free
    pat = np.zeros_like(rel)
    for s in range(N_STEPS):
        pat[np.argsort(-rel[:, s], kind="stable")[:N_PER_STEP], s] = 1.0
    return pat


def encode_audio(x: np.ndarray, sr: int) -> tuple[list[StimPulse], np.ndarray]:
    pat = pulse_pattern(x, sr)
    pulses = [StimPulse(AUDIO_CHANNELS[b], s * STEP_MS, PHASE_US, CURRENT_UA)
              for s in range(N_STEPS) for b in range(N_BANDS) if pat[b, s]]
    return pulses, pat
