---
title: UI & Theme API
description: API reference for webcompy.ui components, headless primitives, theme management, styles, and code blocks.
---

# UI & Theme API

<!-- author:start:intro -->
API reference for `webcompy.ui`: themed components (`webcompy.ui.components`), accessible headless primitives (`webcompy.ui.headless`), theme state and composables (`webcompy.ui.theme`, `webcompy.ui.composables`), stylesheet helpers (`webcompy.ui._styles`), and code block lexers (`webcompy.ui.code_block`).
<!-- author:end:intro -->

<!-- generated:start -->

## Themed Components

### components.Accordion

```python
def Accordion(context: ComponentContext[ThemedAccordionProps]) -> Any
```

Key: `webcompy.ui.components._accordion:Accordion` · Exports: `from webcompy.ui import Accordion`, `from webcompy.ui.components import Accordion`

Render a themed accordion.

Composes the headless `Accordion` and forwards the themed Collapse class hooks and default transition class set to every item, so items share the collapse visuals (bordered sections, animated natural-height expansion). Behavior, the open policy, and accessibility come from the headless component; user classes are appended after the themed defaults.

**Args:**

- `context`: Component context carrying the `items`, `single_open`, `on_toggle`, and `class_name` props.

**Returns:** The rendered themed accordion element.

### components.Alert

```python
def Alert(context: ComponentContext[ThemedAlertProps]) -> Any
```

Key: `webcompy.ui.components._alert:Alert` · Exports: `from webcompy.ui import Alert`, `from webcompy.ui.components import Alert`

Render a themed inline alert.

Composes the headless `Alert` and supplies the default `webcompy-alert` classes with a `webcompy-alert--{variant}` modifier whose rules live in the shipped primitives stylesheet. Role mapping, dismissal, and accessibility come from the headless component; user classes are appended after the themed defaults.

**Args:**

- `context`: Component context carrying the `variant`, `dismissable`, `on_dismiss`, `dismiss_label`, and class pass-through props, plus the message in the `default` slot.

**Returns:** The rendered themed alert element.

### components.Badge

```python
def Badge(context: ComponentContext[ThemedBadgeProps]) -> Any
```

Key: `webcompy.ui.components._badge:Badge` · Exports: `from webcompy.ui import Badge`, `from webcompy.ui.components import Badge`

Render a themed status badge.

Composes the headless `Badge` with the default `webcompy-badge` class plus a `webcompy-badge--{variant}` modifier consuming design tokens. User classes are appended after the themed defaults.

**Args:**

- `context`: Component context carrying the `variant` and `class_name` props, plus the label in the `default` slot.

**Returns:** The rendered themed badge element.

### components.Card

```python
def Card(context: ComponentContext[ThemedCardProps]) -> Any
```

Key: `webcompy.ui.components._card:Card` · Exports: `from webcompy.ui import Card`, `from webcompy.ui.components import Card`

Render a themed structural card.

Composes the headless `Card` with the default `webcompy-card` and region classes (header/body/footer) whose token-based rules live in the shipped primitives stylesheet. Region rendering and slot wiring come from the headless component; user classes are appended after the themed defaults so user rules win at equal specificity.

**Args:**

- `context`: Component context carrying the region class pass-through props and the `header` / `default` / `footer` slots.

**Returns:** The rendered themed card element.

### components.Checkbox

```python
def Checkbox(context: ComponentContext[CheckboxProps]) -> Any
```

Key: `webcompy.ui.components._checkbox:Checkbox` · Exports: `from webcompy.ui import Checkbox`, `from webcompy.ui.components import Checkbox`

Render a themed checkbox.

Composes the headless `Checkbox` and supplies token-based default classes for the root and its parts; behavior and accessibility wiring are inherited.

**Args:**

- `context`: Component context with the checkbox props.

**Returns:** The themed checkbox element.

### components.Collapse

```python
def Collapse(context: ComponentContext[ThemedCollapseProps]) -> Any
```

Key: `webcompy.ui.components._collapse:Collapse` · Exports: `from webcompy.ui import Collapse`, `from webcompy.ui.components import Collapse`

Render a themed collapsible disclosure.

Composes the headless `Collapse` with the default `webcompy-collapse` transition class set. The expand/collapse animation uses the grid-template-rows technique (`0fr` to `1fr` on the content element with direct children clamped to `min-height: 0`), which animates to natural content height without any JS measurement; headless users can substitute their own technique through `transition_name`. Pass `animated=False` for instant expansion. Behavior and accessibility are inherited from the headless component; user classes are appended after the themed defaults so user rules win at equal specificity. The `open` prop accepts a signal-like object as well as a plain boolean (forwarded to the headless component unchanged).

**Args:**

- `context`: Component context carrying the `open`, `on_toggle`, `animated`, and class pass-through props, plus the `trigger` and `default` slots.

**Returns:** The rendered themed collapse element.

### components.Drawer

```python
def Drawer(context: ComponentContext[DrawerProps]) -> Any
```

Key: `webcompy.ui.components._drawer:Drawer` · Exports: `from webcompy.ui import Drawer`, `from webcompy.ui.components import Drawer`

Render a themed drawer.

**Args:**

- `context`: Component context with drawer props.

**Returns:** The themed drawer element.

### components.Dropdown

```python
def Dropdown(context: ComponentContext[DropdownProps]) -> Any
```

Key: `webcompy.ui.components._dropdown:Dropdown` · Exports: `from webcompy.ui import Dropdown`, `from webcompy.ui.components import Dropdown`

Render a themed dropdown.

The menu is anchored to the trigger by default: the framework measures the trigger position while open and keeps the menu pinned below it across scroll and resize. Pass `positioning="none"` to control the menu position entirely through consumer CSS, and `align="end"` to right-align the menu to the trigger's end edge.

**Args:**

- `context`: Component context with dropdown props and slots.

**Returns:** The themed dropdown element.

### components.FormField

```python
def FormField(context: ComponentContext[FormFieldProps]) -> Any
```

