## MODIFIED Requirements

### Requirement: Signal and Computed shall be created via function-style API

The primary creation API for reactive primitives SHALL be function-style: `signal(factory)` for source signals and `computed(fn)` for derived signals. The `Signal()` and `Computed()` class constructors SHALL emit `DeprecationWarning` when called directly by user code. The `Signal` and `Computed` classes SHALL remain as type annotations (`Signal[T]`, `Computed[T]`) and as the runtime return types of `signal()` and `computed()` respectively.

The `Reactive` alias for `Signal` (if it exists) SHALL be deprecated and SHALL emit `DeprecationWarning` upon import or use. Users SHALL use `signal()` for creation and `Signal[T]` for type annotations.

#### Scenario: signal() is the primary creation API
- **WHEN** a developer creates a reactive value
- **THEN** `signal(factory)` SHALL be the recommended API
- **AND** `Signal(value)` SHALL emit `DeprecationWarning`

#### Scenario: computed() is the primary creation API
- **WHEN** a developer creates a derived reactive value
- **THEN** `computed(fn)` SHALL be the recommended API
- **AND** `Computed(fn)` (if callable as constructor) SHALL emit `DeprecationWarning`

#### Scenario: Reactive alias deprecated
- **WHEN** user code imports `Reactive` from `webcompy.signal`
- **THEN** a `DeprecationWarning` SHALL be emitted (or the alias SHALL be removed)
- **AND** the warning message SHALL direct users to `signal()` for creation and `Signal[T]` for annotations

#### Scenario: Signal type annotation still works
- **WHEN** a developer writes `count: Signal[int] = signal(lambda: 0)`
- **THEN** the type annotation SHALL be valid
- **AND** `Signal` SHALL remain importable from `webcompy.signal`
- **AND** no deprecation warning SHALL be emitted for the type annotation usage

#### Scenario: Internal framework code uses Signal._create()
- **WHEN** framework internal code creates a Signal without transfer
- **THEN** `Signal._create(value)` SHALL be used (no warning)
- **AND** this SHALL NOT be part of the public API (underscore-prefixed method)
