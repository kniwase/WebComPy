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
#   scripts/run-e2e-tests.sh --parallel               # run groups in parallel
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
PARALLEL=0

for arg in "$@"; do
  if [[ "$arg" == --serving-mode=* ]]; then
    SERVING_MODE_FILTER="${arg#--serving-mode=}"
  elif [[ "$arg" == --console-level=* ]]; then
    CONSOLE_LEVEL="${arg#--console-level=}"
  elif [[ "$arg" == --console-file-level=* ]]; then
    CONSOLE_FILE_LEVEL="${arg#--console-file-level=}"
  elif [[ "$arg" == "--parallel" ]]; then
    PARALLEL=1
  elif [[ "$arg" == "--help" ]] || [[ "$arg" == "-h" ]]; then
    echo "Usage: scripts/run-e2e-tests.sh [group...] [options]"
    echo ""
    echo "Options:"
    echo "  --serving-mode=prod|static    Run only the specified serving mode"
    echo "  --console-level=off|error|warning|info|log|debug"
    echo "      Minimum console level to display in output (default: warning)"
    echo "  --console-file-level=off|error|warning|info|log|debug"
    echo "      Minimum console level to save to log files (default: debug)"
    echo "  --parallel                     Run groups in parallel"
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

_find_free_port() {
  python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
}

_build_run_tasks() {
  local tasks=()
  for group_name in "${SELECTED_GROUPS[@]}"; do
    local files=""
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

    local modes=("${SERVING_MODES[@]}")
    if [[ "$group_name" == docs-* ]]; then
      modes=("static")
    fi
    if [ -n "$SERVING_MODE_FILTER" ]; then
      if [[ ! " ${modes[*]} " =~ " ${SERVING_MODE_FILTER} " ]]; then
        continue
      fi
      modes=("$SERVING_MODE_FILTER")
    fi

    for mode in "${modes[@]}"; do
      tasks+=("$group_name|$mode|$files")
    done
  done

  printf '%s\n' "${tasks[@]}"
}

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

_run_single() {
  local group_name="$1"
  local mode="$2"
  local files="$3"

  local log_file="$CORPUS_DIR/e2e-$group_name-$mode.log"
  local console_dir="$CORPUS_DIR/console-$group_name-$mode"
  local task_tmp_dir="$CORPUS_DIR/tmp-$group_name-$mode"
  mkdir -p "$console_dir" "$task_tmp_dir"

  local env_console_file_level="${CONSOLE_FILE_LEVEL:-debug}"
  local env_console_stdout_level="${CONSOLE_LEVEL:-warning}"

  local port=""
  local env_extra=()

  if [[ "$mode" == "prod" ]]; then
    port=$(_find_free_port)
    if [[ "$group_name" == docs-* ]]; then
      env_extra+=("DOCS_E2E_PORT=$port")
    elif [[ "$group_name" == runtime-local ]]; then
      env_extra+=("RUNTIME_LOCAL_PORT=$port")
    else
      env_extra+=("E2E_PORT=$port")
    fi
  fi

  if [[ "$group_name" == docs-* ]]; then
    env_extra+=("DOCS_E2E_TMP_DIR=$task_tmp_dir")
    env_extra+=("DOCS_E2E_SERVER_LOG=$task_tmp_dir/server.log")
  elif [[ "$group_name" == runtime-local ]]; then
    env_extra+=("RUNTIME_LOCAL_TMP_DIR=$task_tmp_dir")
  elif [[ "$group_name" == standalone ]]; then
    env_extra+=("STANDALONE_TMP_DIR=$task_tmp_dir")
  else
    env_extra+=("E2E_TMP_DIR=$task_tmp_dir")
    env_extra+=("E2E_SERVER_LOG=$task_tmp_dir/server.log")
  fi

  local start_time=$(date +%s)

  local env_cmd=(env)
  for e in "${env_extra[@]}"; do
    env_cmd+=("$e")
  done

  if "${env_cmd[@]}" CONSOLE_LOG_DIR="$console_dir" \
     CONSOLE_FILE_LEVEL="$env_console_file_level" \
     CONSOLE_STDOUT_LEVEL="$env_console_stdout_level" \
     uv run python -m pytest $files --tb=short --serving-mode="$mode" > "$log_file" 2>&1; then
    local elapsed=$(($(date +%s) - start_time))
    echo -e "${GREEN}OK${NC}  $group_name ($mode)  ${elapsed}s${port:+  port=$port}"
    _print_console_logs "$console_dir" "$env_console_stdout_level"
    echo "0" > "$task_tmp_dir/.result"
  else
    local elapsed=$(($(date +%s) - start_time))
    echo -e "${RED}FAIL${NC}  $group_name ($mode)  ${elapsed}s${port:+  port=$port}"
    echo "       Last 20 lines of log:"
    echo "       ---"
    tail -20 "$log_file" | while IFS= read -r line; do
      echo "       $line"
    done
    echo "       ---"
    _print_console_logs "$console_dir" "$env_console_stdout_level"
    echo "       Full test log: $log_file"
    echo "       Console logs: $console_dir/"
    echo "1" > "$task_tmp_dir/.result"
  fi
}