Key: `webcompy.ui.components._form_field:FormField` · Exports: `from webcompy.ui import FormField`, `from webcompy.ui.components import FormField`

Render a themed form field wrapper.

Composes the headless `FormField` and supplies token-based default classes for the label, control wrapper, and error region; the error gating behavior is inherited. Because slot content evaluates eagerly in this wrapper's pass, the association ids are generated here from the instance's transfer id, provided to the DI scope for the duration of this render pass only (siblings rendered afterwards never observe them), and forwarded to the headless wrapper as `control_id` / `error_id` props so caption, control, and error region agree.

**Args:**

- `context`: Component context with the field props and the control slot content.

**Returns:** The themed form field element.

### components.Input

```python
def Input(context: ComponentContext[InputProps]) -> Any
```

Key: `webcompy.ui.components._input:Input` · Exports: `from webcompy.ui import Input`, `from webcompy.ui.components import Input`

Render a themed text input.

Composes the headless `Input` and supplies token-based default classes; all binding, state, and accessibility behavior is inherited from the headless component. The user `class_name` is appended after the themed default so user rules win at equal specificity.

**Args:**

- `context`: Component context with the input props.

**Returns:** The themed input element.

### components.Modal

```python
def Modal(context: ComponentContext[ModalProps]) -> Any
```

Key: `webcompy.ui.components._modal:Modal` · Exports: `from webcompy.ui import Modal`, `from webcompy.ui.components import Modal`

Render a themed modal dialog.

**Args:**

- `context`: Component context with modal props.

**Returns:** The themed modal element.

### components.Progress

```python
def Progress(context: ComponentContext[ThemedProgressProps]) -> Any
```

Key: `webcompy.ui.components._progress:Progress` · Exports: `from webcompy.ui import Progress`, `from webcompy.ui.components import Progress`

Render a themed progress bar.

Composes the headless `Progress` with the default `webcompy-progress` track and `webcompy-progress-fill` classes whose rules live in the shipped primitives stylesheet; the indeterminate mode animates an internal sweep and honors reduced motion. ARIA semantics and the reactive value binding come from the headless component, whose `value`, `min`, `max`, and `indeterminate` props accept signal-like objects as well as plain values.

**Args:**

- `context`: Component context carrying the `value`, `min`, `max`, `indeterminate`, `aria_label`, and class pass-through props.

**Returns:** The rendered themed progress element.

### components.Radio

```python
def Radio(context: ComponentContext[RadioProps]) -> Any
```

Key: `webcompy.ui.components._radio:Radio` · Exports: `from webcompy.ui import Radio`, `from webcompy.ui.components import Radio`

Render a themed standalone native radio for custom group compositions.

**Args:**

- `context`: Component context with the radio props.

**Returns:** The themed radio input element.

### components.RadioGroup

```python
def RadioGroup(context: ComponentContext[RadioGroupProps]) -> Any
```

Key: `webcompy.ui.components._radio:RadioGroup` · Exports: `from webcompy.ui import RadioGroup`, `from webcompy.ui.components import RadioGroup`

Render a themed radio group (fieldset with same-name radios).

Composes the headless `RadioGroup` and supplies token-based default classes for the fieldset, legend, items, and radios; the shared generated `name` and native keyboard behavior are inherited.

**Args:**

- `context`: Component context with the radio group props.

**Returns:** The themed fieldset element.

### components.Select

```python
def Select(context: ComponentContext[SelectProps]) -> Any
```

Key: `webcompy.ui.components._select:Select` · Exports: `from webcompy.ui import Select`, `from webcompy.ui.components import Select`

Render a themed native select populated from an options prop.

Composes the headless `Select` and supplies token-based default classes; behavior and accessibility wiring are inherited.

**Args:**

- `context`: Component context with the select props.

**Returns:** The themed select element.

### components.Skeleton

```python
def Skeleton(context: ComponentContext[ThemedSkeletonProps]) -> Any
```

Key: `webcompy.ui.components._skeleton:Skeleton` · Exports: `from webcompy.ui import Skeleton`, `from webcompy.ui.components import Skeleton`

Render a themed loading placeholder.

Composes the headless `Skeleton` with the default `webcompy-skeleton` class plus a `webcompy-skeleton--{shape}` modifier. The themed layer supplies a shimmer animation that is suppressed under reduced motion. The `aria-hidden` decoration marking comes from the headless component; pair skeletons with an accessible loading indicator in the surrounding container.

**Args:**

- `context`: Component context carrying the `shape`, `width`, `height`, and `class_name` props.

**Returns:** The rendered themed skeleton element.

### components.Spinner

```python
def Spinner(context: ComponentContext[ThemedSpinnerProps]) -> Any
```

Key: `webcompy.ui.components._spinner:Spinner` · Exports: `from webcompy.ui import Spinner`, `from webcompy.ui.components import Spinner`

Render a themed loading spinner with token-based animation.

Composes the headless `Spinner` and supplies the default `webcompy-spinner` classes whose rules live in the shipped primitives stylesheet inside the `components` layer. The `size` prop selects the `sm`, `md` (default), or `lg` variant. The animation pauses under `prefers-reduced-motion`. Behavior, accessibility, and the `class_name` pass-through are inherited from the headless component; user classes are appended after the themed defaults so user rules win at equal specificity.

**Args:**

- `context`: Component context carrying the `label`, `aria_label`, `class_name`, and `size` props.

**Returns:** The rendered themed spinner element.

### components.Switch

```python
def Switch(context: ComponentContext[SwitchProps]) -> Any
```

Key: `webcompy.ui.components._switch:Switch` · Exports: `from webcompy.ui import Switch`, `from webcompy.ui.components import Switch`

Render a themed switch.

Composes the headless `Switch` and supplies token-based default classes for the track/thumb visuals and its parts; the `role="switch"` semantics and binding behavior are inherited.

**Args:**

- `context`: Component context with the switch props.

**Returns:** The themed switch element.

### components.Tabs

