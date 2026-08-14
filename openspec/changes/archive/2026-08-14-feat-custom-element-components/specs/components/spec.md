## ADDED Requirements

### Requirement: Component definitions may opt into a named custom-element boundary

The function-style component API SHALL expose the custom-element name and observed-attribute options through `define_component`. The Python setup function name SHALL remain the component name used for existing component registration and cid generation; the custom-element name SHALL be an explicit separate value.

#### Scenario: Separating Python and DOM names
- **WHEN** `@define_component("user-card")` decorates `UserCard`
- **THEN** the component registry SHALL retain `UserCard` as the component definition name
- **AND** the rendered DOM boundary SHALL use `<user-card>`
- **AND** existing `webcompy-component` and cid markers SHALL continue to identify `UserCard`

### Requirement: Named component setup functions may return multiple roots

An explicitly named component SHALL accept a sequence of renderable children as its setup result. The sequence SHALL be rendered in order inside the custom-element boundary. An unnamed component SHALL continue to require its existing single element root.

#### Scenario: Returning multiple component roots
- **WHEN** a named component returns an ordered sequence of header, content, and footer elements
- **THEN** all three elements SHALL be rendered inside the named component
- **AND** their order SHALL match the returned sequence

#### Scenario: Rejecting multiple roots for an unnamed component
- **WHEN** an unnamed component returns a sequence with more than one renderable child
- **THEN** component initialization SHALL raise the existing component root error
- **AND** unnamed component DOM behavior SHALL remain unchanged

### Requirement: ComponentContext shall provide document-connection hooks for named components

`ComponentContext` SHALL provide `on_mounted` and `on_unmounted` registration methods for named custom-element components. The methods SHALL accept the same synchronous or asynchronous callback forms supported by the existing lifecycle hooks. The hooks SHALL be released with the component binding.

#### Scenario: Registering document-connection hooks
- **WHEN** a named component calls `context.on_mounted(on_mount)` and `context.on_unmounted(on_unmount)` during setup
- **THEN** both callbacks SHALL be stored for that component instance
- **AND** they SHALL be invoked at the custom-element document-connection points

#### Scenario: Keeping existing lifecycle hooks
- **WHEN** a component registers `on_before_rendering`, `on_after_rendering`, or `on_before_destroy`
- **THEN** each existing hook SHALL retain its current trigger and ordering
- **AND** adding document-connection hooks SHALL not replace or reorder those existing hooks

### Requirement: Document-connection hooks shall be available as standalone decorators

The framework SHALL provide `@on_mounted` and `@on_unmounted` standalone decorators usable inside a named component setup function, equivalent to `context.on_mounted(func)` and `context.on_unmounted(func)`. Using them outside a component setup SHALL raise the same error class as the existing lifecycle decorators.

#### Scenario: Registering hooks via standalone decorators
- **WHEN** a named component applies `@on_mounted` and `@on_unmounted` inside its setup function
- **THEN** both callbacks SHALL be registered for that component instance
- **AND** their behavior SHALL be equivalent to the `ComponentContext` methods

#### Scenario: Using a standalone decorator outside setup
- **WHEN** `@on_mounted` or `@on_unmounted` is applied outside a component setup function
- **THEN** an error SHALL be raised indicating the decorator must be used inside component setup

### Requirement: Document-connection hooks shall be rejected for unnamed components

When an unnamed component registers `on_mounted` or `on_unmounted`, either via the `ComponentContext` methods or via the standalone decorators, component setup SHALL raise `WebComPyComponentException`. The framework SHALL not silently accept the registration and never fire the callback.

#### Scenario: Rejecting hooks in an unnamed component
- **WHEN** an unnamed component calls `context.on_mounted(callback)` during setup
- **THEN** `WebComPyComponentException` SHALL be raised
- **AND** no document-connection callback SHALL be registered

#### Scenario: Rejecting decorators in an unnamed component
- **WHEN** an unnamed component applies `@on_mounted` or `@on_unmounted` during setup
- **THEN** `WebComPyComponentException` SHALL be raised
- **AND** no document-connection callback SHALL be registered

### Requirement: Component scoped styles shall support the named host selector

Scoped styles for a named component SHALL accept `:host` and `:host(<compound-selector>)` as aliases for that component's custom-element wrapper. The generated selector SHALL retain the existing cid attribute scoping and SHALL be shared by static and reactive style paths.

#### Scenario: Styling the custom-element wrapper
- **WHEN** a named component declares scoped style `{":host": {"display": "block"}}`
- **THEN** the generated CSS SHALL target the custom-element wrapper
- **AND** the selector SHALL include the component's existing cid attribute

#### Scenario: Styling a host state
- **WHEN** a named component declares scoped style `{":host(.compact)": {"padding": "0"}}`
- **THEN** the generated CSS SHALL target the named custom element with the `.compact` class
- **AND** the selector SHALL remain cid-scoped

#### Scenario: Rejecting host syntax without a named element
- **WHEN** an unnamed component uses `:host` in its scoped style
- **THEN** style generation SHALL raise `WebComPyException`
- **AND** no invalid `:host` selector SHALL be emitted
