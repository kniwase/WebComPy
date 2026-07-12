## REMOVED Requirements

### Requirement: Signal() direct construction shall emit UserWarning

The `Signal() direct construction shall emit UserWarning` requirement introduced by `feat-signal-composable` is REMOVED. The `Signal` class constructor is an internal API with no runtime warning.

### Requirement: computed(fn) function shall exist

The `computed(fn)` function is REMOVED and replaced by `use_computed(factory)`.

## ADDED Requirements

### Requirement: use_computed() shall create Computed instances

The framework SHALL provide a `use_computed()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable and return a `Computed[T]` instance. Unlike `use_state()`, `use_computed()` SHALL NOT participate in factory-skip transfer — Computed values always recompute from their source Signals.

The factory SHALL be passed to `Computed(fn)`, and the factory SHALL execute eagerly during construction to establish dependency tracking. As with any `Computed`, the resulting instance re-evaluates lazily on subsequent `.value` reads after a dependency change.

The function SHALL accept a single argument: `use_computed(factory: Callable[[], T]) -> Computed[T]`.

The existing `computed(fn)` function SHALL be removed from `webcompy.signal` exports. No deprecated alias SHALL be created.

#### Scenario: Creating a computed value with factory
- **WHEN** a developer writes `doubled = use_computed(lambda: count.value * 2)` inside a component setup function
- **THEN** a `Computed[int]` SHALL be returned
- **AND** the factory SHALL execute eagerly during construction, establishing dependency tracking

#### Scenario: use_computed() does not participate in transfer
- **WHEN** `use_computed(lambda: count.value * 2)` is used during SSR
- **THEN** the Computed value SHALL NOT be included in the transfer payload
- **AND** on the browser, the Computed SHALL recompute from the transferred `count` source Signal

#### Scenario: use_computed() outside component context
- **WHEN** `use_computed(factory)` is called outside a component setup function
- **THEN** a `Computed` SHALL be returned (factory passed to `Computed()`, initial evaluation runs eagerly)
- **AND** no error SHALL be raised
- **AND** no warning about the calling context SHALL be emitted (unlike `use_state()`, `use_computed()` does not emit a "called outside component setup" warning)

#### Scenario: use_computed() imports remove computed()
- **WHEN** a developer writes `from webcompy.signal import computed`
- **THEN** an `ImportError` SHALL be raised (no deprecated alias)
- **AND** `from webcompy.signal import use_computed` SHALL succeed
- **AND** `from webcompy import use_computed` SHALL succeed

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
