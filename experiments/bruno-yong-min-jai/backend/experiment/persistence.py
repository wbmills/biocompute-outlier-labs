"""Run directory layout (immutable trial log + reports):

runs/<run_id>/trials.jsonl   one JSON record per acquired trial (with spikes)
runs/<run_id>/audit.jsonl    every stimulation command, authorised or rejected
runs/<run_id>/report.json    final report (after locked test)
runs/<run_id>/trials.csv     flat per-trial table
runs/<run_id>/evidence.md    one-slide evidence summary
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from backend.schema import Trial, jsonable


class RunStore:
    def __init__(self, root: str | Path, run_id: str):
        self.dir = Path(root) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.trials_path = self.dir / "trials.jsonl"
        self.audit_path = self.dir / "audit.jsonl"

    def append_trial(self, trial: Trial) -> None:
        rec = jsonable(trial.summary(include_spikes=True, max_spikes=100_000))
        with open(self.trials_path, "a") as f:
            f.write(json.dumps(rec) + "\n")

    def write_report(self, report: dict, trials: list[Trial], evidence_md: str) -> None:
        (self.dir / "report.json").write_text(json.dumps(jsonable(report), indent=2))
        (self.dir / "evidence.md").write_text(evidence_md)
        cols = ["trial_id", "source", "split", "encoder_id", "label", "pred_label", "pred_prob",
                "n_spikes", "stim_onset_ms", "response_window_ms", "quality_flags"]
        with open(self.dir / "trials.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for t in trials:
                w.writerow([t.trial_id, t.source, t.split, t.encoder_id, t.label, t.pred_label,
                            None if t.pred_prob is None else round(t.pred_prob, 4), len(t.spikes),
                            t.stim_onset_ms, list(t.response_window_ms),
                            ";".join(t.metadata.get("quality_flags", []))])

    def zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(self.dir.iterdir()):
                if p.is_file():
                    z.write(p, arcname=f"{self.dir.name}/{p.name}")
        return buf.getvalue()
