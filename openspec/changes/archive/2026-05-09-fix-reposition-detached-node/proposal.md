## Why

When `_patch_children()` adopts a DOM node whose `parentNode` is `null` (detached from DOM by external code such as highlight.js replacing innerHTML), `_reposition_node()` silently returns without reinserting the node. The adopted node carries the correct content but remains invisible, and the stale DOM children left by the external code are never fully cleaned up. This causes content to disappear on page transitions between structurally similar pages (e.g., navigating between demo pages that share the same `DemoDisplay` layout).

## What Changes

- Fix `_reposition_node()` to handle detached nodes by resolving the correct parent DOM node from the element tree (`element._parent._get_node()`), then inserting the node at the target index

## Capabilities

### New Capabilities

None. This is a bug fix.

### Modified Capabilities

- **elements**: `_reposition_node()` SHALL recover when a node has been detached from its DOM parent by an external mutation, reinserting it into the correct parent DOM node obtained via `element._parent._get_node()`

## Impact

- `webcompy/elements/types/_dynamic.py` (`_reposition_node`)
- Affected user-visible scenarios: SwitchElement/RouterView page transitions when external JS (hljs, chart libraries, etc.) modifies child DOM nodes of elements that `_patch_children` reuses
