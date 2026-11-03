#!/usr/bin/env bash
# Starts (or probes) the server and runs preflight -> baseline -> optimise -> locked test -> export.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}
PORT=${NEUROHEAR_PORT:-8000}; BASE="http://127.0.0.1:$PORT"
STARTED=""
if ! curl -sf "$BASE/health" >/dev/null 2>&1; then
  NEUROHEAR_PORT=$PORT NEUROHEAR_TRIAL_PAUSE_S=0 $PY -m backend.app >/tmp/neurohear-smoke.log 2>&1 &
  STARTED=$!; trap '[ -n "$STARTED" ] && kill $STARTED' EXIT
  for i in $(seq 1 60); do curl -sf "$BASE/health" >/dev/null && break; sleep 0.5; done
fi
post() { curl -sf -X POST -H 'Content-Type: application/json' -d "${2:-{\}}" "$BASE$1"; }
state() { curl -sf "$BASE/health" | $PY -c "import json,sys; print(json.load(sys.stdin)['experiment']['state'])"; }
wait_ready() { for i in $(seq 1 600); do s=$(state); case $s in READY|REPORT_READY) return 0;; ERROR) echo "ERROR"; return 1;; esac; sleep 0.5; done; return 1; }
post /reset >/dev/null
echo "source: $(curl -sf $BASE/health | $PY -c "import json,sys; print(json.load(sys.stdin)['backend']['provenance'])")"
for step in preflight baseline optimise lock-test; do
  printf "%-10s" "$step"; post /experiments/$step >/dev/null; wait_ready; echo " ok ($(state))"
done
RID=$(curl -sf "$BASE/health" | $PY -c "import json,sys; print(json.load(sys.stdin)['experiment']['run_id'])")
curl -sf "$BASE/experiments/$RID/export" -o "neurohear-$RID.zip"
curl -sf "$BASE/experiments/$RID/report" | $PY -c "
import json,sys; r=json.load(sys.stdin)
print('provenance :', r['provenance'], '| living tissue:', r['is_living_tissue'])
for k,v in r['test_results'].items(): print(f\"{k:15s}: {v['correct']}/{v['n']} held-out, balanced acc {v['balanced_accuracy']:.2f}\")
print('verdict    :', r['verdict'])"
echo "export     : neurohear-$RID.zip"
