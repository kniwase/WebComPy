## ADDED Requirements

### Requirement: useRouter shall provide typed router access via DI
`useRouter()` SHALL be a composable function that returns the Router instance by calling `inject()` with the framework's router DI key. It SHALL raise `InjectionError` if no router is provided (i.e., the app was created without a router).

#### Scenario: Using useRouter in a component
- **WHEN** a component setup function calls `useRouter()`
- **AND** the app was created with a router
- **THEN** the Router instance SHALL be returned

#### Scenario: Using useRouter without a router
- **WHEN** a component setup function calls `useRouter()`
- **AND** the app was created without a router
- **THEN** `InjectionError` SHALL be raised

#### Scenario: useRouter is a thin inject wrapper
- **WHEN** a developer inspects the `useRouter` implementation
- **THEN** it SHALL be equivalent to `return inject(RouterKey)` where `RouterKey` is the framework's public router DI key