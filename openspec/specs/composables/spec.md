# Composables

## Purpose

Composables are reusable stateful logic functions that encapsulate signal state and lifecycle behavior for use inside function-style component setup functions. They provide a composable alternative to class inheritance for sharing logic across components. Instead of extending a base class, a component calls composable functions during setup, and the returned signal values integrate with the component's template and lifecycle.

WebComPy provides built-in composables (`use_async_result`, `use_async`) for common async patterns, and standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) that register hooks implicitly via context variables.
## Requirements
### Requirement: Composables shall be reusable stateful logic functions

Composables SHALL be plain Python functions (or function calls) that encapsulate signal state and lifecycle logic for use inside function-style component setup functions. They SHALL be callable inside a `@define_component` setup function and return values that integrate with the signal system (Signal, Computed, AsyncResult, etc.). WebComPy provides built-in composables (`use_async_result`, `use_async`, and `use_theme`) for common patterns, and standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) that register hooks implicitly via context variables.

#### Scenario: Using a composable inside a component

- **WHEN** a developer calls a composable function inside a `@define_component` setup function
- **THEN** the returned signal values SHALL be usable in the component's template
- **AND** any lifecycle hooks registered by the composable SHALL fire at the correct times

#### Scenario: Using use_theme inside a component

- **WHEN** a developer calls `use_theme()` inside a `@define_component` setup function
- **THEN** the returned `Signal[Theme]` SHALL be usable in the component's template (e.g., to render a theme-aware label)
- **AND** the returned `ThemeController` SHALL be usable in event handlers (e.g., `@click` callbacks)

### Requirement: Signal composables shall create reactive state in component setup

The framework SHALL provide `use_state()`, `use_computed()`, `use_reactive_list()`, and `use_reactive_dict()` composables for creating reactive state inside component setup functions. These composables SHALL be importable from `webcompy` top-level.

`use_state()`, `use_reactive_list()`, and `use_reactive_dict()` SHALL support SSR transfer of their created values when called inside a component setup context. `use_computed()` SHALL NOT participate in transfer; `Computed` values always recompute from their source signals on the browser.

`use_state()`, `use_reactive_list()`, and `use_reactive_dict()` SHALL each accept either a zero-argument factory callable or an explicit string key followed by the factory. The explicit key is the payload-match key for SSR transfer. `use_computed()` SHALL accept a zero-argument factory callable only.

#### Scenario: Creating a signal with use_state()
- **WHEN** a developer writes `count = use_state(lambda: 0)` inside a component setup function
- **THEN** a `Signal[int]` SHALL be returned
- **AND** the signal SHALL be registered for SSR transfer

#### Scenario: Creating a computed with use_computed()
- **WHEN** a developer writes `doubled = use_computed(lambda: count.value * 2)` inside a component setup function
- **THEN** a `Computed[int]` SHALL be returned
- **AND** the factory SHALL execute eagerly during construction to establish dependency tracking
- **AND** the Computed SHALL NOT be included in the SSR transfer payload

#### Scenario: Creating a reactive list with use_reactive_list()
- **WHEN** a developer writes `items = use_reactive_list(lambda: [1, 2, 3])` inside a component setup function
- **THEN** a `ReactiveList[int]` SHALL be returned
- **AND** the list SHALL be registered for SSR transfer

#### Scenario: Creating a reactive dict with use_reactive_dict()
- **WHEN** a developer writes `settings = use_reactive_dict(lambda: {"theme": "dark"})` inside a component setup function
- **THEN** a `ReactiveDict[str, str]` SHALL be returned
- **AND** the dict SHALL be registered for SSR transfer

#### Scenario: Explicit key for use_state()
- **WHEN** a developer writes `count = use_state("count", lambda: 0)` inside a component setup function
- **THEN** the payload-match key for SSR transfer SHALL be `"count"`

#### Scenario: use_computed() outside component context
- **WHEN** `use_computed(factory)` is called outside a component setup function
- **THEN** a `Computed` SHALL be returned
- **AND** no error SHALL be raised
- **AND** no warning about the calling context SHALL be emitted (unlike `use_state()`, `use_computed()` does not emit a "called outside component setup" warning)

