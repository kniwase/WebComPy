## 1. Rename computed() to use_computed() in core signal module

- [x] 1.1 Rename `computed(func)` to `use_computed(func)` in `packages/webcompy/src/webcompy/signal/_computed.py`
- [x] 1.2 Update `packages/webcompy/src/webcompy/signal/__init__.py` to export `use_computed`
- [x] 1.3 Add `use_computed` to `packages/webcompy/src/webcompy/__init__.py`

## 2. Update framework internals to use use_computed

- [x] 2.1 Replace all `computed` imports and usages in `packages/webcompy/src/webcompy/`
- [x] 2.2 Update `packages/webcompy-server/src/`, `packages/webcompy-cli/src/`, `packages/webcompy-testing/src/`

## 3. Update docs_app, CLI templates, and E2E apps

- [x] 3.1 Replace `computed(` usage in `docs_app/` and CLI templates
- [x] 3.2 Replace `computed(` usage in `e2e/` apps
- [x] 3.3 Verify docs_app static site generation

## 4. Update unit tests

- [x] 4.1 Replace `computed(` usage in `tests/` (excluding `computed_property`)
- [x] 4.2 Add `tests/test_use_computed.py` covering imports, error cases, and transfer behavior

## 5. Update base specs and design docs

- [x] 5.1 Sync `openspec/specs/reactive/spec.md`, `composables/spec.md`, `signal-value-transfer/spec.md`, `app-styles/spec.md`
- [x] 5.2 Update `design.md` and `proposal.md`

## 6. Remove _Computed alias and unify signal import paths

- [x] 6.1 Remove `Computed as _Computed` alias in `app/styles.py`
- [x] 6.2 Unify `SignalBase`, `Computed`, `computed_property` imports to `from webcompy.signal import ...`

## 7. Complete remaining framework import unification

- [x] 7.1 Unify remaining imports in `ports/_history.py`, `elements/_head.py`, `elements/types/_element.py`, `components/_libs.py`, `components/_hooks.py`, `components/_context_manager.py`

## 8. Extract shared _resolve_factory helper

- [x] 8.1 Add `_resolve_factory()` to `packages/webcompy/src/webcompy/signal/_composable.py`
- [x] 8.2 Refactor `_resolve_args()` to use `_resolve_factory()`
- [x] 8.3 Use `_resolve_factory()` for `use_computed()` argument validation

## 9. Fix internal docstring and constructor examples

- [x] 9.1 Fix `reactive_block()` docstring to use `Computed(...)`
- [x] 9.2 Use `Computed()` directly in `MultiLineTextElement.__init__`

## 10. Improve error message consistency

- [x] 10.1 Include `func_name` in `_resolve_factory()` error messages
- [x] 10.2 Fix `_resolve_args()` `func_name` formatting
- [x] 10.3 Add `match` assertions to error tests

## 11. Remove unused key parameter from use_computed()

- [x] 11.1 Simplify `use_computed()` to single `Callable[[], T]` argument
- [x] 11.2 Remove `@overload` and `_resolve_factory` usage from `_computed.py`
- [x] 11.3 Update delta spec and tests accordingly

## 12. Update README

- [x] 12.1 Update `README.md` and `README.ja.md` examples to use `use_state` and `use_computed`

## 13. Run validation

- [x] 13.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [x] 13.2 Run `uv run pyright`
- [x] 13.3 Run `uv run python -m pytest tests/ --tb=short`
- [x] 13.4 Run `uv run python -m webcompy generate`
- [x] 13.5 Run `openspec validate refactor-signal-api-unification`
