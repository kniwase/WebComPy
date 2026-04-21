# Design: Switch Patch — DOM Node Reuse on Structural Changes

## Design Decisions

### D1: Node adoption is the central primitive
`_adopt_node()` assigns an existing DOM node to a new Python `ElementBase` or `TextElement` instance. This is the same operation as hydration (the node is already in the DOM); the only difference is the source of the node. By extracting `_adopt_node()` into a shared method, both `feat/hydration-full` and `feat/switch-patch` use the same code path for DOM binding.

### D2: `_detach_from_node()` cleans Python-side state without DOM removal
When an old element's node is adopted by a new element, the old element must release its references (event handlers, signal callbacks, DomNodeRef) without removing the DOM node. `_detach_from_node()` performs this cleanup. It is also called on the old top-level SwitchElement branch after `_patch_children()` has processed all its children.

### D3: Component patching is enabled by default with a rollback path
`_is_patchable()` treats `Component` as patchable when its root tag matches. If this proves too complex or fragile, a one-line change to `_is_patchable()` can disable Component patching and restrict it to leaf `Element`/`TextElement` reuse. This rollback path preserves the value of leaf-only patching while deferring full Component patching.

### D4: Structural diffing is tag-name only
The initial implementation matches old and new nodes by tag name (`_tag_name`). This captures the most common case: same layout structure with identical or similar tags. Future iterations may add template hashing or keyed matching.

### D5: Deferred rendering (`start_defer_after_rendering` / `end_defer_after_rendering`) is preserved
`SwitchElement._refresh()` currently defers `on_after_rendering` callbacks until after all DOM operations complete. The patched `_refresh()` must maintain this guarantee.

## Architecture

### Node Reuse Contract

```
                ┌────────────────────────────┐
                │  _adopt_node(node: DOMNode) │
                └────────────┬───────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌──────────┐       ┌──────────┐        ┌──────────┐
   │ Hydration │       │ Switch   │        │ (将来)   │
   │ (SSR      │       │ Patch    │        │ Repeat   │
   │  DOMを    │       │ (旧branch │        │ Patch)   │
   │  再利用)   │       │  DOMを   │        │          │
   └──────────┘       │  再利用)   │        └──────────┘
                       └──────────┘
```

### SwitchElement Refresh Flow (Current vs Proposed)

```
CURRENT _refresh():
══════════════════════════════════════════════════════
  1. idx = _select_generator()
  2. if idx == _rendered_idx: return
  3. for child in self._children:
        child._remove_element(recursive=True)     ← 全破棄
  4. self._children = _generate_children(generator)  ← 全再生成
  5. for child in self._children:
        child._render()                               ← 全DOM作成
  6. self._parent._re_index_children()

PROPOSED _refresh():
══════════════════════════════════════════════════════
  1. idx = _select_generator()
  2. if idx == _rendered_idx: return
  3. new_children = _generate_children(generator)        ← Python再生成
  4. old_children = self._children
  5. self._children = _patch_children(old_children, new_children)
     ┌──────────────────────────────────────────────┐
     │  _patch_children:                            │
     │   - Find tag-name matches                    │
     │   - _adopt_node() for matched pairs          │
     │   - Recurse into children for ElementBase    │
     │   - _reposition_node() to correct DOM pos    │
     │   - _detach_from_node() for adopted old      │
     │   - _remove_element() for unmatched old      │
     └──────────────────────────────────────────────┘
  6. for child in self._children:
        if not child._mounted:
            child._render()                           ← マッチしなかったものだけDOM作成
  7. self._parent._re_index_children()
```

### `_adopt_node()` on `ElementBase`

Identical to the method in `feat/hydration-full`:

```python
class ElementBase(ElementWithChildren):
    def _adopt_node(self, node: DOMNode) -> None:
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

Identical to the method in `feat/hydration-full`:

```python
class TextElement(ElementAbstract):
    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        current_text = self._get_text()
        if node.textContent != current_text:
            node.textContent = current_text
```

### `_detach_from_node()` on `ElementBase`

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
            self._event_handlers_added.clear()
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

### `_detach_from_node()` on `Component`

When a `Component` is the root of an old branch subtree, its lifecycle must still be properly disposed:

```python
class Component(ElementBase):
    def _detach_from_node(self) -> None:
        """Release Python-side resources without removing the DOM node.
        
        Calls on_before_destroy to dispose EffectScope and DI scope.
        """
        super()._detach_from_node()
        try:
            # Call on_before_destroy for EffectScope / DI scope cleanup
            self._call_lifecycle_hook("on_before_destroy")
        except Exception:
            # Log but don't prevent cleanup
            pass
```

**Important:** Since `_detach_from_node()` does NOT recurse into children (their nodes may also be adopted), the parent `_patch_children()` is responsible for calling `_detach_from_node()` on each child. The top-level old branch `Component` is cleaned up after `_patch_children()` has processed all its children.

### `_is_patchable()` Predicate

```python
def _is_patchable(old: ElementAbstract, new: ElementAbstract) -> bool:
    if isinstance(old, TextElement) and isinstance(new, TextElement):
        return True
    if isinstance(old, DynamicElement) or isinstance(new, DynamicElement):
        return False  # DynamicElements have no own DOM node
    if isinstance(old, ElementBase) and isinstance(new, ElementBase):
        return old._tag_name == new._tag_name
    return False