### Requirement: Two-tier reactive creation API

The framework SHALL provide a two-tier API for creating reactive state, separated by transfer needs and calling context:

**Tier 1 — Public composable API** (`webcompy` top-level):

- `use_state(factory)` / `use_reactive_list(factory)` / `use_reactive_dict(factory)` — transfer-capable source signals
- `use_computed(factory)` — non-transferable derived signals
- Intended for: component setup functions, user-facing application code
- SSR transfer of signal values is active when called inside a component setup context

**Tier 2 — Internal constructor API** (`webcompy.signal`):

- `Signal(value)` / `Computed(fn)` / `ReactiveList(iterable)` / `ReactiveDict(mapping)` — no transfer, no warnings
- Intended for: module-level global state, plugins, DI providers, third-party extensions, framework infrastructure
- The `use_*` composables SHALL use these constructors internally to create signal instances

The two tiers SHALL coexist without runtime conflicts. `Signal()` and `Computed()` constructors SHALL NOT emit `DeprecationWarning` or `UserWarning`. The separation SHALL be enforced through export surfaces (`webcompy` vs `webcompy.signal`) and documentation, not runtime penalties.

#### Scenario: Composables are the primary API for component state
- **WHEN** a developer creates state inside a `@define_component` setup function
- **THEN** `use_state()`, `use_computed()`, `use_reactive_list()`, and `use_reactive_dict()` SHALL be importable from `webcompy`
- **AND** these composables SHALL be the documented primary creation API

#### Scenario: Signal constructors serve non-component contexts
- **WHEN** a module creates global state at module level (`_store = Signal(default)`)
- **THEN** the `Signal` SHALL be created without any warning
- **AND** the module author SHALL NOT be forced to use `use_state()` which would emit "called outside component setup" warning
- **AND** no SSR transfer SHALL occur for module-level signals (they are outside the component tree)

#### Scenario: Plugins use constructors directly
- **WHEN** a `WebComPyPlugin` implementation creates internal `Signal` or `Computed` instances
- **THEN** the plugin SHALL use `from webcompy.signal import Signal, Computed`
- **AND** no warning SHALL be emitted during construction
- **AND** the plugin SHALL NOT be forced to call `use_state()` (plugin setup is outside component context)

#### Scenario: DI providers hold constructor-created signals
- **WHEN** a DI provider function (outside any component) creates a `Signal` to inject
- **THEN** `Signal(value)` SHALL be used directly via `from webcompy.signal import Signal`
- **AND** no warning SHALL be emitted

#### Scenario: Composables use constructors internally
- **WHEN** `use_state(lambda: 0)` is called inside a component setup
- **THEN** the composable SHALL internally call `Signal(factory())` to create the instance
- **AND** no warning SHALL be emitted during this internal construction
- **AND** `use_computed(fn)` SHALL internally call `Computed(fn)`

#### Scenario: Third-party extensions access constructors without penalty
- **WHEN** a third-party library imports `Signal` or `Computed` from `webcompy.signal` and calls the constructor
- **THEN** no deprecation or usage warning SHALL be emitted
- **AND** the library SHALL be free to build on the internal API without fighting the framework's runtime checks

#### Scenario: Framework code uses public import path for signal classes
- **WHEN** framework code imports a name listed in `webcompy.signal.__all__` (e.g., `Signal`, `SignalBase`, `Computed`, `computed_property`)
- **THEN** the import SHALL be from `webcompy.signal`
- **AND** SHALL NOT use private submodule paths (e.g., `webcompy.signal._base`, `webcompy.signal._computed`)
- **AND** SHALL NOT create `_`-prefixed aliases (e.g., `Computed as _Computed`)

#### Scenario: Non-exported internal symbols may use private module paths
- **WHEN** framework code needs an internal symbol not in `webcompy.signal.__all__` (e.g., `consumer_destroy`, `CallbackConsumerNode`, `producer_accessed`)
- **THEN** the import MAY use the private submodule path (e.g., `from webcompy.signal._graph import consumer_destroy`)
- **AND** the symbol SHALL NOT be added to `webcompy.signal.__all__` unless it is intended for public use

