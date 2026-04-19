## Context

WebComPy currently shares state across the component tree through 6 global singletons: `Router._instance`, `RouterView._instance`, `RouterView._router` (ClassVar), `TypedRouterLink._router` (ClassVar), `Component._head_props` (ClassVar), and `ComponentStore` (`@_instantiate` module-level singleton). Additionally, `_active_component_context` and `_active_effect_scope` are `ContextVar` instances used during component setup — this pattern can be extended for DI scoping.

The framework uses function-style components (`@define_component`) where a setup function receives a `Context[PropsType]` and returns an element tree. Component tree structure is implicit: each element has a `_parent` pointer, and `_get_belonging_components()` traverses up to collect ancestors. There is no explicit component tree data structure.

WebComPy runs in two environments: browser (PyScript/Emscripten) and server (CPython). Any DI solution must work in both.

## Goals / Non-Goals

**Goals:**
- Replace all global singletons with DI-provided values
- Enable subtree-scoped dependency injection (provide at a component, inject in descendants)
- Support standalone DI usage outside components (testing, utilities)
- Provide type-safe injection keys (`InjectKey[T]`) alongside class-type keys
- Integrate with existing `ContextVar` + `EffectScope` patterns
- Keep the API simple: `provide(key, value)` / `inject(key)`
- Enable test isolation via explicit scope creation

**Non-Goals:**
- Auto-instantiation via `__init__` annotation inspection (fragile in PyScript/Emscripten)
- Readonly enforcement for injected Signal values
- Generic type keys (e.g., `list[int]`) — use `InjectKey` instead
- Plugin system (orthogonal concern)
- App instance refactoring (separate change)
- Provider lifecycle hooks (use `on_before_destroy` explicitly)

## Decisions

### Decision 1: Hybrid key system (class-type + InjectKey)

**Choice**: Support both class-type keys (`inject(RouterService)`) and `InjectKey[T]` tokens (`inject(ApiBaseUrl)`).

**Rationale**: Class-type keys are natural for service objects (one class = one instance per scope). `InjectKey[T]` handles primitive values, config strings, and cases where multiple values of the same type are needed. Python classes are hashable and identity-stable, making them valid dict keys. `InjectKey` uses `object()` identity internally for uniqueness, with a `name` attribute for debuggability.

**Alternatives considered**:
- String-only keys: simple but collision-prone, no type safety
- Class-only keys: can't represent config values or primitives
- `InjectionToken<T>` (Angular-style with factory): adds complexity for auto-instantiation we don't need

**Constraints**:
- Built-in types (`str`, `int`, `list`, etc.) MUST NOT be used as class keys — they're ambiguous. Use `InjectKey` instead.
- Generic type aliases (e.g., `list[int]`) are NOT supported as keys. Equality/hash is stable in CPython but not identity-cached; Emscripten risk is real.

### Decision 2: Lazy child scope creation (Pattern C)

**Choice**: All components inherit the parent DI scope by default. A child DI scope is created lazily only when `provide()` is called during component setup.

**Rationale**: This combines the simplicity of Vue3's always-inherit model with Angular's explicit-provider philosophy. Components that don't provide anything simply use the parent scope — no overhead. Components that call `provide()` get their own scope, which descendants inherit.

**Alternatives considered**:
- Always-inherit (Vue3): simple but no way to know from the component definition what it provides
- Explicit `providers=[]` in decorator (Angular): verbose, and function-style components determine providers at runtime (not statically)
- Fully standalone (FastAPI): no tree-based scope hierarchy

**Implementation**: `_active_di_scope` ContextVar holds the current scope. In `Component.__setup`, the parent scope is inherited. If `provide()` is called, a child scope is created on first call and set as the active scope for the remainder of setup.

### Decision 3: Non-reactive DI values

**Choice**: `inject()` returns the value as-is. DI itself does not introduce reactivity.

