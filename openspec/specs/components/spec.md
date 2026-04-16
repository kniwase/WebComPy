# Component System

## Purpose

Components are the primary abstraction for building UIs. A component encapsulates a piece of the interface — its structure, behavior, and styling — into a reusable unit. This enables developers to decompose a complex page into manageable pieces, compose those pieces together, and reason about each piece independently.

WebComPy supports two definition styles that serve different needs: function-style components provide a concise, setup-centric API for simple components, while class-style components offer lifecycle decorators and better organization for complex components. Both produce the same `ComponentGenerator` interface, so consumers cannot distinguish between the two styles.

Components also provide scoped CSS to prevent styles from leaking between unrelated parts of the UI, and document head management so that each page component can declare its own title and meta tags.

## Requirements

### Requirement: Components shall be defined as reusable, self-contained units
A component SHALL encapsulate a template (what it renders), optional lifecycle hooks (what it does at key moments), and optional scoped CSS (how it looks). The component SHALL be invocable with props and slots to produce a rendered element.

#### Scenario: Creating a function-style component
- **WHEN** a developer decorates a setup function with `@define_component`
- **THEN** the function SHALL receive a `ComponentContext` with `props`, `slots()`, lifecycle hooks, and head management
- **AND** the function SHALL return the component's template as an element tree

#### Scenario: Creating a class-style component
- **WHEN** a developer subclasses `ComponentAbstract` with `@component_template` and optional lifecycle decorators
- **THEN** the class SHALL define its template as a method
- **AND** lifecycle hooks SHALL be registered via `@on_before_rendering`, `@on_after_rendering`, and `@on_before_destroy`

### Requirement: Components shall receive data via props
A parent component SHALL be able to pass data to a child component through props, which the child accesses as a typed object via `context.props` (function-style) or `self.context.props` (class-style).

#### Scenario: Passing user data to a profile component
- **WHEN** a parent renders `UserProfile(user_data)`
- **THEN** the `UserProfile` component SHALL receive `user_data` as `context.props`
- **AND** the component SHALL be able to use reactive values from props in its template

### Requirement: Components shall support slots for content projection
A component SHALL define named slots that parent components can fill with content, enabling composition patterns where the parent controls what appears in certain regions of the child's template.

#### Scenario: Using a named slot with fallback
- **WHEN** a component calls `context.slots("header", fallback=lambda: html.H1({}, "Default"))`
- **AND** a parent provides content for the "header" slot
- **THEN** the parent's content SHALL be rendered
- **WHEN** no content is provided for the "header" slot
- **THEN** the fallback SHALL be rendered

### Requirement: Scoped CSS shall prevent style leakage between components
A component's scoped CSS SHALL be automatically prefixed with an attribute selector unique to that component, ensuring that styles only apply to elements within that component.

#### Scenario: Defining scoped styles
- **WHEN** a developer sets `generator.scoped_style = {".btn": {"color": "red"}}`
- **THEN** the generated CSS SHALL be `.btn[webcompy-cid-{id}] { color: red; }`
- **AND** the component's root element SHALL have the `webcompy-cid-{id}` attribute
- **AND** the `.btn` style SHALL NOT affect `.btn` elements in other components

### Requirement: Components shall manage their lifecycle
Components SHALL provide hooks for before rendering, after rendering, and before destruction. These hooks allow components to perform side effects like fetching data, setting up subscriptions, or cleaning up resources.

#### Scenario: Fetching data before rendering
- **WHEN** a component registers `on_before_rendering` to load data from an API
- **THEN** the data SHALL be available before the component renders

#### Scenario: Cleaning up before destruction
- **WHEN** a component is removed from the DOM
- **THEN** its `on_before_destroy` callback SHALL fire
- **AND** the component's title and meta entries SHALL be removed from the document head

### Requirement: Components shall manage document head properties
Each component instance SHALL be able to set the document title and meta tags. When multiple components set the title, the most recently rendered one SHALL take precedence. When a component is destroyed, its head entries SHALL be removed.

#### Scenario: Setting the page title from a component
- **WHEN** a component calls `context.set_title("My Page")`
- **THEN** the document title SHALL update to "My Page"
- **AND** when the component is destroyed, its title entry SHALL be removed

### Requirement: Component registration shall enforce unique names
The framework SHALL maintain a global registry of component generators by name. If two components are registered with the same name, an error SHALL be raised.

#### Scenario: Registering duplicate component names
- **WHEN** a developer defines two components with the same name
- **THEN** `WebComPyComponentException` SHALL be raised with a message about the duplicate