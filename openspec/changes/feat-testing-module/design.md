# Design: Testing Module

## Context

After `feat-virtual-dom` completes:

- `VirtualDOMNode` satisfies the `DOMNode` Protocol with tree ops, attribute storage, event listener recording, and `dispatchEvent(VirtualDOMEvent)`.
- `ServerDOMPort` creates `VirtualDOMNode` trees and provides `render_html()` for serialization.
- Element types use a single unified `render()` path across browser and server.
- `RouterLink._on_click()` calls `self._router.__set_path__()` unconditionally (only `pushState` is guarded behind `ENVIRONMENT == "pyscript"`).

This enables a testing module that renders components to `VirtualDOMNode` trees and exercises the full reactive + routing pipeline without a browser.

## Goals / Non-Goals

**Goals:**
- `webcompy.testing` package with `FakeDOMNode`, fake port implementations, and scope helpers
- `create_test_asgi_app()` — lightweight Starlette ASGI app for httpx-based SSR testing of the full HTTP→HTML pipeline
- `TestRenderer` / `TestRendererResult` — render components, query trees, dispatch events, re-render
- Fix `FakeBrowserFFIPort` Protocol compliance
- Migrate E2E tests using a three-tier strategy: httpx ASGI (static renders), TestRenderer (interactive), Playwright (browser-only behavior)
- Exclude `webcompy.testing` from browser wheels
- Backwards-compatible re-exports from `tests/conftest.py`

**Non-Goals:**
- CSS cascade / layout computation
- Real browser `<input>` widget state emulation
- `window.history.pushState` / `popstate` emulation
- Console error capture

## Dependency

**Requires `feat-virtual-dom`** for: `VirtualDOMNode`, `VirtualDOMEvent`, `ServerDOMPort`, unified `render()`, and RouterLink `_on_click` fix. This change cannot be implemented first — it depends on the virtual DOM infrastructure.

## Decisions

### Decision 1: webcompy.testing as a separate package, excluded from browser wheels

**Chosen**: Create `webcompy/testing/` with `__init__.py`, `_dom.py` (FakeDOMNode), `_ports.py` (fake port implementations), `_renderer.py` (TestRenderer / TestRendererResult), and `_asgi.py` (create_test_asgi_app, format_html). Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE`.

**Rationale**: Same approach as `webcompy.cli` and `webcompy.ports._server` — these are server/dev-only code. The `_is_browser_excluded` function uses prefix matching, so `"webcompy.testing"` matches all submodules. This prevents test utilities from being bundled into browser-deployed wheels.

### Decision 2: FakeDOMNode inherits from VirtualDOMNode

**Chosen**: `FakeDOMNode` extends `VirtualDOMNode` and overrides only test-specific behavior: `setAttribute`/`textContent` increment counters, `__setattr__` guard, `__webcompy_prerendered_node__ = False`. All tree operations, attribute storage, event listener management, and `dispatchEvent(VirtualDOMEvent)` are inherited from `VirtualDOMNode`.

```python
from webcompy.ports._server._virtual_dom import VirtualDOMNode

class FakeDOMNode(VirtualDOMNode):
    def __init__(self, tag: str = "div", text_content: str | None = None):
        super().__init__(tag, text_content)
        self.__webcompy_prerendered_node__ = False
        self.textContent_write_count = 0
        self.setAttribute_count = 0

    @VirtualDOMNode.textContent.setter  # type: ignore[attr-defined]
    def textContent(self, value):
        self._text_content = value
        self.textContent_write_count += 1

    def setAttribute(self, name, value):
        super().setAttribute(name, value)
        self.setAttribute_count += 1

    def __setattr__(self, name, value):
        if name.startswith("_VirtualDOMNode__") or name in (
            "__webcompy_node__",
            "__webcompy_prerendered_node__",
        ):
            object.__setattr__(self, name, value)
        else:
            try:
                object.__getattribute__(self, name)
                object.__setattr__(self, name, value)
            except AttributeError:
                object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name.startswith("_VirtualDOMNode__"):
            raise AttributeError(name)
        return object.__getattribute__(self, name)