### Requirement: Standalone lifecycle hooks shall register without explicit context
`@on_before_rendering`, `@on_after_rendering`, and `@on_before_destroy` SHALL be module-level decorators that register lifecycle hooks using the active component context from `contextvars.ContextVar`. They SHALL NOT require an explicit `context` parameter.

#### Scenario: Registering an after-rendering hook with standalone decorator
- **WHEN** a developer decorates a function with `@on_after_rendering` inside a component setup function
- **THEN** the decorated function SHALL be called after the component renders
- **AND** the behavior SHALL be identical to calling `context.on_after_rendering(func)` explicitly

#### Scenario: Calling a standalone hook outside a component setup
- **WHEN** a developer calls `@on_after_rendering` outside of a component setup function
- **THEN** a `LookupError` SHALL be raised with a message indicating the function must be called inside a component setup context

#### Scenario: Nesting with child component instantiation
- **WHEN** a parent component setup function instantiates a child component (which also sets up its own context)
- **THEN** the parent's ContextVar SHALL be correctly restored after the child's setup completes
- **AND** lifecycle hooks registered in the parent's context SHALL not be affected by the child's context

### Requirement: use_async_result shall manage async operation results reactively
`use_async_result` SHALL accept an async function, execute it, and return an `AsyncResult` object with signal state, data, and error properties. It SHALL support automatic execution on rendering, reactive-driven refetching, and manual refetching.

