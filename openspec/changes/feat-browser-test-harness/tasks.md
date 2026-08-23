## 1. Harness server and py-config generation

- [x] 1.1 Add `webcompy_cli/_browser_test_harness.py` (Starlette app): `/_webcompy-assets/*` served from `runtime-assets/{PYSCRIPT_VERSION}/`, `/_webcompy-test/config.json` (generated harness py-config with `experimental_create_proxy: "auto"`, `interpreter` + `lockFileURL` parity with `webcompy_server._html`), `/_webcompy-test/manifest.json` (test module inventory), and `/testharness` (harness HTML with `core.js`, `core.css`, and single `<script type="py" config="...">` boot).
- [x] 1.2 Implement harness py-config builders for both supply modes: wheel mode (`packages=[wheel URLs]` via `webcompy_cli/_wheel_builder`) and source-mount mode (`WEBCOMPY_BROWSER_SOURCE=1` → `files` mappings for `packages/webcompy/src` + `packages/webcompy-testing/src` with `sys.path` prepend in bootstrap).
- [x] 1.3 Mount `tests/browser/**` files via `files` mappings in both supply modes (one explicit mapping per file, deterministic repo-relative target paths).
- [x] 1.4 Add harness HTML generator with sentinel hook: in-page bootstrap sets `<html data-webcompy-test-ready="1">` only after `window.__webcompy_test__` is assigned and `core.js` is initialized.

## 2. In-page runner (browser-side, in webcompy_testing)

- [x] 2.1 Add `webcompy_testing/browser_runner/` (importable inside PyScript): manifest-driven discovery (reads `/_webcompy-test/manifest.json` fallback) enumerating test modules under `tests/browser/`.
- [x] 2.2 Implement in-page fixture registry with at least `app` (fresh `WebComPyApp` + `BrowserRenderContext` provisioning real browser ports) and `dom_root` (fresh `<div>` mounted in `document.body`); unknown fixture name returns structured failure naming the fixture.
- [x] 2.3 Implement per-test isolation protocol: clear `document.body` children (except harness chrome), create a fresh `WebComPyApp`/DI scope, capture `stdout`/`stderr` and per-test console-error delta, and teardown `dom_root` + proxies created for the test.
- [x] 2.4 Implement entrypoint `window.__webcompy_test__.run_one(test_id: str)` as `async def` proxied via `create_proxy`, awaiting coroutine tests, resolving parametrize payloads from the `test_id` suffix, and returning the JSON result `{status, duration_ms, exc_type, traceback, stdout, stderr, console_error_delta}` with source paths carried repo-relatively.

## 3. Pytest integration (CPython side)

- [x] 3.1 Add pytest integration for `tests/browser/**`: mark every collected item as a browser item; enforce `WEBCOMPY_RUN_BROWSER=1` opt-in (missing gate → collection-time message referencing `scripts/run-browser-tests.sh`, no browser/servers started).
- [x] 3.2 Implement `pytest_pyfunc_call` override for browser items: serialize `@pytest.mark.parametrize` parameters into the `test_id`, `await page.evaluate("id => window.__webcompy_test__.run_one(id)", test_id)`, receive JSON, normalize traceback source paths back to repo-relative, and map to pytest outcomes (`passed`/`failed` with remote traceback and captured output/`skipped`).
- [x] 3.3 Implement session fixture: start harness server on `port 0`, launch Playwright Chromium, open the harness page, poll `<html data-webcompy-test-ready="1">` with captured console tail on timeout, and expose the `page` to the `pytest_pyfunc_call` path; sequential execution invariant (one `run_one` at a time).
- [x] 3.4 Enforce CPython-importability invariant for `tests/browser/**`: ruff lint rule (ban top-level `import js` / `from pyscript` outside `def`/`async def`; ban top-level fake-port imports), CI check with a helpful error explaining the function-local import requirement.

## 4. Crash containment and console-error capture

- [x] 4.1 Implement driver-side crash containment: on `page.evaluate` failure due to page close / wasm abort, report the item as an error with the page console tail attached, restart the browser + page and re-wait for the readiness sentinel, and resume with the next item.
- [x] 4.2 Implement per-test console-error capture (at least `type == "error"` messages from harness-page load through test teardown) included in the JSON `console_error_delta` surfaced in pytest reports; strict-mode promotion of non-empty deltas to failure is advisory by default.

## 5. Pilot tests

- [ ] 5.1 Add `tests/browser/test_signal_browser.py`: pure reactive propagation via the `app` fixture (no DOM, validates WebLoop-independent signal path under Emscripten).
- [ ] 5.2 Add `tests/browser/test_dom_browser.py`: real-port DOM manipulation — `BrowserDOMPort` creates real `DivElement`/`TextElement` nodes verified via `js.document` inside the test function.
- [ ] 5.3 Add `tests/browser/test_event_browser.py`: real `FFIPort.create_proxy` / event dispatch (`addEventListener` → `dispatchEvent`) and proxy destruction.
- [ ] 5.4 Add `tests/browser/test_async_browser.py`: `async def` test awaiting an `asyncio.sleep(0)` round-trip and a scheduler microtask, proving WebLoop semantics under Emscripten.

## 6. Entry point, CI, and docs

- [ ] 6.1 Add `scripts/run-browser-tests.sh`: the canonical entry point that sets `WEBCOMPY_RUN_BROWSER=1` and forwards optional path/k selectors to pytest.
- [ ] 6.2 Wire a `browser-tests` CI job (Playwright Chromium, pre-downloaded local runtime via the existing lockflow), initially allowed-to-fail or as a parallel of the `Test` job gated on `WEBCOMPY_RUN_BROWSER=1`.
- [ ] 6.3 Update `AGENTS.md` File → Spec Mapping, Framework Invariants, and Current Specs list; update `CONTRIBUTING.md` and any universal skill docs that reference spec names; run `python3 scripts/check-doc-spec-refs.py` and confirm it passes.
- [ ] 6.4 Update `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping and Critical Framework Invariants to reflect the new `browser-test-harness` spec and the modified `test-execution-paths` tier.