```

**Rationale**: `VirtualDOMNode` already implements the full `DOMNode` Protocol — all tree operations, attribute storage, event listener management, and `dispatchEvent(VirtualDOMEvent)` with bubbling propagation. Writing these again in `FakeDOMNode` would be ~80% code duplication. Inheritance eliminates duplication and ensures `dispatchEvent` semantics remain identical. The dependency direction is safe: `webcompy.testing` → `webcompy.ports._server` — both are excluded from browser wheels. The `__setattr__` guard references `_VirtualDOMNode__` (name-mangled superclass internal name) since Python name mangling is based on the class where the attribute is defined.


### Decision 3: FakeBrowserFFIPort Protocol compliance fix

**Chosen**: Add `to_js` and `assign` methods to `FakeBrowserFFIPort` that match the `FFIPort` ABC.

```python
class FakeBrowserFFIPort:
    def to_js(self, value: Any, **kwargs: Any) -> Any:
        return value
    def assign(self, target: Any, *sources: Any) -> Any:
        for source in sources:
            target.update(source)
        return target
```

**Rationale**: The `FFIPort` ABC defines 5 abstract methods: `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`. The current fake only implements 3 of them. This gap was harmless because no test calls `to_js`/`assign` directly, but as a proper testing module, Protocol compliance matters.

### Decision 4: Scope helpers — create_browser_scope() and create_server_scope()

**Chosen**: Two convenience functions that return pre-wired `DIScope` instances.

```python
def create_browser_scope() -> DIScope:
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    return scope

def create_server_scope() -> DIScope:
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, ServerDOMPort())
    scope.provide(HOST_PORT_KEY, ServerHostPort())
    scope.provide(FFI_PORT_KEY, ServerFFIPort())
    return scope
```

**Rationale**: The `fake_browser_full` fixture in `tests/conftest.py` is 30 lines of setup — monkeypatching `ENVIRONMENT`, creating a `DIScope`, providing ports, setting the active scope. This boilerplate should be a one-liner for app developers writing tests.

### Decision 5: create_test_app() — minimal WebComPyApp factory

**Chosen**: `create_test_app(scope: DIScope, root_component=None, **config_overrides)` instantiates a minimal `WebComPyApp` with the given scope. Returns the app instance with the scope active.

```python
def create_test_app(scope, root_component=None, **kwargs):
    config = AppConfig(**kwargs)
    app = WebComPyApp(config=config)
    if root_component is not None:
        app.set_root(root_component)
    app._active_scope = scope  # so app.di_scope uses this scope
    return app
```

**Rationale**: Many component tests need access to signals, DI values, or the app's `provide()` method. `TestRenderer.render()` handles the simple case; `create_test_app()` handles the advanced case where the test needs to manipulate signals or DI before rendering.

**Implementation note on ContextVar**: Setting `_active_scope` directly bypasses the normal `DIScope.__enter__`/`__exit__` context manager that sets `_active_di_scope` (a `ContextVar`). The implementation MUST also set `_active_di_scope.set(scope)` and provide a cleanup callback (returned from `create_test_app()`) to reset it, OR use `app.di_scope` as a context manager internally. Otherwise, `inject()` calls from within component setup (which checks `_active_di_scope` before falling back to `_app_di_scope`) may fail to resolve dependencies.

### Decision 6: TestRenderer and TestRendererResult

**Chosen**: `TestRenderer` renders a component to a `VirtualDOMNode` tree. `TestRendererResult` wraps the root node and provides query/assertion/event/re-render methods.

```python
from webcompy.testing import TestRenderer

# Basic rendering
result = TestRenderer.render(MyComponent(props={"name": "World"}))

# Query virtual DOM tree
h1 = result.query_selector("h1")
items = result.query_selector_all("li")
node = result.find_by_text("Hello")
node = result.find_by_attribute("id", "main")