#### Scenario: Fetching data on component mount
- **WHEN** a developer calls `use_async_result(fetch_data, immediate=True)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** `AsyncResult.state` SHALL transition from `PENDING` to `LOADING` to `SUCCESS` (or `ERROR`)
- **AND** `AsyncResult.data` SHALL contain the result on success

#### Scenario: Providing a default value
- **WHEN** a developer calls `use_async_result(fetch_list, default=[])` 
- **THEN** `AsyncResult.data.value` SHALL initially be `[]`
- **AND** after successful fetch, `data.value` SHALL contain the fetched list
- **AND** during refetch, `data.value` SHALL preserve the last successful value (SWR pattern)

#### Scenario: Signal-driven refetching with watch
- **WHEN** a developer calls `use_async_result(fetch_search, watch=[query])` with `query` being a `Signal`
- **THEN** whenever `query.value` changes, `refetch()` SHALL be called automatically
- **AND** the async function closure SHALL read the latest value of `query.value`

#### Scenario: Manual refetch triggering
- **WHEN** a developer calls `result.refetch()` or passes `result.refetch` as an event handler
- **THEN** the async function SHALL be re-executed
- **AND** `AsyncResult.state` SHALL transition to `LOADING` then to `SUCCESS` or `ERROR`
- **AND** extra positional arguments passed to `refetch` SHALL be ignored (allowing use as event handlers)

#### Scenario: Deferring execution with immediate=False
- **WHEN** a developer calls `use_async_result(fetch_data, immediate=False)`
- **THEN** the async function SHALL NOT be executed on component mount
- **AND** the async function SHALL only execute when `refetch()` is called or a `watch` signal changes

#### Scenario: Watch cleanup on component destruction
- **WHEN** a component using `use_async_result` with `watch` is destroyed
- **THEN** all reactive subscriptions registered on watched Signals SHALL be cleaned up via `consumer_destroy()`
- **AND** subsequent changes to watched Signals SHALL NOT trigger refetch

### Requirement: AsyncResult shall provide structured async state
`AsyncResult` SHALL expose signal state properties that enable declarative UI rendering of loading, success, and error states.

#### Scenario: Accessing signal state predicates
- **WHEN** a developer accesses `result.is_loading`, `result.is_success`, `result.is_error`, or `result.is_pending`
- **THEN** each SHALL be a `Computed[bool]` that derives from `result.state`
- **AND** exactly one of `is_loading`, `is_success`, `is_error` SHALL be `True` at any time (mutually exclusive)
- **AND** `is_pending` SHALL be `True` only before the first execution

#### Scenario: Displaying different UI for each state
- **WHEN** a developer uses `switch()` with `result.is_loading`, `result.is_success`, and `result.is_error` as case conditions
- **THEN** the corresponding generator SHALL render for the current state
- **AND** transitions between states SHALL update the UI reactively

#### Scenario: Data preservation on error (SWR stale data)
- **WHEN** a successful fetch sets `data.value` to a result
- **AND** a subsequent refetch fails with an error
- **THEN** `data.value` SHALL retain the last successful value
- **AND** `state.value` SHALL be `AsyncState.ERROR`
- **AND** `error.value` SHALL contain the exception

### Requirement: use_async shall execute side-effect-only async operations
`use_async` SHALL accept an async function and execute it after the component renders. It SHALL NOT return a result object. It SHALL be used for fire-and-forget async operations.

#### Scenario: Triggering a side effect after rendering
- **WHEN** a developer calls `use_async(send_analytics_event)` inside a component setup
- **THEN** the async function SHALL be executed after the component renders
- **AND** no return value SHALL be provided (the function returns `None`)

### Requirement: AsyncState shall enumerate async operation phases
`AsyncState` SHALL be a Python enum with four values: `PENDING` (not yet started), `LOADING` (in progress), `SUCCESS` (completed successfully), and `ERROR` (failed with an exception).

#### Scenario: State transitions during a typical fetch cycle
- **WHEN** `AsyncResult` is created with `immediate=False`
- **THEN** `state.value` SHALL be `AsyncState.PENDING`
- **WHEN** `refetch()` is called
- **THEN** `state.value` SHALL become `AsyncState.LOADING`
- **WHEN** the async function resolves successfully
- **THEN** `state.value` SHALL become `AsyncState.SUCCESS`
- **WHEN** the async function raises an exception
- **THEN** `state.value` SHALL become `AsyncState.ERROR`

### Requirement: AsyncResult shall be testable without component context
`AsyncResult` SHALL be constructable and usable outside of a component setup function. Its state machine, data preservation, and error handling SHALL work without a `contextvars.ContextVar` being set.

#### Scenario: Testing AsyncResult state transitions in unit tests
- **WHEN** a developer creates `AsyncResult(fetch_func)` outside a component
- **AND** calls `result.refetch()`
- **THEN** the state SHALL transition correctly (PENDING → LOADING → SUCCESS or ERROR)
- **AND** `data`, `error`, and computed predicates SHALL update accordingly

### Requirement: Effect scope shall integrate with component lifecycle context
A `create_effect_scope()` SHALL be established within the component setup context (via `_active_component_context` ContextVar). Effects created within this scope SHALL be automatically disposed when the component is destroyed, removing all producer/consumer edges from the signal graph.

#### Scenario: Effects created inside a component are auto-cleaned on destruction
- **WHEN** a developer calls `effect(lambda: print(count.value))` inside a `@define_component` setup function
- **AND** the component is later destroyed
- **THEN** the effect's consumer edges SHALL be removed from the signal graph
- **AND** the effect's cleanup callbacks SHALL be invoked
- **AND** changes to `count.value` SHALL NOT trigger the effect

#### Scenario: Existing composable use_async_result can use effect for watch cleanup
- **WHEN** `use_async_result` uses `Signal.on_after_updating(result.refetch)` plus `consumer_destroy()` with `on_before_destroy` cleanup
- **THEN** this pattern SHALL be replaced by `effect()` which automatically tracks dependencies and cleans up on scope disposal
- **AND** the `watch` parameter behavior SHALL remain identical from the user's perspective

### Requirement: use_router shall provide typed router access via DI
`use_router()` SHALL be a composable function that returns the Router instance by calling `inject()` with the framework's router DI key. It SHALL raise `InjectionError` if no router is provided (i.e., the app was created without a router).

#### Scenario: Using use_router in a component
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created with a router
- **THEN** the Router instance SHALL be returned

#### Scenario: Using use_router without a router
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created without a router
- **THEN** `InjectionError` SHALL be raised

#### Scenario: use_router is a thin inject wrapper
- **WHEN** a developer inspects the `use_router` implementation
- **THEN** it SHALL be equivalent to `return inject(RouterKey)` where `RouterKey` is the framework's public router DI key

### Requirement: Composable functions shall return signal primitives with auto-scoped effects
A composable function SHALL create `Signal`, `Computed`, and/or `effect` instances and return them for consumer use. When called within a component setup context, all effects created by the composable SHALL be registered in the active effect scope for automatic cleanup.

#### Scenario: Basic composable with auto-cleanup
- **WHEN** a developer writes `def use_counter(initial=0): count = Signal(initial); ...; return count, increment`
- **AND** calls it within a component's setup function
- **THEN** `count` SHALL be a `Signal` instance whose changes propagate to all dependents
- **AND** any effects created by `use_counter` SHALL be automatically cleaned up when the component is destroyed

#### Scenario: Composable used outside a component context
- **WHEN** a composable is called outside any effect scope (e.g., in a standalone script)
- **THEN** effects created by the composable SHALL still function
- **BUT** cleanup SHALL be the caller's responsibility via explicit `scope.dispose()` or manual `consumer_destroy()`

### Requirement: use_theme shall return a Signal and ThemeController pair for theme manipulation

The framework SHALL provide a `webcompy.ui.composables.use_theme` (also re-exported from `webcompy.ui.theme`) composable function. When called inside a component's setup function, it SHALL return a `(Signal[Theme], ThemeController)` tuple where the signal reflects the current theme state of the active `ThemeManager` and the controller exposes `set(theme)`, `toggle()`, and `cycle()` methods.

#### Scenario: Reading the current theme from a component

- **WHEN** a developer writes `theme, controller = use_theme()` inside a `@define_component` setup function
- **THEN** `theme.value` SHALL return the current `Theme` value
- **AND** the value SHALL update reactively when the `ThemeManager`'s signal changes
- **AND** calling `controller.set(Theme.DARK)` SHALL update both the signal and the `<html>` `data-theme` attribute

#### Scenario: Calling use_theme outside a component setup

- **WHEN** `use_theme()` is called outside of a component setup function
- **THEN** the framework SHALL raise a `LookupError` with a message indicating that `use_theme` must be called inside a component setup context

### Requirement: use_theme shall integrate with the framework's DI scope

`use_theme()` SHALL resolve the active `ThemeManager` from the application DI scope. The same `ThemeManager` instance SHALL be returned to all components within the same app, ensuring consistent theme state across the app.

#### Scenario: Two components share the same ThemeManager

- **WHEN** component A calls `use_theme()` and component B calls `use_theme()` in the same app
- **THEN** both calls SHALL return signals bound to the same `ThemeManager`
- **AND** updating the theme from component A SHALL be visible in component B's signal

### Requirement: use_theme shall be importable from the public `webcompy.ui.theme` and `webcompy.ui.composables` paths

`use_theme` SHALL be importable from both `webcompy.ui.theme` and `webcompy.ui.composables`. Both import paths SHALL refer to the same function object. The function body SHALL declare its framework dependencies (the active `ThemeManager` and friends) via lazy imports inside the function body to avoid the circular import that arises from the public re-export chain.

The previously private `webcompy.ui._composables` module path SHALL NOT be part of the public API; user code that imports from it will fail because the module is removed.

#### Scenario: Importing use_theme from webcompy.ui.theme
- **WHEN** a developer writes `from webcompy.ui.theme import use_theme`
- **THEN** the import SHALL succeed
- **AND** the imported `use_theme` SHALL be callable

#### Scenario: Importing use_theme from webcompy.ui.composables
- **WHEN** a developer writes `from webcompy.ui.composables import use_theme`
- **THEN** the import SHALL succeed
- **AND** the imported `use_theme` SHALL be callable

#### Scenario: Both public import paths refer to the same function
- **WHEN** a developer imports `use_theme` from both `webcompy.ui.theme` and `webcompy.ui.composables`
- **THEN** the two imported objects SHALL be the same callable

#### Scenario: Private underscore path is not part of the public API
- **WHEN** a developer writes `from webcompy.ui._composables import use_theme`
- **THEN** the import SHALL fail (the module is not part of the public API)

### Requirement: use_state() shall create transferable Signal instances with factory-skip

The framework SHALL provide a `use_state()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable and return a `Signal[T]` instance. On the server (or when no hydration payload is available), the factory SHALL run to produce the initial value. On the browser during hydration, the factory SHALL be skipped if the hydration payload contains a value for this signal's key, and the `Signal` SHALL be created with the restored value.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_state(factory: Callable[[], T]) -> Signal[T]` — auto-generated key
2. `use_state(key: str, factory: Callable[[], T]) -> Signal[T]` — explicit key

