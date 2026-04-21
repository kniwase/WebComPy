# Proposal: Switch Patch — DOM Node Reuse on Structural Changes

## Summary

Add a DOM node adoption and patching mechanism to `SwitchElement._refresh()` so that when a conditional branch changes, existing DOM nodes that match the new tree structure are reused rather than destroyed and recreated. This is implemented via `_adopt_node()` on `ElementBase` (shared with the full hydration proposal) and `_patch_children()` which recursively compares old and new element trees by tag name. The optimization targets the runtime performance of navigation and conditional UI switching, complementing the hydration proposals which focus on initial load performance.

## Motivation

Currently, `SwitchElement._refresh()` completely destroys all children of the old branch and generates entirely new children from the winning generator. Every DOM node in the outgoing subtree is removed, and every DOM node in the incoming subtree is created from scratch — even when the two subtrees share a large common structure.

The most impactful scenario is page routing via `RouterView`, which uses `SwitchElement` internally. When navigating between pages, common UI elements (navigation bars, sidebars, footers, layout containers) that exist in both the outgoing and incoming page components are needlessly destroyed and recreated. This causes:

1. **Unnecessary DOM API calls** — `createElement`, `appendChild`, `remove` for nodes that structurally exist in both branches
2. **Unnecessary Signal re-initialization** — reactive subscriptions are torn down and re-created for elements that haven't meaningfully changed
3. **Visual disruption** — the browser must re-layout elements that had identical structure, potentially causing a flash
4. **Wasted time in PyScript/Pyodide** — every DOM API call crosses the Python↔JavaScript FFI bridge, which is the most expensive operation in the WebComPy runtime

The existing fine-grained reactivity system (Signal → direct attribute/text update) already handles non-structural changes efficiently. What is missing is structural diffing — recognizing when two element trees overlap and reusing their shared DOM nodes.

## Known Issues Addressed

- **SwitchElement completely regenerates children on change** (from config.yaml known issues) — fully addressed by `_patch_children()` which performs structural comparison and only creates/destroys nodes that actually differ.
- **No virtual DOM diffing — direct DOM manipulation only** (from config.yaml known issues) — partially addressed. This is not a full virtual DOM diffing system (the fine-grained reactivity model remains), but it adds structural diffing at the points where structural changes occur (DynamicElement refresh).

## Non-goals

- This does not implement a React-style virtual DOM with full-tree diffing. The fine-grained reactivity model remains the primary update mechanism for attribute and text changes.
- This does not add component re-rendering or dynamic props propagation. Components are still initialized once; signal-based props remain the mechanism for propagating reactive data.
- This does not change RepeatElement's unkeyed mode — that is addressed in a separate follow-up proposal (`feat/repeat-patch`).
- This does not implement progressive or partial hydration (addressed by `feat/hydration-partial` and `feat/hydration-full`).
- This does not add template-level structural hashing or compile-time analysis. The initial implementation uses tag-name comparison only; template hashing is a future optimization path.
- This does not guarantee that the rollback path (abandoning patch in favor of full rebuild) will never be needed. If Component patching proves too complex, the implementation may fall back to leaf-only patching.

## Dependencies

- **Informed by** `feat/hydration-full` — the `_adopt_node()` method developed here is designed to be the same API that full hydration uses for prerendered node adoption. The two proposals should converge on a single `_adopt_node()` implementation.
- **Informs** `feat/hydration-full` — the `_adopt_node()` design validated here will inform the full hydration implementation.
- **Informed by** `feat/hydration-measurement` — profiling data will validate the runtime performance improvement.
- **Informs** `feat/repeat-patch` (follow-up) — `_patch_children()` and `_adopt_node()` will be reused for RepeatElement's unkeyed mode.

## Design

### Core Concept: Node Adoption

The central operation is `_adopt_node()`, which assigns an existing DOM node to a new `ElementBase` instance without creating a new DOM node. This is the same operation as hydration — the difference is only where the existing DOM node comes from:

| Context | DOM Node Source |
|---------|----------------|
| Hydration | SSR-parsed DOM tree (prerendered HTML) |
| Patch | Previous render's element tree (old branch) |

Both contexts need the same operations on the new Element:
1. Set `_node_cache` to the existing node
2. Set `_mounted = True`
3. Apply attribute diff (set changed attributes, remove stale attributes)
4. Register Signal callbacks for reactive attributes
5. Attach event handlers (new proxies via `create_proxy`)
6. Initialize DomNodeRef if present

### `_adopt_node()` on `ElementBase`

