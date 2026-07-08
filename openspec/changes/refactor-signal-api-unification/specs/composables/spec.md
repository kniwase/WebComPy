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

### Requirement: use_computed() shall create Computed instances with zero-argument factory

The framework SHALL provide a `use_computed()` composable function importable from `webcompy` and `webcompy.signal`. It SHALL accept a zero-argument factory callable and return a `Computed[T]` instance. Unlike `use_state()`, `use_computed()` SHALL NOT participate in factory-skip transfer — Computed values always recompute from their source Signals (which ARE transferred via `use_state()`). The factory SHALL be passed to `Computed._create()` to produce the Computed; evaluation SHALL remain lazy (the factory is stored, not invoked — it executes on first `.value` access, matching existing `Computed` behavior).

The function SHALL use `typing.overload` to provide two typed signatures:
1. `use_computed(factory: Callable[[], T]) -> Computed[T]` — auto-generated key (same auto-key mechanism as `use_state()`)
2. `use_computed(key: str, factory: Callable[[], T]) -> Computed[T]` — explicit key (for debugging/identification only; key is NOT used for transfer)

Internally, `use_computed()` SHALL use `Computed._create(fn)` to avoid the `DeprecationWarning`.

#### Scenario: Creating a computed value with factory
- **WHEN** a developer writes `doubled = use_computed(lambda: count.value * 2)` inside a component setup function
- **THEN** a `Computed[int]` SHALL be returned
- **AND** a `Computed` SHALL be created immediately (synchronously) from the factory
- **AND** the factory SHALL NOT be invoked until `.value` is accessed (lazy evaluation)
- **AND** the Computed SHALL re-evaluate whenever `count` changes

#### Scenario: use_computed() does not transfer
- **WHEN** `use_computed(lambda: count.value * 2)` is used during SSR
- **THEN** the Computed value SHALL NOT be included in the transfer payload
- **AND** on the browser, the Computed SHALL recompute from the transferred `count` source Signal

#### Scenario: use_computed() outside component context
- **WHEN** `use_computed(factory)` is called outside a component setup function
- **THEN** a `Computed` SHALL be returned (factory passed to `Computed._create()`, evaluation remains lazy)
- **AND** no error SHALL be raised
- **AND** no warning SHALL be emitted (unlike `use_state()`, `use_computed()` does not participate in transfer, so no functionality is lost outside component context)

#### Scenario: No warning from use_computed()
- **WHEN** `use_computed(lambda: x.value * 2)` creates a `Computed` internally
- **THEN** no `DeprecationWarning` SHALL be emitted
- **AND** `Computed._create()` SHALL be used instead of `Computed()`