```python
def Tabs(context: ComponentContext[ThemedTabsProps]) -> Any
```

Key: `webcompy.ui.components._tabs:Tabs` · Exports: `from webcompy.ui import Tabs`, `from webcompy.ui.components import Tabs`

Render themed tabs with token-based defaults.

Composes the headless `Tabs` and supplies the default `webcompy-tabs*` classes whose rules live in the shipped primitives stylesheet inside the `components` layer. Panel switching is instant by design (inactive panels stay mounted and hidden); visual effects can be attached to the `data-state` attributes through the part class hooks. Behavior, accessibility, and class pass-through are inherited from the headless component; user classes are appended after the themed defaults so user rules win at equal specificity. The `active` prop accepts a signal-like object as well as a plain string (forwarded to the headless component unchanged).

**Args:**

- `context`: Component context carrying the `tabs`, `active`, `on_select`, `aria_label`, and class pass-through props.

**Returns:** The rendered themed tabs element.

### components.Textarea

```python
def Textarea(context: ComponentContext[TextareaProps]) -> Any
```

Key: `webcompy.ui.components._textarea:Textarea` · Exports: `from webcompy.ui import Textarea`, `from webcompy.ui.components import Textarea`

Render a themed multiline text area.

Composes the headless `Textarea` and supplies token-based default classes; behavior and accessibility wiring are inherited.

**Args:**

- `context`: Component context with the textarea props.

**Returns:** The themed textarea element.

### components.ToastHost

```python
def ToastHost(context: ComponentContext[ToastHostProps]) -> Any
```

Key: `webcompy.ui.components._toast:ToastHost` · Exports: `from webcompy.ui import ToastHost`, `from webcompy.ui.components import ToastHost`

Render a themed toast host.

**Args:**

- `context`: Component context with toast host props.

**Returns:** The themed toast host element.

## Headless Primitives

### headless.Accordion

```python
def Accordion(context: ComponentContext[AccordionProps]) -> Any
```

Key: `webcompy.ui.headless._accordion:Accordion` · Exports: `from webcompy.ui.headless import Accordion`

Render a stack of Collapse items sharing one open-state.

Each item renders as a headless `Collapse` whose open flag is a view of the accordion's shared set of open keys, so composition keeps Collapse independently useful while the policies apply across items. Multi-open is the default; `single_open=True` closes the other items whenever one opens. Item identity is key-based. `on_toggle` is invoked with `(key, is_open)` for every item whose open state changed, including siblings closed by the single-open policy (closures first, then openings). Only one level of items is supported; nesting accordions deeper is untested and documented as unsupported. The `items` list is read once at setup; a different item set requires remounting. No visual styling is emitted.

**Args:**

- `context`: Component context carrying the `items`, `single_open`, `on_toggle`, `transition_name`, and class pass-through props. `transition_name`, `class_trigger`, and `class_content` are forwarded to every composed Collapse.

**Returns:** The rendered headless accordion element.

### headless.Alert

```python
def Alert(context: ComponentContext[AlertProps]) -> Any
```

Key: `webcompy.ui.headless._alert:Alert` · Exports: `from webcompy.ui.headless import Alert`

Render an inline feedback region with variant-driven semantics.

The error and warning variants announce assertively through `role="alert"`; info and success are polite via `role="status"`. When `dismissable` is set the alert renders an accessible dismiss button; activating it hides the alert (the root carries the boolean `hidden` attribute, removing it from the accessibility tree) and invokes the optional `on_dismiss` callback. The `data-variant` attribute mirrors the variant for styling hooks; no interaction state beyond dismissal is exposed. No visual styling is emitted.

**Args:**

- `context`: Component context carrying the `variant`, `dismissable`, `on_dismiss`, `dismiss_label`, and class pass-through props. The `default` slot supplies the message.

**Returns:** The rendered headless alert element.

### headless.Badge

```python
def Badge(context: ComponentContext[BadgeProps]) -> Any
```

Key: `webcompy.ui.headless._badge:Badge` · Exports: `from webcompy.ui.headless import Badge`

Render a compact status label.

The `data-variant` attribute carries the variant for styling hooks (unknown values fall back to `neutral`). The badge is a static label: it carries no interaction state and emits no visual styling.

**Args:**

- `context`: Component context carrying the `variant` and `class_name` props. The `default` slot supplies the label content.

**Returns:** The rendered headless badge element.

### headless.Card

```python
def Card(context: ComponentContext[CardProps]) -> Any
```

Key: `webcompy.ui.headless._card:Card` · Exports: `from webcompy.ui.headless import Card`

Render a structural container with header, body, and footer regions.

Card is behavior-free: it only wires named regions through so layout containers share class hooks instead of each application re-deriving them. A region element is rendered only when its slot is supplied (`header`, `default` for the body, `footer`). Part class props style individual regions; `class_name` targets the root. No visual styling is emitted.

**Args:**

- `context`: Component context carrying the region class pass-through props and the `header` / `default` / `footer` slots.

**Returns:** The rendered headless card element.

### headless.Checkbox

```python
def Checkbox(context: ComponentContext[CheckboxProps]) -> Any
```

Key: `webcompy.ui.headless._checkbox:Checkbox` · Exports: `from webcompy.ui.headless import Checkbox`

Render a native checkbox bound through the framework `:bind` mechanism.

The checkbox binds to either a forms-module `Field` carrying a `bool` value (`field` prop) or a raw value (`value` plus optional `on_change`); supplying both is an error. When a standalone `label` prop is given the input is wrapped in a native `<label>` for implicit association; inside a `FormField` the `label` prop is ignored because the FormField supplies the caption, and the native input adopts the field's generated ids instead. In the touched-invalid state the input carries `data-state="invalid"` and `aria-invalid`.

**Args:**

- `context`: Component context with the checkbox props. `class_name` targets the root element (the wrapping label when present, otherwise the input), `class_input` the input element, and `class_label` the standalone label.

**Returns:** The rendered checkbox element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied or `on_change` is given without a bound value.