```python
class ElementBase(ElementWithChildren):
    def _adopt_node(self, node: DOMNode) -> None:
        """Adopt an existing DOM node instead of creating a new one.

        The node is assumed to already be in the DOM at the correct position.
        Attributes, event handlers, and Signal callbacks are rebound to this element.
        """
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True

        # Attribute diff: apply current attrs, remove stale ones
        current_attrs = self._get_processed_attrs()
        existing_attr_names = set(node.getAttributeNames())
        new_attr_names = set(current_attrs.keys())
        for name in existing_attr_names - new_attr_names - WEBCOMPY_INTERNAL_ATTRS:
            node.removeAttribute(name)
        for name, value in current_attrs.items():
            if value is not None:
                existing = node.getAttribute(name)
                if existing != value:
                    node.setAttribute(name, value)
            elif name in existing_attr_names:
                node.removeAttribute(name)

        # Signal callbacks for reactive attributes
        for name, value in self._attrs.items():
            if isinstance(value, SignalBase):
                self._add_callback_node(
                    value.on_after_updating(self._generate_attr_updater(name))
                )

        # Event handlers
        self._event_handlers_added = {}
        for name, func in self._event_handlers.items():
            event_handler = _generate_event_handler(func)
            node.addEventListener(name, event_handler, False)
            self._event_handlers_added[name] = event_handler

        # DomNodeRef
        if self._ref:
            self._ref.__init_node__(node)
```

### `_adopt_node()` on `TextElement`

```python
class TextElement(ElementAbstract):
    def _adopt_node(self, node: DOMNode) -> None:
        """Adopt an existing text node."""
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        current_text = self._get_text()
        if node.textContent != current_text:
            node.textContent = current_text
        # Signal callback already registered in __init__
```

### `_is_patchable()` Predicate

```python
def _is_patchable(old: ElementAbstract, new: ElementAbstract) -> bool:
    """Determine whether an old element's DOM node can be reused by a new element."""
    if isinstance(old, TextElement) and isinstance(new, TextElement):
        return True
    if isinstance(old, DynamicElement) or isinstance(new, DynamicElement):
        return False  # DynamicElements have no own DOM node
    if isinstance(old, ElementBase) and isinstance(new, ElementBase):
        return old._tag_name == new._tag_name
    return False
```

This includes `Component` (a subclass of `ElementBase`) in the patchable set. When two Components share the same root tag name, their internal element trees are recursively compared. This is the key decision that enables navigation-time DOM reuse for common layout structures.

**Rollback path:** If Component-inclusive patching proves too complex or fragile, `_is_patchable()` can be restricted to exclude `Component` instances:

```python
    if isinstance(old, Component) or isinstance(new, Component):
        return False  # Fallback: treat Components as unpatchable
```

This would reduce patching to leaf Elements only, deferring Component support to a future phase.

### `_patch_children()` Algorithm

```python
def _patch_children(
    old_children: list[ElementAbstract],
    new_children: list[ElementAbstract],
) -> list[ElementAbstract]:
    """Compare old and new element lists, adopting DOM nodes where possible.

    Returns the new_children list (with DOM nodes adopted where matched).
    Unmatched old elements must be cleaned up by the caller.
    Unmatched new elements must be rendered by the caller.
    """
    matched_old_indices: set[int] = set()

    for new_idx, new_child in enumerate(new_children):
        # Try to find a patchable match in old_children
        for old_idx, old_child in enumerate(old_children):
            if old_idx in matched_old_indices:
                continue
            if _is_patchable(old_child, new_child):
                matched_old_indices.add(old_idx)

                # Adopt the DOM node
                if isinstance(new_child, TextElement) and isinstance(old_child, TextElement):
                    new_child._adopt_node(old_child._node_cache)
                elif isinstance(new_child, ElementBase) and isinstance(old_child, ElementBase):
                    new_child._adopt_node(old_child._node_cache)
                    # Recursively patch children
                    _patch_children(old_child._children, new_child._children)

                # Re-anchor at correct position in DOM
                _reposition_node(new_child, new_idx)
                break
        else:
            # No match found — new_child will need _render()
            pass

    # Cleanup unmatched old children (DOM nodes not adopted)
    for old_idx, old_child in enumerate(old_children):
        if old_idx in matched_old_indices:
            # Node was adopted — only destroy the Python-side state
            old_child._callback_nodes_clear()
            old_child.__purge_signal_members__()
            old_child._clear_node_cache(False)
            # Remove event handlers from adopted node (new element will add its own)
            if isinstance(old_child, ElementBase):
                for name, handler in old_child._event_handlers_added.items():
                    node = old_child._node_cache  # note: cache was cleared
                    # handler cleanup happens via _remove_element pattern
        else:
            # No adoption — standard removal
            old_child._remove_element(recursive=True, remove_node=True)

    return new_children
```

