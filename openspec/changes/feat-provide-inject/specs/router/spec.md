## MODIFIED Requirements

### Requirement: Components shall manage document head properties
Each component instance SHALL be able to set the document title and meta tags. When multiple components set the title, the most recently rendered one SHALL take precedence. When a component is destroyed, its head entries SHALL be removed. Head props SHALL be accessed via DI injection instead of a class variable.

#### Scenario: Setting the page title from a component
- **WHEN** a component calls `context.set_title("My Page")`
- **THEN** the document title SHALL update to "My Page"
- **AND** when the component is destroyed, its title entry SHALL be removed

#### Scenario: Accessing head props via DI
- **WHEN** a component or framework module accesses head props
- **THEN** it SHALL resolve the head props object via `inject(_HEAD_PROPS_KEY)`
- **AND** `Component._head_props` class variable SHALL be removed

### Requirement: Component registration shall enforce unique names
The framework SHALL maintain a registry of component generators by name. If two components are registered with the same name, an error SHALL be raised. The registry (ComponentStore) SHALL be accessed via DI instead of a global singleton.

#### Scenario: Registering duplicate component names
- **WHEN** a developer defines two components with the same name
- **THEN** `WebComPyComponentException` SHALL be raised with a message about the duplicate

#### Scenario: Accessing ComponentStore via DI
- **WHEN** framework code needs the ComponentStore
- **THEN** it SHALL resolve it via `inject(_COMPONENT_STORE_KEY)` instead of the global singleton