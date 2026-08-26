# Inspect PyExec

## Purpose

WebComPy evaluates ad-hoc Python code inside a real PyScript interpreter served locally via the browser harness, returning structured JSON for development-time probing by humans and agents without touching the production server.

## Requirements

### Requirement: The inspect pyexec command shall evaluate Python code inside a real PyScript interpreter served locally

The `webcompy inspect pyexec <code>` command SHALL evaluate a Python code string inside a real PyScript interpreter served from local runtime assets (the same `PYSCRIPT_VERSION`-pinned `core.js` / `pyodide.mjs` / `pyodide-lock.json` used by the browser harness) and SHALL return structured JSON. The code string is the first positional argument; when `--file <path>` is supplied, the file's contents are used as the code. The harness boot is the Phase 1 harness boot (single `<script type="py">`, `experimental_create_proxy: "auto"`, local `interpreter`/`lockFileURL`), and execution reuses the harness `evaluate` entrypoint sibling of `run_one` (proxied via `create_proxy` and awaited via `page.evaluate`). The command SHALL launch a single harness session (one PyScript boot), evaluate the code, capture `stdout`, `stderr`, the Python `repr` of the last expression's value (`result_repr`), and the console-error delta for the evaluation, and return JSON of the shape `{"stdout": str, "stderr": str, "result_repr": str| null, "console_error_delta": [...ConsoleMessage], "exc_type": str| null, "traceback": str| null}`. When `--repl` is passed, the command SHALL keep the same harness session alive and loop `read (stdin line) → evaluate → print JSON line` until EOF/Ctrl-D, with an idle timeout `--repl-timeout` seconds (default 300) that tears down the browser and server. `pyexec` SHALL be confined to the harness interpreter; it SHALL NOT evaluate code in the production `webcompy start` server process. Although the CLI is `webcompy inspect pyexec` for discoverability, this capability is independent from `inspect-cli` (which is `webcompy start` server-backed); the implementation lives with the harness (`webcompy_cli/_browser_test_harness.py` + `webcompy_testing/browser_runner/`).

#### Scenario: Single-shot pyexec returns JSON
- **WHEN** `webcompy inspect pyexec "print(2+2)" --wait-for "#webcompy-app"` is run (or without `wait-for` when harness HTML needs no app selector)
- **THEN** JSON output SHALL contain `{"stdout": "4\n"}` (and `result_repr` corresponding to `None` for a statement) or, for `"2+2"`, `result_repr == "4"`

#### Scenario: pyexec via --file
- **WHEN** `webcompy inspect pyexec --file ./snippet.py` is run
- **THEN** the contents of `snippet.py` SHALL be evaluated in the harness interpreter and the same JSON shape SHALL be returned

#### Scenario: pyexec captures exception
- **WHEN** `webcompy inspect pyexec "1/0"` is run
- **THEN** JSON output SHALL contain `exc_type == "ZeroDivisionError"` and `traceback` containing the PyScript traceback with repo-relative source paths

#### Scenario: pyexec REPL mode loops in the same interpreter
- **WHEN** `webcompy inspect pyexec --repl` is started and lines `"x=1"` then `"x+1"` are fed on stdin
- **THEN** the second evaluation SHALL see `x == 1` (same harness interpreter, state preserved across REPL turns)

#### Scenario: pyexec does not run on the production server
- **WHEN** a production `webcompy start` server is running on some port
- **THEN** `webcompy inspect pyexec "2+2"` SHALL NOT contact that server; it SHALL launch its own harness session whose PyScript boot is traceable to `/_webcompy-assets/core.js` from `runtime-assets/`
