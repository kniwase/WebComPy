# Testing Module

## Purpose

WebComPy provides a `webcompy.testing` package with reusable test utilities for component rendering tests. Developers can import `TestRenderer`, `FakeDOMNode`, fake port implementations, and scope helpers to write unit tests that render components to `VirtualDOMNode` trees, query the structure, dispatch events, and assert on the resulting virtual DOM — without a browser or PyScript runtime.

## Requirements

### Requirement: webcompy.testing package shall provide FakeDOMNode

`FakeDOMNode` SHALL extend `VirtualDOMNode` (from `webcompy.ports._server._virtual_dom`). It SHALL inherit all `DOMNode` Protocol methods — tree operations (`appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove`), attribute operations (`setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`), event operations (`addEventListener`, `removeEventListener`, `dispatchEvent(VirtualDOMEvent)`), and properties (`childNodes`, `parentNode`, `nodeName`, `nodeType`, `textContent`, `__webcompy_node__`). It SHALL add: `textContent_write_count` and `setAttribute_count` counter increments on mutation, `__webcompy_prerendered_node__ = False`, and a `__setattr__` guard for attribute proxying.

#### Scenario: Creating a FakeDOMNode for browser-side mock tests
- **WHEN** `FakeDOMNode("div")` is instantiated (inheriting `VirtualDOMNode.__init__`)
- **THEN** a node with `nodeName == "DIV"` and `nodeType == 1` SHALL be returned (inherited from `VirtualDOMNode`)
- **AND** `__webcompy_node__ == True`
- **AND** `__webcompy_prerendered_node__ == False` (set by `FakeDOMNode.__init__`)

#### Scenario: FakeDOMNode inherits tree operations from VirtualDOMNode
- **WHEN** `parent.appendChild(child)` is called on a `FakeDOMNode`
- **THEN** `child.parentNode` SHALL reference `parent` (inherited from `VirtualDOMNode.appendChild`)
- **AND** `parent.childNodes` SHALL contain `child`

#### Scenario: FakeDOMNode inherits dispatchEvent from VirtualDOMNode
- **WHEN** `handler = lambda ev: None` is registered via `node.addEventListener("click", handler)`
- **AND** `node.dispatchEvent(VirtualDOMEvent("click"))` is called
- **THEN** the handler SHALL be invoked with the event (propagation inherited from `VirtualDOMNode.dispatchEvent`)

### Requirement: webcompy.testing package shall provide fake port implementations

`FakeBrowserDOMPort` SHALL be a subclass of `ServerDOMPort` (from `webcompy.ports._server._dom`). It SHALL override `create_element()` to return `FakeDOMNode` instances instead of `VirtualDOMNode`. It SHALL override `create_text_node()` to return a text `FakeDOMNode`. It SHALL maintain an internal document tree consisting of `<html>`, `<head>`, and `<body>` `FakeDOMNode` instances. The `query_selector()` and `get_element_by_id()` methods SHALL search this internal tree instead of returning `None`. It SHALL inherit `create_event()`, `set_title()`, `add_document_event_listener()`, and `render_html()` from `ServerDOMPort`. The internal document tree SHALL preserve mutations across method calls within the same instance — appending elements to the tree SHALL be visible to subsequent `query_selector` and `get_element_by_id` calls. `FakeBrowserHostPort` SHALL implement `HostPort` with `schedule_macro_task()` calling `callback()` synchronously and `create_js_global_getter()` returning a callable that returns `None`. `FakeBrowserFFIPort` SHALL implement `FFIPort` with all 5 abstract methods: `create_proxy` (returns `MagicMock` wrapping the original), `destroy_proxy`, `is_none`, `to_js`, `assign`. `FakeFetchPort` SHALL implement `FetchPort` with `fetch()` that matches registered responses by `(method, url)` key. It SHALL accept an optional `responses` constructor parameter — a `dict` mapping `(method, url)` tuples to `Response` objects. When `fetch(method, url, *, headers, body)` is called, it SHALL look up `(method, url)` in the responses dict and return the matching `Response`. If no match is found, it SHALL raise `KeyError` with a message listing available keys.

#### Scenario: FakeBrowserDOMPort creates FakeDOMNodes
- **WHEN** `FakeBrowserDOMPort().create_element("span")` is called
- **THEN** a `FakeDOMNode` with `nodeName == "SPAN"` SHALL be returned

