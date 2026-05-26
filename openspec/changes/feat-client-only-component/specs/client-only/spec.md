# Client-Only Component

## Purpose

WebComPy provides a `ClientOnly` element for declaratively rendering content only in the browser environment. During SSR/SSG, `ClientOnly` renders optional fallback content (or nothing). In the browser, `ClientOnly` renders the actual children. This eliminates the need for manual `ENVIRONMENT` checks and ensures browser-specific setup logic (async fetches, signal creation, DI scope changes) never executes on the server.

## ADDED Requirements

### Requirement: ClientOnly shall skip children generator evaluation during SSR/SSG

When `ClientOnlyElement` is rendered in a server environment (`ENVIRONMENT != "pyscript"`), the `children` generator function SHALL NOT be called. Only the `fallback` generator (if provided) SHALL be evaluated and rendered. This ensures that browser-specific side effects (signal creation, async fetches, DI scope changes) are never triggered during static site generation or server-side rendering.

#### Scenario: SSR with fallback content
- **WHEN** a `ClientOnly` element with `fallback=html.P({}, "Loading...")` and `children=lambda: InteractiveChart()` is rendered during SSR
- **THEN** the `children` generator SHALL NOT be called
- **AND** the `fallback` generator SHALL be called exactly once
- **AND** the rendered output SHALL contain only the fallback content

#### Scenario: SSR without fallback content
- **WHEN** a `ClientOnly` element with `children=lambda: AnalyticsWidget()` and no `fallback` is rendered during SSR
- **THEN** the `children` generator SHALL NOT be called
- **AND** the rendered output SHALL contain a zero-width placeholder (empty text node)
- **AND** the placeholder SHALL occupy the correct position in the DOM for later hydration

#### Scenario: SSR with expensive children generator
- **WHEN** a `ClientOnly` element with `children=lambda: ExpensiveComponent()` is rendered during SSR
- **AND** `ExpensiveComponent()` would trigger async fetches or signal creation
- **THEN** `ExpensiveComponent()` SHALL NOT be instantiated
- **AND** no side effects from the children generator SHALL occur

### Requirement: ClientOnly shall render children in the browser environment

When `ClientOnlyElement` is rendered in the browser environment (`ENVIRONMENT == "pyscript"`), the `children` generator SHALL be called and its output rendered. The `fallback` content SHALL NOT be rendered.

#### Scenario: Browser rendering with children
- **WHEN** a `ClientOnly` element with `fallback=html.P({}, "Loading...")` and `children=lambda: InteractiveChart()` is rendered in the browser
- **THEN** the `children` generator SHALL be called exactly once
- **AND** the output of `InteractiveChart()` SHALL be rendered
- **AND** the fallback content SHALL NOT appear in the DOM

#### Scenario: Browser rendering without fallback
- **WHEN** a `ClientOnly` element with `children=lambda: AnalyticsWidget()` and no `fallback` is rendered in the browser
- **THEN** the `children` generator SHALL be called exactly once
- **AND** the output of `AnalyticsWidget()` SHALL be rendered

### Requirement: ClientOnly shall replace fallback with children during hydration

When `ClientOnlyElement._hydrate_node()` is called in the browser, the server-rendered fallback DOM nodes SHALL be replaced with the actual children content. This ensures seamless transition from SSR fallback to interactive browser content without visible layout shift or content mismatch.

#### Scenario: Hydrating a ClientOnly element
- **WHEN** a page containing `ClientOnly(fallback=html.P({}, "Loading..."), children=lambda: InteractiveChart())` is hydrated in the browser
- **THEN** the `<p>Loading...</p>` fallback node SHALL be removed from the DOM
- **AND** the `InteractiveChart()` content SHALL be rendered in its place
- **AND** no hydration mismatch warning or error SHALL occur

#### Scenario: Hydrating a ClientOnly element without fallback
- **WHEN** a page containing `ClientOnly(children=lambda: AnalyticsWidget())` (no fallback) is hydrated in the browser
- **THEN** the placeholder node SHALL be removed from the DOM
- **AND** the `AnalyticsWidget()` content SHALL be rendered in its place

### Requirement: ClientOnly shall be a DynamicElement with async _render()

`ClientOnlyElement` SHALL extend `DynamicElement` and its `_render()` method SHALL be `async def` (inherited from the async rendering pipeline established by `feat/async-rendering-pipeline`). This means `ClientOnly` renders its children directly into the parent element's DOM node, without creating a wrapper element.

#### Scenario: ClientOnly renders children into parent
- **WHEN** a `ClientOnly` element is a child of `html.DIV`
- **THEN** the `ClientOnly`'s rendered children SHALL appear as direct children of the `<div>` element
- **AND** no wrapper element SHALL be inserted between the `<div>` and the children

### Requirement: client_only() generator function shall create ClientOnlyElement instances

The `client_only()` function in `webcompy.elements.generators` SHALL create `ClientOnlyElement` instances. It SHALL accept `children` (a callable returning element content) and optional `fallback` (a callable returning fallback content). This follows the convention established by `switch()` and `repeat()`.

#### Scenario: Using client_only() function
- **WHEN** a developer writes `client_only(children=lambda: InteractiveChart(), fallback=html.P({}, "Loading..."))`
- **THEN** a `ClientOnlyElement` instance SHALL be created with the given generators
- **AND** the element SHALL behave identically to `ClientOnly(children=..., fallback=...)`

### Requirement: ClientOnly shall be exported from webcompy.elements

`ClientOnlyElement` SHALL be exported from `webcompy.elements.types` and `ClientOnly` SHALL be available as a convenience import from `webcompy.elements`. The `client_only` function SHALL be exported from `webcompy.elements`.

#### Scenario: Importing ClientOnly
- **WHEN** a developer writes `from webcompy.elements import ClientOnly, client_only`
- **THEN** both `ClientOnly` and `client_only` SHALL be available
- **AND** `ClientOnly` SHALL be an alias for `ClientOnlyElement`

#### Scenario: Importing ClientOnlyElement
- **WHEN** a developer writes `from webcompy.elements.types import ClientOnlyElement`
- **THEN** `ClientOnlyElement` SHALL be available for type annotations