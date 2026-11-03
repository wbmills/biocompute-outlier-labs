"""Deterministic label -> stimulation-schedule encoders.

The label is a digital tag chosen *before* encoding (button or digital speech
recognition). Encoders are pure functions; nothing downstream of the backend
ever receives the label except the scorer.

Both encoder families use the SAME pulse design (phase width, current), the SAME
number of pulse events per message and the SAME channels, so total charge per
message is identical across classes and candidates (matched stimulation budget).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from backend.schema import StimPulse

DEFAULT_GROUP_A = (8, 9)
DEFAULT_GROUP_B = (18, 19)
DEFAULT_PHASE_US = 160
DEFAULT_CURRENT_UA = 1.0


@dataclass(frozen=True)
class EncoderSpec:
    encoder_id: str
    family: str                       # "rate" | "order"
    params: dict = field(default_factory=dict)
    description: str = ""


def _group(chs, offset, phase_us, current):
    return [StimPulse(int(c), float(offset), int(phase_us), float(current)) for c in chs]


def rate_code(label: str, *, fast_isi_ms: float = 10.0, slow_isi_ms: float = 40.0,
              n_events: int = 4, group_a=DEFAULT_GROUP_A, group_b=DEFAULT_GROUP_B,
              phase_us: int = DEFAULT_PHASE_US, current_uA: float = DEFAULT_CURRENT_UA) -> list[StimPulse]:
    """Candidate A (baseline): events alternate A,B,A,B for both classes;
    YES = fast train, NO = slow train. Same pulses, channels & charge as the
    order code; train DURATION differs by class (a known confound, logged and
    disclosed)."""
    isi = fast_isi_ms if label == "YES" else slow_isi_ms
    out: list[StimPulse] = []
    for k in range(n_events):
        out += _group(group_a if k % 2 == 0 else group_b, k * isi, phase_us, current_uA)
    return out


def order_code(label: str, *, ipi_ms: float = 20.0, group_a=DEFAULT_GROUP_A,
               group_b=DEFAULT_GROUP_B, phase_us: int = DEFAULT_PHASE_US,
               current_uA: float = DEFAULT_CURRENT_UA) -> list[StimPulse]:
    """Candidate B (timing/order code): identical pulses, channels and duration
    for both classes; YES = A,A,B,B ; NO = B,B,A,A. Only temporal arrangement
    differs. Each group event pulses every channel of that group."""
    seq = ("A", "A", "B", "B") if label == "YES" else ("B", "B", "A", "A")
    out: list[StimPulse] = []
    for k, g in enumerate(seq):
        out += _group(group_a if g == "A" else group_b, k * ipi_ms, phase_us, current_uA)
    return out


FAMILIES = {"rate": rate_code, "order": order_code}

# Pre-registered candidate grid (fixed BEFORE any data is collected). Only
# timing is varied; current and pulse width are never optimised.
BASELINE_ID = "A_rate"
CANDIDATES: list[EncoderSpec] = [
    EncoderSpec("A_rate", "rate", {"fast_isi_ms": 10.0, "slow_isi_ms": 40.0},
                "Baseline rate code: 4 events, 10 ms vs 40 ms spacing"),
    EncoderSpec("B_order_ipi5", "order", {"ipi_ms": 5.0},
                "Order code A-A-B-B vs B-B-A-A, 5 ms between events"),
    EncoderSpec("B_order_ipi20", "order", {"ipi_ms": 20.0},
                "Order code, 20 ms between events"),
    EncoderSpec("B_order_ipi60", "order", {"ipi_ms": 60.0},
                "Order code, 60 ms between events"),
]
CANDIDATE_BY_ID = {c.encoder_id: c for c in CANDIDATES}


def encode(label: str, spec: EncoderSpec, *, group_a=DEFAULT_GROUP_A, group_b=DEFAULT_GROUP_B,
           phase_us: int = DEFAULT_PHASE_US, current_uA: float = DEFAULT_CURRENT_UA) -> list[StimPulse]:
    if label not in ("YES", "NO"):
        raise ValueError(f"label must be YES or NO, got {label!r}")
    fn = FAMILIES[spec.family]
    return fn(label, group_a=group_a, group_b=group_b, phase_us=phase_us,
              current_uA=current_uA, **spec.params)


def stimulation_budget(pulses: list[StimPulse]) -> dict:
    return {
        "n_pulses": len(pulses),
        "total_charge_nC": round(sum(p.charge_nC for p in pulses), 4),
        "max_current_uA": max((p.current_uA for p in pulses), default=0.0),
        "duration_ms": max((p.offset_ms for p in pulses), default=0.0),
        "channels": sorted({p.channel for p in pulses}),
    }
