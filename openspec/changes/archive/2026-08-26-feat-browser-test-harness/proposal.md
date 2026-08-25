## Why

WebComPy's browser runtime code is only ever validated in two extremes: fast unit tests running under CPython with fake ports (`tests/`, where `platform.system() == "Emscripten"` is never true), and slow, coarse-grained E2E scenarios (`e2e/`, full PyScript boot per scenario). There is no middle tier. Entire classes of behavior — Pyodide's WebLoop asyncio semantics, real `pyscript.ffi` proxy lifecycles, real DOM event dispatch, UTF-16 string contracts, the `ENVIRONMENT == "pyscript"` code paths — cannot be tested at unit granularity today. Regressions in these areas are only caught by E2E (late, expensive) or not at all.

PyScript's canonical host is a real browser (there is no supported Node.js path for `@pyscript/core`), and the PyScript project itself validates its in-browser Python stdlib by running a test framework *inside* PyScript and streaming JSON results out. We adopt the same proven pattern: a PyScript-native test harness that boots once per session and executes test functions in-page, driven by pytest through Playwright.

## What Changes

- Add a **browser unit test tier** at `tests/browser/`: pytest-collected test modules that execute inside a real PyScript runtime (main thread, real DOM, real browser ports) in headless Chromium.
- Add a **harness server** (Starlette, in `webcompy_cli`) that serves the local PyScript runtime assets, a generated py-config, a test manifest, and the harness HTML page.
- Add an **in-page test runner** (in `webcompy_testing`) that discovers test modules, resolves a small registry of in-page fixtures (fresh `WebComPyApp` + real `BrowserRenderContext` ports, fresh DOM root), enforces a per-test isolation protocol, captures stdout/tracebacks/console errors, and returns JSON results via a `create_proxy`-exposed entrypoint.
- Add a **pytest integration** (conftest/plugin) that collects `tests/browser/**` as normal importable modules, marks them as browser items, and overrides execution to dispatch each test id to the page and translate the JSON result into a pytest outcome.
- Support **two supply modes** for the framework code under test: source-mount mode (fast dev loop, `[files]` config) and wheel mode (CI parity with production packaging, existing wheel builder).
- Gate execution behind `WEBCOMPY_RUN_BROWSER=1` with a `scripts/run-browser-tests.sh` entry point and a dedicated CI job, mirroring the E2E tier's conventions.
- Include 4–5 **pilot tests** proving the tier's value: pure reactive logic, real-port DOM manipulation, real event dispatch with proxies, and asyncio/WebLoop semantics.

## Capabilities

### New Capabilities

- `browser-test-harness`: PyScript-native in-browser unit test execution — harness server, harness page boot, in-page runner with fixture registry and isolation protocol, driver↔page JSON protocol, pytest collection/execution integration, source-mount vs wheel supply modes, crash containment, and console capture.

### Modified Capabilities

- `test-execution-paths`: add `tests/browser/` as a third physical test tier alongside `tests/` (unit) and `e2e/` (E2E), with its own opt-in env-var gate, canonical runner script, and CI wiring.

## Impact

- **New directories**: `tests/browser/` (driver conftest + browser-native tests).
- **`packages/webcompy-testing`**: new in-page runner module (browser-side component, shipped/mounted into the harness page).
- **`packages/webcompy-cli`**: new harness server module reusing runtime-assets serving and wheel-builder machinery.
- **`scripts/`**: new `run-browser-tests.sh`.
- **CI**: new job for the browser test tier (Playwright/Chromium already available for E2E).
- **Docs**: `AGENTS.md` (File → Spec Mapping, Current Specs list, test tier description), `CONTRIBUTING.md` if it describes test layout.
- **Dependencies**: none new at runtime; Playwright already required for E2E/inspect.
- **No changes** to existing `tests/` or `e2e/` behavior.

## Known Issues Addressed

None resolved directly. This change establishes the detection capability for environment-specific issues that the current CPython-only unit tier structurally cannot surface (e.g., behavior behind the binary `Emscripten`-vs-other environment detection, which today is only ever exercised on the "other" branch in unit tests).

## Non-goals

- Dual-running existing `tests/` modules inside PyScript (import-safety classification, CPython-vs-PyScript result diffing) — Phase 2.
- Environment probe suites (codifying asyncio/FFI/UTF-16/event-ordering assumptions, PyScript version-bump diffing) — Phase 2.
- `webcompy inspect pyexec` ad-hoc code execution CLI for development-time verification — Phase 2.
- Running the full pytest framework *inside* Pyodide — rejected for Phase 1; a purpose-built slim runner is the baseline (kept as a documented spike).
- Worker-context (PyWorker/Donkey) test execution — the worker's proxied DOM differs from WebComPy's main-thread runtime; not equivalent fidelity.
- MicroPython (`mpy`) interpreter support — WebComPy targets the Pyodide interpreter only.
- Public user-facing testing API guarantees — the tier is framework-internal first; stabilization for downstream app authors may follow later.