# Event dispatch + re-render
button = result.query_selector("button")
button.dispatchEvent(VirtualDOMEvent("click"))
result.rerender()
assert result.find_by_text("Clicked: 1")

# HTML output
html = result.to_html()

# Assertion helpers
result.assert_element_count("li", 3)
result.assert_has_class("container")
```

`TestRenderer.render()`:
1. Creates a `create_server_scope()`
2. Creates a `WebComPyApp` with default config
3. Monkeypatches `ENVIRONMENT` to non-pyscript on element modules
4. Renders the component via `component.render()`
5. Returns `TestRendererResult(app, root_node, scope)`

`TestRendererResult`:
- `query_selector(tag: str) -> VirtualDOMNode | None` — DFS for first element matching `tag`
- `query_selector_all(tag: str) -> list[VirtualDOMNode]` — DFS for all elements matching `tag`
- `find_by_text(text: str) -> VirtualDOMNode | None` — DFS for node with matching `textContent`
- `find_by_attribute(name: str, value: str) -> VirtualDOMNode | None` — DFS for node with matching attribute
- `to_html() -> str` — delegates to `ServerDOMPort.render_html(root)`
- `rerender()` — re-executes `component.render()` on the virtual tree
- `assert_element_count(tag: str, count: int)` — `assert len(query_selector_all(tag)) == count`
- `assert_has_class(cls: str)` — `assert "class" in root.getAttributeNames()` and the class is present

**Rationale**: This is the jsdom-like API for WebComPy. After `feat-virtual-dom`, any component can be rendered to a `VirtualDOMNode` tree. `TestRenderer` wraps the boilerplate and provides ergonomic query/assertion methods. The `rerender()` method is essential for testing reactive behavior after `dispatchEvent(VirtualDOMEvent)` — it re-drives component `render()` so the queryable tree reflects post-signal-update state.

### Decision 7: httpx ASGI integration — testing the full SSR pipeline

**Chosen**: Add `create_test_asgi_app()` to `webcompy.testing`. This builds a minimal Starlette ASGI app from a given `WebComPyApp` instance, skipping dependency resolution, wheel building, and runtime asset downloading. Users can then test the full ASGI request→SSR→HTML pipeline using `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`.

```python
from httpx import ASGITransport, Client
from webcompy.testing import create_test_app, create_server_scope, create_test_asgi_app

scope = create_server_scope()
app = create_test_app(scope, root_component=MyPage())
asgi = create_test_asgi_app(app)

client = Client(transport=ASGITransport(app=asgi), base_url="http://test")
response = client.get("/mypage")
assert "Hello World" in response.text
assert response.status_code == 200
```

`create_test_asgi_app(app)`:
1. Creates a Starlette app with one catch-all route (`{path:path}`) in history mode (or root route in hash mode)
2. Each request enters `app.di_scope`, calls `app.set_path(requested_path)`, and returns `HTMLResponse(html_string)` where `html_string` is the SSR output via `_HtmlElement.render_html()`
3. Uses `ServerDOMPort`, `ServerHostPort`, `ServerFFIPort` (already provisioned by `create_server_scope()`)

**Rationale**: `TestRenderer.render()` renders a single component to a `VirtualDOMNode` tree, but bypasses the full ASGI pipeline — routing, `app.set_path()`, `AppDocumentRoot` wrapper, `app.di_scope` context manager, and HTML page generation (`generate_html()`). `httpx` + `ASGITransport` exercises this entire pipeline without a browser. This is already a project dependency (used by `ServerFetchPort`). The approach mirrors Django's `Client` / Starlette's `TestClient` pattern.

**Advantages**:
- Full routing + SSR pipeline coverage that `TestRenderer` cannot provide
- Millisecond-level test execution vs 1-2 second Playwright startup
- No added dependencies (`httpx` is already a project dependency)

**Limitations**:
- Stateless — cannot test reactive state changes triggered by click events (use `TestRenderer` for that)
- No PyScript hydration or browser JS runtime (use Playwright E2E for that)

### Decision 9: HTML formatter for test comparison reliability

**Chosen**: Provide `format_html(html: str) -> str` in `webcompy.testing._asgi` that normalizes HTML strings via `beautifulsoup4` parsing and re-serialization, producing a canonical form suitable for string comparison in tests. `TestRendererResult.to_html(pretty: bool = False)` uses this when `pretty=True`. `beautifulsoup4` IS added to the `dev` dependency group — it IS a test utility, not a runtime dependency, so it does not go in core `dependencies`.

```python
from webcompy.testing import format_html