#### Scenario: FakeBrowserDOMPort.create_event returns a VirtualDOMEvent
- **WHEN** `FakeBrowserDOMPort().create_event("click", bubbles=True, cancelable=False)` is called
- **THEN** a `VirtualDOMEvent` with `type == "click"`, `bubbles == True`, `cancelable == False` SHALL be returned

#### Scenario: FakeBrowserHostPort.create_js_global_getter returns a None-returning callable
- **WHEN** `getter = FakeBrowserHostPort().create_js_global_getter("someName")` is called
- **THEN** `getter()` SHALL return `None`

#### Scenario: FakeBrowserFFIPort satisfies the full FFIPort ABC
- **WHEN** `FakeBrowserFFIPort.to_js({"key": "val"})` is called
- **THEN** the original dict SHALL be returned
- **WHEN** `FakeBrowserFFIPort.assign(target, source)` is called
- **THEN** `target.update(source)` SHALL be executed

#### Scenario: FakeFetchPort returns canned responses by (method, url) key
- **WHEN** `FakeFetchPort(responses={("GET", "/api/users"): Response(...)}).fetch(method="GET", url="/api/users")` is called
- **THEN** the matching `Response` SHALL be returned
- **AND** calling `fetch()` with an unregistered `(method, url)` SHALL raise `KeyError`

#### Scenario: FakeBrowserDOMPort query_selector searches internal document tree
- **WHEN** `FakeBrowserDOMPort().query_selector("head")` is called
- **THEN** the internal `_head` `FakeDOMNode` SHALL be returned (not `None`)

#### Scenario: FakeBrowserDOMPort get_element_by_id searches internal document tree
- **WHEN** a `<style id="webcompy-scoped-styles">` element has been appended to the internal `_head` node
- **THEN** `FakeBrowserDOMPort.get_element_by_id("webcompy-scoped-styles")` SHALL return that `FakeDOMNode`

#### Scenario: query_selector returns None for unmatched selectors
- **WHEN** `FakeBrowserDOMPort().query_selector("footer")` is called
- **AND** no `<footer>` element exists in the internal document tree
- **THEN** `None` SHALL be returned

#### Scenario: Internal document tree supports appendChild
- **WHEN** `head.appendChild(style_el)` is called where `head` is the `FakeBrowserDOMPort().query_selector("head")` result
- **THEN** the style element SHALL be added as a child of `head`
- **AND** subsequent `query_selector("style")` calls SHALL find it

#### Scenario: AppendChild mutations persist across queries
- **WHEN** `port.query_selector("head").appendChild(el)` is called
- **AND** `el.setAttribute("data-webcompy-cid", "abc")` is called
- **THEN** a subsequent `port.query_selector('style[data-webcompy-cid="abc"]')` SHALL return `el`

### Requirement: webcompy.testing package shall provide format_html for canonical HTML comparison

`format_html(html: str) -> str` SHALL normalize HTML strings via `beautifulsoup4` parsing and re-serialization, producing a canonical form for reliable string comparison in tests. It SHALL be used by `TestRendererResult.to_html(pretty=True)`.

#### Scenario: Canonicalizing equivalent HTML with format_html
- **WHEN** two equivalent HTML strings with different whitespace or attribute order are passed to `format_html()`
- **THEN** the outputs SHALL be identical

### Requirement: webcompy.testing package shall provide mock_app_run for importing modules that call app.run() at module level

`mock_app_run()` SHALL return a context manager that temporarily replaces `WebComPyApp.run` with a no-op, enabling `import` of modules that call `app.run()` at module level (like demo applications). On exit, `WebComPyApp.run` SHALL be restored to its original value even if an exception occurs.

#### Scenario: mock_app_run enables import of demo modules
- **WHEN** `with mock_app_run():` is entered
- **THEN** importing a module that calls `WebComPyApp().run()` at module level SHALL succeed without error
- **AND** after exit, `WebComPyApp.run` SHALL be restored to its original method

#### Scenario: mock_app_run survives exceptions
- **WHEN** an exception is raised inside `with mock_app_run():`
- **THEN** `WebComPyApp.run` SHALL still be restored to its original method

