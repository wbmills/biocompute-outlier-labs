"""Spoken yes/no through the (simulated) culture: reservoir-computing protocol.

    python -m backend.experiment.audio_protocol --source reactive_sim   # or cl_sdk_sim, sdk_random

Each recording is encoded from its SOUND (backend.encoding.audio), delivered as
pulses, and the masked post-stimulus response is read by a linear readout
(the same frozen logistic-regression decoder as the main protocol).

Leakage rules: whole speakers are held out (no voice appears in both train and
test); the readout is fit on training speakers only; utterances are delivered in
a seeded random order so class is not confounded with time; labels come from
file names and are attached after acquisition.

Readouts and controls on the same held-out speakers:
  neural         masked response window -> linear readout (the result)
  input_only     the pulse pattern itself -> linear readout (no culture at all).
                 If this matches `neural`, the culture adds nothing.
  permuted       training labels shuffled (null distribution for `neural`)
  unmasked       DIAGNOSTIC: window from stimulus onset, includes artifact
  artifact_only  reactive_sim only: neural gain 0, artifact kept, masked
"""
from __future__ import annotations

import argparse
import glob
import json
import time
from pathlib import Path

import numpy as np

from backend.acquisition.simulator_adapter import RandomSimBackend, ReactiveSimBackend
from backend.encoding.audio import encode_audio, load_wav
from backend.experiment import feature_extract as fx
from backend.experiment.decoder import Decoder
from backend.experiment.metrics import score
from backend.schema import IS_LIVING_TISSUE, PROVENANCE

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {"tts": "synthetic speech (macOS text-to-speech)", "human": "recorded human speech"}
ENCODER_ID = "audio_bands_v1"


def load_dataset(root: Path = ROOT / "data" / "audio") -> list[dict]:
    """Files named <yes|no>_<speaker>_<take>.wav under data/audio/{tts,human}/."""
    items = []
    for kind in SOURCES:
        for f in sorted(glob.glob(str(root / kind / "*.wav"))):
            word, speaker = Path(f).stem.split("_")[:2]
            if word in ("yes", "no"):
                items.append({"path": f, "label": word.upper(), "speaker": f"{kind}:{speaker}", "kind": kind})
    return items


def split_speakers(items: list[dict], seed: int, test_frac: float = 1 / 3) -> set[str]:
    """Held-out speakers, chosen per kind so human voices are tested whenever there are 2+."""
    rng = np.random.default_rng([seed, 11])
    test: set[str] = set()
    for kind in SOURCES:
        spk = sorted({it["speaker"] for it in items if it["kind"] == kind})
        if len(spk) >= 2:
            rng.shuffle(spk)
            test |= set(spk[:max(1, round(len(spk) * test_frac))])
    return test


def make_backend(source: str, seed: int, **kw):
    if source == "reactive_sim":
        b = ReactiveSimBackend(seed=seed, raw=False, **kw)
    elif source == "sdk_random":
        b = RandomSimBackend(seed=seed, raw=False)
    elif source == "cl_sdk_sim":
        from backend.acquisition.cl1_adapter import CLBackend
        from backend.encoding.safety import SafetyGate
        b = CLBackend(SafetyGate(live=False, limits=None), seed=seed)
    else:
        raise ValueError(f"unsupported source {source}")
    b.connect()
    return b


def acquire(backend, items: list[dict], seed: int) -> list[dict]:
    order = np.random.default_rng([seed, 12]).permutation(len(items))
    rows = []
    for i in order:
        it = items[i]
        x, sr = load_wav(it["path"])
        pulses, pat = encode_audio(x, sr)                  # label never touches this path
        a = backend.run_trial(pulses)
        win = fx.response_window(pulses, a.stim_onset_ms)
        rows.append({**it, "pattern": pat.ravel(),
                     "neural": fx.spike_features(a.spikes, win, a.stim_onset_ms),
                     "unmasked": fx.unmasked_spike_features(a.spikes, pulses, a.stim_onset_ms),
                     "metadata": {k: v for k, v in a.metadata.items() if k != "observed_stims_ms"}})
    return rows


