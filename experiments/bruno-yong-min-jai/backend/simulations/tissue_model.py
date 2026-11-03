"""Stimulation-reactive, NON-LEARNING mathematical tissue model.

Purpose: rehearsal and software integration only. It is not a model of any
specific culture and its preferences between encodings exist BY CONSTRUCTION
(short-term depression, saturation, global inhibition and fixed seeded
connectivity), not as a discovered biological effect.

Causal contract (enforced by tests):
  * inputs are ONLY pulse events (time, channel, phase width, current) plus the
    seed and a trial counter. No labels, encoder ids or optimiser scores exist
    anywhere in this module's interface.
  * same seed + same trial index + same pulses -> bitwise identical output.
  * gain_scale = 0 removes every stimulus-dependent term (negative control);
    only spontaneous activity and stimulation artifact remain.

rate_j(t) = drift_j * [ baseline_j
            + S( sum_k eff_k * (Gf[j,c_k] a_f(t-t_k-df) + Gs[j,c_k] a_s(t-t_k-ds)) ) ]
            * 1 / (1 + w_inh * Inh(t))
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass

from backend.schema import FS_HZ, N_CHANNELS, SILENT_CHANNELS, StimPulse

GRID = 8  # CL1-like 8x8 MEA layout for spatial locality


def _alpha(dt: np.ndarray, tau: float) -> np.ndarray:
    out = np.zeros_like(dt)
    m = dt >= 0
    x = dt[m] / tau
    out[m] = x * np.exp(1.0 - x)
    return out


def _xy(ch: int) -> tuple[int, int]:
    return ch % GRID, ch // GRID


@dataclass
class TissueConfig:
    seed: int = 123
    n_channels: int = N_CHANNELS
    gain_scale: float = 1.0          # 0 => NO_RESPONSE control
    artifact_scale: float = 1.0      # stimulation artifact amplitude (spikes + voltage)
    noise_scale: float = 1.0         # spontaneous activity multiplier
    tau_fast_ms: float = 8.0
    tau_slow_ms: float = 70.0
    rmax_hz: float = 120.0
    stp_U: float = 0.55              # short-term depression utilisation
    stp_tau_rec_ms: float = 120.0
    w_inh: float = 0.035
    tau_inh_ms: float = 45.0
    burst_prob: float = 0.12         # spontaneous network bursts per trial
    drift_amp: float = 0.25          # slow multiplicative excitability drift
    drift_period_trials: float = 90.0
    dead_fraction: float = 0.1
    # OPT-IN planted STDP on the fast gains: a positive control for the learning
    # analysis, NOT a model of biological learning. Off => model is unchanged.
    plasticity: bool = False
    stdp_lr: float = 0.5
    stdp_tau_ms: float = 20.0
    stdp_window_ms: float = 50.0
    stdp_w_max: float = 150.0
    stdp_homeostasis: float = 0.0    # per-update pull back toward the initial gains


class TissueModel:
    def __init__(self, config: TissueConfig | None = None, **kw):
        self.cfg = config or TissueConfig(**kw)
        c = self.cfg
        rng = np.random.default_rng([c.seed, 7])
        self.baseline_hz = rng.gamma(2.0, 1.0, c.n_channels)          # ~2 Hz mean
        self.dead = rng.random(c.n_channels) < c.dead_fraction
        self.baseline_hz[self.dead] = 0.0
        self.drift_phase = rng.uniform(0, 2 * np.pi, c.n_channels)
        self.spike_amp_uV = rng.uniform(40, 120, c.n_channels)
        self._gain_cache: dict[int, tuple] = {}
        self._gain_init: dict[int, np.ndarray] = {}
        self.plasticity_frozen = False
        # cells above these electrodes still take part in the network; they just aren't recorded
        self.silent = np.isin(np.arange(c.n_channels), SILENT_CHANNELS)

    # ---- fixed, seeded connectivity (lazily per stimulated channel) -----
    def _gains(self, stim_ch: int):
        if stim_ch in self._gain_cache:
            return self._gain_cache[stim_ch]
        c = self.cfg
        rng = np.random.default_rng([c.seed, 1000 + stim_ch])
        sx, sy = _xy(stim_ch)
        d = np.array([np.hypot(_xy(j)[0] - sx, _xy(j)[1] - sy) for j in range(c.n_channels)])
        local = np.exp(-d / 1.8)
        fast_mask = rng.random(c.n_channels) < (0.15 + 0.7 * local)
        Gf = fast_mask * rng.gamma(2.0, 30.0, c.n_channels) * (0.3 + local)
        # slow reverberation: sparse, partly long-range, distinct per stim site
        slow_mask = rng.random(c.n_channels) < 0.3
        Gs = slow_mask * rng.gamma(2.0, 10.0, c.n_channels)
        df = 2.0 + d * 1.5 + rng.uniform(0, 4, c.n_channels)
        ds = 10.0 + rng.uniform(0, 40, c.n_channels)
        Gf[self.dead] = 0.0
        Gs[self.dead] = 0.0
        out = (Gf, Gs, df, ds)
        self._gain_cache[stim_ch] = out
        self._gain_init[stim_ch] = Gf.copy()
        return out

    # ---- opt-in planted plasticity (positive control) --------------------
    def freeze_plasticity(self, frozen: bool = True) -> None:
        self.plasticity_frozen = frozen

    def gain_snapshot(self) -> dict[int, np.ndarray]:
        """Copy of the current fast gains, keyed by stimulated channel."""
        return {ch: g[0].copy() for ch, g in self._gain_cache.items()}

    def _stdp_update(self, ev: list[tuple], spikes: np.ndarray) -> None:
        """Pair-based STDP, applied once per trial. Inputs are ONLY the delivered
        pulse events (t_ms, channel, current, phase) and the model's own neural
        spikes (t_ms, channel); artifact detections are excluded by the caller."""
        c = self.cfg
        if not len(spikes) or not ev:
            return
        t_post, j_post = spikes[:, 0], spikes[:, 1].astype(int)
        dw: dict[int, np.ndarray] = {}
        for t_pre, ch, _, _ in ev:
            dt = t_post - t_pre
            ltp = (dt > 0) & (dt < c.stdp_window_ms)            # pre before post: strengthen
            ltd = (dt < 0) & (dt > -c.stdp_window_ms)           # post before pre: weaken
            d = dw.setdefault(int(ch), np.zeros(c.n_channels))
            np.add.at(d, j_post[ltp], c.stdp_lr * np.exp(-dt[ltp] / c.stdp_tau_ms))
            np.add.at(d, j_post[ltd], -0.5 * c.stdp_lr * np.exp(dt[ltd] / c.stdp_tau_ms))
        for ch, d in dw.items():
            Gf = self._gains(ch)[0]                             # cached array, updated in place
            Gf += d + c.stdp_homeostasis * (self._gain_init[ch] - Gf)
            np.clip(Gf, 0.0, c.stdp_w_max, out=Gf)
            Gf[self.dead] = 0.0

    # ---- core dynamics (shared by per-trial and continuous cl-sdk source) --
    def effective_strengths(self, ev: list[tuple]) -> list[float]:
        """Short-term depression per stimulated channel. ev sorted by time:
        (t_ms, channel, current_uA, phase_us)."""
        c = self.cfg
        R: dict[int, float] = {}
        last: dict[int, float] = {}
        eff = []
        for t0, ch, cur, ph in ev:
            r = R.get(ch, 1.0)
            if ch in last:
                r = 1.0 - (1.0 - r) * np.exp(-(t0 - last[ch]) / c.stp_tau_rec_ms)
            eff.append(r * (cur / 1.0) * (ph / 160.0))
            R[ch] = r - c.stp_U * r
            last[ch] = t0
        return eff

    def rate(self, t: np.ndarray, ev: list[tuple], trial_index: float,
             eff: list[float] | None = None) -> np.ndarray:
        """Firing rate (Hz) on a uniform 1 ms grid t (bin centres) given pulse
        events ev=(t_ms, channel, current_uA, phase_us). No other inputs."""
        c = self.cfg
        n_t = len(t)
        if eff is None:
            eff = self.effective_strengths(ev)
        drive = np.zeros((n_t, c.n_channels))
        total = np.zeros(n_t)
        if c.gain_scale > 0:
            for (t0, ch, _, _), e in zip(ev, eff):
                Gf, Gs, df, ds = self._gains(int(ch))
                dtf = t[:, None] - t0 - df[None, :]
                dts = t[:, None] - t0 - ds[None, :]
                contrib = e * c.gain_scale * (Gf * _alpha(dtf, c.tau_fast_ms) + Gs * _alpha(dts, c.tau_slow_ms))
                drive += contrib
                total += contrib.sum(1)
        evoked = c.rmax_hz * (1.0 - np.exp(-np.maximum(drive, 0) / c.rmax_hz))
        kern = np.exp(-np.arange(0, 6 * c.tau_inh_ms) / c.tau_inh_ms)
        inh = np.convolve(total / c.n_channels, kern / c.tau_inh_ms)[:n_t]
        suppress = 1.0 / (1.0 + c.w_inh * inh)
        drift = 1.0 + c.drift_amp * np.sin(2 * np.pi * trial_index / c.drift_period_trials + self.drift_phase)
        return drift[None, :] * (c.noise_scale * self.baseline_hz[None, :] + evoked) * suppress[:, None]

    # ---- per-trial simulation -------------------------------------------
    def simulate(self, pulses: list[StimPulse], *, trial_index: int, pre_ms: float = 100.0,
                 post_ms: float = 480.0, raw: bool = False, fs_hz: int = FS_HZ) -> dict:
        """Return {'spikes': (n,2)[t_ms,ch], 'duration_ms', 'stim_onset_ms',
        'raw': (samples, ch) float32 uV or None, 'rate': (ms, ch)}.
        Spike times are relative to recording start; stimulus offset 0 is at pre_ms."""
        c = self.cfg
        span = max((p.offset_ms for p in pulses), default=0.0)
        dur = float(np.ceil(pre_ms + span + post_ms))
        t = np.arange(0.0, dur, 1.0) + 0.5                     # 1 ms rate grid (bin centres)
        rng = np.random.default_rng([c.seed, 2, int(trial_index)])

        events = sorted(pulses, key=lambda p: (p.offset_ms, p.channel))
        ev = [(pre_ms + p.offset_ms, p.channel, p.current_uA, p.phase_us) for p in events]
        rate = self.rate(t, ev, trial_index)

        # spontaneous network burst (stimulus independent)
        if rng.random() < c.burst_prob:
            bt = rng.uniform(0, dur)
            part = (rng.random(c.n_channels) < 0.6) & ~self.dead
            rate += np.outer(_alpha(t - bt, 25.0), part * rng.uniform(20, 60, c.n_channels))

        # Poisson spikes on 1 ms grid with sub-ms jitter
        counts = rng.poisson(np.clip(rate, 0, None) / 1000.0)
        ti, ci = np.nonzero(counts)
        reps = counts[ti, ci]
        ti = np.repeat(ti, reps)
        ci = np.repeat(ci, reps)
        st = ti + rng.random(len(ti))
        spikes = np.column_stack([st, ci]).astype(float)
        neural = spikes                                         # before artifact detections are added

        # stimulation artifact -> false "spike" detections near stimulated sites.
        # Their timing follows the pulse schedule, so they are class-correlated:
        # the artifact mask must remove them.
        if c.artifact_scale > 0:
            art = []
            for p in events:
                t0 = pre_ms + p.offset_ms
                sx, sy = _xy(p.channel)
                for j in range(c.n_channels):
                    dist = np.hypot(_xy(j)[0] - sx, _xy(j)[1] - sy)
                    if dist <= 1.5 and rng.random() < 0.9 * c.artifact_scale:
                        art.append((t0 + rng.uniform(0.1, 2.5), j))
            if art:
                spikes = np.vstack([spikes, np.array(art)])
        spikes = spikes[~self.silent[spikes[:, 1].astype(int)]]   # CL1 records nothing there
        order = np.argsort(spikes[:, 0], kind="stable")
        spikes = spikes[order]

        raw_arr = self._voltage(spikes, rate, events, pre_ms, dur, fs_hz, rng) if raw else None
        if c.plasticity and not self.plasticity_frozen:
            self._stdp_update(ev, neural)                       # after the response is generated
        return {"spikes": spikes, "duration_ms": dur, "stim_onset_ms": pre_ms, "raw": raw_arr,
                "rate": rate}

    def _voltage(self, spikes, rate, events, pre_ms, dur, fs, rng) -> np.ndarray:
        c = self.cfg
        n = int(round(dur * fs / 1000.0))
        v = rng.normal(0, 6.0, (n, c.n_channels)).astype(np.float32)        # thermal noise uV
        # LFP-like component: low-passed population rate (upsampled from 1 ms grid)
        lfp_ms = np.apply_along_axis(lambda x: np.convolve(x, np.ones(15) / 15, "same"), 0, rate)
        idx = np.minimum((np.arange(n) * 1000.0 / fs).astype(int), lfp_ms.shape[0] - 1)
        v += (lfp_ms[idx] * 0.6).astype(np.float32)
        # spike waveforms (biphasic, ~1 ms)
        w_t = np.arange(-10, 20)
        wave = (-np.exp(-((w_t - 2) ** 2) / 6.0) + 0.35 * np.exp(-((w_t - 9) ** 2) / 18.0)).astype(np.float32)
        for tms, ch in spikes:
            s0 = int(tms * fs / 1000.0)
            a, b = max(0, s0 - 10), min(n, s0 + 20)
            if b > a:
                v[a:b, int(ch)] += wave[(a - s0 + 10):(b - s0 + 10)] * self.spike_amp_uV[int(ch)]
        # stim artifact: large fast transient + slower tail, decaying with distance
        if c.artifact_scale > 0:
            tail = np.arange(int(0.012 * fs)) / fs * 1000.0                 # 12 ms
            shape = (np.exp(-tail / 0.4) * 1.0 + np.exp(-tail / 3.0) * 0.15).astype(np.float32)
            for p in events:
                s0 = int((pre_ms + p.offset_ms) * fs / 1000.0)
                sx, sy = _xy(p.channel)
                for j in range(c.n_channels):
                    d = np.hypot(_xy(j)[0] - sx, _xy(j)[1] - sy)
                    amp = c.artifact_scale * 1500.0 * p.current_uA * np.exp(-d / 2.0)
                    e = min(n, s0 + len(shape))
                    if e > s0:
                        v[s0:e, j] += amp * shape[: e - s0]
        v[:, self.silent] = 0.0
        return v
