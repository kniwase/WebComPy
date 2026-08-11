# Design: feat-ui-form-controls

## Context

The `forms` capability provides `Field[T]` (`.value: Signal[T]`, `.errors: Computed[list[str]]`, `.valid`/`.invalid`, `.touched`/`.dirty`, `reset()`), `Form` aggregation, and validators. The `:bind` element attribute already accepts a `Field` and wires interaction state automatically: value sync, `dirty` on write-back, `touched` on blur (elements `_bind.py`, forms spec requirement "`:bind` shall wire Field interaction state"). What does not exist is the rendered, accessible control layer — applications currently hand-build inputs and the ARIA/error wiring.

Grounded facts (verified in codebase):

- `:bind` supports `input[type=text|email|password|search|tel|url|number|checkbox|radio]` and `textarea`, chains with user event handlers, and sets Field interaction state — headless controls reuse this mechanism internally rather than reimplementing write-back.
- Function-style components with `TypedDict` props are the established authoring pattern; reactive props flow as Signals/Computeds.
- `primitives.css` (foundation change) is the themed-style delivery point.

## Goals / Non-Goals

**Goals:**

- Headless/themed pairs for Input, Textarea, Select, Checkbox, Switch, Radio/RadioGroup plus the FormField wrapper.
- A binding contract that works with `Field` instances (full validation/interaction state) and with plain value/change props (uncontrolled use).
- Correct accessibility wiring centralized in FormField (label association, `aria-invalid`, `aria-describedby` error linkage, touched-gated error display).

**Non-Goals:**

- Custom listbox/combobox, pickers, upload widgets, layout systems, server-side form actions, new validators (see proposal Non-goals).

## Decisions

### D1: Binding contract — Field instance or raw value props

Every control accepts either a `field` prop (a `Field` instance) or `value` + `on_change` props. With `field`, the control binds via the existing `:bind` mechanism (value sync, dirty/touched wiring comes for free). With raw props, the control is a plain controlled element. Rationale: `field` covers the dominant validated-form case with zero wiring; raw props keep the controls usable outside the forms module (search boxes, filters) without forcing Field adoption. The two modes are mutually exclusive per instance; passing both is an error.

### D2: Native elements as the base

Controls render native `<input>`, `<textarea>`, `<select>`, checkbox/radio inputs. Native elements provide keyboard behavior, mobile semantics, and form participation for free; the framework adds binding and ARIA state on top. The custom listbox Select is explicitly deferred (combobox ARIA is a large surface). Themed styling of native controls uses token-based rules (including focus-visible rings) without resetting essential native behavior.

### D3: FormField centralizes label/error ARIA wiring

`FormField` composes: a `<label>` associated with the control, the control slot, and an error message region. When the bound field is touched and invalid, the control carries `aria-invalid="true"` and the error region's id is referenced by the control's `aria-describedby`; when valid or untouched, the association is absent. Error display gating on `touched` follows the forms capability's design (no error flash on page load, since touched/dirty are transient and never SSR-transferred). Ids are generated per FormField instance and stable across re-renders.

### D4: Switch is a checkbox with role="switch"

Switch renders a checkbox input with `role="switch"` and `aria-checked` reflecting state; binding follows the checkbox path. Rationale: `role="switch"` is the correct ARIA pattern for on/off toggles and keeps native checkbox keyboard behavior (Space to toggle).

### D5: RadioGroup via fieldset/legend and native same-name grouping

RadioGroup renders `fieldset` + `legend` and its Radio items share a generated `name`, so native arrow-key navigation within the group works without custom keyboard code. Group value binding maps to a single Field (string value). Individual Radio items are not meaningfully usable outside a group but remain exported for custom compositions.

### D6: Invalid-state styling hooks

Controls expose `data-invalid="true"` when the bound field is invalid (and touched, matching display gating), giving both themed CSS and headless users a state hook for invalid styling independent of `aria-invalid`.

## Risks / Trade-offs

- **Native Select limitations**: styling native `<select>` is constrained across browsers (option lists render natively). Accepted for v1 correctness; custom widget is the documented upgrade path.
- **`:bind` type restrictions**: `:bind` targets plain `Signal` instances; Field binding goes through the established Field path in `_bind.py` (which handles Fields explicitly), so controls inherit its supported input types. Number inputs coerce per the existing `:bind` rules.
- **Id generation stability**: FormField ids must be stable across re-renders to keep `aria-describedby` valid; generated once per component instance (uuid pattern already used elsewhere in the codebase).
- **Themed native control quirks**: focus rings and invalid states must remain visible across themes; covered by token-driven rules and E2E visual checks in docs demos.