**Note on old element cleanup:** When an old element's DOM node is adopted by a new element, the old element must release its Python-side resources (Signal callbacks, event handler proxies via `destroy()`) without removing the DOM node. This requires a new cleanup method — `_detach_from_node()` — that:

1. Calls `consumer_destroy()` on all `CallbackConsumerNode` instances
2. Calls `handler.destroy()` on all PyScript FFI event handler proxies
3. Calls `__purge_signal_members__()` for SignalReceivable cleanup
4. Calls `DomNodeRef.__reset_node__()` if a ref exists
5. Does NOT call `node.remove()` on the DOM node
6. Does NOT recurse into children (their nodes may also be adopted)

### SwitchElement._refresh() Rewrite

```
CURRENT:
  _refresh():
    idx = _select_generator()
    if idx == _rendered_idx: return
    for child in _children: child._remove_element()       # ← full destroy
    _children = _generate_children(generator)              # ← full generate
    for child in _children: child._render()               # ← full DOM create
    _parent._re_index_children()

PROPOSED:
  _refresh():
    idx = _select_generator()
    if idx == _rendered_idx: return
    new_children = _generate_children(generator)           # ← full Python generate
    old_children = self._children
    self._children = _patch_children(old_children, new_children)
    # _patch_children handles adoption + cleanup of old + marking of new
    for child in self._children:
        if not child._mounted:
            child._render()                                # ← only unadopted new children
    _parent._re_index_children()
```

### Key Concern: Event Handler Proxy Cleanup

In the PyScript environment, event handlers are JavaScript proxies created via `browser.pyscript.ffi.create_proxy()`. These proxies must be explicitly destroyed via `.destroy()` to avoid memory leaks.

The current `_remove_element()` on `ElementBase` handles this:

```python
for name, event_handler in self._event_handlers_added.items():
    node.removeEventListener(name, event_handler)
    event_handler.destroy()
```

In the patch scenario, when an old element's DOM node is adopted by a new element, the old element's event handlers must be removed from the node and their proxies destroyed. But the node itself stays in the DOM. This is handled by `_detach_from_node()`:

```python
class ElementBase:
    def _detach_from_node(self) -> None:
        """Release Python-side resources without removing the DOM node.

        Called when the DOM node is being adopted by another element.
        """
        node = self._node_cache
        if node:
            # Remove old event handlers from the node
            for name, handler in self._event_handlers_added.items():
                node.removeEventListener(name, handler)
                handler.destroy()
        # Destroy Signal callbacks
        for cb in self._callback_nodes:
            consumer_destroy(cb)
        self._callback_nodes.clear()
        # Reset ref
        if self._ref:
            self._ref.__reset_node__()
        # Clear caches (but don't touch the DOM node — new owner needs it)
        self._node_cache = None
        self._mounted = None
        self.__purge_signal_members__()
```

### Key Concern: Component-specific Lifecycle

When a `Component` is the target of patching (i.e., `new_child` is a `Component`), the new Component has already been fully initialized via `__init__()` → `__setup()` → `__init_component()`. This means:

- The new Component's `EffectScope` has been created
- The new Component's DI child scope has been created (if any)
- The new Component's `on_before_rendering` / `on_after_rendering` / `on_before_destroy` hooks have been registered
- The new Component's `HeadPropsStore` entries have been registered

When the old `Component` is cleaned up via `_detach_from_node()` (recursive: no DOM removal), its `on_before_destroy` must still be called to dispose the EffectScope and DI scope. This is already handled because the old Component's `_remove_element()` is called with `recursive=True, remove_node=False`, which triggers `on_before_destroy`.

The key subtlety: `_remove_element(recursive=True, remove_node=False)` on the old Component recurses into its children, calling their `_remove_element()` as well. But some of those children have been adopted by the new tree. Therefore, the cleanup must happen at the `_patch_children()` level rather than via simple recursive `_remove_element()`.

**Resolution:** `_patch_children()` is responsible for cleaning up old elements. For matched (adopted) old elements, it calls `_detach_from_node()` instead of `_remove_element()`. For unmatched old elements, it calls `_remove_element(recursive=True, remove_node=True)` as usual. The old Component at the top level of the old branch is cleaned up after `_patch_children()` has processed its children — its `_detach_from_node()` handles the Component-specific lifecycle (dispose EffectScope, DI scope, head props).

