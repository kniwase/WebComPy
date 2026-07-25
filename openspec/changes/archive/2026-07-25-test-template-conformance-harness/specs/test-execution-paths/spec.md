# Delta Spec: test-execution-paths

## ADDED Requirements

### Requirement: Conformance harness shall run in the unit-test tier

The GFM conformance harness (`tests/conformance/`) SHALL be collected by the default `pytest tests/` invocation without browser, real-time network access, or the `WEBCOMPY_RUN_E2E` opt-in. The harness MAY fetch the spec.txt once into a local cache (tests/conformance/.tmp/, gitignored) on first use; subsequent runs SHALL use the cache. Only cross-environment parity scenarios involving a real browser SHALL live in the E2E tier.

#### Scenario: Default discovery includes conformance suite
- **WHEN** `uv run python -m pytest tests/` runs without any environment flags
- **THEN** the GFM conformance examples SHALL be collected and executed (using the cached spec.txt if available)

#### Scenario: Browser parity scenario is E2E-gated
- **WHEN** the HTML-parser parity scenario runs
- **THEN** it SHALL execute only via the E2E entry point (`scripts/run-e2e-tests.sh`), as part of an existing or new E2E group

## MODIFIED Requirements

(none)
