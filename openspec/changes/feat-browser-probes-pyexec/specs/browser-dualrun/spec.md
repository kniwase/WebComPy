## Purpose

CPython-only unit tests never exercise the `ENVIRONMENT == "pyscript"` code paths; this capability classifies existing `tests/` modules for PyScript eligibility, re-executes the eligible subset inside the real PyScript harness, and reports CPython-vs-PyScript divergences as a first-class bucketed diff so WebLoop, FFI, encoding, and event-ordering gaps become visible before they reach E2E.

## ADDED Requirements

### Requirement: Classifier shall partition tests/ modules into eligible and ineligible sets via a read-only AST pass

A read-only classifier (in `webcompy_cli` alongside the harness) SHALL walk `tests/**/*.py` without importing any test module, parsing each file's AST, and classifying it as eligible iff its top-level imports do not include any of `js`, `pyscript`, `pyodide`, `webcompy_cli` or `docs_app` (never mounted in-page), `webcompy_testing` fake-port symbols, or `e2e.*`, nor a `tests.*` member that is not mounted by the harness (only eligible test modules themselves and their ancestor package `__init__.py` files are mounted; sibling helpers such as `tests/conftest.py` are not), and its top-level contains no disallowed side-effecting calls (any `Call` node at module scope). Imports of `js`-family symbols inside function bodies SHALL NOT disqualify the module. The classifier SHALL emit `eligible.txt` (one repo-relative path per line, sorted) and `ineligible.json` (`{path: reason}`), and SHALL respect a trailing pragma `browser-dualrun: eligible` or `browser-dualrun: skip` placed as a comment on its own line in the file, which overrides the AST judgment in the stated direction.

#### Scenario: Eligible pure module
- **WHEN** `tests/test_signal.py` contains only `from webcompy import Reactive` at top level and imports `js` only inside functions
- **THEN** the classifier SHALL list its path in `eligible.txt`

#### Scenario: Ineligible top-level import
- **WHEN** `tests/test_fake_dom.py` contains `from webcompy_testing import FakeBrowserDOMPort` at top level
- **THEN** the classifier SHALL omit it from `eligible.txt`
- **AND** `ineligible.json` SHALL contain an entry for its path with a reason naming the disqualifying import

#### Scenario: Pragma override
- **WHEN** an ineligible file contains a line `# browser-dualrun: eligible`
- **THEN** the classifier SHALL include the file in `eligible.txt` despite the AST judgment

### Requirement: Dual-run sweep shall execute the eligible subset in both interpreters and emit a bucketed diff

The dual-run sweep SHALL (a) run `pytest` over `eligible.txt` on the CPython side under the normal `tests/` discovery path, collecting `{test_id: outcome}` where `outcome` is `passed|failed|skipped`, and (b) load the same eligible modules into the PyScript harness via its `[files]` mount (already present from the harness change) and, reusing the harness `run_one(test_id)` entrypoint and its per-test isolation (fresh `WebComPyApp`/`BrowserRenderContext`, `dom_root` teardown, stdout/stderr + console-error capture, traceback repo-path rewriting), execute each `test_id` in the real PyScript interpreter and collect the same-shaped map. The driver SHALL diff the two maps into four buckets—`both-pass`, `CPython-only-fail`, `PyScript-only-fail`, and `both-fail`—and SHALL write `artifacts/browser-dualrun.json` (at least `{eligible_count, buckets: {bucket: [test_id]}, cpython_map, pyscript_map, duration_ms}`) and SHALL print a summary table in the pytest terminal summary hook. The suite SHALL default to informational (no hard CI gate); a future change may promote specific buckets once the initial divergence surface is triaged. Unknown fixture requests inside an eligible dual-run test SHALL be reported as `PyScript-only-fail` with a message naming the fixture.

#### Scenario: Dual-run produces a both-pass bucket
- **WHEN** every test in `eligible.txt` passes in both CPython and PyScript
- **THEN** `artifacts/browser-dualrun.json` SHALL have `buckets["both-pass"]` containing all `test_id`s and the other buckets empty

#### Scenario: PyScript-only failure is surfaced
- **WHEN** a test under `tests/test_codec.py` fails only when executed inside PyScript
- **THEN** `buckets["PyScript-only-fail"]` SHALL contain that `test_id` and the JSON SHALL include its PyScript traceback and its CPython passing outcome

#### Scenario: In-page fixture miss is a PyScript-only failure
- **WHEN** a dual-run test references a fixture name not in the in-page registry
- **THEN** the harness SHALL return a `failed` JSON result whose `exc_type`/`traceback` names the unknown fixture
- **AND** the diff SHALL bucket the test under `PyScript-only-fail`

### Requirement: Dual-run invocation and artifact contract

The canonical dual-run entry point SHALL be `scripts/run-browser-tests.sh --dual` (which sets `WEBCOMPY_RUN_BROWSER=1` and `WEBCOMPY_RUN_DUAL=1` in the pytest subprocess) and the underlying pytest hook SHALL also accept `WEBCOMPY_RUN_DUAL=1` set directly. The artifact path SHALL be `artifacts/browser-dualrun.json`, gitignored, written on every dual-run invocation whether Buckets are all-pass or not. The sweep SHALL execute the harness boot exactly once per session (sequential `run_one` calls).

#### Scenario: Canonical dual-run entry
- **WHEN** `scripts/run-browser-tests.sh --dual` is invoked
- **THEN** the pytest subprocess SHALL receive `WEBCOMPY_RUN_DUAL=1` and `WEBCOMPY_RUN_BROWSER=1`
- **AND** the harness SHALL execute the eligible subset and write `artifacts/browser-dualrun.json`

#### Scenario: Artifact written even when divergences exist
- **WHEN** the dual-run sweep finds `PyScript-only-fail` entries
- **THEN** `artifacts/browser-dualrun.json` SHALL still be written with the full `cpython_map` and `pyscript_map` present
