## Purpose

DI scopes define the resolution boundary and lifecycle for provided values. The scope hierarchy mirrors the component tree, with the app scope at the root and component scopes created lazily on `provide()`. Scopes support context manager protocol for standalone usage and test isolation.

## Requirements

### Requirement: DIScope shall form a tree hierarchy
`DIScope` SHALL maintain a parent-child tree structure. A child scope SHALL delegate to its parent for keys it does not provide. The app scope SHALL be the root with no parent.

#### Scenario: Creating a scope hierarchy
- **WHEN** a developer creates `app_scope = DIScope()` and `child_scope = DIScope(parent=app_scope)`
- **THEN** `child_scope` SHALL resolve keys from `app_scope` when not found locally

#### Scenario: Scope hierarchy mirrors component tree
- **WHEN** component A provides a key and component B is a descendant of A
- **THEN** component B's DI scope SHALL be a child of component A's DI scope
- **AND** `inject(key)` in component B SHALL resolve from component A's scope

### Requirement: DIScope shall support context manager protocol
`DIScope` SHALL implement `__enter__` and `__exit__` to set and reset `_active_di_scope` ContextVar, enabling standalone usage and test isolation.

#### Scenario: Using DIScope as a context manager
- **WHEN** a developer writes `with DIScope({RouterKey: mock_router}): ...`
- **THEN** `inject(RouterKey)` inside the `with` block SHALL return `mock_router`
- **AND** after the `with` block, `_active_di_scope` SHALL be restored to its previous value

#### Scenario: Nested context managers
- **WHEN** a developer enters an outer scope and then an inner scope
- **THEN** `inject()` inside the inner scope SHALL resolve from the inner scope first, then the outer
- **AND** exiting the inner scope SHALL restore the outer scope as active

### Requirement: DIScope shall lazily create child scopes for components
When `provide()` is called during component setup, a child DI scope SHALL be created lazily (if not already created for this component). Subsequent `provide()` calls in the same component SHALL add to the same child scope.

#### Scenario: First provide call creates a child scope
- **WHEN** a component setup function calls `provide(ThemeKey, theme)` for the first time
- **THEN** a new child DI scope SHALL be created as a child of the current active scope
- **AND** the child scope SHALL become the active scope for the remainder of this component's setup
- **AND** `ThemeKey → theme` SHALL be registered in the child scope

#### Scenario: Subsequent provide calls use the same child scope
- **WHEN** a component setup function calls `provide(ThemeKey, theme)` and then `provide(AuthKey, auth)`
- **THEN** both keys SHALL be registered in the same child scope
- **AND** only one child scope SHALL be created for this component

#### Scenario: Component with no provide calls inherits parent scope
- **WHEN** a component setup function does not call `provide()`
- **THEN** no child DI scope SHALL be created
- **AND** the component SHALL use the parent DI scope directly

### Requirement: DIScope dispose shall invalidate the scope and its children
`DIScope.dispose()` SHALL mark the scope as invalid (preventing further resolution through it) and recursively dispose all child scopes. Provided values SHALL NOT be automatically cleaned up.

#### Scenario: Disposing a component's DI scope
- **WHEN** a component with a child DI scope is destroyed
- **THEN** the child scope SHALL be disposed
- **AND** `inject()` from descendant scopes SHALL skip the disposed scope

#### Scenario: Disposing does not clean up provided values
- **WHEN** a scope provides a `DatabaseConnection` and is then disposed
- **THEN** the `DatabaseConnection` SHALL NOT be automatically closed
- **AND** the developer SHALL be responsible for cleanup via `on_before_destroy`

### Requirement: DIScope shall support initial providers on construction
`DIScope.__init__` SHALL accept an optional `providers` dict mapping keys to values. These SHALL be registered in the scope immediately.

#### Scenario: Creating a scope with initial providers
- **WHEN** a developer creates `DIScope({RouterKey: router, ApiKey: "url"})`
- **THEN** `inject(RouterKey)` SHALL return `router`
- **AND** `inject(ApiKey)` SHALL return `"url"`

### Requirement: App scope shall be the root DI scope
`WebComPyApp` SHALL create a root `DIScope` accessible as `app.di_scope`. Framework-internal services (Router, ComponentStore, HeadProps) SHALL be provided into this scope during app initialization.

#### Scenario: Creating an app with automatic DI scope
- **WHEN** a developer creates `app = WebComPyApp(root_component, router=router)`
- **THEN** `app.di_scope` SHALL be a `DIScope` instance
- **AND** the Router SHALL be provided into the app scope

#### Scenario: Using app scope for standalone inject
- **WHEN** a developer writes `with app.di_scope: service = inject(SomeKey)`
- **AND** `SomeKey` was provided at the app level
- **THEN** `service` SHALL resolve from the app scope