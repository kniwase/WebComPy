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
  - Known sites: `_manager.py:22`, `_async_result.py:29-31`, `_composable.py:12` (use_counter demo, already fixed in Phase 2 task 1.6)
- [ ] 3.2 For each call inside component setup context (user-facing state that should transfer): replace with `use_state(lambda: value)`
- [ ] 3.3 For each call in framework infrastructure (not user-facing, no transfer needed): replace with `Signal._create(value)`

## 4. Migrate internal framework code — Computed

- [ ] 4.1 Search for all `Computed(` constructor calls in `packages/webcompy/src/webcompy/` (excluding `_computed.py` itself)
  - Known sites: `_manager.py:25`, `_reactive_scoped_style.py:117,118`
- [ ] 4.2 For each call, apply the following criteria:
  - **Inside a `@define_component` setup function** (user-facing derivation that depends on reactive state): replace with `use_computed(fn)`
  - **Framework infrastructure** (not user-facing, not inside a component setup): replace with `Computed._create(fn)`
  - Known sites: `_manager.py:25` (framework infra → `Computed._create`), `_reactive_scoped_style.py:117,118` (framework infra → `Computed._create`)
- [ ] 4.3 Inside `_computed.py` itself: update `use_computed()` to use `Computed._create(fn)` internally; update `computed_property` to use `Computed._create()`

## 5. Update docs_app and examples

- [ ] 5.1 Search docs_app for `Signal(`, `Computed(`, `computed(` direct constructor usage
- [ ] 5.2 Replace all with `use_state()`, `use_computed()` equivalents
- [ ] 5.3 Update any documentation text that references `Signal()` or `computed()` as a creation API
- [ ] 5.4 Verify docs_app still renders correctly after migration

## 6. Sync specs

- [ ] 6.1 Run `openspec sync-specs feat-signal-composable` AND `openspec sync-specs refactor-signal-api-unification` to apply all delta spec changes to base specs
- [ ] 6.2 Manually update `openspec/specs/reactive/spec.md` (188 lines, 20+ scenarios with deprecated API patterns):
  - [ ] 6.2a Grep for all `Signal(`, `Computed(`, `signal(`, `computed(` occurrences in the file; count and list affected scenarios
  - [ ] 6.2b Replace `Signal(value)` examples with `use_state(lambda: value)` (or `Signal._create(value)` for internal/framework examples)
  - [ ] 6.2c Replace `Computed(fn)` examples with `use_computed(fn)` (or `Computed._create(fn)` for internal examples)
  - [ ] 6.2d Verify no scenario text references the deprecated constructor API after update
- [ ] 6.3 Manually update `openspec/specs/signal-value-transfer/spec.md` — replace Purpose section's "auto-tracks every Signal instance assigned to self" with composable registration model; replace all `self.X = Reactive()` / `self.X = Signal()` patterns with `use_state()` equivalent; update restoration model from `_restore_signals()` to factory-skip
- [ ] 6.4 Verify all spec scenarios use current API names across all synced base specs

## 7. Tests

- [ ] 7.1 Write test: `Signal(0)` emits `DeprecationWarning` (not `UserWarning`)
- [ ] 7.2 Write test: `Computed(fn)` constructor emits `DeprecationWarning`
- [ ] 7.3 Write test: `computed(fn)` alias emits `DeprecationWarning`
- [ ] 7.4 Write test: `use_state()` and `use_computed()` do NOT emit any warning
- [ ] 7.5 Write test: `Signal._create()` and `Computed._create()` do NOT emit any warning
- [ ] 7.6 Write test: `Signal[T]` / `Computed[T]` type annotation usage does NOT emit warning
- [ ] 7.7 Write test: `use_async_result()` and `use_theme()` composables do NOT emit `DeprecationWarning` (they use `Signal._create()` / `Computed._create()` internally)
- [ ] 7.8 Run existing tests to verify no regression from internal migration

## 8. Lint, Type Check, and Validation

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 8.2 Run `uv run pyright` — verify deprecation annotations in type stubs
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `openspec validate refactor-signal-api-unification`
