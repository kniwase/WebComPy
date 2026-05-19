## Why

Currently, server-side rendering uses a parallel code path (`_render_html()`) that generates HTML strings directly, completely separate from the browser's DOM creation path (`_create_node()` / `_mount_node()`). After port abstraction (`feat-port-abstraction`), `ServerDOMPort` merely raises exceptions on DOM operations. This change completes the abstraction by implementing a virtual DOM tree on the server side, unifying both rendering paths through `render()`, and replacing `_render_html()` entirely.

## What Changes

- **NEW** `VirtualDOMNode` class satisfying the `DOMNode` Protocol — an in-memory DOM tree node with attribute storage, child management, and HTML serialization
- **MODIFIED** `ServerDOMPort` — replaces exception-throwing stubs with `VirtualDOMNode` factory methods; `create_element()` returns a `VirtualDOMNode`, `create_text_node()` returns a virtual text node
- **REMOVED** `_render_html()` methods from element types (`_abstract.py`, `_base.py`, `_text.py`, `_dynamic.py`) — replaced by `render()` + `ServerDOMPort`
- **MODIFIED** `render()` path becomes the single unified rendering entry point in both environments
- **MODIFIED** Server-side rendering tests can validate full DOM tree structure (attribute values, child ordering, text content) instead of just HTML string comparison
- **NEW** `ServerDOMPort` provides `render_html(node)` method that serializes the virtual tree to an HTML string

## Capabilities

### New Capabilities

- `virtual-dom`: Server-side virtual DOM tree constructed via `ServerDOMPort.create_element()` / `ServerDOMPort.create_text_node()`, satisfying the `DOMNode` Protocol identically to browser nodes. The tree can be serialized to HTML and inspected in tests for exact DOM structure.

### Modified Capabilities

- `elements`: The dual rendering path (`_render()` for browser DOM, `_render_html()` for server HTML) SHALL be unified into a single `render()` entry point. All element types SHALL remove `_render_html()`. Server-side HTML generation SHALL be handled by `ServerDOMPort.render_html()`. Element system no longer has knowledge of HTML string formatting (indentation, newlines).

- `port-abstraction` (from `feat-port-abstraction` change): `ServerDOMPort` SHALL change from exception-throwing phase-1 stubs to full virtual DOM tree construction. `ServerDOMPort.create_element()` SHALL return a `VirtualDOMNode`. `ServerDOMPort.render_html(node)` SHALL serialize a virtual tree to HTML.

## Known Issues Addressed

- **No virtual DOM diffing** — this change introduces a virtual DOM tree for server-side *construction*, not diffing. Browser-side still uses direct DOM manipulation. The virtual DOM serves as a testable representation, not a diffing algorithm.
- **Event dispatching on VirtualDOMNode** — `dispatchEvent()` fires stored event handlers synchronously. Combined with the unified render path, this enables end-to-end component behavior tests (click → signal update → re-render → query updated virtual tree) without a browser.

## Non-goals

- Browser-side virtual DOM diffing (remains direct DOM manipulation)
- Incremental/patch-based SSR updates (full tree rebuild per render)
- Worker thread rendering (virtual DOM builds in main server thread only)
- Full JS event model emulation (no `preventDefault`, `stopPropagation`, `event.target`/`currentTarget` reference management — VirtualDOMEvent covers essential fields only)

## Impact

- **Affected modules**: `webcompy/ports/_server/_dom.py` (major rewrite), element types with `_render_html()` (`_abstract.py`, `_base.py`, `_text.py`, `_dynamic.py`), `webcompy/cli/_html.py` (caller), existing SSG tests (migrate from string comparison to tree inspection)
- **Breaking**: `_render_html()` is **REMOVED** — any code calling it externally must migrate to `ServerDOMPort.render_html(node)`
- **Dependency**: Requires `feat-port-abstraction` to be completed first (depends on `DOMNode` Protocol and `DOMPort.do` interface)
- **Testing**: Server-side rendering tests gain ability to assert exact DOM tree shape instead of fragile HTML string matching