**Rationale**: If a user provides a `Signal`, injecting it returns the Signal object — standard Signal read/write rules apply. If a user provides a plain value, injecting it returns that plain value. This avoids hidden reactive chains and makes the propagation model explicit. Users opt into reactivity by choosing to provide/inject Signal instances.

**Alternatives considered**:
- Auto-unwrap Signals on inject (Vue3 template-style): loses reference sharing, can't observe updates
- Auto-wrap in Signal on inject: unnecessary overhead, creates duplicate state
- Readonly enforcement on inject: too restrictive, prevents legitimate mutation patterns

### Decision 4: Strict inject (exception on missing key)

**Choice**: `inject(key)` raises `InjectionError` if no provider is found. `inject(key, default=value)` returns `T | type(default)` instead of raising.

**Rationale**: This catches configuration errors early (developer forgot to `provide`) — a key advantage over Vue3's silent `undefined + warn` approach. The `default=` parameter provides an explicit opt-out when a key is genuinely optional, and the return type `T | None` (when `default=None`) makes the optionality visible in type annotations.

**Alternatives considered**:
- Always raise (no default): too strict for genuinely optional DI
- Always return `None` + warn (Vue3): too lenient, delays error discovery

### Decision 5: Module-level `provide()`/`inject()` API

**Choice**: `provide(key, value)` and `inject(key, default?)` are module-level functions that delegate to `_active_di_scope` ContextVar.

**Rationale**: Consistent with WebComPy's existing pattern — `on_before_rendering()`, `on_after_rendering()`, `on_before_destroy()` are all module-level functions that use `_active_component_context` ContextVar. Having `provide`/`inject` at the same level avoids the asymmetry of `inject(key)` being module-level while `context.provide(key, value)` being method-level.

**Implementation**: `Context.provide(key, value)` is also available as a convenience method that delegates to the same `_active_di_scope` resolution.

### Decision 6: DIScope as context manager + tree node

**Choice**: `DIScope` is a tree-structured object that supports `__enter__`/`__exit__` for standalone usage and test isolation.

**Rationale**: The scope hierarchy mirrors the component tree. `DIScope.__enter__` sets `_active_di_scope` ContextVar; `__exit__` resets it. `DIScope.dispose()` invalidates the scope (prevents further inject from resolving through it) and disposes child scopes, but does NOT clean up provided values — users handle resource cleanup via `on_before_destroy` explicitly.

```
App DIScope (provide Router, ComponentStore, HeadProps)
  │
  ├── Layout DIScope (provide Theme, Auth)
  │     │
  │     ├── Header (inherit, inject Router ← App, Theme ← Layout)
  │     ├── Content (inherit)
  │     │     └── DetailPanel DIScope (provide LocalConfig)
  │     │           └── Widget (inject LocalConfig ← DetailPanel)
  │     └── Footer (inherit)
  │
  └── Sidebar (inherit Layout scope... no, inherits App scope)
```

### Decision 7: Framework-internal keys use `object()` identities

**Choice**: Internal DI keys (Router, ComponentStore, HeadProps) use `object()` as keys — not `InjectKey`. User-facing wrappers (`useRouter()`) use `InjectKey` for their return type but call `inject()` with internal keys.

**Rationale**: Decouples internal implementation from public API. The internal key identity is an implementation detail that can change between versions. Public `InjectKey` instances (like `RouterKey`) provide a stable API surface for users who want to inject framework services directly.

### Decision 8: InjectKey Generic type for static analysis only

**Choice**: `InjectKey[T]` carries `T` at the type-checker level (pyright/mypy) for type inference on `inject()`. At runtime, `T` is erased — the `InjectKey` instance stores only its `name` and `object()` identity.

**Rationale**: Python's `Generic[T]` is erased at runtime. TypeScript's `InjectionKey<T> = symbol & {__type: T}` pattern isn't directly translatable. However, `@overload` signatures on `inject()` enable pyright to infer `T` from `InjectKey[T]` at check time. This is the same tradeoff Vue3 makes — `InjectionKey<T>` is for the type system, not runtime enforcement.

