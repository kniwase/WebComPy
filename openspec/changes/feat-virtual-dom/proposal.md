## Why

Currently, server-side rendering uses a parallel code path (`_render_html()`) that generates HTML strings directly, completely separate from the browser's DOM creation path (`_create_node()` / `_mount_node()`). After port abstraction (`feat-port-abstraction`), `ServerDOMPort` merely raises exceptions on DOM operations. This change completes the abstraction by implementing a virtual DOM tree on the server side, unifying both rendering paths through `render()`, and replacing `_render_html()` entirely.

## What Changes

- **NEW** `VirtualDOMNode` class satisfying the `DOMNode` Protocol — an in-memory DOM tree node with attribute storage, child management, event dispatch with bubbling propagation, and `dispatchEvent()`
- **NEW** `VirtualDOMEvent` class satisfying the `DOMEvent` Protocol — full event object with `bubbles`, `cancelable`, `preventDefault()`, `stopPropagation()`, and phase tracking
- **MODIFIED** `DOMNode` Protocol — adds `dispatchEvent(event: DOMEvent) -> bool`
- **MODIFIED** `DOMPort` ABC — adds `create_event(event_type, *, bubbles, cancelable) -> DOMEvent`
- **MOVED** `DOMEvent` Protocol from `webcompy/elements/_dom_objs.py` to `webcompy/ports/_dom.py` for co-location with `DOMNode` and `DOMPort`
- **MODIFIED** `ServerDOMPort` — replaces exception-throwing stubs with `VirtualDOMNode` factory methods; `create_element()` returns a `VirtualDOMNode`, `create_text_node()` returns a virtual text node, `create_event()` returns a `VirtualDOMEvent`
- **REMOVED** `_render_html()` methods from element types (`_abstract.py`, `_base.py`, `_text.py`, `_dynamic.py`) — replaced by `render()` + `ServerDOMPort`
- **MODIFIED** `render()` path becomes the single unified rendering entry point in both environments
- **MODIFIED** Server-side rendering tests can validate full DOM tree structure (attribute values, child ordering, text content) instead of just HTML string comparison
- **NEW** `ServerDOMPort` provides `render_html(node)` method that serializes the virtual tree to an HTML string
- **MODIFIED** `RouterLink._on_click()` — executes `__set_path__()` unconditionally; only browser-specific `pushState` remains guarded behind `ENVIRONMENT == "pyscript"`

## Capabilities

### New Capabilities

- `virtual-dom`: Server-side virtual DOM tree constructed via `ServerDOMPort.create_element()` / `ServerDOMPort.create_text_node()`, satisfying the `DOMNode` Protocol identically to browser nodes. The tree can be serialized to HTML and inspected in tests for exact DOM structure.
- `virtual-events`: `DOMPort.create_event()` creates environment-appropriate `DOMEvent` objects. `VirtualDOMNode.dispatchEvent()` implements at-target + bubbling phase propagation with `preventDefault()` and `stopPropagation()` support. Combined with the unified render path and synchronous signal propagation, this enables end-to-end component interaction tests (click → dispatch → signal update → re-render) without a browser.

### Modified Capabilities

- `elements`: The dual rendering path (`_render()` for browser DOM, `_render_html()` for server HTML) SHALL be unified into a single `render()` entry point. All element types SHALL remove `_render_html()`. Server-side HTML generation SHALL be handled by `ServerDOMPort.render_html()`. Element system no longer has knowledge of HTML string formatting (indentation, newlines).

- `port-abstraction` (from `feat-port-abstraction` change): `ServerDOMPort` SHALL change from exception-throwing phase-1 stubs to full virtual DOM tree construction. `ServerDOMPort.create_element()` SHALL return a `VirtualDOMNode`. `ServerDOMPort.create_event()` SHALL return a `VirtualDOMEvent`. `ServerDOMPort.render_html(node)` SHALL serialize a virtual tree to HTML. `DOMNode` Protocol SHALL include `dispatchEvent()`. `DOMPort` ABC SHALL include `create_event()`.

- `router`: `RouterLink._on_click()` SHALL call `Router.__set_path__()` in both environments, enabling RouterLink click → route transition testing via `dispatchEvent(VirtualDOMEvent("click"))`. Only `pushState` and `window.location` access remain browser-guarded.

## Known Issues Addressed

- **No virtual DOM diffing** — this change introduces a virtual DOM tree for server-side *construction*, not diffing. Browser-side still uses direct DOM manipulation. The virtual DOM serves as a testable representation, not a diffing algorithm.
- **Event dispatching on VirtualDOMNode** — `dispatchEvent()` implements standard DOM event propagation (at-target + bubbling). Combined with the unified render path, this enables end-to-end component interaction tests without a browser.
- **DOMEvent Protocol isolation** — `DOMEvent` Protocol moves to `webcompy/ports/_dom.py`, co-located with `DOMNode` and `DOMPort`, making the ports layer self-contained.

## Non-goals

- Browser-side virtual DOM diffing (remains direct DOM manipulation)
- Incremental/patch-based SSR updates (full tree rebuild per render)
- Worker thread rendering (virtual DOM builds in main server thread only)
- Capturing phase in `dispatchEvent()` (WebComPy always uses `useCapture=False`)
- Legacy `document.createEvent("MouseEvent")`-style event creation (constructor-style only)

## Impact

- **Affected modules**: `webcompy/ports/_dom.py` (DOMEvent move + Protocol additions), `webcompy/ports/_server/_dom.py` (major rewrite + create_event), `webcompy/ports/_server/_virtual_dom.py` (new: VirtualDOMNode + VirtualDOMEvent), `webcompy/ports/_browser/_dom.py` (add create_event), `webcompy/router/_link.py` (guard change), element types with `_render_html()` (`_abstract.py`, `_base.py`, `_text.py`, `_dynamic.py`), `webcompy/cli/_html.py` (caller), existing SSG tests (migrate from string comparison to tree inspection)
- **Breaking**: `_render_html()` is **REMOVED** — any code calling it externally must migrate to `ServerDOMPort.render_html(node)`. `DOMEvent` Protocol moves from `webcompy.elements._dom_objs.DOMEvent` to `webcompy.ports._dom.DOMEvent` (backwards-compatible re-export maintained)
- **Dependency**: Requires `feat-port-abstraction` to be completed first (depends on `DOMNode` Protocol and `DOMPort` ABC)
- **Testing**: Server-side rendering tests gain ability to assert exact DOM tree shape and simulate user interactions via event dispatch — no browser required
