## ADDED Requirements

### Requirement: Reactive scoped styles shall support `:host` for named components

A reactive scoped style registered by a named component SHALL accept `:host` and `:host(<compound-selector>)`. Its generated CSS SHALL replace the host pseudo-class with the named custom-element selector, retain cid scoping, and use the same transformation as static scoped styles.

#### Scenario: Rendering a reactive host rule
- **WHEN** a named component registers `reactive_scoped_style(lambda: {":host": {"color": color.value}})`
- **THEN** the emitted `style[data-webcompy-cid-rx]` element SHALL target the named custom-element wrapper
- **AND** the selector SHALL include the component cid attribute

#### Scenario: Updating a reactive host rule
- **WHEN** a signal read by a reactive `:host(.active)` style changes
- **THEN** the existing reactive style element's text content SHALL update
- **AND** the updated selector SHALL remain equivalent to the static scoped-style transformation

#### Scenario: Reactive host style during SSR
- **WHEN** SSG evaluates a named component's reactive scoped style containing `:host`
- **THEN** the generated `style[data-webcompy-cid-rx]` element SHALL contain the named-element selector
- **AND** the server SHALL not require browser custom-element registration

### Requirement: Reactive scoped style shall reject `:host` without a named component

When a reactive scoped style uses `:host` for an unnamed component, the framework SHALL raise `WebComPyException` rather than emitting an unscoped or invalid selector.

#### Scenario: Registering an unnamed reactive host style
- **WHEN** an unnamed component registers a reactive scoped style containing `:host`
- **THEN** registration or first CSS evaluation SHALL raise `WebComPyException`
- **AND** no reactive style element SHALL be created for that invalid rule
