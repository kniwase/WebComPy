## ADDED Requirements

### Requirement: Component setup shall integrate with DI scope
`Component.__setup` SHALL inherit the active DI scope from the ContextVar. When `provide()` is called during setup, a child DI scope SHALL be lazily created and set as the active scope for the remainder of the setup function.

#### Scenario: Component provides a value during setup
- **WHEN** a component setup function calls `provide(ThemeKey, dark_theme)`
- **THEN** a child DI scope SHALL be created for this component
- **AND** `ThemeKey` SHALL be available to descendant components via `inject(ThemeKey)`

#### Scenario: Component injects a value during setup
- **WHEN** a component setup function calls `inject(RouterKey)` and an ancestor scope provides `RouterKey`
- **THEN** the component SHALL receive the provided value

#### Scenario: Component setup restores DI scope on exit
- **WHEN** a component setup function completes or raises
- **THEN** the `_active_di_scope` ContextVar SHALL be reset to its value before the setup started

### Requirement: Component destruction shall dispose DI scope
When a component is destroyed and it has a child DI scope, that scope SHALL be disposed.

#### Scenario: Destroying a component with a DI scope
- **WHEN** a component that called `provide()` during setup is destroyed
- **THEN** its child DI scope SHALL be disposed
- **AND** descendant components' scopes SHALL also be disposed (recursive)

#### Scenario: Destroying a component without a DI scope
- **WHEN** a component that did not call `provide()` during setup is destroyed
- **THEN** no DI scope disposal SHALL occur (no child scope was created)

### Requirement: Context shall provide a provide method
`Context.provide(key, value)` SHALL be available as a convenience method that delegates to the module-level `provide()` function via `_active_di_scope`.

#### Scenario: Using context.provide in a component
- **WHEN** a developer calls `context.provide(ThemeKey, theme)` inside a component setup
- **THEN** the behavior SHALL be identical to calling `provide(ThemeKey, theme)` directly