def readout(rows: list[dict], test: set[str], key: str, y_override=None) -> dict:
    tr = [r for r in rows if r["speaker"] not in test]
    te = [r for r in rows if r["speaker"] in test]
    y_tr = y_override if y_override is not None else [r["label"] for r in tr]
    d = Decoder().fit(np.array([r[key] for r in tr]), list(y_tr), [r["path"] for r in tr]).freeze()
    pred = d.predict(np.array([r[key] for r in te]))[0]
    out = score([r["label"] for r in te], pred)
    for kind in SOURCES:
        idx = [i for i, r in enumerate(te) if r["kind"] == kind]
        if idx:
            out[f"{kind}_correct"] = f"{sum(pred[i] == te[i]['label'] for i in idx)}/{len(idx)}"
    return out


def permutation_p(rows, test, observed: float, n_perm: int, seed: int) -> dict:
    tr_labels = [r["label"] for r in rows if r["speaker"] not in test]
    rng = np.random.default_rng([seed, 13])
    null = [readout(rows, test, "neural", list(rng.permutation(tr_labels)))["balanced_accuracy"]
            for _ in range(n_perm)]
    return {"null_mean": float(np.mean(null)), "null_p95": float(np.percentile(null, 95)),
            "p_value": (1 + sum(v >= observed for v in null)) / (1 + n_perm), "n_perm": n_perm}


def run(source: str, seed: int = 123, n_perm: int = 200) -> dict:
    items = load_dataset()
    if len({it["label"] for it in items}) < 2:
        raise SystemExit("need yes and no recordings: run scripts/make_tts_dataset.sh and/or scripts/record_voice.sh")
    test = split_speakers(items, seed)
    b = make_backend(source, seed)
    try:
        rows = acquire(b, items, seed)
    finally:
        if hasattr(b, "close"):
            b.close()
    res = {"neural": readout(rows, test, "neural"), "input_only": readout(rows, test, "pattern"),
           "unmasked": readout(rows, test, "unmasked")}
    res["permuted"] = permutation_p(rows, test, res["neural"]["balanced_accuracy"], n_perm, seed)
    if source == "reactive_sim":
        res["artifact_only"] = readout(acquire(make_backend(source, seed, gain_scale=0.0), items, seed), test, "neural")
    counts = {kind: sum(it["kind"] == kind for it in items) for kind in SOURCES}
    return {"protocol": "audio_reservoir_v1", "source": source, "provenance": PROVENANCE[source],
            "is_living_tissue": IS_LIVING_TISSUE[source], "seed": seed,
            "input": {SOURCES[k]: n for k, n in counts.items()},
            "n_speakers": len({it["speaker"] for it in items}), "test_speakers": sorted(test),
            "results": res,
            "notes": ["SIMULATED: any advantage of the culture over input_only exists by model construction.",
                      "No claim that cells hear, understand or learn speech; the readout is the only trained part."]}


def train_readout(backend, seed: int) -> dict:
    """Live-demo readout: fit on every recording in the dataset (no held-out
    metric is claimed for live trials), delivered through the dashboard's backend."""
    items = load_dataset()
    if len({it["label"] for it in items}) < 2:
        raise RuntimeError("no yes/no recordings: run scripts/make_tts_dataset.sh and/or scripts/record_voice.sh")
    rows = acquire(backend, items, seed)
    d = Decoder().fit(np.array([r["neural"] for r in rows]), [r["label"] for r in rows],
                      [r["path"] for r in rows]).freeze()
    return {"decoder": d, "backend_id": id(backend), "n": len(rows),
            "speakers": len({r["speaker"] for r in rows}),
            "input": {SOURCES[k]: sum(r["kind"] == k for r in rows) for k in SOURCES}}


