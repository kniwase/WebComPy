# Proposal: `:bind` Two-Way Binding for Form Elements

## Why

Form input in WebComPy currently requires a hand-written write-back handler for every field — bind a Signal to the `value` attribute for Signal→DOM updates, and separately register an `@input`/`@change` handler that copies `ev.target.value` (or `ev.target.checked`) back into the Signal for DOM→Signal updates. This boilerplate appears in the CLI project template (`template_data/app/components/input.py`) and every real form, is error-prone (easy to forget the write-back, or to mismatch `value` vs `checked`), and blocks the planned form-field abstraction (`use_field`), which needs a standard binding mechanism to hook validation/touched/dirty tracking into.

This change adds a `:bind` attribute that performs the two-way wiring declaratively, per element type. The naming follows the Svelte (`bind:value`), Blazor (`@bind`), and Aurelia (`value.bind`) convention, chosen over Vue-style `model` after comparing framework vocabularies.

## What Changes

- Add a `:bind` attribute accepted by the element API and by HTML elements in templates:
  - Element API: `html.INPUT({":bind": my_signal})`, `html.TEXTAREA({":bind": my_signal})`
  - Template: `<input :bind="my_signal">` (second recognized `:`-prefixed attribute alongside `:ref`)
- `:bind` expands to a one-way attribute binding (Signal→DOM, reusing the existing reactive attribute pipeline) plus a write-back event handler (DOM→Signal), per element type:
  - `input[type=text|email|password|search|tel|url]` (and missing `type`), `textarea`: binds `value` + `@input`; write-back sets `signal.value = ev.target.value`
  - `input[type=number]`: binds `value` + `@input`; write-back converts to `int`/`float` matching the Signal's current value type; empty or unparseable input skips the update
  - `input[type=checkbox]`: binds `checked` + `@change`; write-back sets `signal.value = ev.target.checked`
  - `input[type=radio]`: binds `checked` via a `Computed` equality against the element's static `value` attribute; write-back sets the Signal to that `value` when the radio becomes checked
- `:bind` requires a writable `Signal` instance. `Computed`, `ReadonlySignal` (`readonly()`), `ReactiveList`, `ReactiveDict`, and non-Signal values are rejected with a descriptive `WebComPyException`.
- Conflict policy: an explicit attribute duplicating the bound one (`value` for text-like/number, `checked` for checkbox/radio) raises `WebComPyException`. An explicit user handler for the binding event (`@input`/`@change`) is chained — the binding write-back runs first, then the user handler.
- Type-discipline errors: text-like binding requires a `str`-valued Signal, number requires `int`/`float`, checkbox requires `bool`; radio requires a static `value` attribute. `input` with a dynamic (Signal/Computed) `type` attribute combined with `:bind` is rejected (binding semantics cannot be determined).
- Unsupported elements (`<select>`, non-form tags) combined with `:bind` raise a descriptive `WebComPyException` naming the supported elements.
- SSR renders only the bound attribute's initial value (no events, as today); hydration attaches write-back handlers through the existing event-lifecycle path (`create_proxy`/`destroy`).
- Template `:bind="name"` resolves a context variable (no `{{ }}` interpolation inside, same rule as `:ref`) and validates it is a `Signal`.

## Capabilities

### New Capabilities

(none — behavior lands in existing capabilities)

### Modified Capabilities

- `elements`: adds the `:bind` two-way binding requirement (element-type rules, value conversion, conflict policy, SSR behavior, error cases).
- `template-engine`: modifies the colon-prefixed attribute validation requirement to recognize `:bind` alongside `:ref` on HTML elements, with its own validation scenarios.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/_bind.py` (new module with the expansion logic), `packages/webcompy/src/webcompy/elements/types/_element.py` (`Element.__init__` intercepts `:bind`), `packages/webcompy/src/webcompy/template/_binder.py` (`classify_attrs` accepts `:bind`).
- **Specs**: `openspec/specs/elements/spec.md`, `openspec/specs/template-engine/spec.md`.
- **Tests**: new unit tests under `tests/` (element expansion per type, conversion, conflicts, SSR, template `:bind`) and e2e coverage in `e2e/core/`.
- **Follow-up enabler**: this is the binding mechanism the planned `feat-form-fields` change (`use_field` wrapper) builds on; `:bind` accepting a Field object is out of scope here.
- No breaking changes: existing explicit `value` + `@input` patterns continue to work unchanged.

## Known Issues Addressed

None from the documented known-issues list. (Removes the undocumented boilerplate burden of manual two-way wiring; the CLI project template can be simplified in a follow-up.)

## Non-goals

- `<select>`/`<option>` binding (requires property-level assignment and `selected` SSR handling) — deferred to a follow-up change.
- Form field abstraction (`use_field`, validators, touched/dirty), form aggregation (`use_form`), and submit handling — separate planned change (`feat-form-fields`).
- Event modifiers (`@input.debounce` etc.) — remain unsupported as today.
- Binding to non-Signal reactive sources (e.g., arbitrary property paths) — `:bind` targets a `Signal` only.
- Component-tag `:bind` (on component tags, `:bind` remains an ordinary dynamic prop named `bind`, with no special meaning in this change).
