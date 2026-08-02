# Proposal: Form Fields (`use_field` / `use_form`)

## Why

With `:bind` two-way binding (`feat-two-way-binding`), inputs stay in sync with Signals — but forms still lack the higher-level concerns every real form needs: validation with error messages, interaction state (touched/dirty) for deciding when to show errors, and form-level aggregation (overall validity, submit orchestration). Today each developer would hand-roll these per field, with inconsistent conventions. A field-first, Signal-native form abstraction — composable wrappers around individual `Signal`s rather than a monolithic form model — fits WebComPy's composable philosophy and directly reuses the `:bind` mechanism.

## What Changes

- New public module `webcompy.forms` providing:
  - `use_field(signal, validators=[...])` → `Field` wrapper exposing:
    - `.value` — the underlying `Signal` (same object; readable/writable)
    - `.errors` — `Computed[list[str]]` of current validation messages
    - `.valid` / `.invalid` — `Computed[bool]`
    - `.touched` — `Signal[bool]`, set on field blur (auto-wired via `:bind`)
    - `.dirty` — `Signal[bool]`, set on first user edit (auto-wired via `:bind`)
    - `.reset()` — restores the initial value and clears touched/dirty
  - Built-in validators: `required`, `min_length`, `max_length`, `pattern`, `email`, `min_value`, `max_value` — each a factory returning a `(value) -> str | None` callable with an optional custom message
  - `use_form(**fields)` → `Form` aggregation exposing `.valid` / `.invalid` (all fields), `.touched` / `.dirty` (any field), `.touch_all()`, `.reset()`, and `.submit(handler)` returning a submit-event handler that prevents default, touches all fields, and invokes the (optionally async) handler with a values dict only when all fields are valid, tracking `.submitting` and `.submit_error`
- `:bind` (from `feat-two-way-binding`) accepts a `Field` in addition to a `Signal`: it binds `field.value` and additionally wires blur→`touched` and edit→`dirty`. On component tags, `:bind` remains an ordinary prop.
- Validation timing: validators re-evaluate on every value change (Computed); error *display* gating (`touched`) is template logic, e.g. `{% if f.touched.value and f.invalid.value %}`.
- New spec capability `forms` (Field wrapper, validators, Form aggregation); `elements` gains an ADDED requirement for `:bind` accepting `Field`.

Depends on `feat-two-way-binding` (lands first); implemented after it merges.

## Capabilities

### New Capabilities

- `forms`: Field wrapper API, built-in validators, interaction state (touched/dirty), `:bind` integration semantics, Form aggregation and submit orchestration.

### Modified Capabilities

- `elements`: ADDED requirement — `:bind` accepts `Field` objects (extends the `:bind` requirement introduced by `feat-two-way-binding`; kept as a standalone ADDED requirement because it is behaviorally additive).

## Impact

- **Code**: new package `packages/webcompy/src/webcompy/forms/` (`_field.py`, `_validators.py`, `_form.py`, `__init__.py`); `packages/webcompy/src/webcompy/elements/_bind.py` extended to accept `Field` (from `feat-two-way-binding`).
- **Specs**: new `openspec/specs/forms/spec.md`; ADDED requirement in `openspec/specs/elements/spec.md`.
- **Mapping**: `AGENTS.md` File→Spec Mapping gains a `webcompy/forms/` → `forms/spec.md` row; review-skill spec list updated.
- **Tests**: unit tests for Field/validators/Form, `:bind`+Field wiring (touched/dirty), SSR rendering; e2e form scenario in `e2e/core/`.
- No breaking changes.

## Known Issues Addressed

None from the documented known-issues list.

## Non-goals

- Async validators (server-side uniqueness checks etc.) — follow-up.
- `<select>` binding — deferred (as in `feat-two-way-binding`).
- Schema/model-first form API (single dict model exploded into fields) — rejected in favor of field-first design; do not add.
- i18n of built-in validator messages (custom message parameter covers it for now).
- Cross-field validation (e.g., password confirmation) — possible manually via a validator closure reading another field's Signal; no dedicated API in this change.
- Automatic form rendering/ scaffolding (Django-style `{{ form }}`) — rendering stays explicit in templates.
