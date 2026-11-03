"""Artifact masking and trial-level features.

Response window: starts POST_GAP_MS after the FINAL pulse and lasts WINDOW_MS
(Loeffler et al. 2026 used 10 ms / 400 ms). The window is the same for every
encoder condition. Any artifact interval overlapping it fails the quality gate.

Feature paths:
  * spikes: per-channel spike counts in N_BINS equal bins of the window, minus
    the per-channel pre-stimulus baseline rate (spikes/bin).
  * psd: per-channel log band power (Welch) on the raw voltage in the same
    window. Only when raw samples exist.
Normalisation is NOT done here; the decoder fits its scaler on training trials only.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import welch

from backend.schema import FS_HZ, N_CHANNELS, SILENT_CHANNELS, StimPulse

POST_GAP_MS = 10.0
WINDOW_MS = 400.0
BLANK_MS = 5.0          # per-pulse artifact blanking interval
N_BINS = 4
PRE_BASELINE_MS = 90.0
PSD_BANDS = [(4, 12), (12, 30), (30, 80), (80, 200), (300, 3000)]


def artifact_intervals(pulses: list[StimPulse], stim_onset_ms: float, blank_ms: float = BLANK_MS):
    """Every pulse [t, t+blank]. Overlapping intervals merged."""
    iv = sorted((stim_onset_ms + p.offset_ms, stim_onset_ms + p.offset_ms + blank_ms) for p in pulses)
    merged: list[list[float]] = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def response_window(pulses: list[StimPulse], stim_onset_ms: float,
                    post_gap_ms: float = POST_GAP_MS, window_ms: float = WINDOW_MS):
    last = stim_onset_ms + max(p.offset_ms for p in pulses)
    return (last + post_gap_ms, last + post_gap_ms + window_ms)


def overlaps(window, intervals) -> bool:
    a, b = window
    return any(x < b and y > a for x, y in intervals)


def spike_features(spikes: np.ndarray, window, stim_onset_ms: float,
                   n_channels: int = N_CHANNELS, n_bins: int = N_BINS) -> np.ndarray:
    a, b = window
    edges = np.linspace(a, b, n_bins + 1)
    feats = np.zeros((n_channels, n_bins))
    base = np.zeros(n_channels)
    if len(spikes):
        t, ch = spikes[:, 0], spikes[:, 1].astype(int)
        m = (t >= a) & (t < b)
        if m.any():
            bi = np.clip(np.searchsorted(edges, t[m], side="right") - 1, 0, n_bins - 1)
            np.add.at(feats, (ch[m], bi), 1.0)
        pb = (t >= stim_onset_ms - PRE_BASELINE_MS) & (t < stim_onset_ms)
        np.add.at(base, ch[pb], 1.0)
    bin_ms = (b - a) / n_bins
    base_per_bin = base * (bin_ms / PRE_BASELINE_MS)
    out = feats - base_per_bin[:, None]
    out[[c for c in SILENT_CHANNELS if c < n_channels]] = 0.0   # never decode grounded/reference channels
    return out.ravel()


def psd_features(raw: np.ndarray, window, fs: int = FS_HZ) -> np.ndarray:
    a, b = window
    s0, s1 = int(a * fs / 1000), int(b * fs / 1000)
    seg = raw[s0:s1].astype(np.float64)
    nper = min(len(seg), int(0.1 * fs))
    f, P = welch(seg, fs=fs, nperseg=nper, axis=0)
    out = []
    for lo, hi in PSD_BANDS:
        m = (f >= lo) & (f < hi)
        out.append(np.log10(P[m].mean(0) + 1e-6))
    out = np.stack(out, 1)
    out[[c for c in SILENT_CHANNELS if c < out.shape[0]]] = 0.0
    return out.ravel()


def unmasked_spike_features(spikes, pulses, stim_onset_ms, n_channels=N_CHANNELS):
    """DIAGNOSTIC ONLY: window starting at stimulus onset, i.e. INCLUDING the
    stimulation period. Used to demonstrate how artifact inflates accuracy."""
    a = stim_onset_ms
    return spike_features(spikes, (a, a + WINDOW_MS), stim_onset_ms, n_channels)


def quality_flags(spikes: np.ndarray, window, intervals, duration_ms: float,
                  n_channels: int = N_CHANNELS) -> list[str]:
    flags = []
    if overlaps(window, intervals):
        flags.append("artifact_overlaps_window")
    if window[1] > duration_ms:
        flags.append("window_exceeds_recording")
    a, b = window
    n_in = int(((spikes[:, 0] >= a) & (spikes[:, 0] < b)).sum()) if len(spikes) else 0
    if n_in < 3:
        flags.append("too_few_spikes")
    if len(spikes):
        active = len(np.unique(spikes[:, 1]))
        if active < 4:
            flags.append("few_active_channels")
    return flags
