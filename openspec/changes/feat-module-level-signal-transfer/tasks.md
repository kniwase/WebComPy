## 1. Global registry

- [ ] 1.1 Add `_global_transferable_signals: dict[str, SignalBase]` module-level dict in `packages/webcompy/src/webcompy/signal/_composable.py`
- [ ] 1.2 Define `GLOBAL_SIGNAL_COMPONENT_ID = "__global__"` constant in `packages/webcompy/src/webcompy/hydration/_payload.py`
- [ ] 1.3 In `signal()` composable: when `ctx is None`, register in `_global_transferable_signals` instead of just returning `Signal._create(factory())`
- [ ] 1.4 In `signal()` composable: wrap factory execution in `try/except` when `ctx is None`; on failure, create `Signal._create(None)` and log warning

## 2. Collection

- [ ] 2.1 In `collect_transfer_data()` (`_collect.py`): after walking component tree, walk `_global_transferable_signals` and collect values under `GLOBAL_SIGNAL_COMPONENT_ID` key
- [ ] 2.2 Write test: global signals appear in payload under `"__global__"` key

## 3. Restoration in app.run()

- [ ] 3.1 In `app.run()` (or the render context setup): after deserializing payload, walk `_global_transferable_signals` and overwrite `signal._value` for keys found in `payload["__global__"]`
- [ ] 3.2 Use direct `_value` assignment (no `set_value()`, no notifications)
- [ ] 3.3 Write test: global signals are restored before first render
- [ ] 3.4 Write test: global signals NOT in payload retain factory values

## 4. Documentation

- [ ] 4.1 Document the timing window limitation: module-level signals may have incorrect values between import and `app.run()`
- [ ] 4.2 Document the recommended pattern for request-scoped shared state: `provide/inject` from root component setup
- [ ] 4.3 Document that module-level factories should be side-effect-free and not depend on request-scoped DI
- [ ] 4.4 Update docs_app with examples of module-level `signal()` usage

## 5. Tests

- [ ] 5.1 Write test: module-level `signal()` on server — factory runs, value collected, transferred
- [ ] 5.2 Write test: module-level `signal()` on browser — factory fails (DI unavailable), placeholder created, `app.run()` restores value
- [ ] 5.3 Write test: module-level `signal()` on client-side navigation — factory runs, no restoration
- [ ] 5.4 Write test: multiple module-level signals with explicit keys — all collected and restored correctly
- [ ] 5.5 Write test: global registry with no entries — no `"__global__"` key in payload
- [ ] 5.6 Run existing signal-value-transfer E2E tests to verify no regression

## 6. Lint, Type Check, and Validation

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 6.2 Run `uv run pyright`
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 6.4 Run `openspec validate feat-module-level-signal-transfer`