def test_my_component():
    result = TestRenderer.render(MyComponent())
    html = format_html(result.to_html())
    expected = format_html("<div><h1>Hello</h1></div>")
    assert html == expected
```

**Rationale**: SSR output (`render_html()`) is naturally compact — no whitespace between tags. This makes direct string comparison fragile: a single extra space or attribute reordering causes false failures. `beautifulsoup4` parses both actual and expected HTML into a canonical tree and re-serializes them identically, guaranteeing reliable comparison. The library is pure Python, well-maintained, and handles edge cases (void elements, raw content elements like `<script>`/`<style>`, self-closing tags) correctly.

**Why not use `prettify()`?** `prettify()` adds newlines and indentation, which changes inline element layout. Using `str(soup)` or `soup.decode()` preserves semantic equivalence without introducing whitespace artifacts.

**Why not format SSR output by default?** The current `_serialize_node()` output is already compact (no extra whitespace). Introducing `beautifulsoup4` into the production code path would be a runtime dependency with no benefit to end users — browsers render compact HTML correctly, and developer inspection happens via devtools' Elements panel.

**Test verification strategy**: Unit tests for the testing module itself MUST verify both:
- `TestRendererResult.to_html()` (raw, no formatting) — confirms the serialization pipeline is correct
- `format_html(result.to_html()) == format_html(expected)` — confirms canonical comparison works

Existing `webcompy.ports._server._dom` tests for `_serialize_node()` remain unchanged and validate raw output correctness.

### Decision 10: Three-tier test migration strategy

**Chosen**: Replace the previous two-tier strategy (TestRenderer + Playwright) with a three-tier approach using httpx ASGI integration as the first tier for static renders.

```
┌──────────────────────────────────────────────────────┐
│                   Testing Pyramid                    │
│                                                      │
│      ┌─────────────┐    ブラウザ必須の挙動           │
│      │   E2E       │    getComputedStyle, input      │
│      │ (Playwright)│    widget state, navigation      │
│      └──────┬──────┘    lifecycle, console errors    │
│             │                                        │
│      ┌──────▼──────┐    完全な ASGI パイプライン     │
│      │  httpx ASGI │    ルーティング + SSR + HTML     │
│      │ integration │    app.di_scope + set_path      │
│      └──────┬──────┘                                 │
│             │                                        │
│      ┌──────▼──────┐    コンポーネント直接レンダリング │
│      │ TestRenderer│    VirtualDOM ツリー操作        │
│      │  (unit)     │    dispatchEvent + rerender     │
│      └─────────────┘                                 │
└──────────────────────────────────────────────────────┘
```

| Tier | Tool | Scope | Tests |
|------|------|-------|-------|
| Tier 1 (httpx) | `httpx` + `create_test_asgi_app()` | Full SSR pipeline: routing, DI scope, HTML generation, static renders | ~8 tests (initial state / no interaction) |
| Tier 2 (TestRenderer) | `TestRenderer.render()` + `dispatchEvent` + `rerender` | Single-component render + reactive state change via virtual events | ~19 tests (click-driven reactive updates) |
| Tier 3 (Playwright) | E2E (unchanged) | Browser-only behavior | ~8 tests (getComputedStyle, input widget state, navigation lifecycle, console errors) |

**Tier 1 — httpx ASGI (static initial renders)**:

| E2E File | Tests | Mechanism |
|----------|-------|-----------|
| `test_component.py` | 2 | httpx GET → assert HTML contains expected text |
| `test_switch.py` | 1 (`default_state`) | httpx GET → assert HTML contains "on" branch, excludes "off" branch |
| `test_repeat.py` | 1 (`initial_empty`) | httpx GET → assert HTML has zero `<li>` elements |
| `test_keyed_repeat.py` | 1 (`initial_empty`) | httpx GET → assert HTML has zero `<li>` elements |
| `test_dict_repeat.py` | 1 (`initial_empty`) | httpx GET → assert HTML has zero `<li>` elements |
| `test_nested_dynamic.py` | 1 (`initial_list_view`) | httpx GET → assert HTML has 3 list items, 0 grid items |
| `test_di.py` | 1 (`inject_from_app_level`) | httpx GET → assert HTML contains injected value text |

**Tier 2 — TestRenderer (interactive)**:

| E2E File | Tests | Mechanism |
|----------|-------|-----------|
| `test_switch.py` | 2 (`toggle`, `toggle_back`) | `TestRenderer` + `dispatchEvent(VirtualDOMEvent("click"))` |
| `test_reactive.py` | 3 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_repeat.py` | 2 (`add_items`, `remove_items`) | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_keyed_repeat.py` | 3 (`add_items`, `remove_first`, `insert_at_start`) | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_dict_repeat.py` | 3 (`add_items`, `remove_first`, `clear`) | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_nested_dynamic.py` | 5 (`switch_to_grid`, `switch_back`, `add_item`, `add_then_switch`, `remove_first`) | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_scoped_style.py` | 2 | `TestRenderer` + style node `textContent` inspection |
| `test_di.py` | 1 (`provide_inject_from_parent`) | `TestRenderer` with DI scope |
| `test_lifecycle.py` | 1 (`hooks_fire`) | `TestRenderer` |

