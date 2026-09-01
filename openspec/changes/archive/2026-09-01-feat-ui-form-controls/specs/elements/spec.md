# elements Specification (delta)

## MODIFIED Requirements

### Requirement: Form elements shall support `:bind` two-way binding

The `:bind` attribute SHALL provide two-way binding between a writable `Signal` and a form element. It SHALL expand into (a) a one-way attribute binding (Signal→DOM, using the existing reactive attribute pipeline) and (b) a write-back event handler (DOM→Signal) registered through the standard event lifecycle (`create_proxy` on attach, `destroy` on detach). The expansion SHALL happen at `Element` construction time, so the element API and the template path behave identically.

Supported elements and rules:

| Element | Bound attribute | Event | Write-back |
|---|---|---|---|
| `input` with `type` of `text`/`email`/`password`/`search`/`tel`/`url` or no `type` | `value` | `input` | `signal.value = ev.target.value` |
| `textarea` | text content (child `TextElement`) | `input` | `signal.value = ev.target.value` |
| `input[type=number]` | `value` | `input` | converted per the number-conversion requirement below |
| `input[type=checkbox]` | `checked` | `change` | `signal.value = bool(ev.target.checked)` |
| `input[type=radio]` | `checked` | `change` | if `ev.target.checked`, set the Signal to the element's static `value` attribute |
| `select` | `value` | `change` | `signal.value = ev.target.value` |

For `textarea`, the Signal→DOM direction binds the element's text content via a child `TextElement` (HTML textareas expose no `value` attribute); the write-back direction is unchanged.

