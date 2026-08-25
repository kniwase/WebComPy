## Purpose

WebComPy validates browser-runtime behavior at unit granularity inside a real PyScript runtime (main thread, real DOM, real browser ports) — a harness server booting PyScript once per session, an in-page runner executing test functions, and a pytest integration that collects tests/browser/** normally and dispatches each test id to the page, returning JSON results as pytest outcomes.

## ADDED Requirements

### Requirement: Harness server shall serve local PyScript runtime and harness endpoints

The harness server SHALL be a Starlette application launched by the browser-test session fixture on an ephemeral port. It SHALL serve `/_webcompy-assets/*` from the existing `runtime-assets/{PYSCRIPT_VERSION}/` cache (including `core.js`, `core.css`, `pyodide/pyodide.mjs`, and `pyodide/pyodide-lock.json`). It SHALL serve `/_webcompy-test/config.json` (the generated harness py-config with `experimental_create_proxy: "auto"` and the same `interpreter`/`lockFileURL` shape as `webcompy_server._html` when `runtime_serving == "local"`), `/_webcompy-test/manifest.json` (test module inventory), and `/testharness` (the harness HTML). The harness HTML SHALL load `core.js`/`core.css` from the local assets, declare a single `<script type="py" config="...">` bootstrapping the in-page runner, and provide a mount container that per-test fixtures own.

#### Scenario: Harness server exposes required routes
- **WHEN** the browser-test session starts
- **THEN** the harness server SHALL respond `200` to `/_webcompy-assets/core.js`, `/_webcompy-assets/pyodide/pyodide.mjs`, `/_webcompy-test/config.json`, `/_webcompy-test/manifest.json`, and `/testharness`

#### Scenario: Runtime version parity
- **WHEN** the harness py-config is generated
- **THEN** its `interpreter` and `lockFileURL` values SHALL match the shape produced by `webcompy_server._html` for `runtime_serving == "local"` at the same `PYSCRIPT_VERSION`

### Requirement: Supply mode for framework code under test

The harness SHALL support two supply modes for the framework packages under test (`webcompy`, `webcompy_server`, `webcompy_testing`): wheel mode (packages declared via `packages=[wheel urls]` built by the framework wheel builder) and source-mount mode (opted in via `WEBCOMPY_BROWSER_SOURCE=1`, sources mapped into the Emscripten FS via PyScript `files` config entries that the bootstrap prepends to `sys.path`). Test files under `tests/browser/` SHALL be source-mounted in both modes (one explicit `files` mapping per file). Wheel mode SHALL be the default.

#### Scenario: Default supply mode
- **WHEN** `WEBCOMPY_BROWSER_SOURCE` is not set to `1`
- **THEN** the harness py-config SHALL declare framework packages via `packages=[wheel URL]`

#### Scenario: Source-mount supply mode
- **WHEN** `WEBCOMPY_BROWSER_SOURCE=1` is set
- **THEN** the harness py-config SHALL include a `files` mapping for every file under `packages/webcompy/src`, `packages/webcompy-testing/src`, and `packages/webcompy-server/src`, and the bootstrap SHALL prepend the mapped paths to `sys.path`

#### Scenario: Test files are always source-mounted
- **WHEN** any harness run executes
- **THEN** every file under `tests/browser/` SHALL be exposed via a `files` mapping regardless of the framework supply mode

### Requirement: In-page runner discovery, fixture registry, and isolated execution

The in-page runner SHALL discover test modules enumerated in the harness manifest. It SHALL expose a fixture registry resolving at least `app` (a fresh `WebComPyApp` + `BrowserRenderContext`, which provisions all real browser ports when `ENVIRONMENT == "pyscript"`) and `dom_root` (a fresh `<div>` appended to `document.body` and removed on teardown). It SHALL expose the entrypoint `window.__webcompy_test__.run_one(test_id: str)` as an `async def` proxied via `create_proxy` so the driver can call it with `page.evaluate` and await it as a JS Promise. Execution SHALL run the test function (awaiting it if it is a coroutine), collect its `stdout`/`stderr`, `traceback`, timing, and per-test console-error delta, and return a JSON string with at least `{status: "passed"|"failed"|"skipped", duration_ms, exc_type, traceback, stdout, stderr, console_error_delta}`. The isolation protocol between tests SHALL clear `document.body` children (except the harness chrome), create a new `WebComPyApp`/`BrowserRenderContext` under a new DI scope, and tear down the `dom_root` and any proxies created for the test. Unknown fixture names SHALL fail the test with a structured error identifying the unknown name.

#### Scenario: Sync test passes via in-page runner
- **WHEN** a sync browser test function is dispatched as `module::test_name`
- **THEN** the in-page runner SHALL execute it inside the real PyScript environment
- **AND** a passing test SHALL return `{status: "passed"}`

#### Scenario: Async test is awaited
- **WHEN** an `async def` browser test function is dispatched
- **THEN** the in-page runner SHALL `await` it before returning the result

#### Scenario: Fixture injection
- **WHEN** a browser test function declares parameters `app` and/or `dom_root`
- **THEN** the in-page runner SHALL resolve them from the fixture registry before calling the test function

#### Scenario: Unknown fixture fails explicitly
- **WHEN** a browser test function declares a parameter whose name is not in the fixture registry
- **THEN** the test SHALL return `{status: "failed"}` with an error message naming the unknown fixture

#### Scenario: Per-test isolation includes real browser ports
- **WHEN** a test under `ENVIRONMENT == "pyscript"` creates a `WebComPyApp` via the `app` fixture and calls `app.create_render_context()`
- **THEN** the resulting render context SHALL be a `BrowserRenderContext` provisioning the real `BrowserDOMPort`, `BrowserFFIPort`, and other browser ports (not fakes)

### Requirement: Pytest integration collects normally and dispatches each test id to the page

`tests/browser/**` modules SHALL be collected by the standard pytest import path; no custom `pytest_collect_file` that bypasses CPython import is required. Top-level imports in browser test modules SHALL use only CPython-importable modules (`webcompy` public API + stdlib); `js`/`pyscript`/`pyodide` and fake-port imports are forbidden at top level (they SHALL be imported inside functions/hook bodies). The conftest hook in `tests/browser/` (or the `webcompy_testing` pytest plugin supplying it) SHALL mark every collected item under `tests/browser/**` as a browser item and SHALL override `pytest_pyfunc_call` for those items: it SHALL `await page.evaluate("id => window.__webcompy_test__.run_one(id)", test_id)` (where `test_id` is the pytest node id, with parametrize payloads serialized in the id), receive the JSON result, normalize traceback source paths back to repository-relative paths, and map the result to a pytest outcome (`passed` → noop, `failed` → raise `AssertionError` with remote traceback and captured output, `skipped` → `pytest.skip()`).

#### Scenario: CPython-importability invariant
- **WHEN** a browser test module imports `js` or `pyscript` at top level
- **THEN** a lint rule guarding `tests/browser/**` SHALL fail locally and in CI with a message explaining that such imports must be function-local

#### Scenario: Parametrize is round-tripped
- **WHEN** a browser test is annotated with `@pytest.mark.parametrize`
- **THEN** the driver SHALL include the parametrize suffix in `test_id` and the in-page runner SHALL resolve the correct parametrization payload before invoking the function

#### Scenario: Remote failure maps to pytest failure
- **WHEN** the in-page runner returns `{status: "failed", traceback: "...", stdout: "..."}`
- **THEN** the pytest item SHALL fail and the reported traceback SHALL contain the remote PyScript traceback with source paths rewritten to repo-relative form

### Requirement: Session boot amortization and browser parity

The browser-test session SHALL boot a single Playwright Chromium page that loads `/testharness`, wait until `<html data-webcompy-test-ready="1">` appears (set by the in-page runner only after `window.__webcompy_test__` is assigned), capture browser console errors from boot through teardown, and reuse that interpreter for all tests in the session. The default execution model SHALL be sequential (one `run_one` at a time); parallel page distribution is a non-goal. The opt-in gate for this tier SHALL be `WEBCOMPY_RUN_BROWSER=1`, with `scripts/run-browser-tests.sh` as the canonical entry point that sets that variable in the pytest subprocess.

#### Scenario: Single boot per session
- **WHEN** a browser-test session contains N test items
- **THEN** the harness SHALL perform exactly one PyScript boot (one page load) unless a page crash forces a restart

#### Scenario: Opt-in guard
- **WHEN** `WEBCOMPY_RUN_BROWSER=1` is not set
- **THEN** pytest SHALL skip (or fail to collect, with a message referencing `scripts/run-browser-tests.sh`) any item under `tests/browser/` without launching a browser or starting the harness server

#### Scenario: Canonical entry point sets the gate
- **WHEN** `scripts/run-browser-tests.sh` runs (with optional path/parametrize selectors forwarded to pytest)
- **THEN** pytest SHALL receive `WEBCOMPY_RUN_BROWSER=1` in its environment and the tier SHALL be collected and executed

### Requirement: Crash containment and console-error capture

The driver SHALL capture browser console errors emitted after the harness page has loaded (at least every `type == "error"` console message). A per-test delta SHALL be included in the JSON result; the tier MAY promote non-empty deltas to a test failure in strict mode (default: included but advisory). If `page.evaluate` fails because the page has closed or the wasm runtime has aborted, the driver SHALL treat the item as a single error, attach the page console tail to that error, restart the browser and page, re-wait for `data-webcompy-test-ready`, and resume with the next item.

#### Scenario: Console-error delta included
- **WHEN** a browser test triggers a browser console error during its execution
- **THEN** the returned JSON SHALL contain a non-empty `console_error_delta` and the item SHALL surface that delta in its pytest report

#### Scenario: Page crash is contained
- **WHEN** the page crashes (or wasm aborts) during a test
- **THEN** that single test SHALL be reported as an error with the console tail attached
- **AND** the harness SHALL restart the browser and page and continue with the next test in the session
