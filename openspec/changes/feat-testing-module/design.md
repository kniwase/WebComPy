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
- `TestRenderer` / `TestRendererResult` — render components, query trees, dispatch events, re-render
- Fix `FakeBrowserFFIPort` Protocol compliance
- Migrate ~55 E2E tests to unit tests using `TestRenderer`
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

**Chosen**: Create `webcompy/testing/` with `__init__.py`, `_dom.py` (FakeDOMNode), `_ports.py` (fake port implementations), and `_renderer.py` (TestRenderer / TestRendererResult). Add `"webcompy.testing"` to `_BROWSER_ONLY_EXCLUDE`.

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

### Decision 7: E2E test migration strategy

**Chosen**: Migrate tests in dependency order, using `TestRenderer` as the verification tool. Keep E2E tests for browser-only behavior.

**Migratable (with TestRenderer)**:

| E2E File | Tests | Mechanism |
|----------|-------|-----------|
| `test_component.py` | 2 | `TestRenderer` + `query_selector` + `textContent` |
| `test_standalone.py` | 4 | Pure file/string checks (no Playwright) |
| `test_bundled_deps.py` | 9 | Pure file/string checks (no Playwright) |
| `test_static_site.py` | 7 | Pure file/string checks (no Playwright) |
| `test_runtime_local.py` | 2 | HTML string verification |
| `test_switch.py` | 3 | `TestRenderer` + `dispatchEvent(VirtualDOMEvent("click"))` |
| `test_reactive.py` | 3 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_repeat.py` | 3 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_keyed_repeat.py` | 4 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_dict_repeat.py` | 4 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_nested_dynamic.py` | 6 | `TestRenderer` + `dispatchEvent` + `rerender` |
| `test_scoped_style.py` | 2 | `TestRenderer` + style node `textContent` inspection |
| `test_di.py` | 4 | `TestRenderer` with DI scope + `dispatchEvent` for RouterLink navigation |
| `test_lifecycle.py` | 2 | `TestRenderer` + `dispatchEvent` |

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
