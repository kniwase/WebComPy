## Why

When external JavaScript libraries (e.g., highlight.js) modify the DOM inside elements managed by WebComPy, the framework's cleanup loop in `ElementWithChildren._render()` unconditionally removes all child DOM nodes that exceed `_children_length`. This causes externally-injected content (like syntax-highlighted `<span>` elements) to disappear on any re-render. Additionally, when `_patch_children()` adopts a node from an old element, `_adopt_node()` sets `_mounted=True`, but if external code has already detached that node from the DOM (e.g., by replacing `innerHTML`), `_mount_node()` skips reinsertion because `_mounted` is already `True` — silently leaving a dangling node.

## What Changes

- Add `_mount_node()` recovery path for detached nodes: when `_mounted` is `True` but `node.parentNode` is `None`, reinsert the node into the parent DOM at the correct position
- Introduce `:preserve_children` boolean attribute on `Element`: when set, `ElementWithChildren._render()` and `ElementWithChildren._hydrate_node()` skip the excess-child-node cleanup loop, leaving externally-managed child DOM nodes intact
- Thread `_preserve_children` flag through `Component.__init_component()` so components inherit the flag from their root element
- Add `PreserveChildrenKey` to `generators.py` and wire it through `create_element()` (same pattern as `:ref` via `DomNodeRefKey`)

## Capabilities

### New Capabilities

- `element-preserve-children`: The `:preserve_children` attribute that allows elements to retain externally-managed child DOM nodes across re-renders

### Modified Capabilities

- `elements`: `_mount_node()` gains a detached-node recovery path
- `components`: `Component.__init_component()` propagates `_preserve_children` from the root element

## Impact

- `webcompy/elements/types/_abstract.py`: `_mount_node()` new elif branch
- `webcompy/elements/types/_base.py`: `_render()` and `_hydrate_node()` guard with `_preserve_children`
- `webcompy/elements/types/_element.py`: `Element`, `_get_processed_attrs()`, `_init_new_node()`, `_adopt_node()`
- `webcompy/elements/generators.py`: `PreserveChildrenKey` type, `create_element()` extraction
- `webcompy/components/_component.py`: `_preserve_children` propagation in `__init_component()`
- `docs_app/components/demo_display.py`: update to use `:preserve_children` and `hljs.highlight()` + `innerHTML`
- `docs_app/components/syntax_highlighting.py`: same update
- Tests: new VDOM-based unit tests for all three scenarios

## Known Issues Addressed

- Element System: `SwitchElement` completely regenerates children on change — this change improves node reuse by ensuring detached nodes are re-inserted and externally-managed children are preserved

## Non-goals

- A general-purpose "safe zone" or "shadow DOM"-like mechanism for third-party DOM mutation
- Framework-level integration with specific external libraries (hljs, CodeMirror, Monaco, etc.)
- API for users to imperatively mark arbitrary DOM regions as externally-managed after render
