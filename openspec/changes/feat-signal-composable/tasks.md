## 1. Signal._create() and deprecation warning

- [ ] 1.1 Add `Signal._create(cls, value) -> Signal[T]` classmethod in `packages/webcompy/src/webcompy/signal/_signal.py` using `object.__new__()` + `SignalBase.__init__()` to bypass `Signal.__init__`
- [ ] 1.2 Add `UserWarning` to `Signal.__init__()` — message: "Direct Signal() construction bypasses SSR transfer. Use signal(factory) instead."
- [ ] 1.3 Update all internal `Signal(value)` calls in framework code to use `Signal._create(value)` instead
- [ ] 1.4 Write unit tests: warning emitted on direct construction, no warning from `_create()`, type annotation still works

## 2. Context._transferable_signals

- [ ] 2.1 Add `_transferable_signals: dict[str, SignalBase[Any]]` field to `Context.__init__()` in `packages/webcompy/src/webcompy/components/_libs.py`
- [ ] 2.2 In `Component.__setup()` (`_component.py`), after `component_def(context)` returns, merge `context._transferable_signals` into `self.__signal_members__` via `self.__set_signal_member__(key, sig)` for each entry
- [ ] 2.3 Verify the merge also happens in the async re-extraction path (from `fix-async-component-active-context`)

## 3. signal() composable

- [ ] 3.1 Create `packages/webcompy/src/webcompy/signal/_composable.py` with `signal()` function using `@overload` for the two typed signatures
- [ ] 3.2 Implement argument resolution: `str` first arg → `(key, factory)`, callable first arg → `(auto_key, factory)`
- [ ] 3.3 Implement payload check: `inject(HYDRATION_SIGNAL_DATA_KEY, default=None)`, compute `component_id = generate_id(ctx._component_name)`, look up `payload[component_id][key]`
- [ ] 3.4 Implement factory-skip: if payload has value, `Signal._create(restored)` (skip factory); else `Signal._create(factory())`
- [ ] 3.5 Implement registration: `ctx._transferable_signals[key] = sig` when inside component context
- [ ] 3.6 Implement graceful degradation: when `ctx is None`, return `Signal._create(factory())` without registration
- [ ] 3.7 Implement `_auto_key()` helper using `inspect.currentframe()` + `dis.get_instructions()` with `file:line` fallback
- [ ] 3.8 Export `signal` from `webcompy/signal/__init__.py` and `webcompy/__init__.py`

## 4. Remove _restore_signals()

- [ ] 4.1 Remove `_restore_signals()` method from `Component` class in `_component.py`
- [ ] 4.2 Remove the `self._restore_signals()` call from `Component._render()`
- [ ] 4.3 Remove or update the `restore_signal_values()` import in `_component.py` (function may stay in `_restore.py` for potential future use but is no longer called from `_render()`)

## 5. Provide HYDRATION_SIGNAL_DATA_KEY in app.run()

- [ ] 5.1 Verify `HYDRATION_SIGNAL_DATA_KEY` exists in `packages/webcompy/src/webcompy/di/_keys.py`; add if missing
- [ ] 5.2 In `app.run()` (browser entry point), provide `HYDRATION_SIGNAL_DATA_KEY` with `payload.signals` in the root DI scope, alongside `HYDRATION_DATA_KEY`
- [ ] 5.3 Ensure both keys are provided **before** `AppDocumentRoot` creation (before any component setup)

## 6. Spike: PyScript inspect/dis compatibility

- [ ] 6.1 Write a minimal test that calls `inspect.currentframe()` and `dis.get_instructions()` inside a PyScript environment to verify they work
- [ ] 6.2 If they don't work, implement the `file:line` fallback and document the limitation
- [ ] 6.3 If `file:line` also doesn't work (e.g., `co_filename` differs), document the workaround (explicit keys required in PyScript)

## 7. Tests

- [ ] 7.1 Write test: `signal(lambda: 0)` returns `Signal[int]` with correct value on server
- [ ] 7.2 Write test: factory-skip during hydration — payload has value, factory is not called, Signal has restored value
- [ ] 7.3 Write test: factory runs during client-side navigation (no payload)
- [ ] 7.4 Write test: `signal("key", factory)` uses explicit key in payload
- [ ] 7.5 Write test: `signal()` outside component context — factory runs, no error, no registration
- [ ] 7.6 Write test: auto-key uniqueness for same-line calls (column disambiguation)
- [ ] 7.7 Write test: `Signal(0)` emits `UserWarning`, `Signal._create(0)` does not
- [ ] 7.8 Write test: `collect_transfer_data()` collects signals registered via `signal()` through `__signal_members__`
- [ ] 7.9 Write test: full round-trip — SSR creates signal, collects value → browser hydrates, factory skipped, value restored
- [ ] 7.10 Write test: type checking — `signal(0)` is a type error (pyright)
- [ ] 7.11 Run existing signal-value-transfer E2E tests to verify no regression

## 8. Lint, Type Check, and Validation

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 8.2 Run `uv run pyright` — verify `@overload` signatures pass
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `openspec validate feat-signal-composable`
