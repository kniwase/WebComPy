## Context

After `feat-port-abstraction`, framework code accesses all browser APIs through injectable port interfaces. `ServerDOMPort` currently raises exceptions on `create_element()` and `create_text_node()`. The server-side rendering path still depends on `_render_html()` methods scattered across every element type class — a completely separate code path from the browser's `render()` → `_mount_node()` flow.

This change replaces the exception-throwing stubs in `ServerDOMPort` with a virtual DOM tree implementation and unifies the two rendering paths into a single `render()` entry point.

## Goals / Non-Goals

**Goals:**
- Implement `VirtualDOMNode` satisfying the `DOMNode` Protocol with attribute storage, child management, and `__webcompy_node__` marker
- Implement `VirtualDOMEvent` satisfying the `DOMEvent` Protocol with full event propagation (at-target + bubbling)
- Add `dispatchEvent` to `DOMNode` Protocol and `create_event` to `DOMPort` ABC
- Move `DOMEvent` Protocol from `webcompy/elements/_dom_objs.py` to `webcompy/ports/_dom.py`
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
- Capturing phase (event handlers always use `useCapture=False`; at-target + bubbling only)
- `document.createEvent("MouseEvent")`-style legacy API (constructor-style only)

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

### Decision 4: _render_html() removal strategy — implement virtual DOM first, remove old methods last

**Chosen**: Implement `VirtualDOMNode` and `ServerDOMPort.render_html()`, update callers (`cli/_html.py`), then remove `_render_html()` from element base classes last. Ensure the virtual DOM path produces identical HTML output before deletion.

**Rationale**: The `_render_html()` methods encode element-specific HTML formatting rules (void tags, self-closing, text escaping, attribute ordering). These rules must be replicated in `ServerDOMPort.render_html()` before the old methods can be deleted.

**Correct migration ordering:**
1. Implement `VirtualDOMNode` + `VirtualDOMEvent` + `ServerDOMPort.render_html()` (groups 1-2)
2. Update `cli/_html.py` to use `ServerDOMPort.render_html()` (group 6)
3. THEN remove `_render_html()` from element classes — subclasses first (`_text.py`, `_dynamic.py`), base classes last (`_base.py`, `_abstract.py`) (groups 3, 5)

### Decision 5: VirtualDOMNode.event_listeners is a list of (event_name, handler) tuples

**Chosen**: Store event listeners as `list[tuple[str, Callable]]` on `VirtualDOMNode`. `addEventListener` appends, `removeEventListener` removes by identity.

**Rationale**: `ServerFFIPort.create_proxy()` returns the handler as-is (identity). The handlers stored here are the exact functions produced by `_generate_event_handler()`, which wraps user handlers for async resolution. No FFI proxy wrapping is needed.

### Decision 5b: VirtualDOMNode.dispatchEvent() implements standard event propagation

**Chosen**: `VirtualDOMNode.dispatchEvent(event: DOMEvent) -> bool` executes the at-target phase followed by the bubbling phase (if `event.bubbles` is `True`). `VirtualDOMEvent` is a concrete class satisfying the `DOMEvent` Protocol with full event fields.

Event propagation flow:
```
dispatchEvent(event) on a node:
  1. Set event.target = node, event.eventPhase = AT_TARGET (2)
  2. Set event.currentTarget = node
  3. Fire all stored handlers matching event.type synchronously
  4. If event.bubbles and not event._propagation_stopped:
     a. Walk node.parentNode chain upward
     b. For each ancestor:
        - Set event.eventPhase = BUBBLING (3)
        - Set event.currentTarget = ancestor
        - Fire ancestor's handlers matching event.type
        - Stop if event._propagation_stopped
  5. Return not event.defaultPrevented
```

**Rationale**: Three facts make full event propagation viable without a browser:
1. **Handler wrapping happens at `addEventListener` time** — `_generate_event_handler()` wraps the user handler and `ServerFFIPort.create_proxy()` returns it as-is. The stored handler is call-ready.
2. **Signal propagation is synchronous** — `Signal.set_value()` triggers all `on_after_updating` callbacks within the same call stack.
3. **The unified render path** renders to `VirtualDOMNode` — `render()` → `_mount_node()` operates on the virtual tree identically.

The capturing phase is intentionally excluded because WebComPy always passes `useCapture=False` to `addEventListener` — all framework-registered handlers run during the bubbling phase. Bubbling through the ancestor chain is straightforward since `VirtualDOMNode` stores `_parent` references. `event.stopPropagation()` allows event handlers to prevent ancestor dispatch, matching browser behavior.

`preventDefault` gates on `event.cancelable` per spec: `event.defaultPrevented` is set to `True` only when `cancelable` is `True`. The return value (`True` unless default prevented) enables guards like `if not node.dispatchEvent(...): return`.

```python
result = TestRenderer.render(Counter)
button = result.query_selector("button")
assert result.find_by_text("Clicked: 0")

event = VirtualDOMEvent("click", bubbles=True, cancelable=True)
button.dispatchEvent(event)
# → handler fires → signal.set(1) → computed recalc → _refresh()
# → VirtualDOMNode.appendChild()

result.rerender()
assert result.find_by_text("Clicked: 1")
assert event.defaultPrevented == False
```

**Alternative considered**: Skip bubbling, only fire on the target node. Rejected because bubbling is a core DOM event semantic. Without bubbling, event delegation patterns (where a parent listens for child events) would not be testable, and the behavior would diverge from browser DOM. Walking the ancestor chain is a trivial `while parent` loop.