### Requirement: webcompy.testing package shall provide scope helpers

`create_test_app(*, root_component, **config_overrides)` SHALL return a minimal `WebComPyApp` instance. Config overrides SHALL be filtered to valid `WebComPyAppConfig` dataclass fields before constructing the config. When a `WebComPyApp` instance exists, callers SHALL create render contexts via `app.create_render_context(path)` — this SHALL be the standard test pattern for SSR and isolation testing. The old `create_browser_scope()` and `create_server_scope()` helpers are removed; port provisioning is handled internally by `RenderContext.__init__` which selects browser or server ports based on `ENVIRONMENT`.

#### Scenario: create_test_app returns a reusable app instance
- **WHEN** `app = create_test_app(root_component=MyRoot, base_url="/custom/")` is called
- **THEN** a `WebComPyApp` with `base_url="/custom/"` SHALL be returned
- **AND** the app SHALL be reusable across multiple `app.create_render_context()` calls

#### Scenario: Config overrides filter to valid dataclass fields
- **WHEN** `create_test_app(root_component=Root, plugins=["pkg:PluginClass"])` is called
- **THEN** the `plugins` field SHALL be passed through to `WebComPyAppConfig`

#### Scenario: RenderContext-based test isolation
- **WHEN** `ctx = app.create_render_context("/page")` is called
- **THEN** a fresh `RenderContext` with isolated `DIScope`, `ComponentStore`, and `Router` SHALL be returned
- **AND** browser or server ports SHALL be provisioned automatically based on `ENVIRONMENT`

### Requirement: render_app_html shall provide a one-call SSR helper

`render_app_html(app, path="/", **kwargs)` SHALL be a convenience function that creates a `RenderContext` via `app.create_render_context(path)`, generates SSR HTML via `generate_html(ctx, **kwargs)`, calls `ctx.dispose()`, and returns the HTML string. The `**kwargs` SHALL be forwarded to `generate_html()` and SHALL include all required generation parameters (`app_package_name`, `dev_mode`, `prerender`, `app_version`, `wheel_filename`, `pyodide_package_names`, etc.). This replaces the repetitive 4-line `create_render_context → generate_html → dispose` pattern used throughout tests.

#### Scenario: One-call SSR HTML generation
- **WHEN** `html = render_app_html(app, path="/about", app_package_name="pkg", dev_mode=False, prerender=True, app_version="0.0.0", wheel_filename="pkg.whl")` is called
- **THEN** the returned string SHALL be the full SSR HTML for the `/about` route
- **AND** the `RenderContext` SHALL have been properly disposed after generation

### Requirement: create_test_asgi_app shall provide a lightweight Starlette ASGI app for httpx-based SSR testing

`create_test_asgi_app(app)` SHALL return a Starlette ASGI app with a catch-all route (`{path:path}` in history mode, `/` in hash mode) that, on each request, calls `app.create_render_context(path)` to create an isolated `RenderContext`, generates SSR HTML via `_HtmlElement("div", {}, ctx._root).render_html()`, calls `ctx.dispose()` in a `finally` block, and returns `HTMLResponse(html_string)`. It SHALL skip all heavy build steps: dependency resolution, wheel building, WASM downloading, runtime asset downloading, and static file serving. It SHALL be usable with `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))` to test the full SSR pipeline — routing, RenderContext, DI scope, `AppDocumentRoot`, and HTML page generation — without a browser.

#### Scenario: Testing full SSR pipeline with httpx
- **WHEN** a user creates a test app via `create_test_app(root_component=PageComponent())`
- **AND** creates an ASGI app via `create_test_asgi_app(app)`
- **AND** sends `httpx.Client(transport=ASGITransport(app=asgi)).get("/page-path")`
- **THEN** the response status SHALL be 200
- **AND** the response body SHALL contain the page component's rendered text

#### Scenario: Each request creates a fresh RenderContext
- **WHEN** a GET request is sent to `/some-page`
- **THEN** `app.create_render_context("/some-page")` SHALL be called, creating an isolated context
- **AND** `ctx.dispose()` SHALL be called in the response `finally` block
- **AND** the Router SHALL match the correct route