_run_single_bg() {
  local group_name="$1"
  local mode="$2"
  local files="$3"
  local log_file="$CORPUS_DIR/e2e-$group_name-$mode.log"
  local task_tmp_dir="$CORPUS_DIR/tmp-$group_name-$mode"
  mkdir -p "$task_tmp_dir"

  local port=""
  local env_args=()

  if [[ "$mode" == "prod" ]]; then
    port=$(_find_free_port)
    if [[ "$group_name" == docs-* ]]; then
      env_args+=("DOCS_E2E_PORT=$port")
    elif [[ "$group_name" == runtime-local ]]; then
      env_args+=("RUNTIME_LOCAL_PORT=$port")
    else
      env_args+=("E2E_PORT=$port")
    fi
  fi

  if [[ "$group_name" == docs-* ]]; then
    env_args+=("DOCS_E2E_TMP_DIR=$task_tmp_dir")
    env_args+=("DOCS_E2E_SERVER_LOG=$task_tmp_dir/server.log")
  elif [[ "$group_name" == runtime-local ]]; then
    env_args+=("RUNTIME_LOCAL_TMP_DIR=$task_tmp_dir")
  elif [[ "$group_name" == standalone ]]; then
    env_args+=("STANDALONE_TMP_DIR=$task_tmp_dir")
  else
    env_args+=("E2E_TMP_DIR=$task_tmp_dir")
    env_args+=("E2E_SERVER_LOG=$task_tmp_dir/server.log")
  fi

  local console_dir="$CORPUS_DIR/console-$group_name-$mode"
  mkdir -p "$console_dir"
  local env_console_file_level="${CONSOLE_FILE_LEVEL:-debug}"
  local env_console_stdout_level="${CONSOLE_LEVEL:-warning}"

  local env_cmd=(env)
  for e in "${env_args[@]}"; do
    env_cmd+=("$e")
  done

  echo -e "${CYAN}━━━ $group_name ($mode) ━━━${NC}${port:+  port=$port} [background]"

  "${env_cmd[@]}" CONSOLE_LOG_DIR="$console_dir" \
    CONSOLE_FILE_LEVEL="$env_console_file_level" \
    CONSOLE_STDOUT_LEVEL="$env_console_stdout_level" \
    uv run python -m pytest $files --tb=short --serving-mode="$mode" \
    > "$log_file" 2>&1
}