## Risks / Trade-offs

- **[Risk] ContextVar stack overflow for deeply nested components** → ContextVar tokens are properly reset in `finally` blocks; each component's setup is synchronous, so depth is bounded by the component tree. Mitigated by existing pattern (`_active_component_context` already works this way).

- **[Risk] Inject called outside setup or scope** → Raises `InjectionError` with a clear message. This is a feature, not a bug — it catches misuse early, matching Decision 4.

- **[Risk] Lazy scope creation causes subtle ordering issues** → If `provide()` is called mid-setup after some `inject()` calls, those earlier injects resolved from the parent scope while later ones resolve from the child. Mitigation: document that `provide()` should be called at the top of the setup function. The child scope, once created, inherits all parent providers — so values already injected from the parent are consistent.

- **[Risk] ComponentStore migration timing** → `ComponentGenerator` registers itself in `ComponentStore` at import time (in `__init__`). `WebComPyApp.__init__` (and thus DI scope setup) happens later. Bridge: a module-level `_default_component_store` singleton exists during migration; `AppDocumentRoot` provides it into the app scope; components access it via `inject(_COMPONENT_STORE_KEY)` with fallback to `_default_component_store`. Full migration removes the fallback in a later change.

- **[Risk] Class-type key collision between unrelated classes with the same name** → Python class identity is by `id()`, not name. Two different `RouterService` classes in different modules are distinct keys. No collision risk.

- **[Trade-off] No auto-instantiation** → Users must explicitly create instances and `provide()` them. This is more verbose than Angular's `providedIn: 'root'` but avoids Emscripten fragility and keeps the DI system simple. Factory registration (`provide(Key, factory_fn)`) offers a middle ground for lazy instantiation.

- **[Trade-off] No value cleanup on scope dispose** → `DIScope.dispose()` invalidates the scope but doesn't call any cleanup on provided values. Users must handle resource cleanup explicitly via `on_before_destroy`. This is consistent with Angular's approach (services implement `OnDestroy` explicitly).

## Migration Plan

### Phase 1: Core DI system (no singleton replacement)
1. Add `webcompy/di/` module with `InjectKey`, `DIScope`, `provide`, `inject`, `InjectionError`
2. Add `_active_di_scope` ContextVar
3. Modify `Component.__setup` to create child DI scope when `provide()` is called
4. Add `Context.provide()` convenience method
5. Add `DIScope.__enter__`/`__exit__` for standalone usage

### Phase 2: Replace singletons one at a time
6. Replace `Router._instance` → provide via `AppDocumentRoot`, inject in `RouterView`/`TypedRouterLink`
7. Replace `Component._head_props` → provide via `AppDocumentRoot`, inject where needed
8. Replace `ComponentStore` singleton → provide via `AppDocumentRoot`, inject in `ComponentGenerator`
9. Add `useRouter()` composable as public inject wrapper
10. Remove old singleton patterns and reset fixtures

### Rollback
Each phase is independently deployable. If a singleton replacement causes issues, the old global access can be restored while keeping the DI system in place. The bridge pattern (`_default_component_store` fallback) supports incremental migration.

## Open Questions

1. **Should `InjectKey` instances be defined in a central location or co-located with their consumers?** — Central location (like a `webcompy/di/keys.py`) makes discovery easier but creates coupling. Co-located definition (next to the service) is more modular. Recommendation: co-located, with framework keys in `webcompy/di/_keys.py`.

2. **Should `DIScope` support factory-based lazy instantiation?** — `provide(Key, lambda: ExpensiveService())` would create the instance on first `inject()`. This adds complexity but avoids unnecessary initialization. Recommendation: support in Phase 1, as it's a small addition to the `DIScope.inject` method.

3. **Should multiple `provide()` calls for the same key in the same scope overwrite or error?** — Overwriting allows dynamic re-provision (useful for testing); erroring catches accidental duplicates. Recommendation: overwrite with a debug-mode warning.