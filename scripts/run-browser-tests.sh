#!/usr/bin/env bash
# Run WebComPy browser test tier inside a real PyScript runtime.
#
# Usage:
#   scripts/run-browser-tests.sh                                   # all browser tests (wheel mode)
#   scripts/run-browser-tests.sh tests/browser/test_dom_browser.py # specific file
#   scripts/run-browser-tests.sh -k signal                         # keyword selector
#
# Environment:
#   WEBCOMPY_BROWSER_SOURCE=1            mount framework sources instead of wheels
#   WEBCOMPY_BROWSER_SENTINEL_TIMEOUT    readiness timeout in seconds (default 120)
#   WEBCOMPY_BROWSER_STRICT_CONSOLE=1    fail tests that emit console errors
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export WEBCOMPY_RUN_BROWSER=1

has_path=0
for arg in "$@"; do
  case "$arg" in
    tests/*|/*|*::*) has_path=1 ;;
  esac
done

if [ "$has_path" -eq 1 ]; then
  exec uv run python -m pytest "$@"
fi
exec uv run python -m pytest tests/browser "$@"