**Tier 3 — Playwright E2E (browser-required)**:

| Reason | Tests | Files |
|--------|-------|-------|
| `getComputedStyle()` | 5 | `test_scoped_style.py` |
| Browser `<input>` widget state | 2 | `test_keyed_repeat.py`, `test_dict_repeat.py` |
| RouterView lifecycle on navigation | 1 | `test_lifecycle.py` |
| `assert_no_console_errors` | 3 | `test_di.py`, `test_bootstrap.py` |
| All `tests/e2e_docs/` | ~27 | docs E2E (iframe + PyScript) |

**Browser-required (remain in E2E)**:

| Reason | Tests | Files |
|--------|-------|-------|
| `getComputedStyle()` | 5 | `test_scoped_style.py` |
| Browser `<input>` widget state | 2 | `test_keyed_repeat.py`, `test_dict_repeat.py` |
| RouterView lifecycle on navigation | 1 | `test_lifecycle.py` |
| `assert_no_console_errors` | 3 | `test_di.py`, `test_bootstrap.py` |
| All `tests/e2e_docs/` | ~27 | docs E2E (iframe + PyScript) |

## Risks / Trade-offs

- **[TestRenderer environment setup]** Monkeypatching `ENVIRONMENT` on element modules must match the pattern used by `fake_browser_full` fixture. If the patching is skipped, `_init_node()` methods will still have `ENVIRONMENT == "pyscript"` branches that raise exceptions. → Mitigation: `TestRenderer.render()` includes the same monkeypatch logic.
- **[FakeDOMNode inherits VirtualDOMNode]** `FakeDOMNode` extends `VirtualDOMNode`, adding only test-specific attributes (counters, `__setattr__` guard, `__webcompy_prerendered_node__`). Any `VirtualDOMNode` API change will automatically propagate to `FakeDOMNode`. → Trade-off accepted: `webcompy.testing` depends on `webcompy.ports._server` — both are excluded from browser wheels, so this is safe.
- **[E2E coverage gap]** Migrating tests from browser to unit loses coverage of PyScript integration bugs. → Mitigation: remaining E2E tests cover the PyScript lifecycle indirectly. The migrated tests cover logic that was never PyScript-dependent.
