# UI Form Controls Specification (delta)

## ADDED Requirements

### Requirement: Form controls shall support Field binding and raw value binding

Each form control (Input, Textarea, Select, Checkbox, Switch, RadioGroup) SHALL accept either a `field` prop carrying a forms-module `Field` instance, or `value` plus change-callback props. With a `field`, the control SHALL bind through the framework's `:bind` mechanism so that value synchronization, `dirty` on write-back, and `touched` on blur follow the forms capability's rules. With raw props, the control SHALL behave as a plain controlled element. Supplying both modes on one instance SHALL be an error.

#### Scenario: Field-bound input updates validation state

- **WHEN** an Input bound to a required Field receives user text and then loses focus
- **THEN** the Field's value SHALL reflect the text, `dirty` SHALL be true after the write-back, and `touched` SHALL be true after blur

#### Scenario: Raw value mode works without a Field

- **WHEN** an Input is given a value prop and a change callback without a Field
- **THEN** user edits SHALL invoke the change callback with the new value and no forms-module state SHALL be involved

### Requirement: Controls shall render native elements with framework binding

Input and Textarea SHALL render native `<input>`/`<textarea>` elements, Select SHALL render a native `<select>` populated from an options prop, and Checkbox/Radio SHALL render native checkbox/radio inputs. Keyboard, mobile, and form-participation behavior SHALL come from the native elements; the framework SHALL add binding and state wiring only.

#### Scenario: Select renders options from props

- **WHEN** a Select is given three options
- **THEN** the native `<select>` SHALL contain three corresponding `<option>` elements and binding SHALL reflect the selected value

### Requirement: Switch shall use the switch ARIA pattern

Switch SHALL render a checkbox-based input with `role="switch"` whose `aria-checked` reflects the current state, toggled by the native checkbox interaction and bound like a checkbox.

#### Scenario: Switch state is exposed correctly

- **WHEN** a bound Switch is toggled on
- **THEN** `aria-checked` SHALL be true and the bound value SHALL be true

### Requirement: RadioGroup shall provide grouped native radios with accessible structure

RadioGroup SHALL render a `fieldset` with a `legend` containing Radio items that share a generated `name`, so native arrow-key navigation within the group applies. Group value SHALL bind to a single Field or raw value props carrying the selected item's value.

#### Scenario: Native keyboard navigation within the group

- **WHEN** focus is on a radio in a RadioGroup and the user presses an arrow key
- **THEN** selection SHALL move to the adjacent radio in the group per native radio behavior, updating the bound value

### Requirement: FormField shall compose label, control, and error region with correct ARIA

FormField SHALL render a `<label>` associated with its control, a slot for the control, and an error message region. When the bound field is touched and invalid, the control SHALL carry `aria-invalid="true"` and the error region SHALL be associated with the control via `aria-describedby`; otherwise the association SHALL be absent. Error text SHALL display only when the field is touched and invalid. Association ids SHALL be stable across re-renders of the FormField instance.

#### Scenario: Errors appear after blur, wired accessibly

- **WHEN** a required Field bound inside a FormField is left empty and blurred
- **THEN** the error message SHALL display, the control SHALL carry `aria-invalid="true"`, and the error region SHALL be referenced by the control's `aria-describedby`

#### Scenario: No error flash before interaction

- **WHEN** a form page renders for the first time with invalid but untouched fields
- **THEN** no error messages SHALL display and no `aria-invalid` SHALL be present

### Requirement: Controls shall expose invalid state for styling

Bound controls SHALL expose `data-invalid="true"` when their field is invalid and touched, matching the error-display gating, so themed and user CSS can style invalid states via a stable attribute hook.

#### Scenario: Invalid styling hook follows gating

- **WHEN** a bound control's field becomes invalid but remains untouched, and is later blurred
- **THEN** `data-invalid` SHALL be absent before the blur and `"true"` after it

### Requirement: Form controls shall ship as headless/themed pairs per the foundation contract

Each control and the FormField wrapper SHALL exist as headless components honoring the headless contract (behavior-only, state attributes, class pass-through) and themed components composing them with token-based defaults in the primitives stylesheet (including focus-visible rings, invalid states, and disabled states), re-exported at the `webcompy.ui` top level.

#### Scenario: Themed invalid state is visible

- **WHEN** a themed Input is in the touched-invalid state
- **THEN** its themed styling SHALL indicate the invalid state using semantic design tokens while keeping focus indication visible