def live_trial(backend, ro: dict, x: np.ndarray, sr: int, publish) -> dict:
    """One spoken utterance from the dashboard microphone. The system is never
    told which word was said, so there is no true label and no metric."""
    pulses, _ = encode_audio(x, sr)
    tid = f"audio-{time.strftime('%H%M%S')}-{time.time_ns() % 10**6:06d}"
    stim = [p.__dict__ for p in pulses]
    publish({"type": "trial_started", "trial_id": tid, "source": backend.source,
             "encoder_id": ENCODER_ID, "split": "demo", "stimulus": stim})
    a = backend.run_trial(pulses)
    win = fx.response_window(pulses, a.stim_onset_ms)
    arts = fx.artifact_intervals(pulses, a.stim_onset_ms)
    flags = fx.quality_flags(a.spikes, win, arts, a.duration_ms)
    publish({"type": "spikes_batch", "trial_id": tid, "source": backend.source,
             "provenance": PROVENANCE.get(backend.source, backend.source), "encoder_id": ENCODER_ID,
             "split": "demo", "duration_ms": a.duration_ms, "stim_onset_ms": a.stim_onset_ms,
             "response_window_ms": list(win), "artifact_intervals_ms": [list(v) for v in arts],
             "stimulus": stim, "quality_flags": flags,
             "events": [[round(float(t), 2), int(c)] for t, c in a.spikes[:6000]]})
    pred, prob = ro["decoder"].predict(fx.spike_features(a.spikes, win, a.stim_onset_ms))
    res = {"type": "trial_result", "trial_id": tid, "encoder_id": ENCODER_ID, "split": "demo",
           "pred_label": pred[0], "pred_prob": float(prob[0]), "true_label": None, "correct": None,
           "decoder_trained": True, "artifact_masked": True, "source": backend.source,
           "provenance": PROVENANCE.get(backend.source, backend.source),
           "note": f"Live audio trial; readout trained on {ro['n']} recordings from {ro['speakers']} speakers. "
                   "Not included in any metric. Audio is not saved."}
    publish(res)
    return res


def evidence_md(r: dict) -> str:
    res = r["results"]
    def row(name, k):
        v = res[k]
        extra = ", ".join(f"{kind} {v[kind + '_correct']}" for kind in SOURCES if kind + "_correct" in v)
        return f"| {name} | {v['correct']}/{v['n']} | {v['balanced_accuracy']:.2f} | {extra} |"
    lines = [f"# NeuroHear spoken yes/no — {r['provenance']}", "",
             f"Seed {r['seed']} · living tissue: **{r['is_living_tissue']}** · input: "
             + ", ".join(f"{n} {k}" for k, n in r["input"].items()),
             f"{r['n_speakers']} speakers; held out whole: {', '.join(r['test_speakers'])}", "",
             "| Readout (held-out speakers) | Correct | Balanced acc. | By input |", "|---|---|---|---|",
             row("Culture response, masked (result)", "neural"),
             row("Pulse pattern only, no culture", "input_only"),
             row("Unmasked, includes artifact (diagnostic)", "unmasked")]
    if "artifact_only" in res:
        lines.append(row("Artifact only, neural gain 0", "artifact_only"))
    p = res["permuted"]
    lines += ["", f"**Permuted labels:** null mean {p['null_mean']:.2f}, 95th pct {p['null_p95']:.2f}, "
                  f"p = {p['p_value']:.3f} (n_perm={p['n_perm']})", ""] + [f"- {n}" for n in r["notes"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", default="reactive_sim", choices=["reactive_sim", "cl_sdk_sim", "sdk_random"])
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--n-perm", type=int, default=200)
    a = ap.parse_args()
    r = run(a.source, a.seed, a.n_perm)
    out = ROOT / "runs" / f"audio-{time.strftime('%Y%m%d-%H%M%S')}-{a.source}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(r, indent=2, default=float))
    (out / "evidence.md").write_text(evidence_md(r))
    print(evidence_md(r) + f"\nwritten: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
