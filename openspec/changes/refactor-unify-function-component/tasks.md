## 1. ContextVar Infrastructure

- [ ] 1.1 Create `webcompy/components/_hooks.py` with `_active_component_context: ContextVar[Context]` and the three standalone lifecycle decorators (`on_before_rendering`, `on_after_rendering`, `on_before_destroy`) that read the ContextVar and delegate to the active Context's lifecycle methods. Raise `LookupError` with a clear message when called outside a component setup.
- [ ] 1.2 Modify `webcompy/components/_component.py` `__setup` (function-style branch) to set/reset the ContextVar around the `component_def(context)` call using token-based `set`/`reset` so that nested component instantiation preserves the parent context.
- [ ] 1.3 Export `_active_component_context` from `webcompy/components/__init__.py` (internal, underscored) and the three standalone decorators (public API).
- [ ] 1.4 Add unit tests for standalone lifecycle decorators: registration fires correctly when ContextVar is set, `LookupError` raised when called outside context, and nested component instantiation restores parent context.

## 2. AsyncResult Core

- [ ] 2.1 Create `webcompy/aio/_async_result.py` with `AsyncState` enum (`PENDING`, `LOADING`, `SUCCESS`, `ERROR`), `AsyncResult[T]` class with `state: Reactive[AsyncState]`, `data: Reactive[T | None]`, `error: Reactive[Exception | None]`, computed predicates (`is_pending`, `is_loading`, `is_success`, `is_error`), `refetch(*_: Any) -> None`, and internal `_execute` coroutine. `AsyncResult` must NOT depend on ContextVar or component lifecycle.
- [ ] 2.2 Implement SWR-style data preservation: `refetch` sets state to `LOADING` but does NOT reset `data` to `None`. On success, `data` gets the new value. On error, `data` retains the last successful value. If `default` is provided, initial `data` is `default` (never `None` unless `default` is None).
- [ ] 2.3 Export `AsyncState` and `AsyncResult` from `webcompy/aio/__init__.py`.
- [ ] 2.4 Add unit tests for `AsyncResult`: state transitions (PENDING → LOADING → SUCCESS, PENDING → LOADING → ERROR, refetch cycles), SWR data preservation, `default` parameter behavior, computed predicates, and error retention of last successful data. Use `asyncio.run()` for server-side async execution.

## 3. Composable Functions

- [ ] 3.1 Implement `useAsyncResult(func, *, default=None, immediate=True, watch=())` in `webcompy/aio/_async_result.py`. It creates an `AsyncResult`, registers `on_after_rendering(result.refetch)` if `immediate=True`, registers `on_after_updating` callbacks for each Reactive in `watch`, and registers `on_before_destroy` for cleanup of watch callbacks.
- [ ] 3.2 Implement `useAsync(func)` in `webcompy/aio/_async_result.py`. It wraps `AsyncWrapper()(func)` and registers the result via `on_after_rendering`. Returns `None`. Uses ContextVar for lifecycle registration.
- [ ] 3.3 Export `useAsyncResult` and `useAsync` from `webcompy/aio/__init__.py`.
- [ ] 3.4 Add unit tests for `useAsyncResult`: verify `on_after_rendering` registration when `immediate=True`, no registration when `immediate=False`, `watch` reactive triggers `refetch` on value change, and `on_before_destroy` cleans up watch callbacks. Use the `with_component_context` test helper.
- [ ] 3.5 Add unit tests for `useAsync`: verify it registers with `on_after_rendering` and that the async function is called when the hook fires.

## 4. Component API Updates

- [ ] 4.1 Update `webcompy/components/__init__.py` to export `on_before_rendering`, `on_after_rendering`, and `on_before_destroy` from `_hooks.py`.
- [ ] 4.2 Add `DeprecationWarning` to `@component_class` decorator in `webcompy/components/_generator.py` and to class-style decorators (`@component_template`, `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) in `webcompy/components/_decorators.py`. Warnings should use `warnings.warn(..., DeprecationWarning, stacklevel=2)`.
- [ ] 4.3 Add `DeprecationWarning` to `AsyncComputed.__init__` in `webcompy/aio/_aio.py` and `AsyncWrapper.__call__` in `webcompy/aio/_aio.py`.
- [ ] 4.4 Add `DeprecationWarning` to `ClassStyleComponentContenxt` protocol and `ComponentAbstract.__init_subclass__` in `webcompy/components/_abstract.py` (since `__new__` prohibition is class-style-specific).

## 5. Test Infrastructure

- [ ] 5.1 Create `tests/conftest.py` addition: `with_component_context` helper function that sets/resets `_active_component_context` around a setup function call and returns the `Context` object plus lifecycle hooks dict for test verification.
- [ ] 5.2 Add `tests/test_async_result.py` with `TestAsyncResultState`, `TestAsyncResultSWR`, `TestAsyncResultDefault`, and `TestAsyncResultWatch` test classes covering all Level 1 (pure state machine) scenarios from the specs.
- [ ] 5.3 Add `tests/test_hooks.py` with `TestStandaloneLifecycleHooks` (registration, LookupError, nesting) and `TestComposableIntegration` (useAsyncResult/useAsync hook registration with `with_component_context`).

## 6. Documentation and Migration

- [ ] 6.1 Update `README.md` code examples to use standalone lifecycle decorators and `useAsyncResult` instead of `context.on_xxx()` and `@AsyncWrapper()`.
- [ ] 6.2 Add a migration guide comment (not code comment, but docs page or CHANGELOG entry) explaining how to convert class-style components to function-style and how to replace `@AsyncWrapper()` + `context.on_after_rendering` with `useAsyncResult`/`useAsync`.
- [ ] 6.3 Run `uv run ruff check .` and `uv run ruff format .` and `uv run pyright` to ensure all new code passes lint, format, and type checks.