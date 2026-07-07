## 1. Escalate Signal() deprecation

- [ ] 1.1 In `packages/webcompy/src/webcompy/signal/_signal.py`, change `Signal.__init__` warning from `UserWarning` to `DeprecationWarning`; update message to "Signal() is deprecated. Use signal(factory) instead."
- [ ] 1.2 Update type stubs (`.pyi` files) to mark `Signal.__init__` as `@deprecated`
- [ ] 1.3 Update existing tests that expected `UserWarning` to expect `DeprecationWarning`

## 2. Remove or deprecate Reactive alias

- [ ] 2.1 Search for `Reactive` in `packages/webcompy/src/webcompy/signal/__init__.py` and all source files — determine if it's an alias for `Signal`
- [ ] 2.2 If `Reactive` is an alias: add `DeprecationWarning` on import (via module `__getattr__` or wrapper) directing users to `signal()` / `Signal[T]`
- [ ] 2.3 If `Reactive` is a separate class: add `DeprecationWarning` to its `__init__`
- [ ] 2.4 Migrate all internal framework code from `Reactive` to `Signal` (for types) or `signal()` (for creation)
- [ ] 2.5 Update `__init__.py` exports — keep `Reactive` importable but deprecated

## 3. Deprecate Computed() class constructor

- [ ] 3.1 Check if `Computed(fn)` is callable as a separate class constructor (distinct from `computed(fn)`)
- [ ] 3.2 If yes: add `DeprecationWarning` to `Computed.__init__` directing users to `computed(fn)`
- [ ] 3.3 Migrate all internal framework code from `Computed(fn)` to `computed(fn)`
- [ ] 3.4 Update type stubs to mark `Computed.__init__` as `@deprecated`

## 4. Migrate internal framework code

- [ ] 4.1 Search for all `Signal(` direct constructor calls in `packages/webcompy/src/webcompy/` (excluding `_signal.py` itself and `_composable.py`)
- [ ] 4.2 For each call inside component setup context: replace with `signal(lambda: value)` if transfer is needed
- [ ] 4.3 For each call outside component setup: replace with `Signal._create(value)` if no transfer needed
- [ ] 4.4 Search for all `Reactive(` calls and migrate similarly
- [ ] 4.5 Search for all `Computed(` constructor calls and replace with `computed(fn)` or `Computed._create(fn)` if internal

## 5. Update docs_app and examples

- [ ] 5.1 Search docs_app for `Signal(`, `Reactive(`, `Computed(` direct constructor usage
- [ ] 5.2 Replace all with `signal()`, `computed()` equivalents
- [ ] 5.3 Update any documentation text that references `Signal()` as a creation API
- [ ] 5.4 Verify docs_app still renders correctly after migration

## 6. Conditional: ReactiveList/ReactiveDict deprecation (if Phase 3a recommends)

- [ ] 6.1 Check Phase 3a (`investigate-reactive-collections`) recommendation
- [ ] 6.2 If Deprecate: add `DeprecationWarning` to `ReactiveList.__init__` and `ReactiveDict.__init__` with migration message
- [ ] 6.3 If Retain: skip this section
- [ ] 6.4 If Partial Deprecate: add warnings only to the features being deprecated

## 7. Tests

- [ ] 7.1 Write test: `Signal(0)` emits `DeprecationWarning` (not `UserWarning`)
- [ ] 7.2 Write test: `Reactive` import/usage emits `DeprecationWarning` (if alias exists)
- [ ] 7.3 Write test: `Computed(fn)` constructor emits `DeprecationWarning` (if separate from `computed()`)
- [ ] 7.4 Write test: `signal()` and `computed()` do NOT emit any warning
- [ ] 7.5 Write test: `Signal._create()` does NOT emit any warning
- [ ] 7.6 Write test: `Signal[T]` type annotation usage does NOT emit warning
- [ ] 7.7 Run existing tests to verify no regression from internal migration

## 8. Lint, Type Check, and Validation

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 8.2 Run `uv run pyright` — verify deprecation annotations in type stubs
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `openspec validate refactor-signal-api-unification`
