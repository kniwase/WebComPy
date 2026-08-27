## ADDED Requirements

### Requirement: define_component shall support an optional custom-element-name argument with derivation

`define_component` SHALL be used as a decorator factory (`@define_component(...)`); applying the raw undecorated callable as a bare decorator SHALL NOT be supported and SHALL raise `WebComPyComponentException` (or fail fast) with guidance to call the decorator. `define_component` SHALL accept a first positional-or-keyword argument `custom_element_name: str | None = None` in addition to the existing keyword-only arguments (`observed_attributes`, `display`). When `custom_element_name` is provided, its value SHALL form the custom-element tag and SHALL satisfy the custom-element naming rules (lowercase, contains a hyphen, not reserved). When omitted, the tag SHALL be derived from the decorated setup function's name by converting PascalCase/camelCase to kebab-case, and only the derived result SHALL be validated against the same naming rules. The framework SHALL NOT require any relationship between the setup function name and an explicitly provided tag. A round-trip check requiring `kebab_to_pascal(derived_tag) == function.__name__` SHALL NOT be performed; non-round-tripping names such as acronyms SHALL be accepted. Decorating a callable that already carries the component-definition marker SHALL raise `WebComPyComponentException`.

#### Scenario: Derived name from multi-word function

- **WHEN** a developer decorates `def UserCard(context)` with `@define_component()`
- **THEN** definition SHALL succeed
- **AND** the generator SHALL retain `user-card` as its custom-element name

#### Scenario: Non-round-tripping acronym is accepted in derived form

- **WHEN** a developer decorates `def HTTPRequest(context)` with `@define_component()`
- **THEN** definition SHALL succeed
- **AND** the generator SHALL retain `http-request` as its custom-element name while the setup function keeps the name `HTTPRequest`

#### Scenario: Derived name without hyphen fails with guidance

- **WHEN** a developer decorates `def App(context)` with `@define_component()`
- **THEN** definition SHALL raise `WebComPyComponentException` because the derived name `app` has no hyphen
- **AND** the message SHALL guide the developer toward either renaming the function to a multi-word name or passing an explicit tag to `define_component`

#### Scenario: Reserved derived name fails

- **WHEN** a developer decorates `def FontFace(context)` with `@define_component()`
- **THEN** definition SHALL raise `WebComPyComponentException` because the derived name `font-face` is reserved by the custom-elements specification
- **AND** the message SHALL guide the developer toward either renaming the function or passing an explicit tag to `define_component`

#### Scenario: Explicit tag decoupled from function name

- **WHEN** a developer decorates `def Card(context)` with `@define_component("user-card")`
- **THEN** definition SHALL succeed
- **AND** the generator SHALL retain `user-card` as its custom-element name and `Card` as the setup function name
- **AND** no mismatch error SHALL be raised

#### Scenario: Explicit tag passed by keyword

- **WHEN** a developer decorates any setup function with `@define_component(custom_element_name="user-card")`
- **THEN** definition SHALL behave identically to `@define_component("user-card")`

#### Scenario: Invalid explicit tag rejected

- **WHEN** a developer supplies an explicit tag that is not lowercase, lacks a hyphen, or is reserved
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the component SHALL not be registered

#### Scenario: Bare undecorator form guides toward calling the factory

- **WHEN** a developer applies `define_component` directly as `@define_component` above a setup function definition
- **THEN** definition SHALL NOT silently produce a component generator for that function under the optional-name contract
- **AND** the failure SHALL direct the developer to use `@define_component(...)` with parentheses

#### Scenario: Re-decorating a component definition is rejected

- **WHEN** a developer applies `@define_component(...)` a second time to an object that already carries the component-definition marker
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the message SHALL identify that the object is already a component definition

## REMOVED Requirements

### Requirement: Component definitions shall declare a custom-element name consistent with the setup function name

**Reason**: The mandatory consistency between the setup function name and the custom-element tag coupled two independent identifiers, forced unnatural Python names, and rejected legitimate non-round-tripping names such as acronyms. Flexible naming replaces it: derive when possible, decouple when explicit.

**Migration**: Definitions whose function name already equals `kebab_to_pascal(tag)` may drop the argument (`@define_component()`). All other definitions keep their existing explicit tags unchanged — mismatch validation no longer applies. Single-word function names must either be renamed to multi-word names or pass an explicit tag.
