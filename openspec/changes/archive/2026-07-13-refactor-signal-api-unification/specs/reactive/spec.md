## MODIFIED Requirements

### Requirement: Computed values shall be created via use_computed()

The function-style creation API for `Computed` SHALL be `use_computed(factory)`, replacing the previous `computed(factory)` function. The `Computed` class SHALL remain accessible from `webcompy.signal` as a type annotation (`Computed[T]`) and for framework internal use. `use_computed()` SHALL also be importable from `webcompy` top-level alongside `use_state()`, `use_reactive_list()`, and `use_reactive_dict()`.

#### Scenario: Creating a computed value with use_computed()
- **WHEN** a developer writes `doubled = use_computed(lambda: count.value * 2)` inside a component setup function
- **THEN** a `Computed[int]` SHALL be returned
- **AND** the factory SHALL execute eagerly during construction, establishing `count` as a tracked dependency

#### Scenario: use_computed() is importable from webcompy top-level
- **WHEN** a developer writes `from webcompy import use_computed`
- **THEN** `use_computed` SHALL be available
- **AND** `computed` SHALL NOT be available from `webcompy` or `webcompy.signal`

#### Scenario: Computed class remains for type annotations
- **WHEN** a developer writes `doubled: Computed[int] = use_computed(lambda: count.value * 2)`
- **THEN** the type annotation SHALL be valid
- **AND** `Computed` SHALL remain importable from `webcompy.signal`

### MODIFIED Requirement: Signal and Computed classes are internal types

The `Signal` and `Computed` classes SHALL be internal implementation types accessible through `webcompy.signal`. They SHALL NOT emit runtime deprecation warnings when constructed directly. The `use_state()` and `use_computed()` composables SHALL be the public creation APIs, using `Signal()` and `Computed()` constructors internally.

#### Scenario: Signal() constructor is not warned
- **WHEN** framework internal or extension code calls `Signal(0)`
- **THEN** the `Signal` SHALL be created without any warning

#### Scenario: Computed() constructor is not warned
- **WHEN** framework internal or extension code calls `Computed(fn)`
- **THEN** the `Computed` SHALL be created without any warning
