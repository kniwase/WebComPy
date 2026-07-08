## 1. _create() classmethods and deprecation warnings

- [ ] 1.1 Add `Signal._create(cls, value) -> Signal[T]` classmethod in `packages/webcompy/src/webcompy/signal/_signal.py` using `object.__new__()` + `SignalBase.__init__()` to bypass `Signal.__init__`
- [ ] 1.2 Add `ReactiveList._create(cls, value) -> ReactiveList[V]` classmethod in `packages/webcompy/src/webcompy/signal/_list.py` using the same bypass pattern
- [ ] 1.3 Add `ReactiveDict._create(cls, value) -> ReactiveDict[K, V]` classmethod in `packages/webcompy/src/webcompy/signal/_dict.py` using the same bypass pattern
- [ ] 1.4 Add `UserWarning` to `Signal.__init__()` — message: "Direct Signal() construction bypasses SSR transfer. Use use_state(factory) instead."
- [ ] 1.5 Update all internal `Signal(value)` calls in framework code to use `Signal._create(value)` instead
- [ ] 1.6 Write unit tests: warning emitted on direct construction, no warning from `_create()`, type annotation still works

## 2. Context._transferable_signals

- [ ] 2.1 Add `_transferable_signals: dict[str, SignalBase[Any]]` field to `Context.__init__()` in `packages/webcompy/src/webcompy/components/_libs.py`
- [ ] 2.2 In `Component.__setup()` (`_component.py`), after `component_def(context)` returns, merge `context._transferable_signals` into `self.__signal_members__` via `self.__set_signal_member__(key, sig)` for each entry
- [ ] 2.3 Verify the merge also happens in the async re-extraction path (from `fix-async-component-active-context`)

## 3. use_state() composable

- [ ] 3.1 Create `use_state()` function in `packages/webcompy/src/webcompy/signal/_composable.py` with `@overload` for the two typed signatures
- [ ] 3.2 Implement argument resolution: `str` first arg → `(key, factory)`, callable first arg → `(auto_key, factory)`
- [ ] 3.3 Implement payload check: `inject(HYDRATION_SIGNAL_DATA_KEY, default=None)`, compute `component_id = generate_id(ctx._component_name)`, look up `payload[component_id][key]`
- [ ] 3.4 Implement factory-skip: if payload has value, `Signal._create(restored)` (skip factory); else `Signal._create(factory())`
- [ ] 3.5 Implement registration: `ctx._transferable_signals[key] = sig` when inside component context
- [ ] 3.6 Implement graceful degradation: when `ctx is None`, return `Signal._create(factory())` without registration

## 4. use_reactive_list() and use_reactive_dict() composables

- [ ] 4.1 Create `use_reactive_list()` function in `_composable.py` with `@overload` typing — identical factory-skip logic to `use_state()` but creates `ReactiveList._create()` instead of `Signal._create()`
- [ ] 4.2 Create `use_reactive_dict()` function in `_composable.py` with `@overload` typing — identical factory-skip logic but creates `ReactiveDict._create()`
- [ ] 4.3 Both composables SHALL register in `ctx._transferable_signals` when inside component context
- [ ] 4.4 Both composables SHALL degrade gracefully outside component context (factory runs, no registration)

## 5. Auto-key generation

- [ ] 5.1 Implement `_auto_key()` helper in `_composable.py` using `inspect.currentframe()` + `dis.get_instructions()` with `file:line` fallback
- [ ] 5.2 Verify the helper works for all three composables (`use_state`, `use_reactive_list`, `use_reactive_dict`)

## 6. Exports

- [ ] 6.1 Export `use_state`, `use_reactive_list`, `use_reactive_dict` from `webcompy/signal/__init__.py`
- [ ] 6.2 Re-export from `webcompy/__init__.py`

## 7. Remove _restore_signals()

- [ ] 7.1 Remove `_restore_signals()` method from `Component` class in `_component.py`
- [ ] 7.2 Remove the `self._restore_signals()` call from `Component._render()`
- [ ] 7.3 Remove or update the `restore_signal_values()` import in `_component.py` (function may stay in `_restore.py` for potential future use but is no longer called from `_render()`)

## 8. Provide HYDRATION_SIGNAL_DATA_KEY in app.run()

- [ ] 8.1 Verify `HYDRATION_SIGNAL_DATA_KEY` exists in `packages/webcompy/src/webcompy/di/_keys.py`; add if missing
- [ ] 8.2 In `app.run()` (browser entry point), provide `HYDRATION_SIGNAL_DATA_KEY` with `payload.signals` in the root DI scope, alongside `HYDRATION_DATA_KEY`
- [ ] 8.3 Ensure both keys are provided **before** `AppDocumentRoot` creation (before any component setup)

## 9. Spike: PyScript inspect/dis compatibility

- [ ] 9.1 Write a minimal test that calls `inspect.currentframe()` and `dis.get_instructions()` inside a PyScript environment to verify they work
- [ ] 9.2 If they don't work, implement the `file:line` fallback and document the limitation
- [ ] 9.3 If `file:line` also doesn't work (e.g., `co_filename` differs), document the workaround (explicit keys required in PyScript)

## 10. Tests

- [ ] 10.1 Write test: `use_state(lambda: 0)` returns `Signal[int]` with correct value on server
- [ ] 10.2 Write test: factory-skip during hydration — payload has value, factory is not called, Signal has restored value
- [ ] 10.3 Write test: factory runs during client-side navigation (no payload)
- [ ] 10.4 Write test: `use_state("key", factory)` uses explicit key in payload
- [ ] 10.5 Write test: `use_state()` outside component context — factory runs, no error, no registration
- [ ] 10.6 Write test: auto-key uniqueness for same-line calls (column disambiguation)
- [ ] 10.7 Write test: `Signal(0)` emits `UserWarning`, `Signal._create(0)` does not
- [ ] 10.8 Write test: `use_reactive_list(lambda: [1,2,3])` returns `ReactiveList` with working mutation methods
- [ ] 10.9 Write test: `use_reactive_list()` factory-skip restores list value during hydration
- [ ] 10.10 Write test: `use_reactive_dict(lambda: {"a": 1})` returns `ReactiveDict` with working mutation methods
- [ ] 10.11 Write test: `use_reactive_dict()` factory-skip restores dict value during hydration
- [ ] 10.12 Write test: `collect_transfer_data()` collects signals registered via composables through `__signal_members__`
- [ ] 10.13 Write test: full round-trip — SSR creates signal, collects value → browser hydrates, factory skipped, value restored
- [ ] 10.14 Run existing signal-value-transfer E2E tests to verify no regression

## 11. Lint, Type Check, and Validation

- [ ] 11.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 11.2 Run `uv run pyright` — verify `@overload` signatures pass
- [ ] 11.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 11.4 Run `openspec validate feat-signal-composable`
