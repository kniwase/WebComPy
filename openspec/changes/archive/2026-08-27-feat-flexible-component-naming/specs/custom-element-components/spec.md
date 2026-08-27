## MODIFIED Requirements

### Requirement: Named components shall be defined as valid Light DOM custom elements

`define_component` SHALL accept an optional custom-element name as its first positional-or-keyword argument (`custom_element_name: str | None = None`) and an optional sequence of observed attribute names; calling the decorator factory (`@define_component(...)`) SHALL be the only definition form. When the name is provided it SHALL satisfy the browser custom-element naming rules, including containing a hyphen, and SHALL NOT be required to match the setup function name via case conversion. When the name is omitted it SHALL be derived from the setup function's name by case conversion, and the derived value SHALL satisfy the same browser naming rules. Attribute names SHALL be normalized to lower case and duplicate names SHALL be rejected.

#### Scenario: Defining a named component

- **WHEN** a developer decorates a setup function with `@define_component("my-card")`
- **THEN** the returned `ComponentGenerator` SHALL retain `my-card` as its custom-element name
- **AND** a use of the generator SHALL render a `<my-card>` element in the browser and server environments

#### Scenario: Defining a named component with a derived element name

- **WHEN** a developer decorates `def MyCard(context)` with `@define_component()`
- **THEN** the returned `ComponentGenerator` SHALL retain `my-card` as its custom-element name
- **AND** a use of the generator SHALL render a `<my-card>` element in the browser and server environments

#### Scenario: Defining an observed-attribute component

- **WHEN** a developer decorates a setup function with `@define_component(observed_attributes=("theme-color",))`
- **THEN** the generator SHALL retain `theme-color` as an observed attribute
- **AND** the generator's custom-element name SHALL derive from the decorated function's name
- **AND** the browser registration SHALL observe that attribute

#### Scenario: Rejecting an invalid custom-element name

- **WHEN** a developer supplies a name without a hyphen or otherwise invalid under the custom-element naming rules
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the component SHALL not be registered
