## 1. Escalate Signal() deprecation

- [ ] 1.1 In `packages/webcompy/src/webcompy/signal/_signal.py`, change `Signal.__init__` warning from `UserWarning` to `DeprecationWarning`; update message to "Signal() is deprecated. Use use_state(factory) instead."
- [ ] 1.2 Update type stubs (`.pyi` files) to mark `Signal.__init__` as `@deprecated`
- [ ] 1.3 Update existing tests that expected `UserWarning` to expect `DeprecationWarning`

## 2. Deprecate Computed() class constructor and rename computed() to use_computed()

- [ ] 2.1 Add `DeprecationWarning` to `Computed.__init__` in `packages/webcompy/src/webcompy/signal/_computed.py` — message: "Computed() is deprecated. Use use_computed(factory) instead."
- [ ] 2.2 Add `Computed._create(fn)` classmethod as internal bypass (mirrors `Signal._create()`)
- [ ] 2.3 Implement `use_computed()` function in `_computed.py` (more than a rename — requires new functionality):
  - [ ] 2.3a Implement `use_computed()` with `@overload` typing (two signatures: auto-key `use_computed(factory: Callable[[], T]) -> Computed[T]` and explicit-key `use_computed(key: str, factory: Callable[[], T]) -> Computed[T]`)
  - [ ] 2.3b Implement auto-key generation by reusing the `_auto_key()` helper from Phase 2 (`_composable.py`)
  - [ ] 2.3c Use `Computed._create(fn)` internally to avoid `DeprecationWarning`
  - [ ] 2.3d Ensure `use_computed()` does NOT participate in factory-skip transfer (no registration with `__signal_members__`)
- [ ] 2.4 Keep `computed` as a deprecated alias — implement as a **wrapper function** (NOT a simple assignment) that emits `DeprecationWarning` directing to `use_computed()`, then delegates to `use_computed(fn)`
- [ ] 2.5 Update type stubs to mark `Computed.__init__` as `@deprecated`
- [ ] 2.6 Export `use_computed` from `webcompy/signal/__init__.py` and `webcompy/__init__.py`

## 3. Migrate internal framework code and unit tests — Signal

- [ ] 3.1 Search for all `Signal(` direct constructor calls in `packages/webcompy/src/webcompy/` and `tests/` (excluding `_signal.py` itself and tests that explicitly assert the deprecation warning)
  - Known framework sites: `_manager.py:22`, `_async_result.py:29-31`, `_composable.py:12` (use_counter demo, already fixed in Phase 2 task 1.6)
  - Known test scope: existing direct `Signal(` calls in `tests/` SHALL be migrated except tests that intentionally verify direct-constructor deprecation behavior
- [ ] 3.2 For each call inside component setup context (user-facing state that should transfer): replace with `use_state(lambda: value)`
- [ ] 3.3 For each call in framework infrastructure (not user-facing, no transfer needed): replace with `Signal._create(value)`
- [ ] 3.4 For existing unit tests that exercise low-level signal, element, router, or effect infrastructure directly: replace setup values with `Signal._create(value)` unless the test is specifically validating the public composable API
- [ ] 3.5 Verify the existing test suite does not emit bulk `DeprecationWarning` output from migrated `Signal(` calls

## 4. Migrate internal framework code and unit tests — Computed

- [ ] 4.1 Search for all `Computed(` constructor calls in `packages/webcompy/src/webcompy/` and `tests/` (excluding the `Computed` class constructor itself and tests that explicitly assert the deprecation warning)
  - Known framework sites: `_manager.py:25`, `_reactive_scoped_style.py:117,118`, `_async_result.py:33-36`, `_computed.py:69,77`
  - Known test scope: existing direct `Computed(` calls in `tests/` SHALL be migrated except tests that intentionally verify direct-constructor deprecation behavior
- [ ] 4.2 For each call, apply the following criteria:
  - **Inside a `@define_component` setup function** (user-facing derivation that depends on reactive state): replace with `use_computed(fn)`
  - **Framework infrastructure** (not user-facing, not inside a component setup): replace with `Computed._create(fn)`
  - Known sites: `_manager.py:25` (framework infra → `Computed._create`), `_reactive_scoped_style.py:117,118` (framework infra → `Computed._create`), `_async_result.py:33-36` (`AsyncResult.is_pending`, `is_loading`, `is_success`, `is_error` instance attributes → `Computed._create`)
