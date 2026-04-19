## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. Developers SHALL only need to provide a root component and optionally a router — the framework handles all internal wiring. `WebComPyApp` SHALL create a root `DIScope` and provide framework-internal services (Router, ComponentStore, HeadProps) into it.

#### Scenario: Creating a minimal application
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp)`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `app.__component__.render()` SHALL produce the full UI
- **AND** `app.di_scope` SHALL be available for DI

#### Scenario: Creating an application with routing
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, router=router)`
- **THEN** `RouterView` and `RouterLink` SHALL be connected to the router via DI
- **AND** URL changes SHALL trigger reactive UI updates
- **AND** the Router SHALL be provided into `app.di_scope`

## ADDED Requirements

### Requirement: Global singletons shall be replaced by DI-provided values
`Router._instance`, `Component._head_props`, and `ComponentStore` global singletons SHALL be replaced by DI-provided values. Framework code SHALL access these via `inject()` with internal keys (not exposed to users).

#### Scenario: Router is provided via DI
- **WHEN** `WebComPyApp` is created with a router
- **THEN** the router SHALL be provided into the app DI scope using an internal key
- **AND** `RouterView` and `TypedRouterLink` SHALL resolve it via `inject()`

#### Scenario: ComponentStore is provided via DI
- **WHEN** `WebComPyApp` is initialized
- **THEN** the `ComponentStore` SHALL be provided into the app DI scope
- **AND** `ComponentGenerator` SHALL access it via `inject()` with an internal key

#### Scenario: Head props are provided via DI
- **WHEN** `WebComPyApp` is initialized
- **THEN** the head props object SHALL be provided into the app DI scope
- **AND** component head management SHALL use `inject()` to access it

### Requirement: Multiple WebComPy applications shall coexist without interference
Each `WebComPyApp` instance SHALL have its own DI scope. Global singletons SHALL NOT be used for app-scoped state, enabling multiple WebComPy applications on the same page.

#### Scenario: Two apps on the same page
- **WHEN** two `WebComPyApp` instances are created with different root components
- **THEN** each app SHALL have its own Router, ComponentStore, and DI scope
- **AND** components in one app SHALL NOT see DI values from the other