#### Scenario: DI scope is active during request
- **WHEN** a component uses `inject(SomeKey)` during rendering
- **AND** the key was registered via `app.provide(SomeKey, value)` before `create_test_asgi_app()`
- **THEN** `inject(SomeKey)` SHALL return the provided value in the rendered HTML

### Requirement: TestRenderer shall render components to VirtualDOMNode trees

`TestRenderer.render(component)` SHALL create a browser-style DI scope with `FakeBrowserDOMPort` (so that `addEventListener` is called on VDOM nodes during rendering), instantiate the component, render it to a `VirtualDOMNode` tree, and return a `TestRendererResult` wrapping the root `VirtualDOMNode`. `TestRendererResult` SHALL provide query methods (`query_selector`, `query_selector_all`, `find_by_text`, `find_by_attribute`), `to_html()`, and assertion helpers (`assert_element_count`, `assert_has_class`). The `dispatchEvent(VirtualDOMEvent)` mechanism SHALL trigger Signal callbacks that directly mutate the VDOM tree (matching browser behavior), eliminating the need for a separate `rerender()` step. The `close()` method SHALL call `scope.dispose()` (clearing all providers and recursively disposing child scopes) and reset the active DI scope.

#### Scenario: Rendering a simple component
- **WHEN** `result = TestRenderer.render(component)` is called
- **THEN** `result.query_selector("h1")` SHALL return a `VirtualDOMNode`
- **AND** the node's `textContent` SHALL match the component's rendered text

#### Scenario: Querying elements by tag
- **WHEN** a component renders three `<li>` elements
- **AND** `items = result.query_selector_all("li")` is called
- **THEN** `len(items)` SHALL be 3

#### Scenario: Finding a node by text content
- **WHEN** a component renders `<span>Hello World</span>`
- **AND** `node = result.find_by_text("Hello World")` is called
- **THEN** `node` SHALL be the `<span>` VirtualDOMNode

#### Scenario: Finding a node by attribute
- **WHEN** a component renders `<div id="main">`
- **AND** `node = result.find_by_attribute("id", "main")` is called
- **THEN** `node` SHALL be the `<div>` VirtualDOMNode

#### Scenario: Dispatching an event triggers VDOM mutation directly
- **WHEN** `button = result.query_selector("button")` returns a node
- **AND** `button.dispatchEvent(VirtualDOMEvent("click"))` is called
- **THEN** `result.query_selector("span")` SHALL reflect the updated signal value immediately (no `rerender()` needed — Signal callbacks mutate VDOM directly)

#### Scenario: Synchronous signal updates are reflected after dispatchEvent
- **WHEN** `result = TestRenderer.render(component)` is called (using browser-style scope with `FakeBrowserDOMPort`)
- **AND** `dispatchEvent(VirtualDOMEvent("click"))` triggers a signal update synchronously
- **THEN** synchronous signal effects SHALL be reflected in the VDOM tree immediately
- **BUT** `on_after_rendering` lifecycle hooks that depend on `schedule_macro_task()` SHALL fire synchronously (because `FakeBrowserHostPort.schedule_macro_task` calls `callback()` immediately)
- **AND** tests requiring macro-task-dependent lifecycle hooks SHALL wire `FakeBrowserHostPort` to achieve synchronous callback execution

#### Scenario: Generating HTML from the virtual tree
- **WHEN** `html = result.to_html()` is called
- **THEN** the string SHALL match `ServerDOMPort.render_html(root)`

#### Scenario: Assertion helpers
- **WHEN** `result.assert_element_count("li", 3)` is called
- **AND** the tree contains exactly 3 `<li>` elements
- **THEN** no AssertionError SHALL be raised
- **WHEN** `result.assert_has_class("container")` is called
- **AND** the root element has `class` containing `"container"`
- **THEN** no AssertionError SHALL be raised

### Requirement: webcompy.testing shall not be bundled into browser wheels

The `"webcompy.testing"` pattern SHALL be added to `_BROWSER_ONLY_EXCLUDE` in `webcompy/cli/_wheel_builder.py`. All submodules under `webcompy.testing` SHALL be excluded from browser-targeted wheels.

#### Scenario: Testing module excluded from browser wheel
- **WHEN** a browser-targeted wheel is built
- **THEN** no files under `webcompy/testing/` SHALL be present in the wheel archive
