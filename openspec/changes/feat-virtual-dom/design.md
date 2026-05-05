## Context

After `feat-port-abstraction`, framework code accesses all browser APIs through injectable port interfaces. `ServerDOMPort` currently raises exceptions on `create_element()` and `create_text_node()`. The server-side rendering path still depends on `_render_html()` methods scattered across every element type class — a completely separate code path from the browser's `render()` → `_mount_node()` flow.

This change replaces the exception-throwing stubs in `ServerDOMPort` with a virtual DOM tree implementation and unifies the two rendering paths into a single `render()` entry point.

## Goals / Non-Goals

**Goals:**
- Implement `VirtualDOMNode` satisfying the `DOMNode` Protocol with attribute storage, child management, and `__webcompy_node__` marker
- `ServerDOMPort` returns `VirtualDOMNode` instances from `create_element()` / `create_text_node()`
- Remove all `_render_html()` methods from element type classes
- `render()` becomes the single rendering entry point for both environments
- `ServerDOMPort.render_html(node)` serializes the virtual tree to HTML for SSG
- Server-side tests can inspect full virtual DOM tree structure

**Non-Goals:**
- Browser-side virtual DOM or diffing (remains direct DOM manipulation)
- Performance optimization of virtual tree operations
- Worker-thread rendering
- Hydration of virtual trees (only real DOM nodes are hydrated)

## Decisions

### Decision 1: VirtualDOMNode as a concrete class, not a Protocol

**Chosen**: `VirtualDOMNode` is a concrete class implementing the `DOMNode` Protocol. `BrowserDOMNode` wraps a JS proxy. Both satisfy the same Protocol.

**Rationale**: The Protocol is the contract; implementations are concrete. `VirtualDOMNode` needs mutable state (children list, attribute dict, parent reference) that benefits from a concrete implementation. Making it another Protocol would require mock implementations for tests of the mock, creating infinite regress.

### Decision 2: HTML serialization lives on ServerDOMPort, not VirtualDOMNode

**Chosen**: `ServerDOMPort.render_html(node: DOMNode) -> str` traverses the virtual tree and generates HTML. `VirtualDOMNode` itself has no `to_html()` method.

**Rationale**: HTML formatting concerns (indentation, self-closing tags, attribute escaping, newlines) are serialization logic, not tree structure logic. Keeping serialization on the port allows different serialization strategies (pretty-printed for debugging, minified for production) without modifying the node class. This also keeps `VirtualDOMNode` focused purely on being a DOM tree.

### Decision 3: render() path unification — browser and server share init flow

**Chosen**: Both browser and server execute the same `render()` call chain:
```
render() → _mount_node() → _get_node() → _init_node() → _create_node()
```
On the server, `_create_node()` calls `ServerDOMPort.create_element()` which returns a `VirtualDOMNode`. On the browser, it calls `BrowserDOMPort.create_element()` which returns a `BrowserDOMNode`. The rest of the init flow (`_init_new_node`, `_adopt_node`) works identically since both implement `DOMNode`.

**Rationale**: This eliminates the `_render_html()` divergence. The element system no longer needs to know whether it's producing real DOM or virtual DOM — it just calls `dom_port.create_element()` and operates on the returned `DOMNode`.

**Alternative considered**: Keep `_render_html()` alongside virtual DOM. Rejected because maintaining two paths defeats the purpose. The whole point is unification.

### Decision 4: _render_html() removal strategy — one class at a time

**Chosen**: Remove `_render_html()` from the base class first, then each subclass, ensuring the virtual DOM path produces identical HTML output before deletion.

**Rationale**: The `_render_html()` methods encode element-specific HTML formatting rules (void tags, self-closing, text escaping, attribute ordering). These rules must be replicated in `ServerDOMPort.render_html()` before the old methods can be deleted. A class-by-class approach allows side-by-side comparison during migration.

**Migration order within element types:**
1. `_element.py` — standard elements (most complex, self-closing logic)
2. `_text.py` — text nodes and `<br>` (simple)
3. `_switch.py` — conditional rendering (delegates to children)
4. `_repeat.py` — list rendering (delegates to children)
5. `_dynamic.py` — dynamic elements (delegates)
6. `_abstract.py` — abstract base (remove abstract `_render_html`)
7. `_base.py` — remove `_render_html` from concrete base

### Decision 5: VirtualDOMNode.event_listeners is a list of (event_name, handler) tuples

**Chosen**: Store event listeners as `list[tuple[str, Callable]]` on `VirtualDOMNode`. `addEventListener` appends, `removeEventListener` removes by identity.

**Rationale**: On the server, event listeners are never actually invoked — they're recorded for structural testing. A simple list is sufficient. No FFI proxy wrapping is needed (handled by `ServerFFIPort` which returns functions as-is).

### Decision 6: VirtualDOMNode does not implement removeChild/insertBefore positioning

**Chosen**: `VirtualDOMNode.appendChild()` appends to the children list. `removeChild()` removes by identity from the list. `insertBefore()` and `replaceChild()` are **not implemented** (raise `NotImplementedError` in phase 2).

**Rationale**: The current element system never calls `insertBefore` or `replaceChild` on server-side nodes — those are only called during browser DOM reconciliation (`_reconcile_children` in `_repeat.py`). The virtual tree only needs `appendChild` and `removeChild` for tree construction. Adding unused methods adds complexity without value.

## Risks / Trade-offs

- **[HTML output divergence]** ServerDOMPort.render_html() might produce different HTML than the old _render_html() methods. → Mitigation: generate docs_app with both old and new paths, diff the output, fix discrepancies before deleting _render_html().
- **[Virtual tree memory]** Large pages build full in-memory trees before serialization. → Trade-off accepted: SSG renders one page at a time, tree fits in memory. Equivalent to the string concatenation approach.
- **[Protocol compliance]** VirtualDOMNode must match DOMNode Protocol exactly — any mismatch breaks the unified render path. → Mitigation: type checker (`pyright`) validates Protocol conformance at development time.
