## MODIFIED Requirements

### Requirement: Components shall be defined as reusable, self-contained units
A component SHALL encapsulate a template (what it renders), optional lifecycle hooks (what it does at key moments), and optional scoped CSS (how it looks). The component SHALL be invocable with props and slots to produce a rendered element.

#### Scenario: Creating a function-style component
- **WHEN** a developer decorates a setup function with `@define_component`
- **THEN** the function SHALL receive a `ComponentContext` with `props`, `slots()`, lifecycle hooks, and head management
- **AND** the function SHALL return the component's template as an element tree

#### Scenario: Creating a class-style component (DEPRECATED)
- **WHEN** a developer subclasses `ComponentAbstract` with `@component_template` and optional lifecycle decorators
- **THEN** the class SHALL define its template as a method
- **AND** lifecycle hooks SHALL be registered via `@on_before_rendering`, `@on_after_rendering`, and `@on_before_destroy`
- **AND** a `DeprecationWarning` SHALL be emitted indicating that class-style components are deprecated in favor of function-style components with composables

#### Scenario: Registering lifecycle hooks via standalone decorators
- **WHEN** a developer uses `@on_after_rendering` as a decorator inside a function-style component setup
- **THEN** the decorated function SHALL be registered as an after-rendering lifecycle hook
- **AND** the behavior SHALL be equivalent to `context.on_after_rendering(func)`

### Requirement: Components shall manage their lifecycle
Components SHALL provide hooks for before rendering, after rendering, and before destruction. These hooks allow components to perform side effects like fetching data, setting up subscriptions, or cleaning up resources. When `on_after_rendering` is triggered as part of a reactive update cascade (e.g., during `SwitchElement._refresh()`), it SHALL be deferred until after the reactive propagation completes, ensuring the DOM is fully settled before side effects run.

#### Scenario: Using standalone lifecycle decorators in a function-style component
- **WHEN** a developer uses `@on_after_rendering` or `@on_before_destroy` inside a `@define_component` setup function
- **THEN** the hooks SHALL fire at the same lifecycle points as `context.on_after_rendering()` and `context.on_before_destroy()`
- **AND** the hooks SHALL be cleaned up when the component is destroyed