"""NeuroHear HTTP API + dashboard server (Starlette + uvicorn).

Run:  python -m backend.app      (or ./scripts/run_local.sh)
Open: http://localhost:8000

Events stream over Server-Sent Events at /events (one-way, same payloads as the
spec's WebSocket events; SSE needs no extra websocket dependency).
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
import queue
import threading
from pathlib import Path

import numpy as np
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from backend.schema import PROVENANCE, jsonable
from backend.encoding.encoders import CANDIDATES, encode, stimulation_budget
from backend.encoding.safety import SafetyGate, OperatorLimits, StimRejected
from backend.acquisition.simulator_adapter import ReactiveSimBackend, RandomSimBackend
from backend.acquisition.replay_adapter import ReplayBackend, ReplayUnavailable
from backend.acquisition.cl1_adapter import CLBackend, cl_available
from backend.experiment.scheduler import Experiment, EventBus
from backend.experiment import audio_protocol

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
RUNS = Path(os.environ.get("NEUROHEAR_RUNS", ROOT / "runs"))
SOURCES = ["reactive_sim", "sdk_random", "replay", "cl_sdk_sim", "live_cl1"]


class AppState:
    def __init__(self):
        self.bus = EventBus()
        self.lock = threading.Lock()
        self.backend = None
        self.exp: Experiment | None = None
        self.source_error: str | None = None
        self.audio_readout: dict | None = None
        self.init_source(os.environ.get("NEUROHEAR_SOURCE", "reactive_sim"),
                         int(os.environ.get("NEUROHEAR_SEED", "123")),
                         os.environ.get("NEUROHEAR_REPLAY"))

    def make_backend(self, source: str, seed: int, replay_path: str | None):
        if source == "reactive_sim":
            return ReactiveSimBackend(seed=seed)
        if source == "sdk_random":
            return RandomSimBackend(seed=seed)
        if source == "replay":
            if not replay_path:
                raise ValueError("replay requires a run directory or trials.jsonl path")
            return ReplayBackend(replay_path)
        ok, info = cl_available()
        if not ok:
            raise RuntimeError(f"cl-sdk not importable: {info}")
        if source == "cl_sdk_sim":
            return CLBackend(SafetyGate(live=False, limits=None), seed=seed)
        if source == "live_cl1":
            lp = os.environ.get("OPERATOR_LIMITS")
            limits = OperatorLimits.load(lp) if lp else None   # None => fail closed
            return CLBackend(SafetyGate(live=True, limits=limits), seed=seed)
        raise ValueError(f"unknown source {source}")

    def init_source(self, source: str, seed: int, replay_path: str | None = None):
        with self.lock:
            if self.exp and self.exp.busy:
                raise RuntimeError("experiment busy; STOP first")
            old = self.backend
            be = self.make_backend(source, seed, replay_path)
            be.connect()
            if old is not None:
                try:
                    old.close()
                except Exception:
                    pass
            self.backend = be
            self.exp = Experiment(be, runs_root=RUNS, seed=seed, bus=self.bus,
                                  run_controls=source in ("reactive_sim", "sdk_random"),
                                  inter_trial_s=float(os.environ.get("NEUROHEAR_TRIAL_PAUSE_S", "0.03")))
            self.source_error = None
            self.bus.publish({"type": "source", "source": be.source, "status": jsonable(be.get_status())})


S: AppState | None = None


def st() -> AppState:
    global S
    if S is None:
        S = AppState()
    return S


def ok(d: dict, code=200):
    return JSONResponse(jsonable(d), status_code=code)


def err(msg: str, code=400):
    return JSONResponse({"error": msg}, status_code=code)


async def health(_):
    s = st()
    status = s.backend.get_status() if s.backend else {}
    return ok({"ok": True, "backend": status, "experiment": s.exp.snapshot() if s.exp else None,
               "source_error": s.source_error})


async def config(_):
    ok_cl, info = cl_available()
    return ok({"sources": SOURCES, "provenance": PROVENANCE, "cl_sdk": {"available": ok_cl, "info": info},
               "live_stim_env": os.environ.get("LIVE_STIM_ENABLED", ""),
               "operator_limits_file": os.environ.get("OPERATOR_LIMITS"),
               "candidates": [{"encoder_id": c.encoder_id, "family": c.family, "params": c.params,
                               "description": c.description,
                               "YES": [p.__dict__ for p in encode("YES", c)],
                               "NO": [p.__dict__ for p in encode("NO", c)],
                               "budget": stimulation_budget(encode("YES", c))} for c in CANDIDATES]})


async def set_source(req: Request):
    body = await req.json()
    if not body.get("confirm"):
        return err("source switching requires confirm=true")
    try:
        await asyncio.to_thread(st().init_source, body["source"], int(body.get("seed", 123)), body.get("replay_path"))
    except Exception as e:
        st().source_error = str(e)
        return err(f"could not switch source: {e}", 409)
    return ok({"switched": True, "status": st().backend.get_status()})


def _bg(fn_name: str):
    async def handler(_req):
        s = st()
        exp = s.exp
        if exp.busy:
            return err("experiment busy", 409)
        fn = getattr(exp, fn_name)
        pre = {"run_optimise": lambda: exp.baseline_id in exp.val_scores and not exp.locked,
               "run_baseline": lambda: not exp.locked,
               "run_locked_test": lambda: exp.locked and exp.report is None}.get(fn_name)
        if pre and not pre():
            msgs = {"run_optimise": "Run the baseline first (or reset: the encoder is already locked).",
                    "run_baseline": "Encoder already locked. Reset to start a new run.",
                    "run_locked_test": "Optimise first; the locked test needs a frozen encoder. Already run? Reset."}
            return err(msgs[fn_name], 409)

        def run():
            try:
                fn()
            except Exception:
                pass   # error already published by the experiment
        threading.Thread(target=run, daemon=True).start()
        return ok({"started": fn_name, "run_id": exp.run_id}, 202)
    return handler


async def send_trial(req: Request):
    body = await req.json()
    label = str(body.get("label", "")).upper()
    try:
        res = await asyncio.to_thread(st().exp.send_demo, label)
    except StimRejected as e:
        return err(f"stimulation rejected: {e}", 403)
    except ReplayUnavailable as e:
        return err(str(e), 409)
    except Exception as e:
        return err(str(e), 409)
    return ok(res)


async def audio_trial(req: Request):
    """Raw microphone audio -> pulses -> culture -> linear readout. No word recognition."""
    s = st()
    if s.exp.busy:
        return err("experiment busy; STOP first", 409)
    try:
        body = await req.json()
        sr = int(body["sr"])
        x = np.frombuffer(base64.b64decode(body["pcm16"]), dtype="<i2").astype(np.float64)
    except Exception:
        return err("expected JSON {sr, pcm16: base64 little-endian int16 mono}")
    if len(x) < 0.3 * sr:
        return err("recording too short")
    s.exp.busy = True
    try:
        ro = s.audio_readout
        if ro is None or ro["backend_id"] != id(s.backend) or ro["n"] != len(audio_protocol.load_dataset()):
            ro = s.audio_readout = await asyncio.to_thread(audio_protocol.train_readout, s.backend, s.exp.seed)
        res = await asyncio.to_thread(audio_protocol.live_trial, s.backend, ro, x, sr, s.bus.publish)
    except StimRejected as e:
        return err(f"stimulation rejected: {e}", 403)
    except Exception as e:
        return err(str(e), 409)
    finally:
        s.exp.busy = False
    return ok(res)


async def reset(_):
    s = st()
    if s.exp.busy:
        return err("experiment busy; STOP first", 409)
    b = s.backend
    seed = s.exp.seed
    if b.source in ("reactive_sim", "sdk_random"):
        # simulated tissue restarts from its seed so a reset run is exactly repeatable
        await asyncio.to_thread(s.init_source, b.source, seed)
        s.bus.publish({"type": "reset", "run_id": s.exp.run_id})
        return ok({"reset": True, "run_id": s.exp.run_id, "note": "Previous runs remain on disk."})
    s.exp = Experiment(b, runs_root=RUNS, seed=seed, bus=s.bus, run_controls=s.exp.run_controls,
                       inter_trial_s=s.exp.inter_trial_s)
    if hasattr(b, "gate") and b.gate is not None:
        b.gate.audit_path = s.exp.store.audit_path
    s.bus.publish({"type": "reset", "run_id": s.exp.run_id})
    return ok({"reset": True, "run_id": s.exp.run_id, "note": "Previous runs remain on disk."})


async def stop(_):
    s = st()
    s.exp.abort()
    b = s.backend
    if hasattr(b, "stop"):
        b.stop()
    elif getattr(b, "gate", None):
        b.gate.stop()
    s.bus.publish({"type": "error", "message": "STOP pressed: acquisition aborted, stimulation blocked"})
    return ok({"stopped": True})


async def approve(req: Request):
    body = await req.json()
    b = st().backend
    gate = getattr(b, "gate", None)
    if gate is None or not gate.live:
        return err("approval only applies to live hardware", 400)
    try:
        gate.approve(str(body.get("operator_id", "operator")))
    except StimRejected as e:
        return err(str(e), 403)
    return ok({"approved": True, "safety": gate.status()})


async def report(req: Request):
    rid = req.path_params["rid"]
    s = st()
    if s.exp and s.exp.run_id == rid and s.exp.report:
        return ok(s.exp.report)
    p = RUNS / rid / "report.json"
    if p.exists():
        return Response(p.read_text(), media_type="application/json")
    return err("no report for this run (yet)", 404)


async def export(req: Request):
    rid = req.path_params["rid"]
    d = RUNS / rid
    if not d.exists():
        return err("unknown run", 404)
    from backend.experiment.persistence import RunStore
    data = RunStore(RUNS, rid).zip_bytes()
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="neurohear-{rid}.zip"'})


async def runs(_):
    out = []
    if RUNS.exists():
        for d in sorted(RUNS.iterdir(), reverse=True):
            if d.is_dir():
                out.append({"run_id": d.name, "has_report": (d / "report.json").exists(),
                            "has_trials": (d / "trials.jsonl").exists()})
    return ok({"runs": out[:50]})


async def events(req: Request):
    s = st()
    q = s.bus.subscribe()

    async def gen():
        try:
            yield f"data: {json.dumps(jsonable({'type': 'hello', 'experiment': s.exp.snapshot(), 'backend': s.backend.get_status()}))}\n\n"
            while True:
                if await req.is_disconnected():
                    break
                try:
                    ev = await asyncio.to_thread(q.get, True, 1.0)
                    yield f"data: {json.dumps(jsonable(ev))}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            s.bus.unsubscribe(q)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def index(_):
    return FileResponse(STATIC / "index.html")


routes = [
    Route("/", index),
    Route("/health", health),
    Route("/config", config),
    Route("/source", set_source, methods=["POST"]),
    Route("/trials", send_trial, methods=["POST"]),
    Route("/audio-trial", audio_trial, methods=["POST"]),
    Route("/experiments/preflight", _bg("run_preflight"), methods=["POST"]),
    Route("/experiments/baseline", _bg("run_baseline"), methods=["POST"]),
    Route("/experiments/calibration", _bg("run_baseline"), methods=["POST"]),   # spec alias
    Route("/experiments/optimise", _bg("run_optimise"), methods=["POST"]),
    Route("/experiments/lock-test", _bg("run_locked_test"), methods=["POST"]),
    Route("/experiments/run-all", _bg("run_all"), methods=["POST"]),
    Route("/experiments/{rid}/report", report),
    Route("/experiments/{rid}/export", export),
    Route("/runs", runs),
    Route("/reset", reset, methods=["POST"]),
    Route("/stop", stop, methods=["POST"]),
    Route("/operator/approve", approve, methods=["POST"]),
    Route("/events", events),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
]

@contextlib.asynccontextmanager
async def lifespan(_app):
    st()
    yield


app = Starlette(routes=routes, lifespan=lifespan)


def main():
    import uvicorn
    host = os.environ.get("NEUROHEAR_HOST", "127.0.0.1")
    port = int(os.environ.get("NEUROHEAR_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
