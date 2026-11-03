"""Experiment engine: pre-registered plan, state machine, optimiser, sealed test.

IDLE -> READY -> CALIBRATING -> BASELINE -> OPTIMISING -> LOCKED_TEST -> REPORT_READY
                               \\-> QUALITY_FAILED -> REPORT_READY
ANY -> ERROR -> READY (reset)

Integrity rules implemented here:
  * Split (train/val/test), label order and candidate order are assigned from a
    fixed seed at construction, BEFORE any data is collected.
  * The backend receives pulses only; labels are attached after acquisition.
  * Decoders are fit on train trials only, the encoder is chosen on val trials
    only, then decoders + encoder are frozen (fingerprinted) before any test
    trial is acquired. Test labels/metrics are not computed until every test
    trial is in.
  * Every number in the report carries source/provenance and N.
"""
from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import fisher_exact, binomtest
from sklearn.metrics import balanced_accuracy_score

from backend.schema import (Trial, PROVENANCE, LABELS, jsonable)
from backend.encoding.encoders import (CANDIDATES, CANDIDATE_BY_ID, BASELINE_ID, EncoderSpec,
                                       encode, stimulation_budget)
from backend.encoding.safety import StimRejected
from backend.experiment import feature_extract as fx
from backend.experiment.decoder import Decoder, DECODER_VERSION
from backend.experiment.metrics import score
from backend.experiment.controls import permutation_control
from backend.experiment.persistence import RunStore

SOFTWARE_VERSION = "neurohear-0.1.0"
ALPHA_BURDEN = 0.0      # explicit, pre-registered; burden is matched by construction in v1
BETA_ARTIFACT = 0.5     # penalty per unit fraction of response window overlapping artifact


class EventBus:
    def __init__(self):
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=2000)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def publish(self, ev: dict):
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass


@dataclass
class PlanItem:
    encoder_id: str
    label: str
    split: str
    trial_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class Aborted(Exception):
    pass


class ProtocolError(RuntimeError):
    """Step requested out of order. State is left unchanged."""


