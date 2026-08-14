# Delta Spec: custom-element-components

## MODIFIED Requirements

### Requirement: Named components shall be defined as valid Light DOM custom elements

`define_component` SHALL accept a custom-element name and an optional sequence of observed attribute names; this called form SHALL be the only definition form (the bare form is removed — see the `components` capability naming-consistency requirement). The name SHALL satisfy the browser custom-element naming rules, including containing a hyphen, and SHALL match the setup function name via case conversion. Attribute names SHALL be normalized to lower case and duplicate names SHALL be rejected.

#### Scenario: Defining a named component

- **WHEN** a developer decorates a setup function with `@define_component("my-card")`
- **THEN** the returned `ComponentGenerator` SHALL retain `my-card` as its custom-element name
- **AND** a use of the generator SHALL render a `<my-card>` element in the browser and server environments

#### Scenario: Defining an observed-attribute component

- **WHEN** a developer decorates a setup function with `@define_component("my-card", observed_attributes=("theme-color",))`
- **THEN** the generator SHALL retain `theme-color` as an observed attribute
- **AND** the browser registration SHALL observe that attribute

#### Scenario: Rejecting an invalid custom-element name

- **WHEN** a developer supplies a name without a hyphen or otherwise invalid under the custom-element naming rules
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the component SHALL not be registered

## ADDED Requirements

### Requirement: Component wrappers shall be layout-transparent by default

The framework SHALL emit a default rule `[webcompy-component] { display: contents; }` in an early cascade layer (before `webcompy-scope`), in both SSR output and browser runtime injection, so that every component wrapper participates transparently in parent layout unless the author opts into a real box. The rule SHALL be emitted once per document regardless of component count. Authors SHALL be able to override the default per component definition via the `display` keyword argument or per component via `:host` scoped styles, both of which SHALL win over the default through normal cascade layering.

#### Scenario: Wrapper is transparent without author opt-in

- **WHEN** a component with no `display` kwarg and no `:host` display rule renders in the browser or SSR
- **THEN** the document SHALL contain the `[webcompy-component] { display: contents; }` rule
- **AND** the wrapper SHALL generate no layout box, leaving parent layout (flex/grid item identity, inline flow, percentage sizing) to the template children

#### Scenario: Author overrides the default

- **WHEN** a component declares `display="block"` or a `:host` scoped style with a display value
- **THEN** the author-level rule SHALL win over the framework default through cascade layering
- **AND** the wrapper SHALL generate a box with the declared display type
