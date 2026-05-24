#!/usr/bin/env bash
# Run WebComPy E2E tests locally using the same groups and commands as CI.
#
# Usage:
#   scripts/run-e2e-tests.sh                          # all groups (core + docs), both prod & static
#   scripts/run-e2e-tests.sh bootstrap-static         # single group, both modes
#   scripts/run-e2e-tests.sh components interaction   # multiple groups
#   scripts/run-e2e-tests.sh --serving-mode=static    # all groups, static mode only
#   scripts/run-e2e-tests.sh docs-home --serving-mode=static
#   scripts/run-e2e-tests.sh --console-level=error   # only show console errors in output
#   scripts/run-e2e-tests.sh --console-file-level=info # save error+warning+info to file
#
# Prerequisites:
#   uv sync --all-groups
#   uv run playwright install chromium
#
# The script mirrors the CI matrix defined in .github/workflows/ci.yml.
# When you add, rename, or remove E2E test files, update the group definitions
# below AND the CI matrix in .github/workflows/ci.yml.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CORPUS_DIR="$ROOT_DIR/.tmp/e2e-test-corpus"
mkdir -p "$CORPUS_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Group definitions — must match .github/workflows/ci.yml e2e-matrix
declare -A E2E_GROUPS=(
  ["bootstrap-static"]="tests/e2e/test_bootstrap.py tests/e2e/test_static_site.py"
  ["components"]="tests/e2e/test_component.py tests/e2e/test_lifecycle.py tests/e2e/test_scoped_style.py"
  ["reactive-lists"]="tests/e2e/test_reactive.py tests/e2e/test_repeat.py tests/e2e/test_keyed_repeat.py tests/e2e/test_dict_repeat.py"
  ["dynamic-control"]="tests/e2e/test_nested_dynamic.py tests/e2e/test_switch.py"
  ["router"]="tests/e2e/test_router.py tests/e2e/test_async_nav.py"
  ["interaction"]="tests/e2e/test_event.py tests/e2e/test_di.py"
  ["bundled-deps"]="tests/e2e/test_bundled_deps.py tests/e2e/test_bundled_deps_browser.py"
  ["runtime-local"]="tests/e2e/test_runtime_local.py"
  ["standalone"]="tests/e2e/test_standalone.py"
  ["plugin-script"]="tests/e2e/test_eruda.py"
)

# Docs groups are static-only in CI
declare -A DOCS_GROUPS=(
  ["docs-home"]="tests/e2e_docs/test_home.py tests/e2e_docs/test_documents.py tests/e2e_docs/test_helloworld.py"
  ["docs-demos"]="tests/e2e_docs/test_fizzbuzz.py tests/e2e_docs/test_todo.py"
  ["docs-matplotlib"]="tests/e2e_docs/test_matplotlib.py"
  ["docs-fetch"]="tests/e2e_docs/test_fetch.py"
)

SERVING_MODES=("prod" "static")
SELECTED_GROUPS=()
SERVING_MODE_FILTER=""
CONSOLE_LEVEL=""
CONSOLE_FILE_LEVEL=""

for arg in "$@"; do
  if [[ "$arg" == --serving-mode=* ]]; then
    SERVING_MODE_FILTER="${arg#--serving-mode=}"
  elif [[ "$arg" == --console-level=* ]]; then
    CONSOLE_LEVEL="${arg#--console-level=}"
  elif [[ "$arg" == --console-file-level=* ]]; then
    CONSOLE_FILE_LEVEL="${arg#--console-file-level=}"
  elif [[ "$arg" == "--help" ]] || [[ "$arg" == "-h" ]]; then
    echo "Usage: scripts/run-e2e-tests.sh [group...] [options]"
    echo ""
    echo "Options:"
    echo "  --serving-mode=prod|static    Run only the specified serving mode"
    echo "  --console-level=off|error|warning|info|log|debug"
    echo "      Minimum console level to display in output (default: warning)"
    echo "  --console-file-level=off|error|warning|info|log|debug"
    echo "      Minimum console level to save to log files (default: debug)"
    echo ""
    echo "Core E2E groups:"
    for name in "${!E2E_GROUPS[@]}"; do
      echo "  $name"
    done
    echo ""
    echo "Docs E2E groups (static mode only):"
    for name in "${!DOCS_GROUPS[@]}"; do
      echo "  $name"
    done
    echo ""
    echo "Without arguments, all groups run in both prod and static modes."
    exit 0
  else
    SELECTED_GROUPS+=("$arg")
  fi
done