### headless.Collapse

```python
def Collapse(context: ComponentContext[CollapseProps]) -> Any
```

Key: `webcompy.ui.headless._collapse:Collapse` · Exports: `from webcompy.ui.headless import Collapse`

Render a disclosure trigger with an animated content region.

The trigger is a `button` carrying `aria-expanded`, `aria-controls`, and `data-state="open" | "closed"`. Activating it expands/collapses the content region, which is mounted only while open and animates through the Transition capability (a None-to-element swap, so the enter/leave sequences always run). While mounted the content element carries `data-state="open"`. The open state follows the overlay control model: an omitted `open` prop lets the component own internal state (uncontrolled); a signal-like value is written through on toggle; a plain boolean keeps the component parent-driven with changes delivered to `on_toggle`. Generated ids are per-instance and hydration-stable. No visual styling is emitted; animate the natural height in the themed layer via CSS-only techniques (see the themed Collapse documentation).

**Args:**

- `context`: Component context carrying the `open`, `on_toggle`, `transition_name`, and class pass-through props, plus the `default` slot rendered inside the content region.

**Returns:** The rendered headless collapse element.

### headless.Drawer

```python
def Drawer(context: ComponentContext[DrawerProps]) -> Any
```

Key: `webcompy.ui.headless._drawer:Drawer` · Exports: `from webcompy.ui.headless import Drawer`

Render an edge drawer with the modal accessibility contract.

**Args:**

- `context`: Component context carrying drawer props and default slot.

**Returns:** The rendered drawer element.

### headless.Dropdown

```python
def Dropdown(context: ComponentContext[DropdownProps]) -> Any
```

Key: `webcompy.ui.headless._dropdown:Dropdown` · Exports: `from webcompy.ui.headless import Dropdown`

Render a dropdown trigger and menu with keyboard navigation.

The trigger is a button and the menu is a `role="menu"` list whose items carry `role="menuitem"`. The menu renders through `Teleport` to `body` wrapped in a `Transition`. While open, the menu is anchored to the trigger: the trigger rect is measured through the DOM port and supplied as inline `top`/`left` or `top`/`right` offsets, re-measured on document scroll and window resize.

**Args:**

- `context`: Component context with dropdown props and named slots `trigger` and `default`. `align` (`"start"` or `"end"`) picks the horizontal anchor edge; `positioning` (`"anchor"` or `"none"`) disables the built-in anchoring when set to `"none"`.

**Returns:** The rendered dropdown element.

### headless.FormField

```python
def FormField(context: ComponentContext[FormFieldProps]) -> Any
```

Key: `webcompy.ui.headless._form_field:FormField` · Exports: `from webcompy.ui.headless import FormField`

Compose a caption, a bound control, and an accessible error region.

The field's association ids are generated from the instance's hydration-stable transfer id (or taken from the `control_id`/ `error_id` props when a themed wrapper supplies them) and provided through the component DI scope for the duration of this render pass only, so controls rendered afterwards as siblings never observe them. Bound controls rendered in the default slot adopt the ids: the native control receives the `id` referenced by the caption's `<label for>`, and, while the field is touched and invalid, `aria-invalid="true"` plus an `aria-describedby` link to the error region. Error messages render only in the touched-invalid state, so an invalid-but-untouched form shows nothing on load. Group controls (`RadioGroup`) self-label with a `legend`; pass no `label` here for those. The root carries `data-state` following the same gating. The `field` prop is required; raw value mode controls are used without a FormField.

**Args:**

- `context`: Component context with the field props and the control slot content. `class_name` targets the root, `class_label` the caption, `class_control` the control wrapper, and `class_error` the error region.

**Returns:** The rendered wrapper element.

**Raises:**

- `WebComPyException`: When no `field` prop is given.

### headless.Input

```python
def Input(context: ComponentContext[InputProps]) -> Any
```

Key: `webcompy.ui.headless._input:Input` · Exports: `from webcompy.ui.headless import Input`

Render a native text input bound through the framework `:bind` mechanism.

The input binds to either a forms-module `Field` (`field` prop) or a raw value (`value` plus optional `on_change`); supplying both is an error. Inside a `FormField` the native element adopts the field's generated ids so the label association and error description resolve; standalone the control renders without them. In the touched-invalid state the input carries `data-state="invalid"` and `aria-invalid`.

**Args:**

- `context`: Component context with the input props. `input_type` selects the native type (one of text, email, password, search, tel, url, number) and stays static.

**Returns:** The rendered native `<input>` element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied, an unsupported `input_type` is requested, or `on_change` is given without a bound value.

### headless.Modal

```python
def Modal(context: ComponentContext[ModalProps]) -> Any
```

Key: `webcompy.ui.headless._modal:Modal` · Exports: `from webcompy.ui.headless import Modal`

Render an accessible modal dialog without visual styling.

The dialog renders through `Teleport` to `body` wrapped in a `Transition`. While open, focus is trapped, Escape invokes `on_close`, and an optional backdrop click invokes `on_close`. Focus returns to the trigger on close.

**Args:**

- `context`: Component context carrying modal props and the default slot for panel content.

**Returns:** The rendered modal element.

### headless.Progress

```python
def Progress(context: ComponentContext[ProgressProps]) -> Any
```

Key: `webcompy.ui.headless._progress:Progress` · Exports: `from webcompy.ui.headless import Progress`

Render a progressbar with determinate or indeterminate semantics.

The root carries `role="progressbar"` with reactive `aria-valuemin` and `aria-valuemax` from the bounds props; reversed bounds (`min` greater than `max`) are normalized by swapping so the emitted ARIA stays self-consistent. In determinate mode it sets `aria-valuenow` from the value clamped to the bounds and exposes `data-state="determinate"`; in indeterminate mode `aria-valuenow` is omitted (an ARIA progressbar without a current value is indeterminate) and `data-state="indeterminate"` is exposed. Supply `aria_label` for the accessible name; without it the progressbar renders unnamed. A fill element is provided for the determinate bar; its `width` style tracks the clamped percentage (indeterminate visuals belong to the themed layer). No other visual styling is emitted.

