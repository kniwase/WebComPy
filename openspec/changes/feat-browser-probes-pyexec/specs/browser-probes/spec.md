## Purpose

Environment probes codify PyScript-only contracts (WebLoop ordering, FFI lifecycle, JS interop, UTF-16 DOM behavior) as a small authoritative battery, and a version-bump sweep executes the same battery (and optionally the dual-run tier) at two PyScript versions to surface behavioral deltas before the pinned PYSCRIPT_VERSION is changed.

## ADDED Requirements

### Requirement: Probe battery shall reside under tests/browser/probes/ and execute via the browser tier harness

Probe tests SHALL reside in `tests/browser/probes/test_probe_*.py` and SHALL be ordinary browser-tier tests collected and executed through the Phase 1 harness (real PyScript main thread, `app`/`dom_root` fixtures, per-test isolation, console-error capture). Each probe SHALL codify a single PyScript-only contract and SHALL use an idiomatic browser-tier test name describing the contract. The driver SHALL group results for `tests/browser/probes/**` under a `probes` suite in the pytest report and in machine-readable artifacts, and SHALL treat any probe failure as a hard failure.

#### Scenario: Probe failure is authoritative
- **WHEN** `tests/browser/probes/test_probe_webloop_ordering.py::test_sleep_zero_ordering` fails in the browser tier
- **THEN** the pytest session SHALL fail (non-zero exit) and the `probes` suite in the report SHALL list the probe as failed

#### Scenario: Probe authoring is a normal browser test
- **WHEN** an author adds `tests/browser/probes/test_probe_utf16_dom.py` using `def test_splittext_surrogate(browser_dom)` against `BrowserDOMPort`
- **THEN** the test SHALL be collected as a browser-tier item without any custom probe DSL

### Requirement: Initial probe set shall cover the core environment contracts

The initial probe set SHALL include at least one probe for each of the following contracts: `asyncio.sleep(0)` and scheduler microtask ordering under Pyodide WebLoop, `create_proxy`/`destroy` lifecycle (including idempotent destroy and proxy survival across awaits), `js` `to_js`/`is_none`/`undefined` interop contracts, and `Text.splitText` UTF-16 boundary (including surrogate-half splitting mirroring `FakeDOMNode.splitText`'s spec). Each probe file SHALL document the contract it codifies in its module docstring (the text of which is the human-readable contract statement).

#### Scenario: Initial probes are present
- **WHEN** the `tests/browser/probes/` directory is listed
- **THEN** at least one file matching each of the four contract areas above SHALL exist

### Requirement: Version-bump sweep shall execute probes (and optionally dual-run) at two PyScript versions and emit a delta

A manually-triggered version-bump sweep SHALL execute the `tests/browser/probes/**` suite (and, if `WEBCOMPY_RUN_DUAL=1` is set, the eligible dual-run tier as well) twice: once with harness runtime assets from the pinned `PYSCRIPT_VERSION` and once with assets from the candidate version supplied via `WEBCOMPY_PYSCRIPT_CANDIDATE=<version>` (downloaded via the existing `webcompy_cli/_runtime_downloader` local-asset path). Both runs SHALL use the same harness code. The sweep SHALL write `artifacts/browser-version-sweep.json` (`{pinned_version, candidate_version, probes: {only_pinned_pass, only_candidate_pass, both_pass, both_fail}, dualrun?: <same buckets as browser-dualrun>}`) and SHALL fail the CI job if any probe regresses (`regressions` non-empty; equivalently `probes.only_pinned_pass` non-empty). Candidate assets SHALL never be promoted automatically.

#### Scenario: Sweep detects a probe regression at the candidate version
- **WHEN** the sweep runs with `WEBCOMPY_PYSCRIPT_CANDIDATE=2026.9.1` and a UTF-16 probe passes at the pinned version but fails at the candidate
- **THEN** `artifacts/browser-version-sweep.json` SHALL list that probe under `regressions` and in `probes.only_pinned_pass`
- **AND** the CI job SHALL exit non-zero

#### Scenario: Sweep without candidate runs no sweep
- **WHEN** `WEBCOMPY_PYSCRIPT_CANDIDATE` is not set
- **THEN** the sweep workflow SHALL be a no-op (or shall skip its steps with a message) and SHALL not overwrite any existing sweep artifact

### Requirement: Probe and sweep entry points

The canonical entry points SHALL reuse the browser tier: `scripts/run-browser-tests.sh --probes` SHALL run only `tests/browser/probes/**` in the harness, and the sweep workflow SHALL be triggered via `workflow_dispatch` with input `pyscript_candidate_version` (mapped to `WEBCOMPY_PYSCRIPT_CANDIDATE`) or via `WEBCOMPY_PYSCRIPT_CANDIDATE` set in the shell. The `tests/browser/probes/` directory SHALL be discoverable by the harness manifest flow without manual registration; any new `test_probe_*.py` added there SHALL be included automatically in the next harness collection.

#### Scenario: Probes-only run
- **WHEN** `scripts/run-browser-tests.sh --probes` is invoked
- **THEN** only files under `tests/browser/probes/**` SHALL be collected and executed via the harness

#### Scenario: Auto-discovery of new probes
- **WHEN** `tests/browser/probes/test_probe_new_contract.py` is added
- **THEN** the next harness probe run SHALL include it without any code change to the harness or the sweep workflow
