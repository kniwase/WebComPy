## 1. Escalate Signal() deprecation

- [ ] 1.1 In `packages/webcompy/src/webcompy/signal/_signal.py`, change `Signal.__init__` warning from `UserWarning` to `DeprecationWarning`; update message to "Signal() is deprecated. Use use_state(factory) instead."
- [ ] 1.2 Update type stubs (`.pyi` files) to mark `Signal.__init__` as `@deprecated`
- [ ] 1.3 Update existing tests that expected `UserWarning` to expect `DeprecationWarning`

## 2. Deprecate Computed() class constructor and rename computed() to use_computed()

- [ ] 2.1 Add `DeprecationWarning` to `Computed.__init__` in `packages/webcompy/src/webcompy/signal/_computed.py` — message: "Computed() is deprecated. Use use_computed(factory) instead."
- [ ] 2.2 Add `Computed._create(fn)` classmethod as internal bypass (mirrors `Signal._create()`)
- [ ] 2.3 Rename existing `computed()` function to `use_computed()` in `_computed.py`
- [ ] 2.4 Keep `computed` as a deprecated alias that emits `DeprecationWarning` directing to `use_computed()`
- [ ] 2.5 Update type stubs to mark `Computed.__init__` as `@deprecated`
- [ ] 2.6 Export `use_computed` from `webcompy/signal/__init__.py` and `webcompy/__init__.py`

## 3. Migrate internal framework code — Signal

- [ ] 3.1 Search for all `Signal(` direct constructor calls in `packages/webcompy/src/webcompy/` (excluding `_signal.py` itself and `_composable.py`)
  - Known sites: `_manager.py:22`, `_async_result.py:29-31`, `_composable.py:12` (use_counter demo)
- [ ] 3.2 For each call inside component setup context: replace with `use_state(lambda: value)` if transfer is needed
- [ ] 3.3 For each call outside component setup: replace with `Signal._create(value)` if no transfer needed

## 4. Migrate internal framework code — Computed

- [ ] 4.1 Search for all `Computed(` constructor calls in `packages/webcompy/src/webcompy/` (excluding `_computed.py` itself)
  - Known sites: `_manager.py:25`, `_reactive_scoped_style.py:117,118`
- [ ] 4.2 Replace with `use_computed(fn)` for user-facing derivations or `Computed._create(fn)` for internal use
- [ ] 4.3 Inside `_computed.py` itself: update `use_computed()` to use `Computed._create(fn)` internally; update `computed_property` to use `Computed._create()`

## 5. Update docs_app and examples

- [ ] 5.1 Search docs_app for `Signal(`, `Computed(`, `computed(` direct constructor usage
- [ ] 5.2 Replace all with `use_state()`, `use_computed()` equivalents
- [ ] 5.3 Update any documentation text that references `Signal()` or `computed()` as a creation API
- [ ] 5.4 Verify docs_app still renders correctly after migration

## 6. Sync specs

- [ ] 6.1 Run `openspec sync-specs feat-signal-composable` to apply delta spec changes to base specs
- [ ] 6.2 Manually update `openspec/specs/reactive/spec.md` — replace `Signal(value)` examples with `use_state()` and `Computed(fn)` examples with `use_computed()`
- [ ] 6.3 Manually update `openspec/specs/signal-value-transfer/spec.md` Purpose section to reflect `use_state()` registration model (no longer "auto-tracks self attributes")
- [ ] 6.4 Verify all spec scenarios use current API names

## 7. Tests

- [ ] 7.1 Write test: `Signal(0)` emits `DeprecationWarning` (not `UserWarning`)
- [ ] 7.2 Write test: `Computed(fn)` constructor emits `DeprecationWarning`
- [ ] 7.3 Write test: `computed(fn)` alias emits `DeprecationWarning`
- [ ] 7.4 Write test: `use_state()` and `use_computed()` do NOT emit any warning
- [ ] 7.5 Write test: `Signal._create()` and `Computed._create()` do NOT emit any warning
- [ ] 7.6 Write test: `Signal[T]` / `Computed[T]` type annotation usage does NOT emit warning
- [ ] 7.7 Run existing tests to verify no regression from internal migration

## 8. Lint, Type Check, and Validation

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 8.2 Run `uv run pyright` — verify deprecation annotations in type stubs
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `openspec validate refactor-signal-api-unification`
