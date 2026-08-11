# Proposal: feat-ui-form-controls

## Why

WebComPy's `forms` module provides validation logic (`Field` with `value`/`errors`/`touched`/`dirty`, validators, `Form` aggregation), but no rendered controls: applications hand-build inputs, wire bindings, and — most error-prone — implement the accessibility glue themselves (label association, `aria-invalid`, error message linkage via `aria-describedby`, switch/radio semantics). Under the "no JavaScript" promise there is no JS form-library fallback. This change ships the control layer as headless/themed pairs per the UI primitives foundation: headless controls own native-element semantics and Field binding, themed controls provide token-based styling, and a `FormField` wrapper composes label + control + error display with correct ARIA wiring.

## What Changes

- Six control pairs plus a wrapper under the two-layer architecture (`webcompy.ui.headless` / `webcompy.ui.components`, themed re-exported at `webcompy.ui`):
  - **Input**: text input bound to a `Field` (or raw value/change props), native `<input>` base.
  - **Textarea**: multiline variant, same binding contract.
  - **Select**: native `<select>` with options prop, same binding contract (custom listbox deferred).
  - **Checkbox**: native checkbox base with correct checked binding.
  - **Switch**: checkbox-based `role="switch"` with `aria-checked`.
  - **Radio/RadioGroup**: `fieldset`/`legend` grouping with native same-name radio keyboard behavior.
  - **FormField**: composition wrapper — label, control slot, error message region; sets `aria-invalid` on the bound control and associates errors via `aria-describedby`; errors display when the field is touched and invalid.
- Binding contract: controls accept either a `Field` instance (value sync plus touched/dirty updates flow through the Field) or explicit value + change-callback props for uncontrolled/custom use.
- Themed styles for all controls in `_styles/primitives.css` (token-based, including focus rings, invalid states, disabled states).

## Capabilities

### New Capabilities

- `ui-form-controls`: First-party form controls — Input, Textarea, Select, Checkbox, Switch, Radio/RadioGroup, and the FormField wrapper — as headless/themed pairs: Field binding contract, native-element semantics, invalid/error ARIA wiring, and token-based themed styling.

### Modified Capabilities

(none)

## Impact

- **Code**: new headless/themed components in `webcompy/ui/headless/` and `webcompy/ui/components/`; themed rules appended to `_styles/primitives.css`; unit and E2E tests.
- **APIs**: additive only. The `forms` module itself is unchanged (controls consume its public API).
- **Dependencies**: requires the `ui-primitives` foundation and the existing `forms` capability.
- **Docs**: docs_app demo page showing a complete form (validation, error display, reset) built from the primitives.

## Known Issues Addressed

(none)

## Non-goals

- Custom listbox/combobox Select (native `<select>` only; custom widget deferred with autocomplete work).
- Date/time pickers, file upload widgets, masked inputs.
- Form layout systems (grid/inline arrangement is application CSS).
- Server-side form actions (submission handling stays application-level, e.g. via the HTTP client or JSON-RPC).
- New validators or changes to the forms module's validation semantics.