Direct value arguments (e.g., `use_state(0)`) SHALL NOT be accepted — the first argument MUST be callable. Callable factories that require arguments (e.g., `lambda value: value`) SHALL NOT be accepted; the factory MUST be callable with zero arguments.

#### Scenario: Creating a transferable signal with factory
- **WHEN** a developer writes `count = use_state(lambda: 0)` inside a component setup function
- **THEN** a `Signal[int]` SHALL be returned
- **AND** on the server, the factory `lambda: 0` SHALL run to produce the initial value
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: Creating a transferable signal with explicit key
- **WHEN** a developer writes `count = use_state("counter", lambda: 0)`
- **THEN** the signal SHALL be registered with key `"counter"` for payload matching
- **AND** the key SHALL be used during both collection and restoration

#### Scenario: Factory reads server-only data
- **WHEN** a developer writes `theme = use_state(lambda: inject(COOKIE_PORT_KEY).get("theme", "light"))`
- **THEN** on the server, the factory SHALL read the cookie value
- **AND** the value SHALL be collected and transferred to the browser
- **AND** on the browser during hydration, the factory SHALL be skipped and the transferred value used

#### Scenario: use_state() outside component context
- **WHEN** `use_state(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `Signal` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted ("use_state() called outside component setup; signal will not be transferred")
- **AND** no error SHALL be raised

#### Scenario: Type safety with overload
- **WHEN** a developer writes `use_state(0)` (non-callable first argument)
- **THEN** a type checker SHALL report a type error
- **AND** at runtime, a `TypeError` SHALL be raised

#### Scenario: Non-zero-argument factory detection is best-effort
- **WHEN** a developer writes `use_state(lambda value: value)`
- **THEN** a type checker SHALL report a type error (via `@overload` signatures)
- **AND** at runtime, the framework SHALL attempt to validate the factory via `inspect.signature()`
- **AND** if validation detects required parameters, a `UserWarning` SHALL be emitted ("Factory appears to require arguments; use a zero-argument callable")
- **AND** if validation is inconclusive (e.g., `*args`/`**kwargs`, C extension, `functools.partial`), the framework SHALL silently proceed — the factory will fail at call time with a natural Python exception if arguments are required
- **AND** under no circumstances SHALL a `TypeError` be raised preemptively before attempting to call the factory

### Requirement: use_reactive_list() shall create transferable ReactiveList instances with factory-skip

The framework SHALL provide a `use_reactive_list()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable returning a `list[V]` and return a `ReactiveList[V]` instance. The factory-skip mechanism SHALL work identically to `use_state()`: on the server, the factory runs; on the browser during hydration, the factory is skipped if a value exists.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_reactive_list(factory: Callable[[], list[V]]) -> ReactiveList[V]` — auto-generated key
2. `use_reactive_list(key: str, factory: Callable[[], list[V]]) -> ReactiveList[V]` — explicit key

#### Scenario: Creating a transferable reactive list
- **WHEN** a developer writes `items = use_reactive_list(lambda: [1, 2, 3])` inside a component setup function
- **THEN** a `ReactiveList[int]` SHALL be returned
- **AND** the returned instance SHALL support mutation methods (`append`, `pop`, etc.) that trigger change events
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: Mutations on a transferred ReactiveList
- **WHEN** a `ReactiveList` was created via `use_reactive_list()` with a restored value
- **AND** the developer calls `items.append(4)`
- **THEN** the change event SHALL fire normally
- **AND** `on_after_updating` callbacks SHALL be notified

#### Scenario: use_reactive_list() outside component context
- **WHEN** `use_reactive_list(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `ReactiveList` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted
- **AND** no error SHALL be raised

### Requirement: use_reactive_dict() shall create transferable ReactiveDict instances with factory-skip

The framework SHALL provide a `use_reactive_dict()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable returning a `dict[K, V]` and return a `ReactiveDict[K, V]` instance. The factory-skip mechanism SHALL work identically to `use_state()`.

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_reactive_dict(factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]` — auto-generated key
2. `use_reactive_dict(key: str, factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]` — explicit key

#### Scenario: Creating a transferable reactive dict
- **WHEN** a developer writes `settings = use_reactive_dict(lambda: {"theme": "dark"})` inside a component setup function
- **THEN** a `ReactiveDict[str, str]` SHALL be returned
- **AND** the returned instance SHALL support mutation methods (`__setitem__`, `pop`, etc.) that trigger change events
- **AND** on the browser during hydration, the factory SHALL be skipped if a transferred value exists

#### Scenario: use_reactive_dict() outside component context
- **WHEN** `use_reactive_dict(factory)` is called outside a component setup function
- **THEN** the factory SHALL always run (no payload check)
- **AND** a `ReactiveDict` SHALL be returned without transfer registration
- **AND** a `UserWarning` SHALL be emitted
- **AND** no error SHALL be raised

### Requirement: Composable auto-key shall use caller source location

When the `key` parameter is omitted, all composables (`use_state()`, `use_reactive_list()`, `use_reactive_dict()`) SHALL generate a key from the caller's source location using `inspect.currentframe()` and `dis.get_instructions()`. The key format SHALL be `"{filename}:{start_line}:{start_col}"` (Python 3.12+ positions API). If the positions API is unavailable, the fallback format SHALL be `"{filename}:{lineno}"`. The key SHALL be stable across server and browser environments (same source file and line).

#### Scenario: Auto-key from source location
- **WHEN** `use_state(lambda: 0)` is called at `my_component.py:10:14`
- **THEN** the generated key SHALL be `"my_component.py:10:14"`
- **AND** the same key SHALL be generated on both server and browser

#### Scenario: Same-line calls get distinct keys
- **WHEN** two `use_state()` calls appear on the same source line
- **THEN** the column number SHALL disambiguate them
- **AND** each call SHALL get a distinct key

#### Scenario: Fallback when positions API unavailable
- **WHEN** `dis.get_instructions()` or `instr.positions` is not available (e.g., limited runtime)
- **THEN** the fallback key format SHALL be `"{filename}:{lineno}"`
- **AND** same-line calls SHALL share a key (user SHALL use explicit key to disambiguate)

#### Scenario: Fallback with same-line collisions emits UserWarning
- **WHEN** the `file:line` fallback is active
- **AND** multiple composable calls on the same line lack explicit keys
- **THEN** the second and subsequent same-line composable invocations SHALL emit a `UserWarning` ("Auto-key collision detected at {filename}:{lineno} with {previous_key}. Use an explicit key to disambiguate.")
- **AND** the warning SHALL only be emitted once per component per collision (deduplicated via Python's `warnings` module default behavior)

### Requirement: Signal() direct construction is supported without UserWarning

`Signal.__init__()` SHALL create a Signal instance normally without emitting any `UserWarning`. Third-party libraries that subclass `Signal` or call it directly SHALL NOT see any framework-issued `UserWarning`. `use_state()` is the recommended pattern for component setups that participate in SSR transfer, but `Signal()` is not deprecated and remains part of the supported public API.

#### Scenario: Direct Signal() construction emits no warning
- **WHEN** user code calls `Signal(0)` directly (e.g. inside a third-party subclass or test helper)
- **THEN** no `UserWarning` SHALL be emitted
- **AND** the `Signal` SHALL still be created and function normally

#### Scenario: Composables emit no warning
- **WHEN** `use_state(lambda: 0)` creates a `Signal` internally
- **THEN** no `UserWarning` SHALL be emitted

#### Scenario: Signal type annotation still works
- **WHEN** a developer writes `count: Signal[int] = use_state(lambda: 0)`
- **THEN** the type annotation SHALL be valid
- **AND** `Signal` SHALL remain importable from `webcompy.signal`

### Requirement: use_counter SHALL NOT participate in hydration transfer

`use_counter` SHALL create a counter signal that is not registered with `Context._transferable_signals`. The counter state SHALL reset to `initial` on every component setup (including browser hydration) and SHALL NOT emit a `UserWarning`.

#### Scenario: use_counter ignores hydration transfer
- **WHEN** a developer calls `use_counter(initial)` inside a component setup function
- **THEN** the counter signal SHALL NOT be registered with `Context._transferable_signals`
- **AND** the counter state SHALL reset to `initial` on every component setup (including browser hydration)
- **AND** the framework SHALL NOT log a `UserWarning` for the counter

### Requirement: Storage persistence composables shall provide reactive localStorage/sessionStorage-backed state

The framework SHALL provide `use_local_storage(key, default)` and `use_session_storage(key, default)` composables, importable from `webcompy` top-level and from `webcompy.storage`, each returning a `Reactive[T]`. `default` SHALL accept either a value or a zero-argument factory callable.

In the browser (PyScript) environment, the composable SHALL read the current stored value for `key` at creation time and use it as the signal's initial value; when the key is absent, the default SHALL be used. Every subsequent update of the returned signal SHALL be automatically written back to the corresponding Web Storage API. Values SHALL be encoded with `json.dumps` and decoded with `json.loads`.

In any non-PyScript environment (SSR, SSG, server-side tests), the composable SHALL NOT access any storage API and SHALL return `Reactive(default)`.

#### Scenario: Read persisted value on creation
- **GIVEN** the browser's `localStorage` contains `{"theme": "\"dark\""}`-style JSON under key `"theme"`
- **WHEN** a component setup calls `use_local_storage("theme", "light")`
- **THEN** the returned signal's value SHALL be `"dark"`

#### Scenario: Default when key absent
- **WHEN** a component setup calls `use_local_storage("missing", lambda: 42)` and the key is absent
- **THEN** the returned signal's value SHALL be `42`

#### Scenario: Automatic write-back on update
- **GIVEN** `theme = use_local_storage("theme", "light")` in the browser
- **WHEN** `theme.value = "dark"` is assigned
- **THEN** `localStorage.getItem("theme")` SHALL return `'"dark"'`

#### Scenario: SSR performs no storage access
- **WHEN** `use_local_storage("theme", "light")` is called during SSR/SSG (non-PyScript environment)
- **THEN** the returned signal's value SHALL be `"light"`
- **AND** no browser storage API SHALL be accessed

#### Scenario: Callable outside component setup
- **WHEN** `use_local_storage("k", 0)` is called outside any component setup function
- **THEN** a working `Reactive` SHALL be returned
- **AND** no `UserWarning` SHALL be emitted

#### Scenario: Storage-backed signals are excluded from SSR transfer
- **WHEN** a component uses `use_local_storage` inside setup during SSR
- **THEN** the signal SHALL NOT be registered in the SSR transfer payload

### Requirement: Storage composables shall degrade gracefully on failure

Storage composables SHALL follow a non-fatal failure policy: a corrupted stored value (invalid JSON) SHALL produce a `logging.warning` and fall back to the default; a non-JSON-serializable value on write SHALL produce a warning and skip the write; a `setItem` failure (quota, privacy mode) SHALL be caught, logged, and swallowed. No storage failure SHALL break signal reactivity or propagate to the caller.

#### Scenario: Corrupted stored value
- **GIVEN** `localStorage` contains invalid JSON under key `"settings"`
- **WHEN** `use_local_storage("settings", lambda: {})` is called in the browser
- **THEN** a warning SHALL be logged
- **AND** the signal's value SHALL be `{}`

#### Scenario: Non-serializable value skips write
- **GIVEN** `data = use_local_storage("data", None)` in the browser
- **WHEN** `data.value = object()` is assigned
- **THEN** a warning SHALL be logged
- **AND** the write SHALL be skipped
- **AND** the signal's in-memory value SHALL update normally

