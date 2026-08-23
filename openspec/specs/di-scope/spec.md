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

#### Scenario: Context manager restores even when descendant is active
- **WHEN** a `with DIScope():` block contains component setup that calls `provide()` and makes a descendant child scope active (via `_pending_di_parent`)
- **THEN** exiting the `with` block SHALL restore `_active_di_scope` to the value active before the block was entered
- **AND** `inject()` after the block SHALL NOT resolve values from the descendant child scope

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

### Requirement: RenderContext dispose shall unwind the active DI binding

When `RenderContext.dispose()` disposes its root scope tree, `_active_di_scope` SHALL NOT remain bound to the disposed root or any disposed descendant. The context SHALL reset the ContextVar to its pre-render value whenever the active scope belongs to the disposed tree (the root scope or any descendant created under it), and SHALL leave active scopes belonging to other, surviving render contexts untouched. If the immediate predecessor ContextVar value is itself already disposed (three overlapping contexts where the middle was disposed before the newest), the implementation SHALL walk the predecessor chain (`_prev_active_app_context` / `_prev_render_context_cv` / `_prev_active_di_scope` or the module fallback chain) to the next live context instead of clearing to `None`; this applies equally to `_active_app_context`, the per-app `_render_context_cv`, and `_active_di_scope`.

#### Scenario: Disposing with a component child scope active
- **WHEN** a component setup has called `provide()`, making an untokenized child scope the active `_active_di_scope`
- **AND** the owning `RenderContext` is disposed
- **THEN** `_active_di_scope` SHALL be reset to the value from before the render context entered (or `None`)
- **AND** subsequent `inject()`/`provide()` calls SHALL NOT resolve through the disposed scope

#### Scenario: Disposing while a foreign scope is active
- **WHEN** the active `_active_di_scope` belongs to another, still-live render context's tree
- **THEN** disposing SHALL leave that foreign scope active

#### Scenario: Disposing with three overlapping contexts restores the oldest live context
- **WHEN** three render contexts are created in order `ctx1 < ctx2 < ctx3` (each sets `_active_app_context`, `_render_context_cv`, and `_active_di_scope`)
- **AND** the middle context `ctx2` is disposed while `ctx3` is still active
- **AND** the newest context `ctx3` is then disposed
- **THEN** `_active_app_context`, the app's `_render_context_cv`, and `_active_di_scope` SHALL be bound to `ctx1` (the oldest still-live context)
- **AND** the module-level browser fallbacks (`_app_instance` / `_app_di_scope`) SHALL also be `ctx1` / `ctx1._di_scope`
- **AND** disposing `ctx1` finally SHALL clear all three bindings to `None`

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