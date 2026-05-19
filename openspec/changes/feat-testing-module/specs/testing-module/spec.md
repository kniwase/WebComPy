# Testing Module

## Purpose

WebComPy provides a `webcompy.testing` package with reusable test utilities for component rendering tests. Developers can import `TestRenderer`, `FakeDOMNode`, fake port implementations, and scope helpers to write unit tests that render components to `VirtualDOMNode` trees, query the structure, dispatch events, and assert on the resulting virtual DOM — without a browser or PyScript runtime.

## ADDED Requirements

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

`FakeBrowserDOMPort` SHALL implement `DOMPort` with `create_element()` returning a `FakeDOMNode` and `create_text_node()` returning a text `FakeDOMNode`. `FakeBrowserHostPort` SHALL implement `HostPort` with `schedule_macro_task()` as a no-op. `FakeBrowserFFIPort` SHALL implement all 5 abstract methods of `FFIPort`: `create_proxy`, `destroy_proxy`, `is_none`, `to_js`, `assign`.

#### Scenario: FakeBrowserDOMPort creates FakeDOMNodes
- **WHEN** `FakeBrowserDOMPort().create_element("span")` is called
- **THEN** a `FakeDOMNode` with `nodeName == "SPAN"` SHALL be returned

#### Scenario: FakeBrowserFFIPort satisfies the full FFIPort ABC
- **WHEN** `FakeBrowserFFIPort.to_js({"key": "val"})` is called
- **THEN** the original dict SHALL be returned
- **WHEN** `FakeBrowserFFIPort.assign(target, source)` is called
- **THEN** `target.update(source)` SHALL be executed and `target` returned

### Requirement: webcompy.testing package shall provide scope helpers

`create_browser_scope()` SHALL return a `DIScope` with `FakeBrowserDOMPort`, `FakeBrowserHostPort`, and `FakeBrowserFFIPort` wired to their standard injection keys. `create_server_scope()` SHALL return a `DIScope` with `ServerDOMPort`, `ServerHostPort`, and `ServerFFIPort` wired to their standard injection keys. `create_test_app(scope, **config_overrides)` SHALL return a minimal `WebComPyApp` instance with the given DI scope set directly on `app._active_scope` — this is an intentional test-only escape hatch, not a public API contract, and SHALL NOT be used in production code.

#### Scenario: create_browser_scope returns a ready-to-use DIScope
- **WHEN** `scope = create_browser_scope()` is called
- **THEN** `scope.inject(DOM_PORT_KEY)` SHALL return a `FakeBrowserDOMPort`
- **AND** `scope.inject(FFI_PORT_KEY)` SHALL return a `FakeBrowserFFIPort`
- **AND** `scope.inject(HOST_PORT_KEY)` SHALL return a `FakeBrowserHostPort`

#### Scenario: create_server_scope returns a ready-to-use DIScope
- **WHEN** `scope = create_server_scope()` is called
- **THEN** `scope.inject(DOM_PORT_KEY)` SHALL return a `ServerDOMPort`
- **AND** `scope.inject(FFI_PORT_KEY)` SHALL return a `ServerFFIPort`

### Requirement: TestRenderer shall render components to VirtualDOMNode trees

`TestRenderer.render(component)` SHALL set the runtime environment to non-PyScript during rendering to ensure the element system uses server-side code paths (i.e., `_create_node()` calls `ServerDOMPort.create_element()` rather than `BrowserDOMPort.create_element()`). It SHALL create a server-side DI scope, instantiate a minimal `WebComPyApp`, render the component via `component.render()`, and return a `TestRendererResult` wrapping the root `VirtualDOMNode`. `TestRendererResult` SHALL provide query methods (`query_selector`, `query_selector_all`, `find_by_text`, `find_by_attribute`), `to_html()`, `rerender()`, and assertion helpers (`assert_element_count`, `assert_has_class`).

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

#### Scenario: Dispatching an event and re-rendering
- **WHEN** `button = result.query_selector("button")` returns a node
- **AND** `button.dispatchEvent(VirtualDOMEvent("click"))` is called
- **AND** `result.rerender()` is called
- **THEN** `result.query_selector("span")` SHALL reflect the updated signal value

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
