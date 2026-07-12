## MODIFIED Requirements

### Requirement: use_router shall provide typed router access via DI
`use_router()` SHALL be a composable function that returns the Router instance by calling `inject()` with the framework's router DI key. It SHALL raise `InjectionError` if no router is provided (i.e., the app was created without a router).

#### Scenario: Using use_router in a component
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created with a router
- **THEN** the Router instance SHALL be returned

#### Scenario: Using use_router without a router
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created without a router
- **THEN** `InjectionError` SHALL be raised

#### Scenario: use_router is a thin inject wrapper
- **WHEN** a developer inspects the `use_router` implementation
- **THEN** it SHALL be equivalent to `return inject(RouterKey)` where `RouterKey` is the framework's public router DI key
