#!/usr/bin/env bash
# Run WebComPy browser test tier inside a real PyScript runtime.
#
# Usage:
#   scripts/run-browser-tests.sh                                   # all browser tests (wheel mode)
#   scripts/run-browser-tests.sh tests/browser/test_dom_browser.py # specific file
#   scripts/run-browser-tests.sh -k signal                         # keyword selector
#   scripts/run-browser-tests.sh --probes                          # only tests/browser/probes/**
#   scripts/run-browser-tests.sh --dual                            # + CPython-vs-PyScript sweep
#
# Environment:
#   WEBCOMPY_BROWSER_SOURCE=1            mount framework sources instead of wheels
#   WEBCOMPY_BROWSER_SENTINEL_TIMEOUT    readiness timeout in seconds (default 120)
#   WEBCOMPY_BROWSER_STRICT_CONSOLE=1    fail tests that emit console errors
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export WEBCOMPY_RUN_BROWSER=1

target="tests/browser"
rest=()
has_path=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dual)
      export WEBCOMPY_RUN_DUAL=1
      shift
      ;;
    --probes)
      target="tests/browser/probes"
      shift
      ;;
    tests/*|/*|*::*)
      has_path=1
      rest+=("$1")
      shift
      ;;
    *)
      rest+=("$1")
      shift
      ;;
  esac
done

if [ "$has_path" -eq 1 ]; then
  exec uv run python -m pytest "${rest[@]}"
fi
exec uv run python -m pytest "$target" "${rest[@]}"
