## MODIFIED Requirements

### Requirement: Component registration shall enforce unique names with per-app stores
The framework SHALL maintain a per-app registry of component generators by name. If two components are registered with the same name within the same app, an error SHALL be raised. Each `WebComPyApp` SHALL own its own `ComponentStore` instance, provided into the app's DI scope. `ComponentGenerator` SHALL register into the active app's store via DI when a scope is available. When no DI scope exists (import time), registration SHALL be deferred until an app scope becomes active. No module-level `_default_component_store` global SHALL exist.

#### Scenario: Registering duplicate component names within the same app
- **WHEN** a developer defines two components with the same name in the same application
- **THEN** `WebComPyComponentException` SHALL be raised with a message about the duplicate

#### Scenario: Per-app component store isolation
- **WHEN** two `WebComPyApp` instances exist with different component sets
- **THEN** each app's `ComponentStore` SHALL only contain the components registered for that app
- **AND** scoped CSS collection SHALL be isolated per app

#### Scenario: Import-time registration without DI scope
- **WHEN** a `@define_component` decorated function is defined at module level (before any app exists)
- **THEN** the `ComponentGenerator` SHALL store its registration info locally
- **AND** when an app is created and its DI scope becomes active, the component SHALL be registered into that app's store

### Requirement: Components shall manage document head properties
Each component instance SHALL be able to set the document title and meta tags through the app-scoped `HeadPropsStore` accessed via DI. When multiple components set the title, the most recently rendered one SHALL take precedence. When a component is destroyed, its head entries SHALL be removed from the app-scoped store.

#### Scenario: Setting the page title from a component
- **WHEN** a component calls `context.set_title("My Page")`
- **THEN** the document title SHALL update to "My Page" in the relevant app's scope
- **AND** when the component is destroyed, its title entry SHALL be removed from the app-scoped store

#### Scenario: Multiple apps with independent head management
- **WHEN** two `WebComPyApp` instances exist simultaneously
- **THEN** each app SHALL have its own `HeadPropsStore` provided via DI
- **AND** title and meta settings in one app SHALL NOT affect the other