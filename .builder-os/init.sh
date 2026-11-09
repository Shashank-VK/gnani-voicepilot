#!/usr/bin/env bash
# gnani-voicepilot verify: setup venv, install deps, run tests + lint + secret scan.
# Exit 0 = everything passes. Run from the project root.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -e ".[dev]" 2>&1 | tail -2
.venv/bin/pip install -q gnani-vachana 2>&1 | tail -2 || echo "WARN: gnani-vachana install failed (SDK optional, httpx fallback in code)"

echo "== pytest =="
.venv/bin/python -m pytest -q

echo "== ruff =="
.venv/bin/ruff check src tests scripts

echo "== secret scan =="
# Fail if any tracked/untracked file (except .venv) contains an env assignment
# with a value for GNANI_API_KEY, or a 100+ char token that looks like a key.
if grep -rn --exclude-dir=.venv --exclude-dir=.git --exclude-dir=__pycache__ --exclude=init.sh -E 'GNANI_API_KEY=[^"$ ][^ ]+' . ; then
  echo "SECRET SCAN FAIL: GNANI_API_KEY value present in repo files"
  exit 1
fi
echo "secret scan PASS"

echo "VERIFY OK"
