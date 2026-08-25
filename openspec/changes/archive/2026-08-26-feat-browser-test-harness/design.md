## Context

WebComPy pins PyScript 2026.3.1 and already serves it locally (`_webcompy-assets/core.js`, `pyodide.mjs`, `pyodide-lock.json`) for production apps and for the E2E `my_app` fixture. The app boot path generates a `<script type="py" config="...">` element with `packages=[wheel urls]` and `experimental_create_proxy: "auto"`. When `ENVIRONMENT == "pyscript"` the `BrowserRenderContext` provisions all 13 browser ports into a fresh DI scope, so a per-test fresh `WebComPyApp` automatically has real DOM/FFI/host/fetch bindings. The test gap is that unit tests never reach this path (`ENVIRONMENT == "other"` + fakes) and E2E never exercises unit granularity. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- A repeatable, session-scoped harness that boots real PyScript once and executes many browser-native test functions in-page, driven by pytest.
- A pytest integration that reuses normal import-based collection (tests are CPython-importable, with `js`/`pyscript` imports function-local) and translates in-page JSON results into pytest outcomes so the existing reporter/console-log experience continues to apply.
- Two supply modes—source-mount (dev loop) vs wheel (CI parity)—without wheel rebuild churn.
- Per-test DI/DOM isolation with crash containment and console-error capture.
- Four to five pilot tests proving DOM, FFI, reactive, and WebLoop fidelity.

**Non-Goals:**
- Dual-running existing `tests/` inside PyScript, environment probe suites, and ad-hoc `pyexec` — all Phase 2.
- `@pyscript/bridge` or `polyscript` internals as the execution bridge; the design is self-contained.
- Running full pytest *inside* Pyodide/Node — rejected for Phase 1 (kept as a spike).
- MicroPython (`mpy`) interpreter, worker-context (PyWorker/Donkey) execution, signed wasm asset variations.

## Decisions

### D1 — Superset harness server reuses dev-server/runtime-assets building blocks

A small Starlette app (new module in `webcompy_cli`) is launched by the pytest session fixture on `port 0`:

- `/_webcompy-assets/*` served from the existing `runtime-assets/{version}/` cache (no new download behavior).
- `/ _webcompy-test/config.json` generated harness `py-config` (`experimental_create_proxy: "auto"`, `interpreter` + `lockFileURL` identical to `webcompy_server._html` when `runtime_serving == "local"`).
- `/_webcompy-test/manifest.json` — test module inventory (drivers fetches it; also consumed by the in-page runner as fallback).
- `/testharness` — harness HTML: `core.js` + `core.css`, a single `<script type="py" config="...">` that bootstraps the in-page runner, and an empty app mount container the per-test fixtures own.

Reusing `webcompy_cli/_runtime_downloader` + `_server` routes is the smallest delta and guarantees version parity. The harness server lifetime is the pytest session's.

*Alternative considered:* reuse `webcompy start` as-is and mount a harness route on it. Rejected — the test harness needs immediate wheel/manifest control independent of the app package packaging.

### D2 — Driver ↔ page protocol is a `create_proxy`-exposed entrypoint (no PyScript internals)

The in-page bootstrap does `window.__webcompy_test__ = ffi.create_proxy({"run_one": run_one})` via `pyscript.ffi` (or the js window from the `js` module). The driver calls `page.evaluate("id => window.__webcompy_test__.run_one(id)", test_id)`. `run_one` is `async def` so pyodide FFI auto-converts to a JS Promise and the driver's `await` resolves natively. Results are serialized with `json.dumps`/`ffi.to_js` as a JSON string.

The gateway never reaches into PyScript/PolyScript internals (script-tag `.interpreter`, `hooks.main.onReady`, Donkey). The only browser contract is `window` and `create_proxy`.

*Alternative considered:* `@pyscript/bridge` — this bootstraps a second interpreter configuration orthogonal to the page's `<script type="py">` config and complicates state isolation.

### D3 — Pytest integration wraps normal collection, not a custom collector

Browser test modules follow one rule: top-level is CPython-importable (only `webcompy` public API + stdlib; `js`/`pyscript`/`pyodide` imports are function-local; no fakes from `webcompy_testing` at top level). A pytest hook in `tests/browser/conftest.py`/`webcompy_testing` marks every item under `tests/browser/**` as a browser item; `pytest_pyfunc_call` is overridden for those items:

- The hook extracts the test id (`module::class::func[param]`), serializes `@pytest.mark.parametrize` parameters, calls `page.evaluate(...)`, receives JSON `{status, duration_ms, exc_type, traceback, stdout, stderr, console_error_delta}`, and synthesizes a pytest outcome (`passed`/`failed`/`skipped`) with the remote traceback attached as the assertion output.

Normal `pyproject.toml` / ruff / pyright behavior is preserved. No AST-collection shim is needed.

*Alternative considered:* custom `pytest_collect_file` producing `BrowserTestItem` instances via AST scanning. Rejected — it blocks on top-level `js` imports or requires stubs, and forfeits the CPython-importability invariant Phase 2's dual-run depends on.

### D4 — In-page fixture registry + per-test app context (borrows the existing browser render context)

Per-test isolated state:

- A fresh `WebComPyApp(AppConfig(...))` and `BrowserRenderContext` under `app.di_scope` (which already provisions all real browser ports when `ENVIRONMENT == "pyscript"`). No new port provisioning code is introduced.
- A fresh DOM container `doc.createElement("div")` appended to `document.body` as `dom_root`, removed and proxies destroyed on teardown.
- `stdout`/`stderr` capture via `io.StringIO` + `contextmanager(sys.stdout)`, traceback via `traceback.format_exception`.

