## Why

WebComPy relies on multiple global singletons (`Router._instance`, `RouterView._router`, `Component._head_props`, `ComponentStore`) to share state across the component tree. This makes testing difficult (requiring explicit singleton resets), prevents multiple applications from coexisting on the same page, and forces shared state to flow through props or globals — there is no mechanism for subtree-scoped dependency injection. A provide/inject DI system will eliminate these singletons, enable test isolation, support multi-app scenarios, and give developers a standard way to share state across the component tree without prop drilling.

## What Changes

- Add a `provide(key, value)` / `inject(key, default?)` DI system using ContextVar-based scope chaining
- Introduce `InjectKey[T]` for type-safe token keys (complementing class-type keys)
- Add `DIScope` class for explicit scope creation, supporting standalone usage and test overrides
- Integrate DI scope with `Component.__setup` — child components inherit parent scopes; `provide()` calls lazily create child scopes
- Replace `Router._instance`, `RouterView._router`, `TypedRouterLink._router`, `Component._head_props`, and `ComponentStore` singleton with DI-provided values
- Add `useRouter()` composable as a typed inject wrapper (replacing direct `_instance` access)
- Framework-internal DI keys use `object()` identities (hidden from users); user-facing keys use `InjectKey`
- `inject()` of an unprovided key raises `InjectionError` unless `default=` is specified (returning `T | type(default)`)
- DI values are non-reactive by default; users opt into reactivity by providing/injecting `Signal` instances
- `DIScope` supports context manager protocol for standalone/test usage

## Capabilities

### New Capabilities
- `di-injection`: The core `provide()` / `inject()` API, `InjectKey[T]` token type, injection key resolution rules, and error behavior
- `di-scope`: `DIScope` class, scope hierarchy (app → component tree), lazy child scope creation, `ContextVar` integration, context manager protocol

### Modified Capabilities
- `components`: Component setup integrates with DI scope; `Context.provide()` method added; component destruction disposes child DI scope
- `composables`: `useRouter()` added as typed inject wrapper; existing composables unchanged but benefit from DI for internal singleton replacement
- `architecture`: Global singletons replaced by DI-provided values; multi-app isolation becomes possible
- `router`: `Router._instance` singleton replaced by DI; `RouterView` and `TypedRouterLink` resolve router via `inject()` instead of class variables

## Impact

- **New module**: `webcompy/di/` — `InjectKey`, `DIScope`, `provide()`, `inject()`, `InjectionError`
- **Modified**: `webcompy/components/_component.py` — `__setup` creates/manages child DI scope
- **Modified**: `webcompy/components/_libs.py` — `Context` gains `provide()` method
- **Modified**: `webcompy/router/_router.py` — remove `_instance` class variable
- **Modified**: `webcompy/router/_view.py` — use `inject()` instead of `_instance`/`_router`
- **Modified**: `webcompy/router/_link.py` — use `inject()` instead of `_router`
- **Modified**: `webcompy/components/_component.py` — `_head_props` moved to DI
- **Modified**: `webcompy/components/_generator.py` — `ComponentStore` accessed via DI instead of global singleton
- **Modified**: `webcompy/app/_root_component.py` — provide Router, ComponentStore, HeadProps into app DI scope
- **Modified**: `tests/conftest.py` — singleton reset fixtures replaced by DI scope fixtures
- **Breaking**: Code that accesses `Router._instance` directly will break (use `inject(RouterKey)` or `useRouter()`)

## Known Issues Addressed

- "Multiple global singletons (Router, RouterView, ComponentStore, Component._head_props)" — all replaced by DI
- "No provide/inject (DI) system" — this change adds it

## Non-goals

- Auto-instantiation of classes via `__init__` annotation inspection (too fragile in PyScript/Emscripten)
- Generic type keys (e.g., `inject(list[int])`) — equality/hash works but identity isn't cached; use `InjectKey` instead
- Readonly/inject-side mutation prevention for Signal values — users control this by choosing what to provide
- Plugin system — orthogonal concern, will be a separate change
- App instance refactoring (`WebComPyApp` as central application object) — separate `feat-app-instance` change
- Provider lifecycle hooks (`on_provide`, `on_dispose`) — explicit `on_before_destroy` suffices