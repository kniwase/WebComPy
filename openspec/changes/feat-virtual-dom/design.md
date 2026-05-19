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

### Decision 4: _render_html() removal strategy — implement virtual DOM first, remove old methods last

**Chosen**: Implement `VirtualDOMNode` and `ServerDOMPort.render_html()`, update callers (`cli/_html.py`), then remove `_render_html()` from element base classes last. Ensure the virtual DOM path produces identical HTML output before deletion.

**Rationale**: The `_render_html()` methods encode element-specific HTML formatting rules (void tags, self-closing, text escaping, attribute ordering). These rules must be replicated in `ServerDOMPort.render_html()` before the old methods can be deleted.

**Correct migration ordering:**
1. Implement `VirtualDOMNode` + `ServerDOMPort.render_html()` (groups 1-2)
2. Create `webcompy.testing` module and extract test utilities from `conftest` (group 3)
3. Update `cli/_html.py` to use `ServerDOMPort.render_html()` (group 6)
4. THEN remove `_render_html()` from element classes — subclasses first (`_text.py`, `_dynamic.py`), base classes last (`_base.py`, `_abstract.py`) (groups 4-5)

### Decision 5: VirtualDOMNode.event_listeners is a list of (event_name, handler) tuples

**Chosen**: Store event listeners as `list[tuple[str, Callable]]` on `VirtualDOMNode`. `addEventListener` appends, `removeEventListener` removes by identity.

**Rationale**: On the server, event listeners are never actually invoked — they're recorded for structural testing. A simple list is sufficient. No FFI proxy wrapping is needed (handled by `ServerFFIPort` which returns functions as-is).

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
1. Implement VirtualDOMNode + ServerDOMPort.render_html() (groups 1-2)
2. Create webcompy.testing module (group 3)
3. Update cli/_html.py to use ServerDOMPort.render_html() (group 6)
4. THEN remove _render_html() from element classes (groups 4-5)

### Decision 8: webcompy.testing module — extract test utilities from conftest

**Chosen**: Create a `webcompy.testing` package that houses `FakeDOMNode` and fake port implementations (`FakeBrowserDOMPort`, `FakeBrowserHostPort`, `FakeBrowserFFIPort`), plus convenience helpers (`create_browser_scope()`, `create_server_scope()`, `create_test_app()`). The module SHALL be excluded from browser wheels via `_BROWSER_ONLY_EXCLUDE`.

**Rationale**: `tests/conftest.py` currently contains ~200 lines of reusable fake/mock classes that are also imported directly by 8+ test files (`from conftest import FakeDOMNode`). These utilities are useful for third-party app testing as well. Extracting them to a proper package under `webcompy.testing`:
- Makes them importable by external app test suites
- Provides pre-configured DI scope helpers (`create_browser_scope()`, `create_server_scope()`)
- Centralizes the fake implementations in one discoverable location
- Fixes `FakeBrowserFFIPort` Protocol non-compliance (missing `to_js`/`assign`)

**Exclusion from browser wheels**: Adding `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py` ensures the testing module is never bundled into browser-deployed wheels. The `_is_browser_excluded` function uses prefix matching, so `"webcompy.testing"` matches all submodules.

**Alternative considered**: Keep in `conftest.py`. Rejected because external projects cannot import from test conftest, and the fake classes have outgrown their single-file origin.

### Decision 9: TestRenderer — jsdom-like high-level testing API

**Chosen**: Provide a `TestRenderer` class in `webcompy.testing` that renders components to `VirtualDOMNode` trees and offers query/assertion methods on the result. This is the WebComPy equivalent of jsdom or React Testing Library's `render()`.

```python
from webcompy.testing import TestRenderer

result = TestRenderer.render(MyComponent(props={"name": "World"}))

# Query the virtual DOM tree
h1 = result.query_selector("h1")
assert h1.textContent == "Hello World"
items = result.query_selector_all("li")
assert len(items) == 3

# Convenience finders
node = result.find_by_text("Hello")
node = result.find_by_attribute("id", "main")

# HTML output
html = result.to_html()

# Built-in assertion helpers
result.assert_element_count("li", 3)
result.assert_has_class("container")
```

**Rationale**: After virtual DOM unification, any component can be rendered server-side via `render()` → `VirtualDOMNode`. `TestRenderer` wraps the boilerplate of DI scope setup, renders the component, and provides query/assertion methods. This turns component rendering tests from fragile HTML string comparison into structural assertions on the virtual DOM tree. The `TestRendererResult` query methods (`query_selector`, `query_selector_all`, `find_by_text`, `find_by_attribute`) traverse the `VirtualDOMNode` tree and return matching nodes for further inspection.

**Alternative considered**: Let users call `component.render()` directly via `create_server_scope()`. Rejected because the setup boilerplate (DI scope, ENVIRONMENT patching, app instantiation) is non-trivial and error-prone. A single `TestRenderer.render()` call is the ergonomic entry point.

## Risks / Trade-offs

- **[HTML output divergence]** ServerDOMPort.render_html() might produce different HTML than the old _render_html() methods. → Mitigation: generate docs_app with both old and new paths, diff the output, fix discrepancies before deleting _render_html().
- **[Virtual tree memory]** Large pages build full in-memory trees before serialization. → Trade-off accepted: SSG renders one page at a time, tree fits in memory. Equivalent to the string concatenation approach.
- **[Protocol compliance]** VirtualDOMNode must match DOMNode Protocol exactly — any mismatch breaks the unified render path. → Mitigation: type checker (`pyright`) validates Protocol conformance at development time.
