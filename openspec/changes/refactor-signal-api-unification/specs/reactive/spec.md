## MODIFIED Requirements

### Requirement: Signal and Computed shall be created via function-style API

The primary creation API for reactive primitives SHALL be function-style: `use_state(factory)` for source signals and `use_computed(factory)` for derived signals. The `Signal()` and `Computed()` class constructors SHALL emit `DeprecationWarning` when called directly by user code. The `Signal` and `Computed` classes SHALL remain as type annotations (`Signal[T]`, `Computed[T]`) and as the runtime return types of `use_state()` and `use_computed()` respectively.

#### Scenario: use_state() is the primary creation API
- **WHEN** a developer creates a reactive value
- **THEN** `use_state(factory)` SHALL be the recommended API
- **AND** `Signal(value)` SHALL emit `DeprecationWarning`

#### Scenario: use_computed() is the primary creation API
- **WHEN** a developer creates a derived reactive value
- **THEN** `use_computed(factory)` SHALL be the recommended API
- **AND** `Computed(fn)` SHALL emit `DeprecationWarning`

#### Scenario: Signal type annotation still works
- **WHEN** a developer writes `count: Signal[int] = use_state(lambda: 0)`
- **THEN** the type annotation SHALL be valid
- **AND** `Signal` SHALL remain importable from `webcompy.signal`
- **AND** no deprecation warning SHALL be emitted for the type annotation usage

#### Scenario: Internal framework code uses Signal._create()
- **WHEN** framework internal code creates a Signal without transfer
- **THEN** `Signal._create(value)` SHALL be used (no warning)
- **AND** this SHALL NOT be part of the public API (underscore-prefixed method)
