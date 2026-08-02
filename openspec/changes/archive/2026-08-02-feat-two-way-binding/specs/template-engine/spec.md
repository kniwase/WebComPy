# Delta: template-engine

## MODIFIED Requirements

### Requirement: Template engine shall validate colon-prefixed attributes on HTML elements

On HTML elements, the recognized `:`-prefixed attributes SHALL be `:ref` and `:bind`. Any other `:`-prefixed attribute SHALL raise `WebComPyException` at bind time with a message naming the attribute and suggesting `{{ }}` interpolation as the alternative. The value resolved via `:ref` SHALL be a `DomNodeRef` instance; any other type SHALL raise `WebComPyException` at bind time naming the variable and its observed type. The value resolved via `:bind` SHALL be a writable `Signal` instance; any other type SHALL raise `WebComPyException` at bind time naming the variable and its observed type. Neither `:ref` nor `:bind` SHALL accept `{{ }}` interpolation inside the attribute value.

#### Scenario: Non-ref non-bind colon attribute rejected
- **WHEN** the template contains `<div :class="cls">`
- **THEN** `WebComPyException` SHALL be raised at bind time
- **AND** the message SHALL name `:class` and suggest using `class="{{ cls }}"` interpolation

#### Scenario: Ref binding type validation
- **WHEN** `render_template('<input :ref="r">', {"r": "not-a-ref"})` is called
- **THEN** `WebComPyException` SHALL be raised at bind time naming `r` and its observed type (`str`)

#### Scenario: Bind attribute resolves to a Signal
- **WHEN** `render_template('<input :bind="text">', {"text": Signal("hi")})` is called
- **THEN** the produced element SHALL behave exactly like `html.INPUT({":bind": text})` (two-way binding per the elements spec)

#### Scenario: Bind attribute type validation
- **WHEN** `render_template('<input :bind="text">', {"text": "literal"})` is called
- **THEN** `WebComPyException` SHALL be raised at bind time naming `text` and its observed type (`str`)

#### Scenario: Interpolation inside :bind rejected
- **WHEN** the template contains `<input :bind="{{ text }}">`
- **THEN** `WebComPyException` SHALL be raised at bind time stating `{{ }}` interpolation is not supported in `:bind` attributes

#### Scenario: Component tags unaffected
- **WHEN** a `:`-prefixed attribute appears on a component tag (e.g., `<user-card :count="n">`)
- **THEN** it SHALL continue to be bound as a dynamic prop (no error)
