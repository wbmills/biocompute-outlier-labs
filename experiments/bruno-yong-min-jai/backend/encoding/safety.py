"""Stimulation safety gate + audit log.

Two layers:
  1. SDK-level constraints (always enforced): phase width positive multiple of
     20 us, |current| <= 3.0 uA, charge per pulse <= 3.0 nC, event rate <= 200 Hz.
     These are cl-sdk validation limits, NOT a safety certification for any culture.
  2. Operator limits (required for live hardware): allowed channels, max current,
     max phase width, max pulses per trial, min inter-trial interval, max session
     stims. For LIVE mode there is NO default: if operator limits are not loaded
     the gate fails closed.

Live stimulation additionally requires env LIVE_STIM_ENABLED=true AND a runtime
operator approval (approve()). Every command, delivered or rejected, is audited.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from backend.schema import StimPulse

SDK_MAX_CURRENT_UA = 3.0
SDK_MAX_CHARGE_NC = 3.0
SDK_PHASE_BIN_US = 20
SDK_MAX_RATE_HZ = 200.0


class StimRejected(Exception):
    pass


@dataclass
class OperatorLimits:
    allowed_channels: list[int]
    max_current_uA: float
    max_phase_us: int
    max_pulses_per_trial: int
    min_inter_trial_s: float
    max_session_stims: int
    max_trial_span_ms: float = 1000.0
    approved_by: str = ""                  # operator identifier (no personal data needed)

    @classmethod
    def load(cls, path: str | Path) -> "OperatorLimits":
        d = {k: v for k, v in json.loads(Path(path).read_text()).items() if not k.startswith("_")}
        lim = cls(**d)
        if not lim.allowed_channels or lim.max_current_uA <= 0 or lim.max_pulses_per_trial <= 0 \
                or lim.max_session_stims <= 0 or lim.max_phase_us <= 0 or not lim.approved_by:
            raise ValueError("operator limits incomplete; live stimulation stays blocked")
        return lim


# Limits for *simulated* backends only. Never applied to live hardware.
SIM_LIMITS = OperatorLimits(
    allowed_channels=list(range(64)), max_current_uA=SDK_MAX_CURRENT_UA,
    max_phase_us=400, max_pulses_per_trial=64, min_inter_trial_s=0.0,
    max_session_stims=10_000_000, max_trial_span_ms=1000.0, approved_by="simulator")


class SafetyGate:
    def __init__(self, *, live: bool, limits: OperatorLimits | None,
                 audit_path: str | Path | None = None):
        self.live = live
        self.limits = limits if limits is not None else (None if live else SIM_LIMITS)
        self.audit_path = Path(audit_path) if audit_path else None
        self._operator_approved = False
        self._stopped = False
        self._session_stims = 0
        self._last_trial_t = -1e18
        self._lock = threading.Lock()

    # ---- live interlocks -------------------------------------------------
    @staticmethod
    def env_interlock() -> bool:
        return os.environ.get("LIVE_STIM_ENABLED", "").strip().lower() == "true"

    def approve(self, operator_id: str) -> None:
        if not self.live:
            return
        if not self.env_interlock():
            raise StimRejected("LIVE_STIM_ENABLED is not 'true'; cannot approve live stimulation")
        if self.limits is None:
            raise StimRejected("operator limits not loaded; live stimulation fails closed")
        self._operator_approved = True
        self._stopped = False
        self._audit({"event": "operator_approved", "operator": operator_id})

    def stop(self) -> None:
        self._stopped = True
        self._operator_approved = False
        self._audit({"event": "STOP"})

    def status(self) -> dict:
        return {
            "live": self.live,
            "env_interlock": self.env_interlock() if self.live else None,
            "operator_approved": self._operator_approved if self.live else None,
            "limits_loaded": self.limits is not None,
            "stopped": self._stopped,
            "session_stims": self._session_stims,
            "limits": asdict(self.limits) if self.limits else None,
        }

    # ---- validation ----------------------------------------------------
    def validate(self, pulses: list[StimPulse]) -> None:
        """Raise StimRejected if anything is out of bounds. Pure check."""
        if self._stopped:
            raise StimRejected("STOP is active")
        if self.live:
            if not self.env_interlock():
                raise StimRejected("live stim blocked: LIVE_STIM_ENABLED != true")
            if self.limits is None:
                raise StimRejected("live stim blocked: no operator limits configured (fail closed)")
            if not self._operator_approved:
                raise StimRejected("live stim blocked: operator approval required")
        lim = self.limits
        if lim is None:
            raise StimRejected("no limits configured")
        if not pulses:
            raise StimRejected("empty stimulus")
        if len(pulses) > lim.max_pulses_per_trial:
            raise StimRejected(f"{len(pulses)} pulses > max {lim.max_pulses_per_trial}")
        for p in pulses:
            if p.channel not in lim.allowed_channels:
                raise StimRejected(f"channel {p.channel} not in allowed set")
            if p.phase_us <= 0 or p.phase_us % SDK_PHASE_BIN_US:
                raise StimRejected(f"phase {p.phase_us} us must be a positive multiple of 20")
            if p.phase_us > lim.max_phase_us:
                raise StimRejected(f"phase {p.phase_us} us > max {lim.max_phase_us}")
            if not (0 < p.current_uA <= min(lim.max_current_uA, SDK_MAX_CURRENT_UA)):
                raise StimRejected(f"current {p.current_uA} uA out of bounds")
            if p.charge_nC > SDK_MAX_CHARGE_NC:
                raise StimRejected(f"charge {p.charge_nC:.3f} nC > {SDK_MAX_CHARGE_NC}")
            if p.offset_ms < 0 or p.offset_ms > lim.max_trial_span_ms:
                raise StimRejected(f"offset {p.offset_ms} ms outside trial span")
        by_ch: dict[int, list[float]] = {}
        for p in pulses:
            by_ch.setdefault(p.channel, []).append(p.offset_ms)
        min_gap = 1000.0 / SDK_MAX_RATE_HZ
        for ch, ts in by_ch.items():
            ts = sorted(ts)
            for a, b in zip(ts, ts[1:]):
                if b - a < min_gap - 1e-9:
                    raise StimRejected(f"channel {ch}: {b - a:.2f} ms spacing exceeds {SDK_MAX_RATE_HZ} Hz")
        now = time.monotonic()
        if now - self._last_trial_t < lim.min_inter_trial_s:
            raise StimRejected("inter-trial refractory interval not elapsed")
        if self._session_stims + len(pulses) > lim.max_session_stims:
            raise StimRejected("session stimulation budget exhausted")

    def authorise(self, pulses: list[StimPulse], context: dict | None = None) -> None:
        """Validate + count + audit. Call immediately before delivery."""
        with self._lock:
            try:
                self.validate(pulses)
            except StimRejected as e:
                self._audit({"event": "rejected", "reason": str(e), "n_pulses": len(pulses),
                             "pulses": [asdict(p) for p in pulses], **(context or {})})
                raise
            self._session_stims += len(pulses)
            self._last_trial_t = time.monotonic()
            self._audit({"event": "authorised", "n_pulses": len(pulses),
                         "pulses": [asdict(p) for p in pulses], **(context or {})})

    def _audit(self, rec: dict) -> None:
        if not self.audit_path:
            return
        rec = {"t_unix": time.time(), "live": self.live, **rec}
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
