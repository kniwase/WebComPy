# UI Form Controls Specification (delta)

## ADDED Requirements

### Requirement: Form controls shall support Field binding and raw value binding

Each form control (Input, Textarea, Select, Checkbox, Switch, RadioGroup) SHALL accept either a `field` prop carrying a forms-module `Field` instance, or `value` plus change-callback props. With a `field`, the control SHALL bind through the framework's `:bind` mechanism so that value synchronization, `dirty` on write-back, and `touched` on blur follow the forms capability's rules. With raw props, the control SHALL behave as a plain controlled element whose change callback is invoked after write-back to the control's internal signal. Supplying both modes on one instance SHALL be an error.

#### Scenario: Field-bound input updates validation state

- **WHEN** an Input bound to a required Field receives user text and then loses focus
- **THEN** the Field's value SHALL reflect the text, `dirty` SHALL be true after the write-back, and `touched` SHALL be true after blur

#### Scenario: Raw value mode works without a Field

- **WHEN** an Input is given a value prop and a change callback without a Field
- **THEN** user edits SHALL invoke the change callback with the new value and no forms-module state SHALL be involved

#### Scenario: Both binding modes rejected

- **WHEN** a control is constructed with both a `field` prop and a `value` prop
- **THEN** the control SHALL raise an error identifying the conflict

### Requirement: Controls shall render native elements with framework binding

Input and Textarea SHALL render native `<input>`/`<textarea>` elements, Select SHALL render a native `<select>` populated from an options prop (value/label pairs), and Checkbox/Radio SHALL render native checkbox/radio inputs. Keyboard, mobile, and form-participation behavior SHALL come from the native elements; the framework SHALL add binding and state wiring only. Each control SHALL render through a named Light DOM custom element wrapper without breaking the native control's form participation or id-based ARIA references.

#### Scenario: Select renders options from props

- **WHEN** a Select is given three options
- **THEN** the native `<select>` SHALL contain three corresponding `<option>` elements and binding SHALL reflect the selected value

#### Scenario: Native control reaches the DOM inside its wrapper

- **WHEN** a themed Input renders in a browser
- **THEN** a native `<input>` SHALL be reachable in the document light DOM such that an external `<label for>` referencing the control's id resolves to it

### Requirement: Switch shall use the switch ARIA pattern

Switch SHALL render a checkbox-based input with `role="switch"` whose `aria-checked` reflects the current state, toggled by the native checkbox interaction and bound like a checkbox.

#### Scenario: Switch state is exposed correctly

- **WHEN** a bound Switch is toggled on
- **THEN** `aria-checked` SHALL be true and the bound value SHALL be true

### Requirement: RadioGroup shall render grouped native radios from an options prop

RadioGroup SHALL render a `fieldset` with a `legend` and one native radio per entry of its `options` prop (value/label pairs), with all radios sharing a `name` generated from the RadioGroup instance's hydration-stable transfer id, so native arrow-key navigation within the group applies. Group value SHALL bind to a single Field or raw value/change props carrying the selected item's value. The `Radio` control SHALL remain exported for custom compositions in which the author supplies the shared name.

#### Scenario: Native keyboard navigation within the group

- **WHEN** focus is on a radio in a RadioGroup and the user presses an arrow key
- **THEN** selection SHALL move to the adjacent radio in the group per native radio behavior, updating the bound value

#### Scenario: Group items share a generated name

- **WHEN** a RadioGroup renders three options
- **THEN** all three radio inputs SHALL carry the same generated `name` attribute value, distinct from that of another RadioGroup instance on the page

### Requirement: FormField shall compose label, control, and error region with correct ARIA

FormField SHALL render a `<label for>` associated with its control when a non-empty label text is given (group controls such as RadioGroup self-label with a `legend` and are used without a FormField label), a slot for the control, and an error message region. FormField SHALL provide its association ids — a control id and an error region id derived from its hydration-stable transfer id — through a component-scoped dependency-injection context; bound controls SHALL consume that context to set their native element's `id` and the error linkage, and SHALL remain fully functional standalone when no context is provided. When the bound field is touched and invalid, the control SHALL carry `aria-invalid="true"` and the error region SHALL be associated with the control via `aria-describedby`; otherwise the association SHALL be absent. Error text SHALL display only when the field is touched and invalid. Association ids SHALL be stable across re-renders of the FormField instance and identical between server-rendered markup and the hydrated client tree.

#### Scenario: Errors appear after blur, wired accessibly

- **WHEN** a required Field bound inside a FormField is left empty and blurred
- **THEN** the error message SHALL display, the control SHALL carry `aria-invalid="true"`, and the error region SHALL be referenced by the control's `aria-describedby`

#### Scenario: No error flash before interaction

- **WHEN** a form page renders for the first time with invalid but untouched fields
- **THEN** no error messages SHALL display and no `aria-invalid` SHALL be present

#### Scenario: SSR and hydration ids match

- **WHEN** a FormField and its control are server-rendered and then hydrated
- **THEN** the control's `id` and the error region's `id` in the hydrated tree SHALL equal those present in the server-rendered markup

### Requirement: Bound controls shall expose validation state via data-state

Bound controls SHALL expose `data-state="invalid"` on their root when their field is invalid and touched, and `data-state="valid"` otherwise, matching the error-display gating, so themed and user CSS can style invalid states through the headless contract's state-attribute vocabulary. Controls in raw value mode SHALL expose `data-state="valid"` (validation state is unknown without a Field).

#### Scenario: Invalid styling hook follows gating

- **WHEN** a bound control's field becomes invalid but remains untouched, and is later blurred
- **THEN** `data-state` SHALL be `"valid"` before the blur and `"invalid"` after it

### Requirement: Form controls shall ship as headless/themed pairs per the foundation contract

Each control and the FormField wrapper SHALL exist as headless components honoring the headless contract (behavior-only, `data-state`, class pass-through with documented part-class props) and themed components composing them with token-based defaults in the primitives stylesheet (including focus-visible rings, invalid states, and disabled states), re-exported at the `webcompy.ui` top level. Headless components SHALL register under `headless-*` custom element names and themed components under `webcompy-*` names.

#### Scenario: Themed invalid state is visible

- **WHEN** a themed Input is in the touched-invalid state
- **THEN** its themed styling SHALL indicate the invalid state using semantic design tokens while keeping focus indication visible

#### Scenario: Three import paths resolve correctly

- **WHEN** a developer imports `Input` from `webcompy.ui.headless`, from `webcompy.ui.components`, and from `webcompy.ui`
- **THEN** the first import SHALL yield the headless component and the second and third SHALL yield the themed component
