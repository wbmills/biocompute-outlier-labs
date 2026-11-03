"""Replay of previously recorded trials (from a NeuroHear run directory, or any
file in the same trials.jsonl format, e.g. organiser-supplied stimulus-labelled
CL1 recordings converted to it).

A replay can ONLY return responses to stimulus schedules that were actually
delivered when the data were recorded. Requesting any other schedule raises
ReplayUnavailable: no counterfactual responses are ever fabricated.
Provenance of the original data is carried through (replay_of).
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

from backend.schema import Acquisition, StimPulse, PROVENANCE


class ReplayUnavailable(Exception):
    pass


def schedule_key(pulses) -> tuple:
    return tuple(sorted((round(float(p.offset_ms), 3), int(p.channel), int(p.phase_us),
                         round(float(p.current_uA), 4)) for p in pulses))


class ReplayBackend:
    source = "replay"

    def __init__(self, trials_path: str | Path):
        self.path = Path(trials_path)
        if self.path.is_dir():
            self.path = self.path / "trials.jsonl"
        self._pool: dict[tuple, deque] = defaultdict(deque)
        self.replay_of: set[str] = set()
        self.n_loaded = 0
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("split") == "demo" or not rec.get("stimulus"):
                continue
            pulses = [StimPulse(**p) for p in rec["stimulus"]]
            self._pool[schedule_key(pulses)].append(rec)
            self.replay_of.add(rec.get("metadata", {}).get("replay_of") or rec["source"])
            self.n_loaded += 1
        self.connected = False

    def connect(self):
        self.connected = True

    def close(self):
        self.connected = False

    def available_schedules(self) -> int:
        return sum(1 for v in self._pool.values() if v)

    def get_status(self) -> dict:
        orig = sorted(self.replay_of)
        living = any(o == "live_cl1" for o in orig)
        return {"source": self.source,
                "provenance": "REPLAY OF " + " + ".join(PROVENANCE.get(o, o) for o in orig),
                "is_living_tissue": living, "replay_of": orig, "connected": self.connected,
                "ready": self.connected and self.available_schedules() > 0,
                "trials_loaded": self.n_loaded, "file": str(self.path),
                "disclosure": "Replays recorded responses only for schedules that were actually delivered."}

    def run_trial(self, pulses: list[StimPulse]) -> Acquisition:
        q = self._pool.get(schedule_key(pulses))
        if not q:
            raise ReplayUnavailable("No recorded response for this stimulation schedule; "
                                    "replay cannot provide counterfactual responses.")
        rec = q.popleft()
        sp = np.array(rec.get("spikes") or [], dtype=float).reshape(-1, 2)
        return Acquisition(spikes=sp, duration_ms=rec["duration_ms"], stim_onset_ms=rec["stim_onset_ms"],
                           raw_samples=None, delivered=list(pulses),
                           metadata={"replay_of": rec.get("metadata", {}).get("replay_of") or rec["source"],
                                     "original_trial_id": rec["trial_id"]})
