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

### Requirement: ClientOnly shall not execute children component __init__ on the server

When `ClientOnlyElement` is rendered in a server environment, the `children` generator function SHALL NOT be called at all — not even to create `Component` instances. This means `Component.__init__()` SHALL NOT execute for any component defined inside a `ClientOnly` boundary during SSR/SSG. This prevents browser-only imports, DOM API calls, and PyScript-specific code from being triggered during static site generation.

#### Scenario: ClientOnly block with browser-only imports
- **WHEN** a developer writes:
  ```python
  ClientOnly(
      fallback=html.P({}, "Chart loading..."),
      children=lambda: MyChartComponent(props)
  )
  ```
- **AND** `MyChartComponent.__init__()` imports or references a PyScript-only module
- **AND** the page is rendered during SSG
- **THEN** `MyChartComponent.__init__()` SHALL NOT be executed
- **AND** no ImportError or NameError SHALL occur
- **AND** only the fallback content SHALL appear in the generated HTML

#### Scenario: ClientOnly block with inline browser-only setup
- **WHEN** a developer writes `ClientOnly(children=lambda: html.CANVAS({}, "content"))` during SSG
- **AND** `html.CANVAS` may reference browser-only module code
- **THEN** the `lambda` SHALL NOT be called on the server
- **AND** the canvas element SHALL NOT be part of the SSR output

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

When `ClientOnlyElement._hydrate_node()` is called in the browser, the server-rendered fallback DOM nodes SHALL be replaced with the actual children content. Because `_render()` is async (per `feat/async-rendering-pipeline`), `_hydrate_node()` SHALL NOT call `child._render()` directly — that would produce an un-awaited coroutine. Instead, `_hydrate_node()` SHALL generate the children, set up their DOM references, and schedule the async rendering via `asyncio.ensure_future(self._render())`. The fallback nodes SHALL be removed from the DOM and the children content SHALL render in their place, ensuring seamless transition from SSR fallback to interactive browser content without visible layout shift or content mismatch.

#### Scenario: Hydrating a ClientOnly element
- **WHEN** a page containing `ClientOnly(fallback=html.P({}, "Loading..."), children=lambda: InteractiveChart())` is hydrated in the browser
- **THEN** the `<p>Loading...</p>` fallback node SHALL be removed from the DOM
- **AND** `ClientOnlyElement._hydrate_node()` SHALL generate the children and schedule async rendering via `asyncio.ensure_future(self._render())`
- **AND** the `InteractiveChart()` content SHALL be rendered asynchronously in its place
- **AND** if `self._render()` raises during this async rendering, the error SHALL be logged via the framework's error reporting mechanism and the fallback SHALL NOT be restored (the DOM may be in a transitional state)
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