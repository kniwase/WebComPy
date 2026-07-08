## MODIFIED Requirements

### Requirement: Signal() direct construction shall emit DeprecationWarning

`Signal.__init__()` SHALL emit a `DeprecationWarning` (escalated from `UserWarning` in `feat-signal-composable`) with the message "Signal() is deprecated. Use use_state(factory) instead." The `Signal` class SHALL remain as the return type of `use_state()` and for type annotations.

The internal `Signal._create()` classmethod SHALL continue to bypass the warning for framework internal use.

#### Scenario: DeprecationWarning on direct construction
- **WHEN** user code calls `Signal(0)` directly
- **THEN** a `DeprecationWarning` SHALL be emitted (not `UserWarning`)
- **AND** the `Signal` SHALL still be created and function normally

#### Scenario: No warning from use_state() composable
- **WHEN** `use_state(lambda: 0)` creates a `Signal` internally
- **THEN** no `DeprecationWarning` SHALL be emitted
- **AND** `Signal._create()` SHALL be used instead of `Signal()`

### Requirement: Computed() direct construction shall emit DeprecationWarning

`Computed.__init__()` SHALL emit a `DeprecationWarning` with the message "Computed() is deprecated. Use use_computed(factory) instead." The `Computed` class SHALL remain as the return type of `use_computed()` and for type annotations.

An internal `Computed._create(fn)` classmethod SHALL bypass the warning for framework internal use.

#### Scenario: DeprecationWarning on direct Computed construction
- **WHEN** user code calls `Computed(lambda: x.value * 2)` directly
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the `Computed` SHALL still be created and function normally

#### Scenario: No warning from use_computed() composable
- **WHEN** `use_computed(lambda: x.value * 2)` creates a `Computed` internally
- **THEN** no `DeprecationWarning` SHALL be emitted
- **AND** `Computed._create()` SHALL be used instead of `Computed()`

#### Scenario: computed() alias emits DeprecationWarning
- **WHEN** user code calls `computed(fn)` (the old function name)
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the warning message SHALL direct users to `use_computed()`
