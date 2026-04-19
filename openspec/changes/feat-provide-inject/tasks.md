## 1. DI Core Infrastructure

- [x] 1.1 Create `webcompy/di/__init__.py` with public API exports (`provide`, `inject`, `InjectKey`, `DIScope`, `InjectionError`)
- [x] 1.2 Implement `InjectKey[T]` class in `webcompy/di/_key.py` — Generic with `__init__(name: str)`, unique `object()` identity, `__repr__` showing name, `__eq__`/`__hash__` based on identity
- [x] 1.3 Implement `InjectionError` exception in `webcompy/di/_exceptions.py` with key description in message
- [x] 1.4 Implement `DIScope` class in `webcompy/di/_scope.py` — `__init__(providers=None, parent=None)`, `provide(key, value)`, `inject(key, default=_MISSING)`, `dispose()`, `__enter__`/`__exit__`, parent chain traversal for resolution, `_active_di_scope` ContextVar management
- [x] 1.5 Implement module-level `provide(key, value)` function — delegates to `_active_di_scope.get().provide(key, value)` with lazy child scope creation
- [x] 1.6 Implement module-level `inject(key, default?)` function with `@overload` signatures for type inference — delegates to `_active_di_scope.get().inject(key, default)`, raises `InjectionError` if no active scope or key not found
- [x] 1.7 Add `DIScope` factory/lazy instantiation support — `provide(key, factory_fn)` where `callable(value)` triggers lazy init on first `inject()`

## 2. Component Integration

- [x] 2.1 Add `_active_di_scope` ContextVar to `webcompy/components/_hooks.py` (alongside existing `_active_component_context` and `_active_effect_scope`)
- [x] 2.2 Modify `Component.__setup` to inherit `_active_di_scope` and manage lazy child scope creation when `provide()` is called
- [x] 2.3 Add `Context.provide(key, value)` convenience method to `webcompy/components/_libs.py` — delegates to module-level `provide()`
- [x] 2.4 Modify `Component` destruction to dispose child DI scope (if one was created during setup)
- [x] 2.5 Ensure `_active_di_scope` is properly reset in `finally` blocks (matching existing ContextVar reset pattern)

## 3. App-Level DI Scope

- [x] 3.1 Add `di_scope` property to `WebComPyApp` that returns the root `DIScope`
- [x] 3.2 Add `provide(key, value)` method to `WebComPyApp` — delegates to `self.di_scope.provide(key, value)`
- [x] 3.3 Modify `AppDocumentRoot.__init__` to create the root `DIScope` and provide framework-internal services
- [x] 3.4 Set `_active_di_scope` to app scope before component tree rendering begins (in `AppDocumentRoot._render` or equivalent)

## 4. Framework-Internal DI Keys

- [x] 4.1 Create `webcompy/di/_keys.py` with internal key definitions: `_ROUTER_KEY`, `_COMPONENT_STORE_KEY`, `_HEAD_PROPS_KEY` (all `object()` instances)
- [x] 4.2 Create public DI keys: `RouterKey = InjectKey[Router]("webcompy-router")` for user-facing injection
- [x] 4.3 Provide Router into app scope from `AppDocumentRoot.__init__` using both internal key and public `RouterKey`

## 5. Router Singleton Migration

- [x] 5.1 Modify `RouterView` to resolve router via `inject(_ROUTER_KEY)` instead of `_instance`/`_router` class variables
- [x] 5.2 Modify `TypedRouterLink` to resolve router via `inject(_ROUTER_KEY)` instead of `_router` class variable
- [x] 5.3 Remove `Router._instance` class variable and related singleton logic
- [x] 5.4 Remove `RouterView.__set_router__()` method (no longer needed — router is in DI scope)
- [x] 5.5 Update `AppDocumentRoot.__init__` — remove `RouterView.__set_router__()` and `TypedRouterLink.__set_router__()` calls, replace with DI provides

## 6. Head Props Migration

- [x] 6.1 Create `HeadProps` data class (or use existing structure) to hold `title: Signal[str]` and `head_meta: Signal[dict]`
- [x] 6.2 Provide `HeadProps` into app scope from `AppDocumentRoot.__init__` using `_HEAD_PROPS_KEY`
- [x] 6.3 Modify `Component._set_title()` and `Component._set_meta()` to access head props via `inject(_HEAD_PROPS_KEY)`
- [x] 6.4 Remove `Component._head_props` ClassVar

## 7. ComponentStore Migration

- [x] 7.1 Add bridge: `_default_component_store` module-level singleton as fallback for pre-DI access
- [x] 7.2 Provide `ComponentStore` into app scope from `AppDocumentRoot.__init__` using `_COMPONENT_STORE_KEY`
- [x] 7.3 Modify `ComponentGenerator.__init__` to access `ComponentStore` via `inject(_COMPONENT_STORE_KEY, default=_default_component_store)` (fallback for import-time registration)
- [x] 7.4 Modify `AppDocumentRoot.style` property to access `ComponentStore` via `inject(_COMPONENT_STORE_KEY)`
- [x] 7.5 Remove `@_instantiate` decorator from `ComponentStore` once all access is via DI

## 8. Composables

- [x] 8.1 Implement `useRouter()` composable in `webcompy/router/` — `return inject(RouterKey)`
- [x] 8.2 Export `useRouter` from `webcompy/router/__init__.py`
- [x] 8.3 Verify `useAsyncResult` and `useAsync` still work without changes (they don't directly use singletons)

## 9. Testing

- [x] 9.1 Add unit tests for `InjectKey` — identity uniqueness, repr, Generic type annotation
- [x] 9.2 Add unit tests for `DIScope` — creation, parent chain resolution, provide/inject, child scope lazy creation, dispose, context manager protocol
- [x] 9.3 Add unit tests for `inject()` — resolution, `InjectionError` on missing key, `default=` parameter, calling outside scope
- [x] 9.4 Add unit tests for `provide()` — lazy child scope creation in component setup, multiple provide calls in same scope, overwrite behavior
- [x] 9.5 Add integration test: component provides value, descendant injects it
- [x] 9.6 Add integration test: app provides value, deeply nested component injects it
- [x] 9.7 Add test: `DIScope` as context manager for test isolation (mock injection)
- [x] 9.8 Add test: multiple `WebComPyApp` instances coexist without DI interference
- [x] 9.9 Update existing router tests — remove `Router._instance = None` workarounds, use DI scope fixtures instead
- [x] 9.10 Update `tests/conftest.py` — replace singleton reset fixtures with DI scope fixtures

## 10. Public API and Exports

- [x] 10.1 Export `provide`, `inject`, `InjectKey`, `DIScope`, `InjectionError` from `webcompy/__init__.py`
- [x] 10.2 Export `RouterKey` from `webcompy/router/__init__.py`
- [x] 10.3 Update `webcompy/py.typed` and `.pyi` stubs if needed
- [x] 10.4 Run `uv run ruff check .` and `uv run ruff format .` — fix any lint/format issues
- [x] 10.5 Run `uv run pyright` — fix any type errors
- [x] 10.6 Run `uv run python -m pytest tests/ --tb=short` — ensure all tests pass