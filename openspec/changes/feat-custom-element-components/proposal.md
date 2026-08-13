## Why

WebComPy components currently render as their template's single root element and identify their boundary through framework-specific attributes. This makes component boundaries less visible in browser tooling and prevents a component from returning multiple root elements without changing the element reconciliation model. Defining named components as Light DOM custom elements provides a native DOM boundary, preserves a one-node component boundary for reconciliation, and creates an integration point for browser lifecycle and attribute-based interoperation.

## What Changes

- Extend `define_component` with an optional custom element name and declarations for observed attributes.
- Render named components as one custom-element wrapper node whose children are the component's template output.
- Allow named components to return multiple root children while preserving the existing one-node boundary seen by parent elements, `repeat`, and `switch`.
- Register named component elements in the browser and expose document-connection lifecycle hooks for mounted and unmounted custom elements.
- Define the browser registration and hydration ordering so server-rendered custom-element tags are upgraded before client hydration.
- Reflect declared custom-element attribute changes into component props in the attribute-to-props direction only.
- Preserve the existing `webcompy-component` and `webcompy-cid-*` markers so current scoped CSS and hydration behavior remain compatible.
- Add scoped-style `:host` support for named components, including static and reactive scoped styles and server-rendered output.
- Add unit, browser, hydration, SSR/SSG, reconciliation, attribute-reflection, lifecycle, and scoped-style coverage plus documentation.

## Known Issues Addressed

- None. The existing MD5-based component ID generation remains unchanged; this change does not address its collision risk.

## Non-goals

- Shadow DOM or Shadow DOM-based style encapsulation.
- Replacing cid-attribute scoping with tag-selector scoping. Nested component boundaries require a separate design for that migration.
- Reflecting component props or signals back to custom-element attributes.
- A general utility for exposing browser events as read-only signals. That will be considered in a separate change.
- Removing or deprecating unnamed components and their existing single-root behavior.

## Capabilities

### New Capabilities

- `custom-element-components`: Named Light DOM custom elements for component boundaries, multi-root component content, browser lifecycle callbacks, attribute-to-props reflection, registration, and hydration coordination.

### Modified Capabilities

- `components`: Named component definitions, wrapper rendering, multi-root output, mounted/unmounted lifecycle hooks, observed attributes, and `:host` scoped-style behavior.
- `app-lifecycle`: Browser registration and custom-element upgrade ordering before hydration.
- `scoped-css-incremental`: Static scoped-style handling for `:host` in incrementally injected styles.
- `reactive-scoped-style`: Reactive scoped-style handling for `:host` using the same selector transformation as static styles.

## Impact

- Affects the function-component generator and component/context lifecycle APIs in the browser core.
- Adds a browser-port/FFI integration for custom-element registration and lifecycle/attribute callbacks; server rendering remains browser-API-free.
- Changes the DOM shape of components that opt into a custom element name, while preserving the existing DOM shape for unnamed components.
- Requires app startup and hydration coordination, custom-element registry collision handling, and tests for multiple apps or duplicate names on one page.
- Reuses the current cid markers and shared CSS selector transformation so SSR, runtime injection, and reactive style updates remain aligned.