- [ ] 4.3 Inside `_computed.py` itself: update `use_computed()` to use `Computed._create(fn)` internally; update `computed_property` to use `Computed._create()`; keep `computed()` as a deprecating wrapper that delegates to `use_computed()`
- [ ] 4.4 For existing unit tests that exercise low-level computed behavior directly: replace setup values with `Computed._create(fn)` unless the test is specifically validating the public composable API
- [ ] 4.5 Verify the existing test suite does not emit bulk `DeprecationWarning` output from migrated `Computed(` calls

## 5. Update docs_app, templates, and examples

- [ ] 5.1 Search docs_app and project templates for `Signal(`, `Computed(`, `computed(` direct constructor/function usage
  - Known docs_app sites: `docs_app/components/navigation.py`, `docs_app/components/demo_display.py`, `docs_app/components/theme_toggle.py`, `docs_app/static/_demos/todo/app.py`, `docs_app/static/_demos/fetch_sample/app.py`, `docs_app/static/_demos/matplotlib_sample/app.py`, `docs_app/static/_demos/fizzbuzz/app.py`
  - Known template sites: `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/input.py`, `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py`
- [ ] 5.2 Replace all application/demo state with `use_state()` and derived values with `use_computed()` equivalents
- [ ] 5.3 Update documentation text and code snippets that reference `Signal()` or `computed()` as a creation API, including docs_app content and package docstrings
- [ ] 5.4 Verify docs_app still renders correctly after migration
- [ ] 5.5 Verify `webcompy init` templates no longer introduce deprecated `Signal()` or `computed()` usage

## 6. Sync specs

- [ ] 6.1 Run `openspec sync-specs feat-signal-composable` AND `openspec sync-specs refactor-signal-api-unification` to apply all delta spec changes to base specs
- [ ] 6.2 Manually update `openspec/specs/reactive/spec.md` (188 lines, 20+ scenarios with deprecated API patterns):
  - [ ] 6.2a Manually identify all affected scenarios by reading the file and noting every `Signal(`, `Computed(`, `signal(`, `computed(` occurrence (grep is a helper, not authoritative — manually verify each match is a construction site, not a type annotation or prose reference)
  - [ ] 6.2b For each identified scenario: replace `Signal(value)` with `use_state(lambda: value)` (user-facing) or `Signal._create(value)` (internal/framework), and replace `Computed(fn)` with `use_computed(fn)` (user-facing) or `Computed._create(fn)` (internal)
  - [ ] 6.2c Manually review each scenario after update to verify the replacement did not break prose flow or type annotation semantics
  - [ ] 6.2d Verify no scenario text references the deprecated constructor API after update (manual review pass, not grep)
- [ ] 6.2e Manually update `openspec/specs/composables/spec.md` — the "Basic composable with auto-cleanup" scenario (L165) uses `Signal(initial)` which will emit `DeprecationWarning` after Phase 3; replace with `use_state(lambda: initial)` or `Signal._create(initial)`
- [ ] 6.3 Manually update `openspec/specs/signal-value-transfer/spec.md` — replace Purpose section's "auto-tracks every Signal instance assigned to self" with composable registration model; replace all `self.X = Reactive()` / `self.X = Signal()` patterns with `use_state()` equivalent; update restoration model from `_restore_signals()` to factory-skip
- [ ] 6.4 Verify all spec scenarios use current API names across all synced base specs

## 7. Tests

- [ ] 7.1 Write test: `Signal(0)` emits `DeprecationWarning` (not `UserWarning`)
- [ ] 7.2 Write test: `Computed(fn)` constructor emits `DeprecationWarning`
- [ ] 7.3 Write test: `computed(fn)` alias emits `DeprecationWarning`
- [ ] 7.4 Write test: `use_state()` and `use_computed()` do NOT emit any warning
- [ ] 7.5 Write test: `Signal._create()` and `Computed._create()` do NOT emit any warning
- [ ] 7.6 Write test: `Signal[T]` / `Computed[T]` type annotation usage does NOT emit warning
- [ ] 7.7 Write test: `use_async_result()`, `use_theme()`, and `use_counter()` composables do NOT emit `DeprecationWarning` (they use `Signal._create()` / `Computed._create()` internally)
- [ ] 7.8 Run existing tests to verify no regression from internal/test migration and no bulk `DeprecationWarning` output remains outside tests that intentionally assert deprecation behavior

## 8. Lint, Type Check, and Validation

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 8.2 Run `uv run pyright` — verify deprecation annotations in type stubs
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `openspec validate refactor-signal-api-unification`