### Rollback Strategy

If Component-inclusive patching proves too complex during implementation, the rollback path is:

1. **Restrict `_is_patchable()`** to exclude `Component` instances — this immediately reduces patching to leaf Elements only without changing any other code.
2. **Remove `_detach_from_node()` from Component** — the Component-specific lifecycle handling is the most complex part. Without Component patching, it becomes unnecessary.
3. **Keep `_adopt_node()` and `_patch_children()` for leaf Elements** — these are still useful for `switch` cases that return raw element trees (not wrapped in Components), and they remain reusable for the `feat/repeat-patch` follow-up.

The rollback does not invalidate the work done on `_adopt_node()` for `ElementBase` and `TextElement`, as these are also needed by the full hydration proposal.

## Implementation Steps

### Step 1: Add `_adopt_node()` to `ElementBase` and `TextElement`

- Implement `ElementBase._adopt_node(node)` with attribute diff, Signal callback registration, event handler attachment, and DomNodeRef initialization.
- Implement `TextElement._adopt_node(node)` with text content update.
- Write unit tests verifying DOM node reuse (no `createElement` calls) and correct attribute/event/Signal rebinding.
- Estimated: 1.5 hours.

### Step 2: Add `_detach_from_node()` to `ElementBase`

- Implement the cleanup method that releases Python-side resources without removing the DOM node.
- Handle Component-specific cleanup (call `on_before_destroy` for EffectScope and DI scope disposal).
- Handle event handler proxy `destroy()` calls.
- Write unit tests verifying no DOM node removal and complete Signal/callback cleanup.
- Estimated: 1.5 hours.

### Step 3: Implement `_patch_children()` and `_is_patchable()`

- Implement the recursive patching algorithm with Component-inclusive `_is_patchable()`.
- Handle matched/unmatched element tracking and cleanup.
- Handle DOM node repositioning (adopted nodes may need to move to their new position in the parent's `childNodes`).
- Write unit tests for various tree shapes: identical structure, partial overlap, complete replacement, Component-to-Component patching.
- Estimated: 2 hours.

### Step 4: Integrate into `SwitchElement._refresh()`

- Replace the full-destroy-and-regenerate logic with `_patch_children()`.
- Only call `_render()` on new children that were not adopted.
- Handle the deferred rendering mechanism (`start_defer_after_rendering` / `end_defer_after_rendering`).
- Write integration tests including routing scenarios via Playwright MCP.
- Estimated: 1 hour.

### Step 5: Evaluate and decide on Component patching

- Run integration tests for Component patching scenarios.
- If issues arise, restrict `_is_patchable()` to exclude `Component` and document the limitation.
- If successful, proceed with the full B-2 approach.
- Estimated: 1 hour.

## Metrics Expected

For a navigation between two pages that share a common layout structure (e.g., `div > (nav > ...) + (main > ...)`):

| Metric | Before | After |
|--------|--------|-------|
| `createElement` calls | ~N (entire subtree) | ~D (only differing nodes) |
| `removeChild` calls | ~N (entire subtree) | ~D (only removed nodes) |
| Signal callback registrations | ~N (all destroyed + recreated) | ~N (still recreated, but on adopted nodes) |
| Event handler proxies | ~N (all destroyed + recreated) | ~N (all destroyed + recreated on adopted nodes) |
| FFI bridge crossings | ~3N (create + mount + attrs) | ~3D + N_attrs (diff + rebind) |

Where N = total nodes in the subtree, D = number of nodes that differ between branches.

For a typical page with 50 shared layout nodes and 30 content-specific nodes: ~130 fewer `createElement`/`appendChild`/`removeChild` calls, each crossing the Python↔JavaScript FFI bridge.

## Specs Affected

- `elements` — adds `_adopt_node()` method to `ElementBase` and `TextElement`; adds `_detach_from_node()` to `ElementBase`; updates the "Conditional rendering shall display one branch at a time" requirement to include DOM node reuse behavior; updates the "Pre-rendered DOM nodes shall be reused during hydration" requirement to reference `_adopt_node()` as the shared mechanism
- `components` — no API changes; internal lifecycle (`on_before_destroy`) is called during patch cleanup
- `app` — no changes needed
- `router` — no API changes; `RouterView` automatically benefits from `SwitchElement` patching