**Args:**

- `context`: Component context carrying the `value`, `min`, `max`, `indeterminate`, `aria_label`, and class pass-through props.

**Returns:** The rendered headless progress element.

### headless.Radio

```python
def Radio(context: ComponentContext[RadioProps]) -> Any
```

Key: `webcompy.ui.headless._radio:Radio` · Exports: `from webcompy.ui.headless import Radio`

Render a standalone native radio for custom group compositions.

The radio's `checked` state compares the shared group binding (a `Field` or raw `Signal` in the `value` prop) with the static `option_value` prop, and selecting it writes `option_value` back through the framework `:bind` mechanism. A plain (non-Signal) `value` is rejected: the group signal must be shared across the radios, so bind a `Field` or pass a `Signal`. The caller supplies the shared `name` so native arrow-key navigation applies; `RadioGroup` is the intended default for grouped radios.

**Args:**

- `context`: Component context with the radio props.

**Returns:** The rendered native `<input type="radio">` element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied, no binding is given, `value` carries a plain non-Signal value, or `option_value`/`name` are missing.

### headless.RadioGroup

```python
def RadioGroup(context: ComponentContext[RadioGroupProps]) -> Any
```

Key: `webcompy.ui.headless._radio:RadioGroup` · Exports: `from webcompy.ui.headless import RadioGroup`

Render a fieldset of same-name native radios from an options prop.

The group binds the selected item's string value to either a forms-module `Field` (`field` prop) or a raw value (`value` plus optional `on_change`); supplying both is an error. One radio per option is rendered inside a native `<label>`, all sharing a `name` generated from the instance's hydration-stable transfer id, so native arrow-key navigation moves selection within the group without custom keyboard code. The optional `legend` captions the group (the group self-labels; a surrounding `FormField` should omit its `label` for group controls). In the touched-invalid state the fieldset carries `data-state="invalid"` and `aria-invalid`.

**Args:**

- `context`: Component context with the radio group props. `class_name` targets the fieldset root, `class_legend` the legend, `class_input` the radios, and `class_label` the option labels.

**Returns:** The rendered `<fieldset>` element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied or no binding is given.

### headless.Select

```python
def Select(context: ComponentContext[SelectProps]) -> Any
```

Key: `webcompy.ui.headless._select:Select` · Exports: `from webcompy.ui.headless import Select`

Render a native select populated from an options prop.

The select binds to either a forms-module `Field` (`field` prop) or a raw value (`value` plus optional `on_change`); supplying both is an error. Bound values are option strings: the Signal must carry a `str` value, and each option's `value` is written back unchanged on selection. Options are rendered as native `<option>` elements, each reflecting the `selected` state so server-rendered output matches the current value. Inside a `FormField` the native element adopts the field's generated ids; standalone the control renders without them.

**Args:**

- `context`: Component context with the select props. `options` is a sequence of `SelectOption` value/label pairs; an empty label falls back to the option value.

**Returns:** The rendered native `<select>` element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied or `on_change` is given without a bound value.

### headless.Skeleton

```python
def Skeleton(context: ComponentContext[SkeletonProps]) -> Any
```

Key: `webcompy.ui.headless._skeleton:Skeleton` · Exports: `from webcompy.ui.headless import Skeleton`

Render a decorative loading placeholder.

The placeholder is marked `aria-hidden="true"`: skeletons are visual decoration and must not reach assistive technology. The surrounding container must carry the accessible loading indication (e.g. a `Spinner` with `role="status"` or visible loading text). `shape` selects the geometry hook (`data-shape`: rectangle, line, or circle; unknown values fall back to rectangle); optional `width` and `height` strings are applied as inline styles. The shimmer animation belongs to the themed layer.

**Args:**

- `context`: Component context carrying the `shape`, `width`, `height`, and `class_name` props.

**Returns:** The rendered headless skeleton element.

### headless.Spinner

```python
def Spinner(context: ComponentContext[SpinnerProps]) -> Any
```

Key: `webcompy.ui.headless._spinner:Spinner` · Exports: `from webcompy.ui.headless import Spinner`

Render an accessible loading status region without visual styling.

The root element carries `role="status"`, `data-state="loading"`, and the framework class followed by the user `class_name` classes. The accessible name comes from `label` rendered as visually hidden text; when `label` is empty, `aria_label` is applied as the `aria-label` attribute instead. Supplying neither leaves the status region unnamed. No colors, spacing, typography, or animation are emitted; style the component through `class_name` and the `data-state` attribute.

**Args:**

- `context`: Component context carrying the `label`, `aria_label`, and `class_name` props.

**Returns:** The rendered headless spinner element.

### headless.Switch

```python
def Switch(context: ComponentContext[SwitchProps]) -> Any
```

Key: `webcompy.ui.headless._switch:Switch` · Exports: `from webcompy.ui.headless import Switch`

Render a checkbox-based switch with `role="switch"` semantics.

The switch binds like a `Checkbox` (`field` or `value` plus optional `on_change`, mutually exclusive) and toggles through the native checkbox interaction, preserving keyboard behavior. The input exposes `aria-checked` reflecting the current state. A standalone `label` wraps the input in a `<label>`; inside a `FormField` the label prop is ignored and the input adopts the field's generated ids.

**Args:**

- `context`: Component context with the switch props. `class_name` targets the root (wrapping label or input), `class_input` the input, and `class_label` the standalone label.

**Returns:** The rendered switch element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied or `on_change` is given without a bound value.

### headless.Tabs

```python
def Tabs(context: ComponentContext[TabsProps]) -> Any
```

Key: `webcompy.ui.headless._tabs:Tabs` · Exports: `from webcompy.ui.headless import Tabs`

Render an accessible tablist whose panels all stay mounted.