if [ ${#SELECTED_GROUPS[@]} -eq 0 ]; then
  SELECTED_GROUPS=("${!E2E_GROUPS[@]}" "${!DOCS_GROUPS[@]}")
fi

PASSED=0
FAILED=0
declare -a FAILED_NAMES=()

_print_console_logs() {
  local console_dir="$1"
  local level_name="${2:-warning}"
  local level_num=2
  case "$level_name" in
    off)    level_num=0 ;;
    error)  level_num=1 ;;
    warning) level_num=2 ;;
    info)   level_num=3 ;;
    log)    level_num=4 ;;
    debug)  level_num=5 ;;
  esac

  if [ "$level_num" -eq 0 ] || [ ! -d "$console_dir" ]; then
    return
  fi

  local found=0
  for logfile in "$console_dir"/console-*.log; do
    [ -f "$logfile" ] || continue
    while IFS= read -r line; do
      local msg_level_num=4
      if [[ "$line" == \[error\]* ]]; then
        msg_level_num=1
      elif [[ "$line" == \[warning\]* ]]; then
        msg_level_num=2
      elif [[ "$line" == \[info\]* ]]; then
        msg_level_num=3
      elif [[ "$line" == \[log\]* ]]; then
        msg_level_num=4
      elif [[ "$line" == \[debug\]* ]]; then
        msg_level_num=5
      fi
      if [ "$msg_level_num" -le "$level_num" ]; then
        if [ "$found" -eq 0 ]; then
          echo "       Console messages:"
          echo "       ---"
          found=1
        fi
        if [ "$msg_level_num" -le 1 ]; then
          echo -e "       ${RED}${line}${NC}"
        elif [ "$msg_level_num" -le 2 ]; then
          echo -e "       ${YELLOW}${line}${NC}"
        else
          echo "       $line"
        fi
      fi
    done < "$logfile"
  done
  if [ "$found" -eq 1 ]; then
    echo "       ---"
  fi
}

run_group() {
  local group_name="$1"
  local files="$2"
  local modes=("${SERVING_MODES[@]}")

  if [[ "$group_name" == docs-* ]]; then
    modes=("static")
  fi

  if [ -n "$SERVING_MODE_FILTER" ]; then
    if [[ ! " ${modes[*]} " =~ " ${SERVING_MODE_FILTER} " ]]; then
      return
    fi
    modes=("$SERVING_MODE_FILTER")
  fi

  for mode in "${modes[@]}"; do
    echo -e "${CYAN}━━━ $group_name ($mode) ━━━${NC}"
    local log_file="$CORPUS_DIR/e2e-$group_name-$mode.log"
    local console_dir="$CORPUS_DIR/console-$group_name-$mode"
    mkdir -p "$console_dir"
    local start_time=$(date +%s)

    local env_console_file_level="${CONSOLE_FILE_LEVEL:-debug}"
    local env_console_stdout_level="${CONSOLE_LEVEL:-warning}"

    if CONSOLE_LOG_DIR="$console_dir" \
       CONSOLE_FILE_LEVEL="$env_console_file_level" \
       CONSOLE_STDOUT_LEVEL="$env_console_stdout_level" \
       uv run python -m pytest $files --tb=short --serving-mode="$mode" > "$log_file" 2>&1; then
      local elapsed=$(($(date +%s) - start_time))
      echo -e "${GREEN}OK${NC}  $group_name ($mode)  ${elapsed}s"
      _print_console_logs "$console_dir" "$env_console_stdout_level"
      ((PASSED++)) || true
    else
      local elapsed=$(($(date +%s) - start_time))
      echo -e "${RED}FAIL${NC}  $group_name ($mode)  ${elapsed}s"
      echo "       Last 20 lines of log:"
      echo "       ---"
      tail -20 "$log_file" | while IFS= read -r line; do
        echo "       $line"
      done
      echo "       ---"
      _print_console_logs "$console_dir" "$env_console_stdout_level"
      echo "       Full test log: $log_file"
      echo "       Console logs: $console_dir/"
      ((FAILED++)) || true
      FAILED_NAMES+=("$group_name ($mode)")
    fi
  done
}

for group_name in "${SELECTED_GROUPS[@]}"; do
  files=""
  if [[ "$group_name" == docs-* ]]; then
    files="${DOCS_GROUPS[$group_name]:-}"
    if [ -z "$files" ]; then
      echo -e "${RED}Unknown group: $group_name${NC}"
      echo "Available docs groups: ${!DOCS_GROUPS[*]}"
      exit 1
    fi
  else
    files="${E2E_GROUPS[$group_name]:-}"
    if [ -z "$files" ]; then
      echo -e "${RED}Unknown group: $group_name${NC}"
      echo "Available core groups: ${!E2E_GROUPS[*]}"
      exit 1
    fi
  fi
  run_group "$group_name" "$files"
done

echo ""
echo "──────────────────────────────────────────────"
echo -e "Total: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
if [ ${#FAILED_NAMES[@]} -gt 0 ]; then
  echo "Failures:"
  for name in "${FAILED_NAMES[@]}"; do
    echo "  - $name"
  done
fi
echo "Logs saved to: $CORPUS_DIR"
echo "──────────────────────────────────────────────"

[ $FAILED -eq 0 ]