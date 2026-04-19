## Purpose

The DI injection system provides a mechanism for components and standalone code to resolve dependencies by key. Based on the provide/inject pattern, it replaces global singletons with scoped dependency resolution, enabling subtree-scoped state sharing, test isolation, and multi-app support.

## Requirements

### Requirement: inject shall resolve values from the active DI scope
`inject(key)` SHALL return the value associated with the given key by traversing the DI scope chain upward from the current scope to the root app scope. The closest (most specific) scope that provides the key SHALL win.

#### Scenario: Injecting a value provided at the app level
- **WHEN** a developer calls `app.provide(ApiKey, "secret")` and a deeply nested component calls `inject(ApiKey)`
- **THEN** the component SHALL receive `"secret"`

#### Scenario: Injecting a value provided at a parent component
- **WHEN** a parent component calls `provide(ThemeKey, dark_theme)` and a child component calls `inject(ThemeKey)`
- **THEN** the child SHALL receive `dark_theme`

#### Scenario: Child scope shadows parent scope
- **WHEN** a parent provides `ThemeKey = "light"` and a child component provides `ThemeKey = "dark"`
- **AND** a grandchild component calls `inject(ThemeKey)`
- **THEN** the grandchild SHALL receive `"dark"` (child scope wins)

### Requirement: inject shall raise InjectionError for unprovided keys
`inject(key)` SHALL raise `InjectionError` with a descriptive message including the key identity when no scope in the chain provides the given key.

#### Scenario: Injecting an unprovided key
- **WHEN** a developer calls `inject(NoSuchKey)` and no scope provides `NoSuchKey`
- **THEN** `InjectionError` SHALL be raised

#### Scenario: Injecting outside any DI scope
- **WHEN** a developer calls `inject(SomeKey)` outside a component setup and outside a `DIScope` context
- **THEN** `InjectionError` SHALL be raised

### Requirement: inject shall support optional default values
`inject(key, default=value)` SHALL return the default value instead of raising `InjectionError` when no provider is found. The return type SHALL be `T | type(default)` where `T` is the key's type parameter.

#### Scenario: Injecting with None default
- **WHEN** a developer calls `inject(ApiKey, default=None)` and no scope provides `ApiKey`
- **THEN** `None` SHALL be returned (no exception raised)

#### Scenario: Injecting with a typed default
- **WHEN** a developer calls `inject(ConfigKey, default=default_config)` and no scope provides `ConfigKey`
- **THEN** `default_config` SHALL be returned and the return type SHALL be `Config | type(default_config)`

### Requirement: InjectionKey shall provide type-safe token keys
`InjectKey[T]` SHALL be a unique key object parameterized by type `T` for static type analysis. At runtime, the type parameter is erased, but `@overload` signatures on `inject()` SHALL enable type checkers to infer `T` from `InjectKey[T]`.

#### Scenario: Creating an InjectKey for a string value
- **WHEN** a developer creates `ApiKey = InjectKey[str]("api-key")`
- **THEN** `inject(ApiKey)` SHALL have return type `str` at type-check time

#### Scenario: InjectKey identity is unique
- **WHEN** a developer creates `Key1 = InjectKey("name")` and `Key2 = InjectKey("name")`
- **THEN** `Key1` and `Key2` SHALL be distinct keys (different object identities)
- **AND** `inject(Key1)` SHALL NOT resolve values provided for `Key2`

#### Scenario: InjectKey repr is debuggable
- **WHEN** a developer creates `Key = InjectKey("my-service")`
- **THEN** `repr(Key)` SHALL include `"my-service"` for debugging

### Requirement: Class-type keys shall resolve service instances
A Python class object SHALL be usable as an injection key. `inject(RouterService)` SHALL resolve the value provided for `RouterService` as a class key.

#### Scenario: Providing and injecting a service class
- **WHEN** a developer calls `provide(RouterService, router_instance)` and later `inject(RouterService)`
- **THEN** `router_instance` SHALL be returned

#### Scenario: Built-in types shall not be used as class keys
- **WHEN** a developer attempts to use a built-in type as a key (e.g., `inject(str)`)
- **THEN** the behavior is undefined (built-in types are ambiguous as keys — use `InjectKey` instead)

### Requirement: DI values shall be non-reactive by default
`inject()` SHALL return the provided value as-is without introducing reactivity. If a `Signal` is provided and injected, standard Signal read/write rules apply. If a plain value is provided, changes to the original variable SHALL NOT propagate.

#### Scenario: Injecting a Signal value
- **WHEN** a developer provides `provide(CountKey, Signal(0))` and injects `count = inject(CountKey)`
- **THEN** `count` SHALL be the Signal object
- **AND** `count.value` SHALL be `0`
- **AND** `count.value = 5` SHALL trigger Signal's normal propagation

#### Scenario: Injecting a plain value
- **WHEN** a developer provides `provide(MessageKey, "hello")` and injects `msg = inject(MessageKey)`
- **THEN** `msg` SHALL be `"hello"`
- **AND** reassigning `msg = "bye"` locally SHALL NOT affect other injectors

#### Scenario: Changes to provider's variable do not propagate
- **WHEN** a provider holds `theme = Signal("dark")`, provides `provide(ThemeKey, theme)`, and later reassigns `theme = Signal("light")`
- **THEN** injectors that already resolved `ThemeKey` SHALL still hold the original Signal object
- **AND** the reassignment SHALL NOT affect previously injected references