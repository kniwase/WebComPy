## ADDED Requirements

### Requirement: Browser startup shall register named custom elements before hydration

When `app.run()` starts in the browser, the application SHALL register currently known named component custom elements before calling child `_hydrate_node()` methods. Registration SHALL occur early enough for SSR nodes to upgrade, while server and SSG entry points SHALL skip registration.

#### Scenario: Starting hydration with named components
- **WHEN** `app.run()` starts with pre-rendered named component markup
- **THEN** the named custom-element definitions SHALL be registered before child hydration
- **AND** hydration SHALL adopt upgraded existing nodes instead of replacing them

#### Scenario: Starting without named components
- **WHEN** an application contains only unnamed components
- **THEN** startup SHALL not perform custom-element registration
- **AND** the existing hydration sequence SHALL remain unchanged

#### Scenario: Running SSR or SSG
- **WHEN** the application renders through a server-side entry point
- **THEN** no browser custom-element registry or FFI callback SHALL be accessed
- **AND** generated HTML SHALL contain any named custom-element tags normally

### Requirement: Browser startup shall make named custom elements available before first creation

Named component generators that are resolved during or after initial application startup SHALL be registered before their first DOM node creation or hydration adoption. Registration failures SHALL propagate as framework component errors and SHALL not leave a partially initialized application silently running.

#### Scenario: Resolving a named lazy route
- **WHEN** a lazy route resolves a named component during navigation
- **THEN** the custom element SHALL be registered before the route component creates or adopts its wrapper
- **AND** the route SHALL render using the registered custom element

#### Scenario: Registration failure during startup
- **WHEN** a named element conflicts with an incompatible existing custom-element definition
- **THEN** `app.run()` SHALL report a `WebComPyComponentException`
- **AND** hydration SHALL not proceed as if the component were registered
