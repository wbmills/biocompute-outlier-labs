import json, os, socket, threading, time, urllib.request
import pytest

@pytest.fixture(scope="module")
def server(tmp_path_factory):
    os.environ["NEUROHEAR_RUNS"] = str(tmp_path_factory.mktemp("runs"))
    os.environ["NEUROHEAR_TRIAL_PAUSE_S"] = "0"
    import importlib, uvicorn, backend.app as appmod
    appmod = importlib.reload(appmod)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(appmod.app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=srv.run, daemon=True); th.start()
    for _ in range(100):
        if srv.started: break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True; th.join(5)

def call(base, path, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, (json.loads(r.read()) if "json" in r.headers.get("content-type", "") else r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def test_health_and_provenance(server):
    code, h = call(server, "/health")
    assert code == 200 and h["backend"]["provenance"] == "SIMULATED MODEL"

def test_demo_trial_and_bad_label(server):
    code, r = call(server, "/trials", {"label": "YES"})
    assert code == 200 and r["decoder_trained"] is False and r["provenance"] == "SIMULATED MODEL"
    code, _ = call(server, "/trials", {"label": "PERHAPS"})
    assert code == 409

def test_source_switch_needs_confirm(server):
    code, _ = call(server, "/source", {"source": "sdk_random"})
    assert code == 400

def test_locked_test_before_optimise_is_refused(server):
    code, r = call(server, "/experiments/lock-test", {})
    assert code == 409 and "Optimise first" in r["error"]
    code, r = call(server, "/experiments/optimise", {})
    assert code == 409

def test_full_protocol_and_export(server):
    call(server, "/reset", {})
    code, r = call(server, "/experiments/run-all", {})
    assert code == 202
    for _ in range(240):
        _, h = call(server, "/health")
        if h["experiment"]["state"] in ("REPORT_READY", "ERROR"): break
        time.sleep(0.5)
    assert h["experiment"]["state"] == "REPORT_READY", h["experiment"]["error"]
    rid = h["experiment"]["run_id"]
    code, rep = call(server, f"/experiments/{rid}/report")
    assert code == 200 and rep["is_living_tissue"] is False
    code, data = call(server, f"/experiments/{rid}/export")
    assert code == 200 and data[:2] == b"PK"

def test_live_source_unavailable_without_sdk(server):
    from backend.acquisition.cl1_adapter import cl_available
    if cl_available()[0]:
        pytest.skip("cl-sdk installed")
    code, r = call(server, "/source", {"source": "live_cl1", "confirm": True})
    assert code == 409 and "cl-sdk" in r["error"]
