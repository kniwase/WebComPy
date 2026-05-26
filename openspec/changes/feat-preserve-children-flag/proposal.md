## Why

When external JavaScript libraries (e.g., highlight.js) modify the DOM inside elements managed by WebComPy, the framework's cleanup loop in `ElementWithChildren._render()` unconditionally removes all child DOM nodes that exceed `_children_length`. This causes externally-injected content (like syntax-highlighted `<span>` elements) to disappear on any re-render. Additionally, when `_patch_children()` adopts a node from an old element, `_adopt_node()` sets `_mounted=True`, but if external code has already detached that node from the DOM (e.g., by replacing `innerHTML`), `_mount_node()` skips reinsertion because `_mounted` is already `True` — silently leaving a dangling node.

A separate SPA navigation bug was discovered during implementation: when `_patch_children()` removes an unmatched old child (e.g., a `<br>` element created by `NewLine`), the DOM sibling indices shift. `NewLine._init_node()` then finds a different sibling node at the expected index (e.g., a Code card `<div>`), detects the tag mismatch, and unconditionally calls `existing_node.remove()` — destroying WebComPy-managed content. After `_patch_children()` completes and calls `_render()` on remaining children, the destroyed nodes are missing from the DOM, causing visual content loss during client-side navigation.

## What Changes

- Add `_mount_node()` recovery path for detached nodes: when `_mounted` is `True` but `node.parentNode` is `None`, reinsert the node into the parent DOM at the correct position
- Introduce `:preserve_children` boolean attribute on `Element`: when set, `ElementWithChildren._render()` and `ElementWithChildren._hydrate_node()` skip the excess-child-node cleanup loop, leaving externally-managed child DOM nodes intact
- Thread `_preserve_children` flag through `Component.__init_component()` so components inherit the flag from their root element
- Fix `NewLine._init_node()` to check for `__webcompy_node__` before removing an existing DOM node at the sibling index, preventing it from destroying WebComPy-managed nodes during SPA navigation
- Add `PreserveChildrenKey` to `generators.py` and wire it through `create_element()` (same pattern as `:ref` via `DomNodeRefKey`)
- Enhance `SyntaxHighlighting` component: accept `SignalBase[str]` in addition to `str` for the `code` prop, add input validation (size limit, null-byte detection), switch from `hljs.highlightElement()` to `hljs.highlight()` + `innerHTML`, use `:preserve_children` on the `<code>` element
- Simplify `DemoDisplay`: remove duplicated hljs logic, delegate code rendering to `SyntaxHighlighting` with `source_code` Signal

## Capabilities

### New Capabilities

- `element-preserve-children`: The `:preserve_children` attribute that allows elements to retain externally-managed child DOM nodes across re-renders
- `syntax-highlighting-component`: A reusable `SyntaxHighlighting` component with `SignalBase[str]` support, input validation, and safe `hljs.highlight()` integration — **this is a docs_app-internal component and is not synced to the main framework specs**

### Modified Capabilities

- `elements`: `_mount_node()` gains a detached-node recovery path; `NewLine._init_node()` protects WebComPy-managed nodes from accidental removal
- `components`: `Component.__init_component()` propagates `_preserve_children` from the root element

## Impact

- `webcompy/elements/types/_abstract.py`: `_mount_node()` new elif branch
- `webcompy/elements/types/_text.py`: `NewLine._init_node()` `__webcompy_node__` guard
- `webcompy/elements/types/_base.py`: `_render()` and `_hydrate_node()` guard with `_preserve_children`
- `webcompy/elements/types/_element.py`: `Element`, `_get_processed_attrs()`, `_init_new_node()`, `_adopt_node()`
- `webcompy/elements/generators.py`: `PreserveChildrenKey` type, `create_element()` extraction
- `webcompy/components/_component.py`: `_preserve_children` propagation in `__init_component()`
- `docs_app/components/syntax_highlighting.py`: Signal support, input validation, `hljs.highlight()` + `innerHTML`, `:preserve_children`
- `docs_app/components/demo_display.py`: remove hljs logic, delegate to `SyntaxHighlighting`
- `docs_app/templates/home.py`: existing `SyntaxHighlighting` call sites remain compatible (static string props unchanged)
- Tests: new VDOM-based unit tests for all three scenarios + syntax highlighting component tests

## Known Issues Addressed

- Element System: `SwitchElement` completely regenerates children on change — this change improves node reuse by ensuring detached nodes are re-inserted and externally-managed children are preserved

## Non-goals

- A general-purpose "safe zone" or "shadow DOM"-like mechanism for third-party DOM mutation
- Framework-level integration with specific external libraries (hljs, CodeMirror, Monaco, etc.)
- API for users to imperatively mark arbitrary DOM regions as externally-managed after render