class Experiment:
    def __init__(self, backend, *, runs_root="runs", seed: int = 123,
                 candidates: list[EncoderSpec] | None = None, baseline_id: str = BASELINE_ID,
                 n_train: int = 8, n_val: int = 4, n_test: int = 10, n_preflight: int = 6,
                 bus: EventBus | None = None, run_controls: bool = True, inter_trial_s: float = 0.0):
        self.backend = backend
        self.seed = seed
        self.candidates = candidates or list(CANDIDATES)
        self.cand_by_id = {c.encoder_id: c for c in self.candidates}
        assert baseline_id in self.cand_by_id
        self.baseline_id = baseline_id
        self.n_train, self.n_val, self.n_test = n_train, n_val, n_test
        self.n_preflight = n_preflight
        self.bus = bus or EventBus()
        self.run_controls = run_controls
        self.inter_trial_s = inter_trial_s
        self.run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.store = RunStore(runs_root, self.run_id)
        if hasattr(backend, "gate") and backend.gate is not None and backend.gate.audit_path is None:
            backend.gate.audit_path = self.store.audit_path
        self.state = "IDLE"
        self.error: str | None = None
        self.trials: dict[str, Trial] = {}
        self.decoders: dict[str, Decoder] = {}
        self.val_scores: dict[str, dict] = {}
        self.preflight: dict | None = None
        self.locked = False
        self.winner_id: str | None = None
        self.lock_fingerprints: dict[str, str] = {}
        self.report: dict | None = None
        self.active_encoder_id = baseline_id
        self._abort = threading.Event()
        self.busy = False
        self._make_plan()
        self.set_state("READY")

    # ------------------------------------------------------------------ plan
    def _make_plan(self):
        rng = np.random.default_rng([self.seed, 99])
        self.calib_plan: dict[str, list[PlanItem]] = {}
        for c in self.candidates:
            items = []
            for lab in LABELS:
                items += [PlanItem(c.encoder_id, lab, "train") for _ in range(self.n_train)]
                items += [PlanItem(c.encoder_id, lab, "val") for _ in range(self.n_val)]
            rng.shuffle(items)
            self.calib_plan[c.encoder_id] = items
        self._test_rng = np.random.default_rng([self.seed, 100])   # sealed; used only at lock-test

    def plan_summary(self) -> dict:
        return {"seed": self.seed, "candidates": [c.encoder_id for c in self.candidates],
                "baseline": self.baseline_id, "n_train_per_label": self.n_train,
                "n_val_per_label": self.n_val, "n_test_per_label_per_condition": self.n_test,
                "calibration_trials": sum(len(v) for v in self.calib_plan.values()),
                "test_trials": 2 * self.n_test * 2}

    # ---------------------------------------------------------------- utils
    def set_state(self, s: str):
        self.state = s
        self.bus.publish({"type": "state", "state": s, "run_id": self.run_id})

    def abort(self):
        self._abort.set()

    def _progress(self, done, total):
        self.bus.publish({"type": "progress", "state": self.state, "completed": done, "total": total})

    @property
    def source(self) -> str:
        return self.backend.source

    def provenance(self) -> str:
        st = self.backend.get_status()
        return st.get("provenance", PROVENANCE.get(self.source, self.source))

    # ---------------------------------------------------------- acquisition
    def _acquire(self, item: PlanItem, backend=None) -> Trial:
        if self._abort.is_set():
            raise Aborted("aborted by operator")
        be = backend or self.backend
        spec = self.cand_by_id.get(item.encoder_id) or CANDIDATE_BY_ID[item.encoder_id]
        pulses = encode(item.label, spec)
        self.bus.publish({"type": "trial_started", "trial_id": item.trial_id, "source": be.source,
                          "encoder_id": item.encoder_id, "split": item.split,
                          "stimulus": [p.__dict__ for p in pulses]})
        acq = be.run_trial(pulses)           # <- pulses only; label is never passed
        win = fx.response_window(pulses, acq.stim_onset_ms)
        arts = fx.artifact_intervals(pulses, acq.stim_onset_ms)
        flags = fx.quality_flags(acq.spikes, win, arts, acq.duration_ms)
        feats = fx.spike_features(acq.spikes, win, acq.stim_onset_ms)
        meta = dict(acq.metadata)
        meta["quality_flags"] = flags
        meta["budget"] = stimulation_budget(pulses)
        meta["feat_unmasked"] = fx.unmasked_spike_features(acq.spikes, pulses, acq.stim_onset_ms)
        if acq.raw_samples is not None and win[1] * 25 <= len(acq.raw_samples):
            meta["feat_psd"] = fx.psd_features(acq.raw_samples, win)
        tr = Trial(trial_id=item.trial_id, run_id=self.run_id, source=be.source, label=item.label,
                   encoder_id=item.encoder_id, encoder_params=dict(spec.params), stimulus=pulses,
                   stim_onset_ms=acq.stim_onset_ms, spikes=acq.spikes, duration_ms=acq.duration_ms,
                   response_window_ms=win, artifact_intervals_ms=arts, raw_samples=None,
                   features=feats, split=item.split, metadata=meta)
        rec = tr.summary()
        rec["metadata"] = {k: v for k, v in meta.items() if not k.startswith("feat_")}
        tr_for_log = Trial(**{**tr.__dict__, "metadata": rec["metadata"]})
        self.store.append_trial(tr_for_log)
        self.bus.publish({"type": "spikes_batch", "trial_id": tr.trial_id, "source": be.source,
                          "provenance": PROVENANCE.get(be.source, be.source),
                          "encoder_id": tr.encoder_id, "split": tr.split,
                          "duration_ms": tr.duration_ms, "stim_onset_ms": tr.stim_onset_ms,
                          "response_window_ms": list(win), "artifact_intervals_ms": [list(a) for a in arts],
                          "stimulus": [p.__dict__ for p in pulses], "quality_flags": flags,
                          "events": [[round(float(t), 2), int(c)] for t, c in acq.spikes[:6000]]})
        if self.inter_trial_s:
            time.sleep(self.inter_trial_s)
        return tr

    def _run_items(self, items: list[PlanItem], backend=None, store=True) -> list[Trial]:
        out = []
        for i, it in enumerate(items):
            tr = self._acquire(it, backend)
            if store:
                self.trials[tr.trial_id] = tr
            out.append(tr)
            self._progress(i + 1, len(items))
        return out

    def _xy(self, encoder_id: str, split: str, feat: str = "spikes"):
        trs = [t for t in self.trials.values() if t.encoder_id == encoder_id and t.split == split]
        if feat == "spikes":
            X = np.array([t.features for t in trs])
        else:
            X = np.array([t.metadata[f"feat_{feat}"] for t in trs])
        return X, [t.label for t in trs], trs

    def _guarded(fn):
        def wrap(self, *a, **k):
            if self.busy:
                raise RuntimeError("experiment busy")
            self.busy = True
            try:
                return fn(self, *a, **k)
            except ProtocolError as e:
                self.bus.publish({"type": "error", "message": str(e)})
                raise
            except Aborted as e:
                self.error = str(e)
                self.set_state("ERROR")
                self.bus.publish({"type": "error", "message": str(e)})
            except StimRejected as e:
                self.error = f"stimulation rejected: {e}"
                self.set_state("ERROR")
                self.bus.publish({"type": "error", "message": self.error})
            except Exception as e:
                self.error = f"{type(e).__name__}: {e}"
                self.set_state("ERROR")
                self.bus.publish({"type": "error", "message": self.error})
                raise
            finally:
                self.busy = False
        return wrap

    # ------------------------------------------------------------- phases
    @_guarded
    def run_preflight(self):
        self.set_state("CALIBRATING")
        rates, active = [], set()
        dur = 500.0
        if hasattr(self.backend, "record_spontaneous"):
            for i in range(self.n_preflight):
                acq = self.backend.record_spontaneous(dur)
                if len(acq.spikes):
                    active |= set(int(c) for c in acq.spikes[:, 1])
                rates.append(len(acq.spikes) / (dur / 1000.0))
                self.bus.publish({"type": "spikes_batch", "trial_id": f"preflight-{i}", "source": self.source,
                                  "provenance": PROVENANCE.get(self.source, self.source), "split": "control",
                                  "encoder_id": None, "duration_ms": dur, "stim_onset_ms": 0,
                                  "response_window_ms": [0, 0], "artifact_intervals_ms": [], "stimulus": [],
                                  "quality_flags": [],
                                  "events": [[round(float(t), 2), int(c)] for t, c in acq.spikes[:6000]]})
                self._progress(i + 1, self.n_preflight)
        self.preflight = {"n_recordings": len(rates), "mean_population_rate_hz": float(np.mean(rates)) if rates else None,
                          "active_channels": sorted(active), "n_active_channels": len(active),
                          "note": "spontaneous activity only; no stimulation"}
        self.bus.publish({"type": "preflight", **jsonable(self.preflight)})
        self.set_state("READY")
        return self.preflight

    def _fit_candidate(self, cid: str) -> dict:
        Xtr, ytr, trtr = self._xy(cid, "train")
        Xva, yva, trva = self._xy(cid, "val")
        dec = Decoder().fit(Xtr, ytr, [t.trial_id for t in trtr])
        pred, prob = dec.predict(Xva)
        for t, p, pr in zip(trva, pred, prob):
            t.pred_label, t.pred_prob = p, float(pr)
        sc = score(yva, pred)
        flagged = sum(1 for t in trtr + trva if t.metadata["quality_flags"])
        art_frac = np.mean([1.0 if "artifact_overlaps_window" in t.metadata["quality_flags"] else 0.0
                            for t in trtr + trva])
        budget = trtr[0].metadata["budget"]
        bacc = sc["balanced_accuracy"] if sc["balanced_accuracy"] is not None else 0.0
        objective = bacc - ALPHA_BURDEN * budget["total_charge_nC"] - BETA_ARTIFACT * art_frac
        self.decoders[cid] = dec
        res = {"encoder_id": cid, "description": self.cand_by_id[cid].description,
               "val": sc, "objective": float(objective), "n_train": len(trtr), "n_val": len(trva),
               "quality_flagged_trials": flagged, "artifact_fraction": float(art_frac),
               "budget": budget, "source": self.source, "provenance": self.provenance()}
        self.val_scores[cid] = res
        self.bus.publish({"type": "candidate_scored", **jsonable(res)})
        return res

    @_guarded
    def run_baseline(self):
        if self.locked:
            raise ProtocolError("encoder locked; reset to start a new run")
        self.set_state("BASELINE")
        self._run_items(self.calib_plan[self.baseline_id])
        res = self._fit_candidate(self.baseline_id)
        self.set_state("READY")
        return res

    @_guarded
    def run_optimise(self):
        if self.locked:
            raise ProtocolError("encoder locked; reset to start a new run")
        if self.baseline_id not in self.val_scores:
            raise ProtocolError("run baseline first")
        self.set_state("OPTIMISING")
        others = [c.encoder_id for c in self.candidates if c.encoder_id != self.baseline_id]
        # interleave candidates (round-robin over each candidate's shuffled plan) to limit drift confounds
        queues = [list(self.calib_plan[c]) for c in others]
        items = []
        while any(queues):
            for q in queues:
                if q:
                    items.append(q.pop(0))
        self._run_items(items)
        for cid in others:
            self._fit_candidate(cid)
        # select on validation objective only; ties -> baseline, then pre-registered order
        order = [self.baseline_id] + others
        best = max(order, key=lambda c: (round(self.val_scores[c]["objective"], 9), -order.index(c)))
        self.winner_id = best
        self._lock()
        self.set_state("READY")
        return self.leaderboard()

    def _lock(self):
        for cid, d in self.decoders.items():
            d.freeze()
            self.lock_fingerprints[cid] = d.fingerprint()
        self.locked = True
        self.active_encoder_id = self.winner_id
        self.bus.publish({"type": "locked", "winner": self.winner_id, "fingerprints": self.lock_fingerprints,
                          "leaderboard": jsonable(self.leaderboard())})

    def leaderboard(self) -> list[dict]:
        rows = sorted(self.val_scores.values(), key=lambda r: -r["objective"])
        return [{"encoder_id": r["encoder_id"], "description": r["description"],
                 "val_balanced_accuracy": r["val"]["balanced_accuracy"], "val_correct": r["val"]["correct"],
                 "val_n": r["val"]["n"], "objective": r["objective"],
                 "is_baseline": r["encoder_id"] == self.baseline_id,
                 "is_winner": r["encoder_id"] == self.winner_id, "provenance": r["provenance"]}
                for r in rows]

    @_guarded
    def run_locked_test(self):
        if not self.locked:
            raise ProtocolError("optimise (and lock) before the locked test")
        self.set_state("LOCKED_TEST")
        conds = [self.baseline_id] + ([self.winner_id] if self.winner_id != self.baseline_id else [])
        items = [PlanItem(c, lab, "test") for c in conds for lab in LABELS for _ in range(self.n_test)]
        self._test_rng.shuffle(items)
        test_trials = self._run_items(items)
        # sealed: predictions & metrics only after ALL test trials are acquired
        results = {}
        for c in conds:
            trs = [t for t in test_trials if t.encoder_id == c]
            X = np.array([t.features for t in trs])
            pred, prob = self.decoders[c].predict(X)
            for t, p, pr in zip(trs, pred, prob):
                t.pred_label, t.pred_prob = p, float(pr)
            assert self.decoders[c].fingerprint() == self.lock_fingerprints[c], "decoder changed after lock"
            results[c] = {"encoder_id": c, **score([t.label for t in trs], pred)}
        self.test_results = results
        q_bad = np.mean([bool(t.metadata["quality_flags"]) for t in self.trials.values()])
        report = self._build_report(results, test_trials, q_bad)
        self.report = report
        self.store.write_report(report, list(self.trials.values()), self._evidence_md(report))
        if q_bad > 0.5:
            self.set_state("QUALITY_FAILED")
        self.set_state("REPORT_READY")
        self.bus.publish({"type": "report_ready", "run_id": self.run_id, "provenance": self.provenance(),
                          "report": jsonable(report)})
        return report

    # ------------------------------------------------------------- controls
    def _controls(self, test_trials) -> dict:
        c = self.winner_id
        Xtr, ytr, trtr = self._xy(c, "train")
        Xte, yte, _ = self._xy(c, "test")
        obs = self.test_results[c]["balanced_accuracy"]
        out = {"PERMUTED_LABELS": {**permutation_control(Xtr, ytr, Xte, yte, obs, seed=self.seed),
                                   "encoder_id": c, "n_test": len(yte)}}
        # TRAIN_TEST_SEPARATION
        ids = {s: {t.trial_id for t in self.trials.values() if t.split == s} for s in ("train", "val", "test")}
        out["TRAIN_TEST_SEPARATION"] = {
            "disjoint": not (ids["train"] & ids["val"] or ids["train"] & ids["test"] or ids["val"] & ids["test"]),
            "n_train": len(ids["train"]), "n_val": len(ids["val"]), "n_test": len(ids["test"]),
            "decoders_frozen_before_test": True, "fingerprints": self.lock_fingerprints,
            "scaler_fit_on": "train only", "unit": "whole trials"}
        # ARTIFACT_MASK: declared mask + diagnostic of what happens without it
        Xtr_u = np.array([t.metadata["feat_unmasked"] for t in trtr])
        Xte_u = np.array([t.metadata["feat_unmasked"] for t in self.trials.values()
                          if t.encoder_id == c and t.split == "test"])
        d_u = Decoder().fit(Xtr_u, ytr, [])
        bacc_u = balanced_accuracy_score(yte, d_u.predict(Xte_u)[0])
        out["ARTIFACT_MASK"] = {"blank_ms_per_pulse": fx.BLANK_MS, "post_gap_ms": fx.POST_GAP_MS,
                                "window_ms": fx.WINDOW_MS,
                                "window_overlaps_artifact_trials": int(sum(
                                    "artifact_overlaps_window" in t.metadata["quality_flags"]
                                    for t in self.trials.values())),
                                "diagnostic_unmasked_balanced_accuracy": float(bacc_u),
                                "note": "Diagnostic only: features from a window that INCLUDES the stimulation period."}
        # NO_RESPONSE
        if self.run_controls and hasattr(self.backend, "control_clone"):
            nb = self.backend.control_clone(gain_scale=0.0)
            # simulated control is cheap: use 2x the main sample sizes for a tighter null estimate
            items = [PlanItem(c, lab, "control") for lab in LABELS for _ in range(2 * self.n_train)]
            titems = [PlanItem(c, lab, "control") for lab in LABELS for _ in range(2 * self.n_test)]
            rng = np.random.default_rng([self.seed, 5])
            rng.shuffle(items)
            rng.shuffle(titems)
            self.set_state("LOCKED_TEST")
            a = self._run_items(items, nb, store=False)
            b = self._run_items(titems, nb, store=False)
            d0 = Decoder().fit(np.array([t.features for t in a]), [t.label for t in a], [])
            p0 = d0.predict(np.array([t.features for t in b]))[0]
            s0 = score([t.label for t in b], p0)
            du = Decoder().fit(np.array([t.metadata["feat_unmasked"] for t in a]), [t.label for t in a], [])
            pu = du.predict(np.array([t.metadata["feat_unmasked"] for t in b]))[0]
            out["NO_RESPONSE"] = {**s0, "metric_status": s0["status"], "status": "acquired",
                                  "how": "same model and seed with stimulus response disabled (gain=0); artifact retained",
                                  "encoder_id": c,
                                  "unmasked_balanced_accuracy": float(balanced_accuracy_score([t.label for t in b], pu)),
                                  "binomial_p_vs_chance": float(binomtest(s0["correct"], s0["n"], 0.5, alternative="greater").pvalue),
                                  "expectation": "masked ~chance; unmasked inflated by artifact alone"}
        else:
            out["NO_RESPONSE"] = {"status": "not acquired",
                                  "note": "Request operator-supported no-stim / media-only recording on hardware."}
        out["NO_CELL_SALINE"] = {"status": "not acquired", "note": "Never fabricated. Requires operator-supported measurement."}
        return out

    def _build_report(self, results, test_trials, q_bad) -> dict:
        st = self.backend.get_status()
        controls = self._controls(test_trials)
        base, win = results[self.baseline_id], results.get(self.winner_id)
        perm = controls["PERMUTED_LABELS"]
        separable = (win["balanced_accuracy"] is not None and perm["p_value"] is not None
                     and perm["p_value"] < 0.05 and win["balanced_accuracy"] > perm["null_p95"])
        gain = None
        if self.winner_id != self.baseline_id and base["balanced_accuracy"] is not None:
            table = [[win["correct"], win["n"] - win["correct"]], [base["correct"], base["n"] - base["correct"]]]
            p = float(fisher_exact(table, alternative="greater")[1])
            gain = {"delta_pp": round(100 * (win["balanced_accuracy"] - base["balanced_accuracy"]), 1),
                    "fisher_one_sided_p": p, "supported": p < 0.05}
        if self.winner_id == self.baseline_id:
            verdict = "No demonstrated gain: baseline encoder was selected on validation."
        elif gain and gain["supported"]:
            verdict = "Chosen encoder outperformed baseline on sealed held-out trials (see N, CI, controls)."
        else:
            verdict = "No demonstrated gain on sealed held-out trials (difference not significant at this N)."
        living = st.get("is_living_tissue")
        return {
            "run_id": self.run_id, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": self.source, "provenance": st.get("provenance"), "is_live": self.source == "live_cl1",
            "is_living_tissue": living, "hardware_id": st.get("hardware_id"),
            "stim_approved_by": (st.get("safety", {}).get("limits") or {}).get("approved_by"),
            "software_commit": SOFTWARE_VERSION, "decoder": DECODER_VERSION,
            "cl_sdk_version": st.get("cl_sdk_version"), "seed": self.seed,
            "plan": self.plan_summary(), "preflight": self.preflight,
            "encoder_ids": [c.encoder_id for c in self.candidates],
            "params": {c.encoder_id: c.params for c in self.candidates},
            "baseline_id": self.baseline_id, "winner_id": self.winner_id,
            "validation_leaderboard": self.leaderboard(),
            "primary_metric": "held-out balanced accuracy (sealed test, whole-trial)",
            "test_results": results, "gain_vs_baseline": gain,
            "separability_above_permutation_null": separable, "verdict": verdict,
            "controls": controls, "artifact_exclusion": controls["ARTIFACT_MASK"],
            "permutation_control": perm, "no_cell_control_status": "not acquired",
            "stimulation_budget": {c: self.val_scores[c]["budget"] for c in self.val_scores},
            "data_quality": {"fraction_trials_flagged": float(q_bad)},
            "simulator_disclosure": st.get("disclosure"),
            "notes": [
                "Calibration blocks: baseline acquired first, other candidates interleaved; the sealed test interleaves baseline and winner.",
                "The digital label is known before encoding; a decoder of the pulse train would be trivially perfect. "
                "Results concern information in the post-stimulus NEURAL response only.",
                "No claim of speech understanding, hearing, or biological learning.",
            ] + (["SIMULATED: encoding preferences exist by model construction, not as a biological finding."]
                 if not living else []),
        }

    def _evidence_md(self, r: dict) -> str:
        def fmt(x):
            return "—" if x is None else f"{x:.2f}"
        lines = [f"# NeuroHear evidence — {r['provenance']}", "",
                 f"Run `{r['run_id']}` · seed {r['seed']} · living tissue: **{r['is_living_tissue']}**", "",
                 "| Condition | Held-out correct | Balanced acc. | 95% CI (acc.) |", "|---|---|---|---|"]
        for cid, res in r["test_results"].items():
            ci = res.get("ci95") or (None, None)
            tag = " (baseline)" if cid == r["baseline_id"] else " (chosen)"
            lines.append(f"| {cid}{tag} | {res['correct']}/{res['n']} | {fmt(res['balanced_accuracy'])} | "
                         f"{fmt(ci[0])}–{fmt(ci[1])} |")
        p = r["permutation_control"]
        nr = r["controls"]["NO_RESPONSE"]
        am = r["controls"]["ARTIFACT_MASK"]
        lines += ["", f"**Permuted labels:** null mean {p['null_mean']:.2f}, 95th pct {p['null_p95']:.2f}, "
                      f"p = {p['p_value']:.3f} (n_perm={p['n_perm']})",
                  "**No-response control:** " + (f"{nr['correct']}/{nr['n']} masked (bal. acc {fmt(nr['balanced_accuracy'])}, binomial p vs chance {nr['binomial_p_vs_chance']:.2f}); "
                                                   f"unmasked {nr['unmasked_balanced_accuracy']:.2f}" if nr.get("status") == "acquired"
                                                   else nr["status"]),
                  f"**Artifact mask:** {am['blank_ms_per_pulse']} ms blank/pulse, window starts {am['post_gap_ms']} ms after final pulse, "
                  f"{am['window_ms']} ms long. Without mask (diagnostic): {am['diagnostic_unmasked_balanced_accuracy']:.2f}",
                  "**No-cell/saline control:** not acquired", "", f"**Verdict:** {r['verdict']}", ""]
        lines += [f"- {n}" for n in r["notes"]]
        return "\n".join(lines) + "\n"

    # ---------------------------------------------------------------- demo
    def send_demo(self, label: str) -> dict:
        if self.busy:
            raise RuntimeError("experiment busy")
        if label not in LABELS:
            raise ValueError("label must be YES or NO")
        self.busy = True
        try:
            cid = self.active_encoder_id
            item = PlanItem(cid, label, "demo")
            tr = self._acquire(item)
            dec = self.decoders.get(cid)
            if dec is not None:
                pred, prob = dec.predict(tr.features)
                tr.pred_label, tr.pred_prob = pred[0], float(prob[0])
            res = {"type": "trial_result", "trial_id": tr.trial_id, "encoder_id": cid, "split": "demo",
                   "pred_label": tr.pred_label, "pred_prob": tr.pred_prob,
                   "true_label": label, "correct": None if tr.pred_label is None else tr.pred_label == label,
                   "decoder_trained": dec is not None, "artifact_masked": True,
                   "source": self.source, "provenance": self.provenance(),
                   "note": "Single demo trial; not included in any metric."}
            self.bus.publish(res)
            return res
        except StimRejected as e:
            self.bus.publish({"type": "error", "message": f"stimulation rejected: {e}"})
            raise
        finally:
            self.busy = False

    def snapshot(self) -> dict:
        n = {s: sum(1 for t in self.trials.values() if t.split == s) for s in ("train", "val", "test")}
        return jsonable({"run_id": self.run_id, "state": self.state, "error": self.error, "busy": self.busy,
                         "source": self.source, "provenance": self.provenance(), "seed": self.seed,
                         "locked": self.locked, "winner_id": self.winner_id, "baseline_id": self.baseline_id,
                         "active_encoder_id": self.active_encoder_id, "counts": n,
                         "plan": self.plan_summary(), "leaderboard": self.leaderboard(),
                         "test_results": getattr(self, "test_results", None),
                         "preflight": self.preflight, "report_ready": self.report is not None})

    def run_all(self):
        self.run_preflight()
        self.run_baseline()
        self.run_optimise()
        return self.run_locked_test()