### Decision 9: DOMPort.create_event() — constructor-style event factory

**Chosen**: `DOMPort.create_event(event_type: str, *, bubbles: bool = False, cancelable: bool = False) -> DOMEvent`. BrowserDOMPort creates a native JS `Event` (via `new Event(type, {bubbles, cancelable})`), ServerDOMPort returns a `VirtualDOMEvent`.

```python
def create_event(self, event_type: str, *, bubbles: bool = False, cancelable: bool = False) -> DOMEvent:
    ...
```

**Rationale**: The `new Event(type, eventInitDict)` constructor pattern is the modern standard. `bubbles` and `cancelable` as keyword-only arguments mirror the `EventInit` dictionary. The legacy `document.createEvent("MouseEvent")` API is not supported because WebComPy has no use for MouseEvent-specific properties (clientX, screenY, etc.) — test events are dispatched programmatically, not derived from actual mouse positions.

### Decision 10: DOMEvent Protocol moves to ports/_dom.py

**Chosen**: Move the `DOMEvent` Protocol from `webcompy/elements/_dom_objs.py` to `webcompy/ports/_dom.py`, alongside `DOMNode` and `DOMPort`. `webcompy/elements/_dom_objs.py` re-exports it for backwards compatibility.

**Rationale**: `DOMEvent`, `DOMNode`, and `DOMPort` form a cohesive domain — they are the three pillars of the abstracted DOM layer. Grouping them in the same module makes the ports layer self-contained: all type contracts that port implementations must satisfy live in `webcompy/ports/_dom.py`. This also enables `VirtualDOMEvent` (in `ports/_server/`) to reference the Protocol without importing from `webcompy/elements/`, avoiding potential circular dependencies.

### Decision 6: VirtualDOMNode implements all DOMNode tree operations

**Chosen**: `VirtualDOMNode` implements all `DOMNode` Protocol tree operations: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, and `remove`. All are straightforward list operations on the internal `_children` list.

**Rationale**: The `DOMNode` Protocol contract requires these methods, and they are trivial to implement as list operations. `insertBefore(new, ref)` finds `ref` in the children list and inserts `new` before it. `replaceChild(new, old)` replaces `old` with `new` at the same position. Completing the Protocol ensures `VirtualDOMNode` is a compliant implementation and avoids `NotImplementedError` surprises if the element system ever calls these methods on server-side nodes.

### Decision 7: cli/_html.py migration — render_html() on ServerDOMPort

**Chosen**: `cli/_html.py`'s `_HtmlElement` is refactored to use `ServerDOMPort.render_html()` instead of calling `self._render_html()`. The `generate_html()` function injects `ServerDOMPort` from the app's DI scope and calls `port.render_html(root_element)` on the constructed virtual tree.

**Rationale**: `_HtmlElement.render_html()` (line 19) currently calls `self._render_html(False, 0)`. After `_render_html()` is removed from base classes, this no longer works. The migration path:

```
Before: _HtmlElement.render_html() → self._render_html(False, 0)
After:  ServerDOMPort.render_html(node) → traverses virtual tree, generates HTML
```

The `generate_html()` function, which has access to the `WebComPyApp` instance, enters the app's DI scope:
```python
with app.di_scope:
    port = inject(DOM_PORT_KEY)
    root = ... # build element tree (now creates VirtualDOMNodes)
    html = port.render_html(root)
```

**Migration ordering**: Remove `_render_html()` from element base classes LAST (after all callers are updated), not first. This is the opposite of Decision 4 in feat-port-abstraction's design — the correct order is:
1. Implement VirtualDOMNode + VirtualDOMEvent + ServerDOMPort.render_html() (groups 1-2)
2. Update cli/_html.py to use ServerDOMPort.render_html() (group 6)
3. THEN remove _render_html() from element classes — subclasses first, base classes last (groups 3, 5)

### Decision 8: RouterLink._on_click() accessible outside browser

**Chosen**: Modify `RouterLink._on_click()` to execute `self._router.__set_path__()` unconditionally. Only `pushState` and `window.location` access remain guarded behind `ENVIRONMENT == "pyscript"`.

**Rationale**: `Router._router.__set_path__()` is pure Python logic (guards → navigate → after_route_change hooks). It works with any `HistoryPort`, including `MockHistoryPort`. The `from pyscript import context` and `context.window.history.pushState()` are browser-only infrastructure. Moving `__set_path__` outside the guard enables `dispatchEvent(VirtualDOMEvent("click"))` on rendered RouterLinks to trigger full route transitions in test contexts. This is the smallest possible change — 1-2 lines — to unlock RouterLink navigation testing without a browser.

## Risks / Trade-offs

- **[HTML output divergence]** ServerDOMPort.render_html() might produce different HTML than the old _render_html() methods. → Mitigation: generate docs_app with both old and new paths, diff the output, fix discrepancies before deleting _render_html().
- **[Virtual tree memory]** Large pages build full in-memory trees before serialization. → Trade-off accepted: SSG renders one page at a time, tree fits in memory. Equivalent to the string concatenation approach.
- **[Protocol compliance]** VirtualDOMNode must match DOMNode Protocol exactly — any mismatch breaks the unified render path. → Mitigation: type checker (`pyright`) validates Protocol conformance at development time.