The root contains a `role="tablist"` bar of `role="tab"` buttons followed by every `role="tabpanel"`. Inactive panels are hidden with the boolean `hidden` attribute instead of being unmounted, so panel internal state (form input, scroll, component lifecycle) survives switches and switching is instant. Tab switching drives no animation: element replacement is outside the Transition capability's contract.

The active tab resolves in three modes: an omitted `active` prop lets the component own internal state (uncontrolled); a `SignalBase` value is written through on activation; a plain string keeps the component parent-controlled, with changes delivered only to `on_select`. Each tab carries `aria-selected`, `aria-controls` and `data-state="active" | "inactive"` with roving focus semantics (active `tabindex="0"`, inactive `"-1"`); Left/Right arrows move focus with wrapping and activate automatically, Home/End jump to the first/last tab. Generated ids are per-instance and hydration-stable. The `tabs` list is read once at setup; a different tab set requires remounting. Style through `class_name` and the part class props and the `data-state` attributes.

**Args:**

- `context`: Component context carrying the `tabs`, `active`, `on_select`, `aria_label`, and class pass-through props.

**Returns:** The rendered headless tabs element.

### headless.Textarea

```python
def Textarea(context: ComponentContext[TextareaProps]) -> Any
```

Key: `webcompy.ui.headless._textarea:Textarea` · Exports: `from webcompy.ui.headless import Textarea`

Render a native textarea bound through the framework `:bind` mechanism.

The textarea binds to either a forms-module `Field` (`field` prop) or a raw value (`value` plus optional `on_change`); supplying both is an error. Inside a `FormField` the native element adopts the field's generated ids; standalone the control renders without them. The bound text content is the reactive value (textareas expose no `value` attribute in markup), matching the framework binding rules.

**Args:**

- `context`: Component context with the textarea props. `rows` sets the visible line count.

**Returns:** The rendered native `<textarea>` element.

**Raises:**

- `WebComPyException`: When both binding modes are supplied or `on_change` is given without a bound value.

### headless.ToastHost

```python
def ToastHost(context: ComponentContext[ToastHostProps]) -> Any
```

Key: `webcompy.ui.headless._toast:ToastHost` · Exports: `from webcompy.ui.headless import ToastHost`

Render a toast queue inside a Teleport'd live region.

Each toast item is wrapped in its own `Transition` with `on_leave_end` removing the record from the queue.

**Args:**

- `context`: Component context with toast queue and handlers.

**Returns:** The rendered host element.

## Theme, Composables & Styles

### get_styles_dir

```python
def get_styles_dir() -> Traversable
```

Key: `webcompy.ui._styles:get_styles_dir` · Exports: `from webcompy.ui._styles import get_styles_dir`

Return the directory containing the framework stylesheet files.

### get_styles_file

```python
def get_styles_file(name: str) -> bytes | None
```

Key: `webcompy.ui._styles:get_styles_file` · Exports: `from webcompy.ui._styles import get_styles_file`

Return the content of one framework stylesheet file.

**Args:**

- `name`: Filename relative to the styles directory.

**Returns:** The file content as bytes, or `None` when `name` is not one of the bundled framework stylesheets or the file is missing.

### get_styles_files

```python
def get_styles_files() -> dict[str, bytes]
```

Key: `webcompy.ui._styles:get_styles_files` · Exports: `from webcompy.ui._styles import get_styles_files`

Return a mapping of relative filename to file content for the framework CSS.

Works both for installed wheels and for source-tree development because `importlib.resources.files` resolves to the package data on disk in either case.

### read_theme_from_cookie

```python
def read_theme_from_cookie(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> Theme
```

Key: `webcompy.ui.theme._server:read_theme_from_cookie` · Exports: `from webcompy.ui.theme import read_theme_from_cookie`

Extract the theme preference from request headers.

Searches the `Cookie` header for the `webcompy-theme` cookie and decodes its value.

**Args:**

- `headers`: Request headers as a mapping or a sequence of `(name, value)` pairs.

**Returns:** The requested theme, or `Theme.SYSTEM` when the cookie is absent, empty, or contains an unrecognized value.

### Theme

```python
class Theme(StrEnum)
```

Key: `webcompy.ui.theme._theme:Theme` · Exports: `from webcompy.ui.theme import Theme`

Color scheme preference with light, dark, and system variants.

Each member's value is the string form persisted in the theme cookie.

### THEME_KEY

```python
THEME_KEY: InjectKey[object] = InjectKey[object]('webcompy-ui-theme')
```

Key: `webcompy.ui.theme._theme:THEME_KEY` · Exports: `from webcompy.ui.theme import THEME_KEY`

DI key under which an application provides its `ThemeManager`.

### ThemeManager

```python
class ThemeManager:
    def __init__(self, app: WebComPyApp, render_context: Any, initial: Theme) -> None
```

Key: `webcompy.ui.theme._manager:ThemeManager` · Exports: `from webcompy.ui.theme import ThemeManager`

Reactive theme state holding a `Signal[Theme]` and a derived CSS style.

The derived style emits explicit `color-scheme` declarations and dark-token overrides for the active theme, registered with the app via `register_style`. Theme changes are persisted through the theme cookie unless persistence is disabled in the app configuration.

**Args:**

- `app`: Owning application, used to register the reactive style.
- `render_context`: Active render context.
- `initial`: Starting preference; a `Theme` member, a matching string, or any other value normalized to `Theme.SYSTEM`.

**Attributes:**

- `signal`: Reactive signal holding the current theme.
- `value`: Current theme.

#### Members

**`cycle`** (method)

```python
def cycle(self) -> None
```

Advance the theme through light, dark, then system, wrapping around.

**`register_style`** (method)

```python
def register_style(self) -> None
```

Register the reactive theme CSS with the app.

**`set`** (method)

```python
def set(self, theme: Theme) -> None
```

Set the active theme and persist it when persistence is enabled.

**Args:**

- `theme`: Theme to activate.

**`signal`** (property)

```python
@property
def signal(self) -> Signal[Theme]
```

Reactive signal holding the current theme.

**`toggle`** (method)