if [ "$PARALLEL" -eq 1 ]; then
  declare -a PIDS=()
  declare -A PID_TASK=()

  while IFS='|' read -r group_name mode files; do
    _run_single_bg "$group_name" "$mode" "$files" &
    pid=$!
    PIDS+=("$pid")
    PID_TASK["$pid"]="$group_name ($mode)"
  done < <(_build_run_tasks)

  PASSED=0
  FAILED=0
  declare -a FAILED_NAMES=()

  for pid in "${PIDS[@]}"; do
    if wait "$pid"; then
      ((PASSED++)) || true
    else
      ((FAILED++)) || true
      FAILED_NAMES+=("${PID_TASK[$pid]}")
    fi
  done

  echo ""
  echo "──────────────────────────────────────────────"
  echo -e "Total: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
  if [ ${#FAILED_NAMES[@]} -gt 0 ]; then
    echo "Failures:"
    for name in "${FAILED_NAMES[@]}"; do
      echo "  - $name"
      log_name="${name% (*}"
      log_mode="${name#* (}"
      log_mode="${log_mode%)}"
      log_file="$CORPUS_DIR/e2e-$log_name-$log_mode.log"
      if [ -f "$log_file" ]; then
        echo "    Last 10 lines:"
        tail -10 "$log_file" | while IFS= read -r line; do
          echo "      $line"
        done
      fi
    done
  fi
  echo "Logs saved to: $CORPUS_DIR"
  echo "──────────────────────────────────────────────"

  [ $FAILED -eq 0 ]
else
  PASSED=0
  FAILED=0
  declare -a FAILED_NAMES=()

  while IFS='|' read -r group_name mode files; do
    echo -e "${CYAN}━━━ $group_name ($mode) ━━━${NC}"
    start_time=$(date +%s)

    log_file="$CORPUS_DIR/e2e-$group_name-$mode.log"
    console_dir="$CORPUS_DIR/console-$group_name-$mode"
    task_tmp_dir="$CORPUS_DIR/tmp-$group_name-$mode"
    mkdir -p "$console_dir" "$task_tmp_dir"

    env_console_file_level="${CONSOLE_FILE_LEVEL:-debug}"
    env_console_stdout_level="${CONSOLE_LEVEL:-warning}"

    port=""

    if [[ "$mode" == "prod" ]]; then
      port=$(_find_free_port)
    fi

    env_args=()
    if [ -n "$port" ]; then
      if [[ "$group_name" == docs-* ]]; then
        env_args+=("DOCS_E2E_PORT=$port")
      elif [[ "$group_name" == runtime-local ]]; then
        env_args+=("RUNTIME_LOCAL_PORT=$port")
      else
        env_args+=("E2E_PORT=$port")
      fi
    fi

    if [[ "$group_name" == docs-* ]]; then
      env_args+=("DOCS_E2E_TMP_DIR=$task_tmp_dir")
      env_args+=("DOCS_E2E_SERVER_LOG=$task_tmp_dir/server.log")
    elif [[ "$group_name" == runtime-local ]]; then
      env_args+=("RUNTIME_LOCAL_TMP_DIR=$task_tmp_dir")
    elif [[ "$group_name" == standalone ]]; then
      env_args+=("STANDALONE_TMP_DIR=$task_tmp_dir")
    else
      env_args+=("E2E_TMP_DIR=$task_tmp_dir")
      env_args+=("E2E_SERVER_LOG=$task_tmp_dir/server.log")
    fi

    env_cmd=(env)
    for e in "${env_args[@]}"; do
      env_cmd+=("$e")
    done

    if "${env_cmd[@]}" CONSOLE_LOG_DIR="$console_dir" \
       CONSOLE_FILE_LEVEL="$env_console_file_level" \
       CONSOLE_STDOUT_LEVEL="$env_console_stdout_level" \
       uv run python -m pytest $files --tb=short --serving-mode="$mode" > "$log_file" 2>&1; then
      elapsed=$(($(date +%s) - start_time))
      echo -e "${GREEN}OK${NC}  $group_name ($mode)  ${elapsed}s${port:+  port=$port}"
      _print_console_logs "$console_dir" "$env_console_stdout_level"
      ((PASSED++)) || true
    else
      elapsed=$(($(date +%s) - start_time))
      echo -e "${RED}FAIL${NC}  $group_name ($mode)  ${elapsed}s${port:+  port=$port}"
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
  done < <(_build_run_tasks)

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
fi