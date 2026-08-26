## Why

Phase 1 provides the PyScript harness and the browser-tier collection/execution plumbing, but it only covers new browser-native tests. Two additional verification needs remain structurally unmet: (1) the existing ~200-file `tests/` suite still never runs under `ENVIRONMENT == "pyscript"` — the CPython-vs-Emscripten semantic gap (WebLoop, `to_js`/`create_proxy`, UTF-16, event-loop ordering) is not cross-checked outside E2E; and (2) environment assumptions remain implicit, so a PyScript or pyodide version bump can silently change behavior without a targeted regression signal. Finally, development-time probing requires a REPL-like loop inside the app's own interpreter, not only a tiered test run.

## What Changes

- Add **dual-run classification**: an AST scan classifies `tests/` modules into dual-run-eligible (CPython-importable and not DOM/fake-dependent) vs browser-only vs CPython-only, and the in-page runner loads the eligible subset from `tests/` via the existing `[files]` mount so the same test file executes in both interpreters.
- Add **CPython-vs-PyScript diff reporting**: a single harness-session sweep runs the eligible subset under PyScript and, on the CPython side, under normal `pytest tests/` discovery; results are bucketed into `both-pass`, `CPython-only fail`, `PyScript-only fail`, and `both fail`, surfaced as a pytest report (and an optional JSON artifact) so divergence is first-class, not discarded output.
- Add **environment probe suite** under `tests/browser/probes/`: small, version-pinned probes codifying PyScript-only assumptions (WebLoop `asyncio.sleep(0)` ordering, `create_proxy`/`destroy` lifecycles, `js` `to_js`/`is_none` contracts, `FakeDOMNode.splitText`-mirrored UTF-16 boundaries, event ordering) plus a version-bump sweep mode that runs the probe (and dual-run) tier twice—once at the pinned `PYSCRIPT_VERSION` and once at the candidate version—reporting behavioral deltas before the pin is changed.
- Add **`webcompy inspect pyexec`**: an ad-hoc, PyScript-native evaluation subcommand (session-scoped harness reuse) that evaluates Python snippets inside the harness/app's interpreter and returns JSON. It reuses the Phase 1 `window.__webcompy_test__.evaluate`-style gateway in a single-shot harness session and is also exposed as `webcompy inspect pyrepl`-capable non-interactive evaluation so agents can probe quickly.

## Capabilities

### New Capabilities

- `browser-dualrun`: classification of `tests/` modules for PyScript eligibility, in-page loading of eligible modules via the harness `[files]` mount, CPython-vs-PyScript diffed execution and report (JSON and pytest outcome).
- `browser-probes`: environment probe suite under `tests/browser/probes/` plus a version-bump sweep that compares probe (and dual-run) outcomes across two PyScript versions.
- `inspect-pyexec`: `webcompy inspect pyexec` — single-shot and REPL evaluation of Python code inside a real PyScript interpreter served locally via the browser harness, with structured JSON output.

### Modified Capabilities

- (none)

## Impact

- **`tests/browser/`**: new `probes/` subdirectory; no changes to existing `tests/` files except the classifier's read-only analysis (no edits to test bodies).
- **`webcompy_cli`**: extends the harness server from Phase 1 with a probe/dual-run CLI orchestration and the `inspect pyexec` subcommand.
- **`webcompy_testing`**: extends the in-page runner to import-and-run dual-run modules from `tests/` and to surface the `evaluate` gateway `pyexec` needs.
- **CI**: extends the `browser-tests` job from Phase 1 (or adds a sibling `browser-probes` / `browser-dualrun` mode) to run the eligible `tests/` sweep and the probe suite; adds a manually-triggered `browser-version-sweep` workflow that runs the same suites at the candidate PyScript version.
- **Docs**: `AGENTS.md` (add `browser-dualrun`/`browser-probes`/`inspect-pyexec` to File → Spec Mapping), `CONTRIBUTING.md` (probe authoring, dual-run eligibility rule, `PYSCRIPT_VERSION` bump procedure).
- **No runtime dependency added**: Playwright/Chromium already required; `PYSCRIPT_VERSION` pin unchanged except via explicit sweep workflow.

## Known Issues Addressed

Related to the general issue "Browser detection is binary (Emscripten vs other) — no partial API availability checks": probes codify the practical availability and lifecycle contracts that the binary check masks (FFI/JS/encoding availability, WebLoop schedule ordering). None of the general issues are resolved outright; this change adds their detection surface so a bump or regression becomes visible before it reaches E2E.

## Non-goals

- Publishing a stable user-facing browser testing API for downstream WebComPy app authors — probes and dual-run remain framework-internal in Phase 2.
- `@pyscript/bridge` / worker-context (PyWorker/Donkey) test execution — retained as fallback only.
- Running the full pytest framework *inside* Pyodide/pytest-pyodide — retained as a spike (Phase 2 may add an experiment task but does not promise it).
- MicroPython (`mpy`) interpreter support.
- Full parity of the entire `tests/` suite — many `tests/` modules import fakes or rely on CPython-only assumptions and remain correctly classified as non-eligible.
- `pyexec` running arbitrary code inside the production app server — it runs in the harness session's isolated interpreter, not via arbitrary evaluation on a production server process.