```python
def toggle(self) -> None
```

Toggle light and dark, resolving `SYSTEM` against the OS preference.

**`value`** (property)

```python
@property
def value(self) -> Theme
```

Current theme.

### ToastRecord

```python
class ToastRecord:
    id: str
    message: str
    variant: Literal['info', 'success', 'warning', 'error']
    duration: float | None
    leaving: bool = False
```

Key: `webcompy.ui.composables._toast:ToastRecord` · Exports: `from webcompy.ui.composables import ToastRecord`

Single toast entry.

### ToastState

```python
class ToastState:
    def __init__(
        self,
        toasts: Signal[list[ToastRecord]],
        dismiss: Callable[[str], None],
    ) -> None
```

Key: `webcompy.ui.composables._toast:ToastState` · Exports: `from webcompy.ui.composables import ToastState`

Queue state and dismissal handle for a Toast host.

### use_theme

```python
def use_theme() -> tuple[Signal[Theme], ThemeController]
```

Key: `webcompy.ui.composables._theme:use_theme` · Exports: `from webcompy.ui.composables import use_theme`, `from webcompy.ui.theme import use_theme`

Resolve the reactive theme signal and a `ThemeController` from DI.

Requires a `ThemeManager` to have been provided under `THEME_KEY` in the active DI scope.

**Returns:** A `(signal, controller)` pair: the reactive `Signal[Theme]` and a `ThemeController` bound to the same manager.

**Raises:**

- `LookupError`: If no theme manager is registered in the active DI scope.
- `TypeError`: If the injected value is not a `ThemeManager`.

### use_toast

```python
def use_toast() -> tuple[ToastPush, ToastState]
```

Key: `webcompy.ui.composables._toast:use_toast` · Exports: `from webcompy.ui.composables import use_toast`

Create a component-scoped toast queue.

**Returns:** A tuple of a push function and the queue state. The push function accepts a message, variant, and duration in seconds (`None` disables auto-dismiss).

## Code Block & Syntax Highlighting

### BashLexer

```python
class BashLexer
```

Key: `webcompy.ui.code_block.lexers._bash:BashLexer` · Exports: `from webcompy.ui.code_block.lexers import BashLexer`

Tokenize bash/shell source with a single grouped regular expression.

Words are classified as keywords or builtins against fixed sets; shell variable references like `$NAME` and `${NAME}` are preserved verbatim as identifier tokens.

**Attributes:**

- `name`: Primary name `"bash"`.
- `aliases`: Alternative lookup names (`"sh"`, `"shell"`, `"zsh"`).
- `file_extensions`: Registered file extensions (`.sh`, `.bash`, `.zsh`).

#### Members

**`tokenize`** (method)

```python
def tokenize(self, code: str) -> Iterable[Token]
```

Tokenize bash source in source order.

**Args:**

- `code`: Source text to tokenize; empty input yields no tokens.

**Yields:** Token: Classified spans whose concatenated values equal `code` exactly.

### CodeBlock

```python
def CodeBlock(context: ComponentContext[CodeBlockProps]) -> Any
```

Key: `webcompy.ui.code_block._component:CodeBlock` · Exports: `from webcompy.ui.code_block import CodeBlock`

Render source code with syntax highlighting inside `pre`/`code`.

Tokenizes the code with the lexer registered for `lang` and renders one `<span>` per token as a direct child of the `<code>` element. When the language is unknown or tokenization produces no tokens, the whole code is rendered as a single `tok-ident` span. Empty code renders no token spans. When `code` is a `Signal`, the spans re-render from a reactive token list whenever the signal value changes.

**Args:**

- `context`: Component context carrying the `code` and `lang` props.

**Returns:** The rendered element tree: a `pre.code-block` wrapping a `code.language-{lang}` element whose direct children are the token spans.

### get_lexer

```python
def get_lexer(name: str) -> Lexer
```

Key: `webcompy.ui.code_block.lexers._registry:get_lexer` · Exports: `from webcompy.ui.code_block import get_lexer`, `from webcompy.ui.code_block.lexers import get_lexer`

Return the lexer registered under `name`, an alias, or a file extension.

Lookup is case-insensitive and also accepts file extensions with or without a leading dot.

**Args:**

- `name`: Primary name, alias, or file extension to resolve.

**Returns:** The registered lexer.

**Raises:**

- `LexerNotFoundError`: If no lexer matches `name`.

### highlight

```python
def highlight(code: str, lang: str) -> str
```

Key: `webcompy.ui.code_block._highlight:highlight` · Exports: `from webcompy.ui.code_block import highlight`

Highlight source code as an HTML string of token spans.

Escapes HTML special characters in token text. When the language is unknown or the lexer yields no tokens, emits a single `<span class="tok-ident">` containing the escaped code.

**Args:**

- `code`: Source code to highlight.
- `lang`: Language name, alias, or file extension for lexer lookup.

**Returns:** A string of `<span class="...">` token spans.

### Lexer

```python
class Lexer(Protocol)
```

Key: `webcompy.ui.code_block.lexers._base:Lexer` · Exports: `from webcompy.ui.code_block import Lexer`, `from webcompy.ui.code_block.lexers import Lexer`

Protocol for source code tokenizers.

**Attributes:**

- `name`: Primary language identifier used for registry lookup.
- `aliases`: Alternative names the lexer is registered under.
- `file_extensions`: File extensions (with leading dot) the lexer is registered under.

#### Members

**`tokenize`** (method)

```python
def tokenize(self, code: str) -> Iterable[Token]
```

Tokenize source text into classified spans.

**Args:**

- `code`: Source text to tokenize; empty input yields no tokens.

**Returns:** Tokens in source order whose concatenated values equal `code` exactly.

### LexerInfo

```python
class LexerInfo:
    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]
    source: str
```

Key: `webcompy.ui.code_block.lexers._base:LexerInfo` · Exports: `from webcompy.ui.code_block import LexerInfo`

Introspection record describing a registered lexer.

**Attributes:**

