#!/usr/bin/env bash
# Run the PyScript version-bump sweep: execute the probe battery at the pinned
# PYSCRIPT_VERSION and at a candidate version, then diff the outcomes.
#
# Usage:
#   scripts/run-browser-version-sweep.sh <candidate-pyscript-version>
#
# Outputs:
#   artifacts/probes-pinned.json       outcome report at the pinned version
#   artifacts/probes-candidate.json    outcome report at the candidate version
#   artifacts/browser-version-sweep.json  bucketed diff (regression gate)
#
# Exit code is nonzero when any probe regressed (passed pinned, failed candidate).
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <candidate-pyscript-version>" >&2
  exit 2
fi
CANDIDATE="$1"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p artifacts

echo "==> probe run at pinned version"
WEBCOMPY_RUN_BROWSER=1 \
WEBCOMPY_DUALRUN_REPORT=artifacts/probes-pinned.json \
  uv run python -m pytest tests/browser/probes -p webcompy_cli._dualrun_pytest_plugin -q --tb=short

echo "==> downloading candidate runtime assets and running probes ($CANDIDATE)"
WEBCOMPY_RUN_BROWSER=1 \
WEBCOMPY_PYSCRIPT_CANDIDATE="$CANDIDATE" \
WEBCOMPY_DUALRUN_REPORT=artifacts/probes-candidate.json \
  uv run python -m pytest tests/browser/probes -p webcompy_cli._dualrun_pytest_plugin -q --tb=short

echo "==> diffing outcomes"
PINNED="$(grep -oP '(?<=^PYSCRIPT_VERSION = ")[^"]+' packages/webcompy-server/src/webcompy_server/_html.py)"
uv run python -m webcompy_cli._version_sweep \
  artifacts/probes-pinned.json artifacts/probes-candidate.json \
  --pinned-version "$PINNED" --candidate-version "$CANDIDATE" \
  --artifacts-dir artifacts