```

**Rollback:** If Component patching proves too fragile:

```python
def _is_patchable(old, new):
    if isinstance(old, Component) or isinstance(new, Component):
        return False  # Fallback: treat Components as unpatchable
    # ... rest unchanged
```

### `_patch_children()` Algorithm

```python
def _patch_children(
    old_children: list[ElementAbstract],
    new_children: list[ElementAbstract],
) -> list[ElementAbstract]:
    matched_old_indices: set[int] = set()

    for new_idx, new_child in enumerate(new_children):
        for old_idx, old_child in enumerate(old_children):
            if old_idx in matched_old_indices:
                continue
            if _is_patchable(old_child, new_child):
                matched_old_indices.add(old_idx)

                if isinstance(new_child, TextElement) and isinstance(old_child, TextElement):
                    new_child._adopt_node(old_child._node_cache)
                elif isinstance(new_child, ElementBase) and isinstance(old_child, ElementBase):
                    new_child._adopt_node(old_child._node_cache)
                    _patch_children(old_child._children, new_child._children)

                _reposition_node(new_child, new_idx)
                break
        else:
            pass  # No match — new_child will be rendered by caller

    # Cleanup unmatched old children (DOM nodes not adopted)
    for old_idx, old_child in enumerate(old_children):
        if old_idx in matched_old_indices:
            old_child._detach_from_node()
        else:
            old_child._remove_element(recursive=True, remove_node=True)

    return new_children
```

### `_reposition_node()` Utility

```python
def _reposition_node(element: ElementAbstract, new_index: int) -> None:
    """Ensure the adopted DOM node is at the correct child index in its parent."""
    node = element._node_cache
    parent = node.parentNode if node else None
    if not parent:
        return
    target = parent.childNodes[new_index] if new_index < parent.childNodes.length else None
    if node != target:
        if target:
            parent.insertBefore(node, target)
        else:
            parent.appendChild(node)
```

## Integration with Deferred Rendering

The existing `start_defer_after_rendering()` / `end_defer_after_rendering()` mechanism in `SwitchElement._refresh()` must be preserved:

```python
def _refresh(self):
    self._start_defer_after_rendering()
    try:
        idx = _select_generator()
        if idx == _rendered_idx:
            return
        # ... patch logic ...
        for child in self._children:
            if not child._mounted:
                child._render()
        self._parent._re_index_children()
    finally:
        self._end_defer_after_rendering()
```

This ensures that `on_after_rendering` hooks of newly created (non-adopted) components run after all DOM mutations are settled.

## Component-Specific Lifecycle Details

When a `Component` is the target of adoption (i.e., it was created in the new branch but its DOM node comes from the old branch):
- The **new** `Component` has already been initialized with a fresh `EffectScope`, DI child scope, registered hooks, and `HeadPropsStore` entries.
- The **old** `Component`'s `_detach_from_node()` disposes its `EffectScope` and triggers `on_before_destroy` (which also removes old `HeadPropsStore` entries from the DI scope).
- The new `Component`'s `on_after_rendering` runs via the deferred rendering mechanism after patch completion.
- Since the old `Component`'s children are processed by `_patch_children()` before the old parent `Component` is cleaned up, child nodes are adopted before the parent calls `_detach_from_node()`.

## Rollback Strategy

If Component-inclusive patching proves too complex:
1. Add `isinstance(old, Component) or isinstance(new, Component): return False` to `_is_patchable()`.
2. The `Component._detach_from_node()` override can be simplified or removed (if not needed for leaf-only).
3. `_adopt_node()` and `_patch_children()` remain fully functional for leaf elements.

## Metrics Expected

| Metric | Before | After | Notes |
|--------|--------|-------|-------|
| `createElement` calls | ~N (entire subtree) | ~D (only differing nodes) | N = total nodes, D = differing nodes |
| `removeChild` calls | ~N | ~D | Old unmatched nodes removed |
| Signal callback registrations | ~N (destroyed + recreated) | ~N (on adopted nodes, recreated) | Unchanged count, but on existing nodes |
| Event handler proxies | ~N (destroyed + recreated) | ~N | Same as above |
| FFI bridge crossings | ~3N | ~3D + N_attrs | DOM create + mount + attribute writes |

For a typical page with 50 shared layout nodes and 30 content-specific nodes: **~130 fewer `createElement`/`appendChild`/`removeChild` calls**, each crossing the Python↔JavaScript FFI bridge.

## Dependencies

- **Informed by:** `feat/hydration-full` — `_adopt_node()` is the same method.
- **Informs:** `feat/hydration-full` — `_adopt_node()` converges on a single implementation.
- **Depends on:** `feat/hydration-measurement` — profiling validates runtime improvement.
- **Informs:** `feat/repeat-patch` (future) — `_patch_children()` and `_adopt_node()` will be reused for unkeyed RepeatElement patching.
