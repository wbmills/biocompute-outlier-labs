#!/usr/bin/env bash
# One-command start: creates a venv on first run, then serves http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."
# cl-sdk needs Python >= 3.12
py_ok() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; }
if [ -x .venv/bin/python ]; then
  if ! py_ok .venv/bin/python; then
    echo "ERROR: .venv uses $(.venv/bin/python --version 2>&1); cl-sdk needs Python >= 3.12." >&2
    echo "Remove .venv and re-run, or recreate it with: uv venv --python 3.12 .venv" >&2
    exit 1
  fi
else
  PY=""
  for c in python3.12 python3.13 python3.14 python3 "$(command -v uv >/dev/null && uv python find 3.12 2>/dev/null || true)"; do
    if [ -n "$c" ] && command -v "$c" >/dev/null && py_ok "$c"; then PY=$c; break; fi
  done
  if [ -z "$PY" ]; then
    echo "ERROR: no Python >= 3.12 found (cl-sdk requires it). Install one, e.g. 'uv python install 3.12'." >&2
    exit 1
  fi
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements.txt cl-sdk
fi
export NEUROHEAR_SOURCE="${NEUROHEAR_SOURCE:-reactive_sim}"
export NEUROHEAR_SEED="${NEUROHEAR_SEED:-123}"
echo "NeuroHear on http://localhost:${NEUROHEAR_PORT:-8000}  (source: $NEUROHEAR_SOURCE, seed: $NEUROHEAR_SEED)"
exec .venv/bin/python -m backend.app
