# Component System

## Purpose

Components are the primary abstraction for building UIs. A component encapsulates a piece of the interface — its structure, behavior, and styling — into a reusable unit. This enables developers to decompose a complex page into manageable pieces, compose those pieces together, and reason about each piece independently.

WebComPy uses function-style components defined with `@define_component`. A setup function receives a `ComponentContext` and returns an element tree. Standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) register hooks without requiring explicit context access. Composables like `useAsyncResult` and `useAsync` encapsulate stateful logic for reuse across components.

Components also provide scoped CSS to prevent styles from leaking between unrelated parts of the UI, and document head management so that each page component can declare its own title and meta tags.

**What WebComPy does not yet provide:** Other frameworks offer dependency injection (Vue's provide/inject, React's Context API) to share state across the component tree without passing props through every intermediate layer. WebComPy currently requires all shared state to be passed via props or accessed through global singletons. Component IDs are generated via MD5 hash, which is not collision-proof for very large applications.

## Requirements

### Requirement: Components shall be defined as reusable, self-contained units
A component SHALL encapsulate a template (what it renders), optional lifecycle hooks (what it does at key moments), and optional scoped CSS (how it looks). The component SHALL be invocable with props and slots to produce a rendered element.

#### Scenario: Creating a function-style component
- **WHEN** a developer decorates a setup function with `@define_component`
- **THEN** the function SHALL receive a `ComponentContext` with `props`, `slots()`, lifecycle hooks, and head management
- **AND** the function SHALL return the component's template as an element tree

#### Scenario: Registering lifecycle hooks via standalone decorators
- **WHEN** a developer uses `@on_after_rendering` as a decorator inside a function-style component setup
- **THEN** the decorated function SHALL be registered as an after-rendering lifecycle hook
- **AND** the behavior SHALL be equivalent to `context.on_after_rendering(func)`

### Requirement: Components shall receive data via props
A parent component SHALL be able to pass data to a child component through props, which the child accesses as a typed object via `context.props`.

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
Components SHALL provide hooks for before rendering, after rendering, and before destruction. These hooks allow components to perform side effects like fetching data, setting up subscriptions, or cleaning up resources. When `on_after_rendering` is triggered as part of a reactive update cascade (e.g., during `SwitchElement._refresh()`), it SHALL be deferred until after the reactive propagation completes, ensuring the DOM is fully settled before side effects run.

#### Scenario: Using standalone lifecycle decorators in a function-style component
- **WHEN** a developer uses `@on_after_rendering` or `@on_before_destroy` inside a `@define_component` setup function
- **THEN** the hooks SHALL fire at the same lifecycle points as `context.on_after_rendering()` and `context.on_before_destroy()`
- **AND** the hooks SHALL be cleaned up when the component is destroyed

#### Scenario: Cleaning up before destruction
- **WHEN** a component is removed from the DOM
- **THEN** its `on_before_destroy` callback SHALL fire
- **AND** the component's title and meta entries SHALL be removed from the document head

#### Scenario: After-rendering hook during route navigation
- **WHEN** a component's `on_after_rendering` hook fires as a result of a route change (i.e., `SwitchElement._refresh()` replacing one component with another)
- **THEN** the hook SHALL execute after the entire DOM update and reactive propagation has completed
- **AND** any async operations started in the hook SHALL run in a clean event loop context

### Requirement: Component after-rendering lifecycle hook shall be deferred when triggered by reactive navigation
When a component's `on_after_rendering` hook is triggered as a side effect of a reactive change (such as a route change via `SwitchElement._refresh()`), the hook SHALL NOT execute synchronously within the reactive callback chain. Instead, it SHALL be deferred to run after the reactive propagation has completed and the DOM is fully updated.

#### Scenario: Navigating to a page that starts async operations in on_after_rendering
- **WHEN** a user clicks a `RouterLink` to navigate to a new page
- **AND** the new page component has an `on_after_rendering` hook that starts an async operation (e.g., `HttpClient.get()`)
- **THEN** the async operation SHALL execute successfully without errors
- **AND** the component SHALL be fully mounted in the DOM before `on_after_rendering` fires

#### Scenario: Direct URL access to a page with on_after_rendering
- **WHEN** a page is loaded directly via URL (initial hydration)
- **AND** the page component has an `on_after_rendering` hook
- **THEN** `on_after_rendering` SHALL fire after the component is fully rendered
- **AND** the behavior SHALL be consistent with the deferred behavior during navigation

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