- `name`: Primary language identifier.
- `aliases`: Alternative lookup names.
- `file_extensions`: Registered file extensions (with leading dot).
- `source`: Origin label: `"builtin"`, `"pygments:<lexname>"`, or `"custom"`.

### LexerNotFoundError

```python
class LexerNotFoundError(KeyError):
    def __init__(self, name: str) -> None
```

Key: `webcompy.ui.code_block.lexers._registry:LexerNotFoundError` · Exports: `from webcompy.ui.code_block import LexerNotFoundError`, `from webcompy.ui.code_block.lexers import LexerNotFoundError`

Raised by `get_lexer` when no lexer matches the requested name.

The error message lists the currently registered lexer names.

**Args:**

- `name`: The lookup name that failed to resolve.

**Attributes:**

- `name`: The lookup name that failed to resolve.

### list_lexers

```python
def list_lexers() -> list[LexerInfo]
```

Key: `webcompy.ui.code_block.lexers._registry:list_lexers` · Exports: `from webcompy.ui.code_block import list_lexers`, `from webcompy.ui.code_block.lexers import list_lexers`

Return introspection records for every registered lexer.

**Returns:** `LexerInfo` records sorted by primary name, one per lexer.

### PYGMENTS_SHORT_CLASS

```python
PYGMENTS_SHORT_CLASS: dict[TokenType, str] = ...
```

Key: `webcompy.ui.code_block._compatibility:PYGMENTS_SHORT_CLASS` · Exports: `from webcompy.ui.code_block import PYGMENTS_SHORT_CLASS`

Pygments short class emitted alongside each semantic `tok-*` class.

An empty string means no Pygments class is emitted for that token type.

### PythonLexer

```python
class PythonLexer:
    def __init__(self) -> None
```

Key: `webcompy.ui.code_block.lexers._python:PythonLexer` · Exports: `from webcompy.ui.code_block.lexers import PythonLexer`

Tokenize Python source on top of the `tokenize` module.

Emits the defined name after `class`/`def` as a function token, classifies operators per Pygments conventions, and colors f-string literal parts as strings. Syntactically invalid input falls back to a single identifier token containing the whole source.

**Attributes:**

- `name`: Primary name `"python"`.
- `aliases`: Alternative lookup names (`"py"`, `"python3"`).
- `file_extensions`: Registered file extensions (`.py`, `.pyw`).

#### Members

**`tokenize`** (method)

```python
def tokenize(self, code: str) -> Iterable[Token]
```

Tokenize Python source in source order.

**Args:**

- `code`: Source text to tokenize; empty input yields no tokens.

**Yields:** Token: Classified spans whose concatenated values equal `code` exactly; syntactically invalid input is yielded as a single identifier token.

### register_builtin_lexers

```python
def register_builtin_lexers() -> None
```

Key: `webcompy.ui.code_block.lexers._registry:register_builtin_lexers` · Exports: `from webcompy.ui.code_block import register_builtin_lexers`, `from webcompy.ui.code_block.lexers import register_builtin_lexers`

Register the built-in Python, Bash, and TOML lexers.

Idempotent: performs no work when a Python lexer is already registered. The registrations are labeled `"builtin"`.

### register_lexer

```python
def register_lexer(lexer: Lexer, *, override: bool = False, source: str = 'custom') -> None
```

Key: `webcompy.ui.code_block.lexers._registry:register_lexer` · Exports: `from webcompy.ui.code_block import register_lexer`, `from webcompy.ui.code_block.lexers import register_lexer`

Register a lexer under its name, aliases, and file extensions.

**Args:**

- `lexer`: Lexer instance implementing the `Lexer` protocol.
- `override`: Replace an existing registration under the same primary name.
- `source`: Origin label recorded for `list_lexers` introspection.

**Raises:**

- `TypeError`: If `lexer` does not implement the `Lexer` protocol.
- `ValueError`: If the primary name is already registered while `override` is `False`.

### Token

```python
class Token:
    type: TokenType
    value: str
```

Key: `webcompy.ui.code_block._tokens:Token` · Exports: `from webcompy.ui.code_block import Token`

A single classified span of highlighted source text.

Immutable and hashable; the fields cannot be reassigned.

**Attributes:**

- `type`: Category of the token.
- `value`: Raw source text of the span, preserved verbatim.

**Raises:**

- `TypeError`: If `type` is not a `TokenType` or `value` is not a `str`.

### TokenType

```python
class TokenType(StrEnum)
```

Key: `webcompy.ui.code_block._tokens:TokenType` · Exports: `from webcompy.ui.code_block import TokenType`

Category a highlighted token belongs to.

Each member's value is the suffix of the emitted `tok-{value}` CSS class name.

### TomlLexer

```python
class TomlLexer
```

Key: `webcompy.ui.code_block.lexers._toml:TomlLexer` · Exports: `from webcompy.ui.code_block.lexers import TomlLexer`

Tokenize TOML source with a single grouped regular expression.

Recognizes sections, strings, dates, numbers, booleans, and operators; section headers are additionally classified from a dedicated section pattern.

**Attributes:**

- `name`: Primary name `"toml"`.
- `aliases`: Alternative lookup names (none).
- `file_extensions`: Registered file extensions (`.toml`).

#### Members

**`tokenize`** (method)

```python
def tokenize(self, code: str) -> Iterable[Token]
```

Tokenize TOML source in source order.

**Args:**

- `code`: Source text to tokenize; empty input yields no tokens.

**Yields:** Token: Classified spans whose concatenated values equal `code` exactly.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Core guides: [UI Primitives](/documents/basic/ui-primitives), [Overlay Components](/documents/basic/overlay), [Disclosure & Feedback](/documents/basic/disclosure), and [Styling & Themes](/documents/basic/styling-and-themes).
- Architecture & styling: [UI Headless Contract](/documents/advanced/ui-headless-contract) and [Styling Deep Dive](/documents/advanced/styling-deep-dive).
<!-- author:end:see-also -->
