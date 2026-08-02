# Delta: elements

## ADDED Requirements

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

For `textarea`, the Signal→DOM direction binds the element's text content via a child `TextElement` (HTML textareas expose no `value` attribute); the write-back direction is unchanged.

For radio, the Signal→DOM direction SHALL use a `Computed` that compares the Signal value with the element's static `value` attribute (`checked` is true when equal), so a group of radios sharing one Signal stays in sync.

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

#### Scenario: No :bind attribute reaches the DOM
- **WHEN** any element is created with `:bind`
- **THEN** the rendered DOM node SHALL NOT have a `:bind` attribute

#### Scenario: SSR renders bound attribute only
- **WHEN** an element with `:bind` is rendered on the server
- **THEN** the output HTML SHALL contain the bound attribute (`value` or `checked`) with the Signal's initial value
- **AND** no event registration SHALL occur server-side

### Requirement: `:bind` write-back for number inputs shall convert to the Signal's numeric type

For `input[type=number]`, the write-back handler SHALL convert `ev.target.value` to `int` when the Signal's current value is an `int` (excluding `bool`), otherwise to `float`. An empty string or an unparseable value SHALL be skipped (the Signal keeps its previous value).

#### Scenario: Integer conversion
- **WHEN** a `Signal(5)` is bound to `input[type=number]` and the user enters `"42"`
- **THEN** the Signal SHALL become `42` (int)

#### Scenario: Float conversion
- **WHEN** a `Signal(0.5)` is bound and the user enters `"1.25"`
- **THEN** the Signal SHALL become `1.25` (float)

#### Scenario: Empty input skipped
- **WHEN** a `Signal(5)` is bound and the user clears the input
- **THEN** the Signal SHALL remain `5`

### Requirement: `:bind` shall validate the Signal kind and value type at construction time

The `:bind` value SHALL be a writable `Signal` instance. `Computed`, `ReadonlySignal` (`readonly()`), `ReactiveList`, `ReactiveDict`, and non-Signal values SHALL raise `WebComPyException` naming the received type. Value-type discipline SHALL be enforced from the Signal's current value: text-like/textarea requires `str`, number requires `int`/`float` (excluding `bool`), checkbox requires `bool`. Radio requires a static `value` attribute on the element. An `input` whose `type` attribute is dynamic (`SignalBase`) combined with `:bind` SHALL raise (binding semantics cannot be determined).

#### Scenario: Computed rejected
- **WHEN** `html.INPUT({":bind": some_computed})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a writable Signal

#### Scenario: Type mismatch rejected
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": Signal("text")})` is used
- **THEN** `WebComPyException` SHALL be raised naming the required type (`bool`)

#### Scenario: Radio without static value rejected
- **WHEN** `html.INPUT({"type": "radio", ":bind": choice})` lacks a `value` attribute
- **THEN** `WebComPyException` SHALL be raised stating radio `:bind` requires a static `value` attribute

#### Scenario: Dynamic type attribute rejected
- **WHEN** `html.INPUT({"type": some_signal, ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a static `type` attribute

### Requirement: `:bind` shall reject unsupported elements and conflicting attributes

`:bind` on elements other than the supported set (including `select` and `option`) SHALL raise `WebComPyException` naming the supported elements. An explicit attribute duplicating the bound one (`value` for text-like/number, `checked` for checkbox/radio) SHALL raise `WebComPyException`. An explicit user handler for the binding event SHALL be chained: the binding write-back SHALL run first, then the user handler. An explicit static `value` attribute on a radio is REQUIRED and is NOT a conflict.

#### Scenario: select rejected
- **WHEN** `html.SELECT({":bind": sig})` is used
- **THEN** `WebComPyException` SHALL be raised naming the supported elements

#### Scenario: Conflicting value attribute rejected
- **WHEN** `html.INPUT({"value": "x", ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating the conflict with the explicit `value` attribute

#### Scenario: User handler chained after binding
- **WHEN** `html.INPUT({":bind": text_signal, "@input": user_handler})` is used and the user types
- **THEN** the Signal SHALL be updated first
- **AND** `user_handler` SHALL be called after the update