Fixture names are resolved from the test function's signature against a small in-page registry. The Phase 1 registry exposes at least:

| Fixture | Value |
|---|---|
| `app` | Fresh `WebComPyApp` (consumer-provided `AppConfig`) + helper `ctx = app.create_render_context()` |
| `dom_root` | Fresh `<div>` mounted in `document.body` |

The registry is extensible; unknown names raise a structured failure.

*Alternative considered:* mounting an actual `WebComPyApp` at harness-page level and hot-reloading it per test. Rejected — it couples harness boot to app boot and complicates teardown.

### D5 — Two supply modes; test files always source-mounted

- **Wheel mode** (CI default): framework code under test (`webcompy`, `webcompy_server`, `webcompy_testing`) is the newly built wheel requested from `webcompy_cli/_wheel_builder`; declared in `packages=[wheel urls]` in the harness py-config.
- **Source-mount mode** (developer opt-in, env var `WEBCOMPY_BROWSER_SOURCE=1`): framework sources are mounted via PyScript `files` config entries that map the `packages/*/src/` trees into the Emscripten FS. A small convention—prepend to `sys.path` early in bootstrap—makes `import webcompy` resolve to the live checkout without a wheel rebuild. All three trees (`packages/webcompy/src`, `packages/webcompy-testing/src`, `packages/webcompy-server/src`) are mounted: `webcompy_testing/__init__.py` imports from `webcompy_server.ports` at top level, so the runner's parent package requires it to be importable.

Test files themselves (everything under `tests/browser/`) are always source-mounted via the same `files` mechanism, regardless of framework mode. The harness py-config is synthesized per run with one explicit mapping per file, so no zip/unpack step is needed.

*Alternative considered:* serving sources as a zip and `zipfile` unpacking in-page. Rejected — explicit per-file mappings over localhost are simple and cacheable; zip adds extra unpack logic.

### D6 — Boot amortization and crash safety

The interpreter lives for the whole pytest session. Tests run sequentially in that interpreter via the serialized `run_one` gateway. `pytest_runtest_protocol` is not parallelized for this tier (Playwright session = one page). Isolation is per-test reset as above. The driver wraps `page.evaluate` and:

- Treats a page crash (browser closed / wasm abort string in console errors) as a single test error, records it, restarts the browser + page + sentinel wait, and resumes at the next test.
- Optionally exposes `WEBCOMPY_BROWSER_BATCH=0` to disable batching in Phase 1 (each call is `run_one`).

## Risks / Trade-offs

- **`js` imports that leak to top level break CPython collection** → Mitigation: document the invariant, lint it (ruff rule: ban `import js`/`from pyscript` outside `def`/`async def` in `tests/browser/**`), CI fails fast with a helpful message pointing to the invariant.
- **`files` config path drift (future PyScript `files` semantics change)** → Mitigation: isolate the mapping logic in one function; add a version guard that validates the generated py-config against `webcompy_server._html`'s structure.
- **Tracer leakage (module-level caches, etc.) across tests** → Mitigation: per-test fresh `WebComPyApp`/`RenderContext` + explicit `dom_root` teardown; evict test modules from `sys.modules` between tests; ship a small allowlist of globals known to be idempotent; restart the page after N tests as a safety valve.
- **Sentinel race (driver polled too early, PyScript not yet ready)** → Mitigation: the harness HTML sets `<html data-webcompy-test-ready="1">` only after the in-page runner assigns `window.__webcompy_test__`; the driver polls that attribute with the same `WEBCOMPY_BROWSER_SENTINEL_TIMEOUT` conventions used in `e2e/` (visible failure with captured console errors).
- **Traceback source paths in the Emscripten FS differ from checkout** → Mitigation: source-mount uses deterministic `packages/webcompy/src → /webcompy-src` equivalent that carries repo-relative prefixes into tracebacks; the driver rewrites them back to repo paths before re-raising.
- **Performance of per-file mounts for large trees** → Mitigation: source-mount mode is opt-in; wheel mode has no per-file penalty; measure with the pilot suite and cap the mount to the minimal set (`packages/webcompy/src`, `packages/webcompy-testing/src`, `packages/webcompy-server/src`, `tests/browser`) unless benchmarks justify full-tree mounts.
- **A hanging in-page test wedges the remaining session** → Mitigation: dead-worker fail-fast surfaces an explanatory error instead of cascading opaque queue timeouts, and crash classification already recycles the page on wasm aborts / page closes. A per-test watchdog that interrupts an in-flight `page.evaluate` is deferred as a Phase 1 calibration follow-up: the Playwright sync API cannot be driven across threads, so force-interrupting a blocked evaluate requires recycling the browser from outside the worker loop.

## Migration Plan

1. Land behind `WEBCOMPY_RUN_BROWSER=1` with no default-testpath change; no existing tests are affected.
2. Ship the new `tests/browser/` directory with the pilot suite; expose `scripts/run-browser-tests.sh` as the canonical entry point (mirroring `run-e2e-tests.sh`).
3. Add a CI job `browser-tests` (Playwright Chromium, local runtime assets pre-downloaded via `webcompy` lock ensure, same as `e2e/`) — initially allowed to be non-blocking if flake budget is uncertain, promote to required after green streak.
4. Document isolation and import invariants in `CONTRIBUTING.md` once Phase 1 exits.

No rollback complexity: the tier is additive and independently skippable on every run.

## Open Questions

- None that block specs/tasks. The per-file mount cap and the optional page-restart-every-N-tests tuning are Phase 1 implementation calibrations tracked as explicit tasks.
