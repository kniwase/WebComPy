# Forms

## Purpose

Field-first form abstraction built on top of the reactive Signal system. A `Field` wraps a single writable `Signal` with validation state (`errors`/`valid`/`invalid`) and interaction state (`touched`/`dirty`); a `Form` aggregates fields flatly and orchestrates submission (preventDefault, touch-all, validity gate, async handler, `submitting`/`submit_error`). The `:bind` attribute (see `elements`) accepts a `Field` and wires interaction state automatically. `touched`/`dirty` are transient UI state and never participate in SSR transfer, so error displays gated on `touched` never flash on page load.

## Requirements

### Requirement: Field shall wrap a Signal with validation and interaction state

The framework SHALL provide a `Field` class and `use_field(signal, validators=[...])` composable in the `webcompy.forms` module. `Field` SHALL expose:

- `value` — the underlying `Signal` (the same object passed in)
- `errors` — `Computed[list[str]]` of validation messages, re-evaluated on value change
- `valid` / `invalid` — `Computed[bool]` derived from `errors`
- `touched` — `Signal[bool]`, initially `False`
- `dirty` — `Signal[bool]`, initially `False`
- `reset()` — restores the value captured at construction and clears `touched`/`dirty`

`Field` SHALL NOT be a `SignalBase` subclass. `touched`/`dirty` SHALL be transient UI state and SHALL NOT participate in SSR transfer. `use_field` SHALL be callable inside or outside component setup.

#### Scenario: Creating a field
- **WHEN** `use_field(Signal(""), validators=[required()])` is called
- **THEN** `field.valid.value` SHALL be `False` and `field.errors.value` SHALL contain the required message
- **AND** `field.touched.value` and `field.dirty.value` SHALL be `False`

#### Scenario: Errors react to value changes
- **WHEN** a field with `required()` has its value set to `"alice"`
- **THEN** `field.errors.value` SHALL become `[]` and `field.valid.value` SHALL become `True`

#### Scenario: Reset restores initial state
- **WHEN** a field's value, `touched`, and `dirty` have changed and `reset()` is called
- **THEN** the value SHALL return to the construction-time value and `touched`/`dirty` SHALL be `False`

### Requirement: Built-in validators shall cover common rules

The framework SHALL provide validator factories in `webcompy.forms`: `required`, `min_length(n)`, `max_length(n)`, `pattern(regex)`, `email`, `min_value(n)`, `max_value(n)`. Each SHALL accept an optional custom message and return a `(value) -> str | None` callable. `required` SHALL treat `None`, whitespace-only strings, and `False` as missing. `email` SHALL use a pragmatic (non-RFC-complete) pattern. `min_value`/`max_value` SHALL be used for numeric bounds (the names `min`/`max` SHALL NOT be used, to avoid shadowing builtins).

#### Scenario: Required with checkbox
- **WHEN** `required()` validates `False`
- **THEN** the required message SHALL be returned (enabling "must agree" checkboxes)

#### Scenario: Custom message
- **WHEN** `min_length(8, message="Too short")` validates `"abc"`
- **THEN** `"Too short"` SHALL be returned

#### Scenario: Multiple validators accumulate
- **WHEN** a field has `[required(), min_length(8)]` and the value is `""`
- **THEN** `errors` SHALL contain the required message (and any others that fail)

### Requirement: `:bind` shall wire Field interaction state

When `:bind` receives a `Field`, it SHALL bind `field.value` per the elements `:bind` rules, SHALL set `field.dirty` to `True` on each write-back, and SHALL register a `blur` handler that sets `field.touched` to `True` (chained before any user `blur` handler).

#### Scenario: Blur marks touched
- **WHEN** a `Field` is bound via `html.INPUT({":bind": field})` and the input fires `blur`
- **THEN** `field.touched.value` SHALL become `True`

#### Scenario: Edit marks dirty
- **WHEN** a bound field's write-back handler runs
- **THEN** `field.dirty.value` SHALL become `True` before the value update

### Requirement: Form shall aggregate fields and orchestrate submission

`use_form(**fields)` SHALL return a `Form` exposing `valid`/`invalid` (all fields valid), `touched`/`dirty` (any field), `touch_all()`, `reset()` (all fields), `values()` (name→value dict), `submitting` (`Signal[bool]`), and `submit_error` (`Signal[BaseException | None]`). `form.submit(handler)` SHALL return an event handler that: calls `ev.preventDefault()`, calls `touch_all()`, returns early if any field is invalid, otherwise invokes `handler(values)` (awaiting it if awaitable) with `submitting` toggled around the call and exceptions captured into `submit_error`.

#### Scenario: Submit blocked when invalid
- **WHEN** `form.submit(handler)` fires and any field is invalid
- **THEN** all fields SHALL be touched (errors visible), `handler` SHALL NOT be called, and `submitting` SHALL remain `False`

#### Scenario: Successful async submit
- **WHEN** all fields are valid and the submit handler is an async function
- **THEN** `submitting` SHALL be `True` during the await and `False` after, and `handler` SHALL receive the values dict

#### Scenario: Handler exception captured
- **WHEN** the submit handler raises
- **THEN** the exception SHALL be stored in `submit_error` and `submitting` SHALL return to `False`