For `select`, the bound `value` attribute SHALL be kept in sync so programmatic Signal changes update the selection, and the write-back SHALL fire on the `change` event (select's native commit event), setting the Signal to `ev.target.value` without coercion (option values are strings). Single selection only; `:bind` on a `select` with a `multiple` attribute SHALL raise `WebComPyException`.

For radio, the Signal→DOM direction SHALL use a `Computed` that compares the Signal value with the element's static `value` attribute (`checked` is true when equal), so a group of radios sharing one Signal stays in sync. The comparison SHALL be a plain Python `==` on the resolved values. In templates, HTML attribute values are always strings, so the static `value` attribute is compared as a string; a template radio bound to a non-string-valued Signal (e.g. `<input type="radio" value="1" :bind="choice">` with an int-valued Signal) SHALL NOT be rendered checked. The element API (`html.INPUT({"type": "radio", "value": 1, ":bind": choice})`) preserves non-string values and SHALL compare them without coercion. Template users SHALL bind radio groups to string-valued Signals.

The `:bind` key SHALL NOT be emitted as a DOM attribute.

#### Scenario: Text input two-way binding
- **WHEN** an element is created as `html.INPUT({":bind": text_signal})` with a `Signal("hello")`
- **THEN** the input's `value` attribute SHALL render as `"hello"`
- **AND** when the user types, the `input` event handler SHALL set `text_signal.value` to `ev.target.value`
- **AND** setting `text_signal.value = "world"` SHALL update the DOM attribute

#### Scenario: Checkbox binding
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": flag_signal})` is used with a `Signal(False)`
- **THEN** the `checked` attribute SHALL reflect the Signal
- **AND** on `change`, the Signal SHALL be set to `ev.target.checked`

#### Scenario: Radio group binding
- **WHEN** two radios share one Signal: `html.INPUT({"type": "radio", "value": "a", ":bind": choice})` and `html.INPUT({"type": "radio", "value": "b", ":bind": choice})`
- **THEN** the radio whose static `value` equals `choice.value` SHALL be rendered checked
- **AND** when the second radio fires `change` with `ev.target.checked` true, `choice.value` SHALL become `"b"`
- **AND** the first radio's `checked` SHALL become false reactively

#### Scenario: Template radio value compared as string
- **WHEN** a radio is created via template `<input type="radio" value="1" :bind="choice">` with an int-valued `choice = Signal(1)`
- **THEN** the `checked` Computed SHALL compare `1 == "1"`, which is `False`
- **AND** the radio SHALL NOT be rendered checked
- **AND** template users SHALL bind radio groups to string-valued Signals; the element API (`html.INPUT({"value": 1, ":bind": choice})`) SHALL compare non-string values without coercion

#### Scenario: Select two-way binding
- **WHEN** `html.SELECT({":bind": choice_signal}, option_a, option_b)` is used with `Signal("a")`
- **THEN** the select's `value` attribute SHALL render as `"a"`
- **AND** when the user picks the second option, the `change` event handler SHALL set `choice_signal.value` to `"b"`
- **AND** setting `choice_signal.value = "a"` programmatically SHALL update the DOM selection

#### Scenario: Multiple select rejected
- **WHEN** `html.SELECT({"multiple": True, ":bind": choice_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` does not support multiple selects

#### Scenario: No :bind attribute reaches the DOM
- **WHEN** any element is created with `:bind`
- **THEN** the rendered DOM node SHALL NOT have a `:bind` attribute

#### Scenario: SSR renders bound attribute only
- **WHEN** an element with `:bind` is rendered on the server
- **THEN** the output HTML SHALL contain the bound attribute (`value` or `checked`) with the Signal's initial value
- **AND** no event registration SHALL occur server-side

### Requirement: `:bind` shall validate the Signal kind and value type at construction time

The `:bind` value SHALL be a writable `Signal` instance. `Computed`, `ReadonlySignal` (`readonly()`), `ReactiveList`, `ReactiveDict`, and non-Signal values SHALL raise `WebComPyException` naming the received type. Value-type discipline SHALL be enforced from the Signal's current value: text-like/textarea/select requires `str`, number requires `int`/`float` (excluding `bool`), checkbox requires `bool`. Radio requires a static `value` attribute on the element. An `input` whose `type` attribute is dynamic (`SignalBase`) combined with `:bind` SHALL raise (binding semantics cannot be determined).

#### Scenario: Computed rejected
- **WHEN** `html.INPUT({":bind": some_computed})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a writable Signal

#### Scenario: Type mismatch rejected
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": Signal("text")})` is used
- **THEN** `WebComPyException` SHALL be raised naming the required type (`bool`)

#### Scenario: Select with non-string Signal rejected
- **WHEN** `html.SELECT({":bind": Signal(True)})` is used
- **THEN** `WebComPyException` SHALL be raised naming the required type (`str`)

#### Scenario: Radio without static value rejected
- **WHEN** `html.INPUT({"type": "radio", ":bind": choice})` lacks a `value` attribute
- **THEN** `WebComPyException` SHALL be raised stating radio `:bind` requires a static `value` attribute

#### Scenario: Dynamic type attribute rejected
- **WHEN** `html.INPUT({"type": some_signal, ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a static `type` attribute

## REMOVED Requirements

### Requirement: `:bind` shall reject unsupported elements and conflicting attributes

**Reason**: Superseded by ":bind shall reject invalid target elements and conflicting attributes" — `select` gains `:bind` support, so the requirement's element-support clause and its "select rejected" scenario change together; the tooling contract requires a renamed requirement when scenarios are dropped.

**Migration**: Update tests referencing the old header to the renamed requirement. `:bind` on a plain single-selection `select` now succeeds; rejection semantics are unchanged for all other unsupported elements (explicitly including `option`) and for conflicting attributes.

## ADDED Requirements

### Requirement: `:bind` shall reject invalid target elements and conflicting attributes

`:bind` on elements other than the supported set (including `option`) SHALL raise `WebComPyException` naming the supported elements. An explicit attribute duplicating the bound one (`value` for text-like/number/select, `checked` for checkbox/radio) SHALL raise `WebComPyException`. For `textarea`, the bound target is the text content; a non-empty children list combined with `:bind` SHALL raise `WebComPyException`. An explicit user handler for the binding event SHALL be chained: the binding write-back SHALL run first, then the user handler. An explicit static `value` attribute on a radio is REQUIRED and is NOT a conflict.

#### Scenario: Option rejected
- **WHEN** `html.OPTION({":bind": sig})` is used
- **THEN** `WebComPyException` SHALL be raised naming the supported elements

#### Scenario: Conflicting value attribute rejected
- **WHEN** `html.INPUT({"value": "x", ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating the conflict with the explicit `value` attribute

#### Scenario: Conflicting textarea text content rejected
- **WHEN** `html.TEXTAREA({":bind": text_signal}, "default")` is used with explicit text content
- **THEN** `WebComPyException` SHALL be raised stating the conflict with explicit text content

#### Scenario: User handler chained after binding
- **WHEN** `html.INPUT({":bind": text_signal, "@input": user_handler})` is used and the user types
- **THEN** the Signal SHALL be updated first
- **AND** `user_handler` SHALL be called after the update
