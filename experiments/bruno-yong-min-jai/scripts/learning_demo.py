"""Planted-learning POSITIVE CONTROL: can our protocol detect learning when we
build it into the simulator, and find none when the pairing is a sham?

    .venv/bin/python scripts/learning_demo.py            # -> runs/learning_demo/

SIMULATED · planted STDP rule (positive control) · not biological evidence.
The rule lives in TissueModel._stdp_update; it sees only delivered pulses and
the model's own spikes. Labels never reach the model: the script turns a label
into a "hint" pulse, and the model only ever sees that pulse.

Supervised Hebbian conditioning, as in classic MEA pairing studies:
  training (contingent)  YES/NO order code, then a hint pulse on the Y group
                         (YES) or N group (NO) 10 ms after the last input pulse
  training (sham)        identical, but the hint group is a balanced random
                         draw independent of the label
  probe                  input only, plasticity frozen; FIXED readout: YES if
                         baseline-corrected spikes(Y) > spikes(N) in the masked
                         window (10 ms after the last pulse, 400 ms); ties wrong
  conditions             contingent, sham, contingent with plasticity off;
                         separate identically seeded fresh models
Pre-registered success rule: contingent last-block accuracy exceeds both sham
and plasticity-off by >= 15 points, averaged over seeds.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.acquisition.simulator_adapter import ReactiveSimBackend  # noqa: E402
from backend.encoding.encoders import (CANDIDATE_BY_ID, DEFAULT_CURRENT_UA,  # noqa: E402
                                       DEFAULT_PHASE_US, encode)
from backend.experiment import feature_extract as fx  # noqa: E402
from backend.schema import StimPulse  # noqa: E402

BADGE = "SIMULATED · planted STDP rule (positive control) · not biological evidence"
INPUT_SPEC = CANDIDATE_BY_ID["B_order_ipi20"]
Y_GROUP = (34, 35)      # fixed before running; not inputs (8, 9, 18, 19), not silent
N_GROUP = (36, 37)
# One tuning pass after the first run (contingent 53 -> 56%, rule failed by margin 4):
# hint delay 10 -> 4 ms and STDP learning rate 0.5 -> 2.0. Not tuned against sham.
HINT_DELAY_MS = 4.0
STDP_LR = 2.0
N_BLOCKS, N_TRAIN, N_PROBE = 10, 20, 20
SEEDS = (123, 124, 125, 126, 127)
CONDITIONS = ("contingent", "sham", "plasticity_off")
RULE_POINTS = 15.0


def _balanced(rng, n: int) -> list[str]:
    labs = ["YES", "NO"] * (n // 2)
    rng.shuffle(labs)
    return labs


def _hint(group, after_ms: float) -> list[StimPulse]:
    return [StimPulse(ch, after_ms + HINT_DELAY_MS, DEFAULT_PHASE_US, DEFAULT_CURRENT_UA) for ch in group]


def probe_readout(acq, pulses) -> str | None:
    """Fixed readout, no fitted decoder. None = tie (scored wrong)."""
    win = fx.response_window(pulses, acq.stim_onset_ms)
    f = fx.spike_features(acq.spikes, win, acq.stim_onset_ms).reshape(-1, fx.N_BINS).sum(1)
    y, n = f[list(Y_GROUP)].sum(), f[list(N_GROUP)].sum()
    return "YES" if y > n else "NO" if n > y else None


def run_condition(condition: str, seed: int, n_blocks: int = N_BLOCKS) -> list[float]:
    b = ReactiveSimBackend(seed=seed, raw=False, plasticity=condition != "plasticity_off", stdp_lr=STDP_LR)
    acc = []
    for blk in range(n_blocks):
        labs = _balanced(np.random.default_rng([seed, blk, 1]), N_TRAIN)
        hints = _balanced(np.random.default_rng([seed, blk, 2]), N_TRAIN)   # sham: label-independent
        b.model.freeze_plasticity(False)
        for lab, sham_hint in zip(labs, hints):
            pulses = encode(lab, INPUT_SPEC)
            target = lab if condition != "sham" else sham_hint
            last = max(p.offset_ms for p in pulses)
            b.run_trial(pulses + _hint(Y_GROUP if target == "YES" else N_GROUP, last))
        b.model.freeze_plasticity(True)
        probe = _balanced(np.random.default_rng([seed, blk, 3]), N_PROBE)
        ok = 0
        for lab in probe:
            pulses = encode(lab, INPUT_SPEC)
            ok += probe_readout(b.run_trial(pulses), pulses) == lab
        acc.append(ok / N_PROBE)
    return acc


def run(seeds=SEEDS, n_blocks: int = N_BLOCKS) -> dict:
    curves = {c: np.array([run_condition(c, s, n_blocks) for s in seeds]) for c in CONDITIONS}
    last = {c: float(curves[c][:, -1].mean()) for c in CONDITIONS}
    margin = min(last["contingent"] - last["sham"], last["contingent"] - last["plasticity_off"]) * 100
    return {"curves": curves, "seeds": list(seeds), "last": last,
            "first": {c: float(curves[c][:, 0].mean()) for c in CONDITIONS},
            "margin_points": margin, "passed": margin >= RULE_POINTS}


def plot(r: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(1, r["curves"]["contingent"].shape[1] + 1)
    for c, col in zip(CONDITIONS, ("#1f77b4", "#ff7f0e", "#7f7f7f")):
        m, lo, hi = r["curves"][c].mean(0), r["curves"][c].min(0), r["curves"][c].max(0)
        ax.plot(x, m * 100, marker="o", color=col, label=c.replace("_", " "))
        ax.fill_between(x, lo * 100, hi * 100, color=col, alpha=0.15)
    ax.axhline(50, color="k", ls="--", lw=1, label="chance")
    ax.set(xlabel="Block (20 training + 20 probe trials)", ylabel="Probe accuracy (%)", ylim=(0, 105),
           title=f"Planted learning: mean, min–max over {len(r['seeds'])} seeds")
    ax.legend(loc="lower right")
    fig.text(0.5, 0.01, BADGE, ha="center", fontsize=13, fontweight="bold", color="#b00020")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=130)


def evidence_md(r: dict) -> str:
    n_pt = N_PROBE * len(r["seeds"])
    lines = ["# NeuroHear planted-learning positive control", "", f"**{BADGE}**", "",
             f"Input `{INPUT_SPEC.encoder_id}` on groups A (8, 9) / B (18, 19); readout groups Y {Y_GROUP}, N {N_GROUP}; "
             f"hint {HINT_DELAY_MS:.0f} ms after the last input pulse; STDP learning rate {STDP_LR}. Seeds {r['seeds']}; "
             f"{N_PROBE} probe trials per block per seed (N = {n_pt} per point).", "",
             "| Condition | First block | Last block | Last block per seed |", "|---|---|---|---|"]
    for c in CONDITIONS:
        per = ", ".join(f"{v * 100:.0f}" for v in r["curves"][c][:, -1])
        lines.append(f"| {c.replace('_', ' ')} | {r['first'][c] * 100:.0f}% | {r['last'][c] * 100:.0f}% | {per} |")
    verdict = "PASSED" if r["passed"] else "DID NOT PASS"
    lines += ["", f"**Pre-registered rule:** contingent last-block accuracy exceeds both sham and plasticity-off by "
                  f">= {RULE_POINTS:.0f} points, averaged over seeds. Smallest margin: {r['margin_points']:.0f} points. "
                  f"**{verdict}.**", "",
              ("- The learning exists because we wrote the rule. This shows the protocol can detect planted learning "
               "and does not report it for a label-independent sham." if r["passed"] else
               "- The positive control FAILED: with this design the protocol did not detect the planted learning, "
               "so we cannot yet claim it would detect learning in real cells.") + " It says nothing about real neurons.",
              "- One tuning pass was made after the first run failed (hint 10 -> 4 ms, learning rate 0.5 -> 2.0). "
              "Diagnosed cause of the failure: non-selective potentiation (adjacent Y/N groups and inputs that "
              "already drive channel 36 directly).",
              "- The model never receives labels: only pulses (inputs and hint) and its own spikes drive the rule."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Planted-learning positive control (SIMULATED)")
    ap.add_argument("--out", default=str(ROOT / "runs" / "learning_demo"))
    a = ap.parse_args()
    r = run()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    plot(r, out / "learning_curve.png")
    (out / "learning_evidence.md").write_text(evidence_md(r))
    print(BADGE)
    for c in CONDITIONS:
        print(f"{c:15s} first block {r['first'][c] * 100:5.1f}%  ->  last block {r['last'][c] * 100:5.1f}%")
    print(f"rule (>= {RULE_POINTS:.0f} pts over sham and plasticity-off): margin {r['margin_points']:.0f} pts -> "
          f"{'PASSED' if r['passed'] else 'DID NOT PASS'} | written to {out}")


if __name__ == "__main__":
    main()
