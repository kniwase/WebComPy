# Elements — Delta: feat-hydration-partial

## Changes

### Updated: Pre-rendered DOM nodes shall skip redundant writes during hydration

When attributes or text content on a prerendered node already match the component's current state, the framework SHALL NOT perform `setAttribute` or `textContent` assignment. This optimization applies only to prerendered nodes (those with `__webcompy_prerendered_node__ = True`); newly created nodes retain unconditional writes.

For `TextElement._init_node()`: text content SHALL be compared via `existing_node.textContent` before assignment. If equal, no DOM write occurs.

For `Element._init_node()`: each attribute SHALL be compared via `node.getAttribute(name)` before `setAttribute`. If equal, no DOM write occurs. Attributes with `None` value in the component state SHALL still be removed via `removeAttribute` if present on the node.

### Updated: Loading screen shall be semi-transparent

The loading screen overlay (`#webcompy-loading`) SHALL use a semi-transparent dark background (e.g., `rgba(0, 0, 0, 0.5)`) instead of an opaque background. This allows the pre-rendered content beneath to remain visible during hydration, so the user sees content immediately and developers can observe the hydration process.