# Virtual DOM

## Purpose

WebComPy uses a `DOMNode` Protocol to abstract DOM operations. In the browser, `BrowserDOMNode` wraps a real JavaScript DOM node. On the server, `VirtualDOMNode` builds an in-memory DOM tree that satisfies the same Protocol. This enables a single rendering code path that works identically in both environments — the element system calls `dom_port.create_element()` and operates on the returned `DOMNode` without knowing whether it's real or virtual.

The virtual tree can be serialized to HTML for static site generation and inspected in tests to verify exact DOM structure. Events can be created via `DOMPort.create_event()` and dispatched on `VirtualDOMNode` to simulate user interactions for component behavior testing.

In the refactored package structure, `VirtualDOMNode`, `VirtualDOMEvent`, and `ServerDOMPort` have moved from `packages/webcompy/src/webcompy/ports/_server/_virtual_dom.py` to `packages/webcompy-server/src/webcompy_server/ports/_virtual_dom.py`. All import paths change from `webcompy.ports._server._virtual_dom` to `webcompy_server.ports`. All behavior stays exactly the same.

## Requirements

### MODIFIED: VirtualDOMNode shall satisfy the DOMNode Protocol

`VirtualDOMNode` SHALL be a concrete class that satisfies the `DOMNode` Protocol. It SHALL store tag name, attributes, children, event listeners, text content, and `__webcompy_node__` marker in Python data structures without any browser API access. The class SHALL be importable from `webcompy_server.ports` (formerly `webcompy.ports._server._virtual_dom`).

#### Scenario: Creating a virtual element node
- **WHEN** `ServerDOMPort.create_element("div")` is called
- **THEN** a `VirtualDOMNode` with `nodeName == "DIV"` SHALL be returned
- **AND** `nodeType == 1` (element node)
- **AND** `__webcompy_node__ == True`

#### Scenario: Creating a virtual text node
- **WHEN** `ServerDOMPort.create_text_node("hello")` is called
- **THEN** a `VirtualDOMNode` with `nodeName == "#text"` SHALL be returned
- **AND** `textContent == "hello"`
- **AND** `nodeType == 3` (text node)

### MODIFIED: VirtualDOMNode tree operations shall match DOM semantics

`VirtualDOMNode.appendChild(child)` SHALL append `child` to the node's children list. `insertBefore(new, ref)` SHALL insert `new` before `ref` in the children list. `replaceChild(new, old)` SHALL replace `old` with `new` at the same position. `removeChild(child)` SHALL remove `child` from the children list by identity. `remove()` SHALL remove the node from its parent's children. `childNodes` SHALL return the list of child nodes.

#### Scenario: Building a virtual tree
- **WHEN** `parent.appendChild(child1)` and `parent.appendChild(child2)` are called on a `VirtualDOMNode`
- **THEN** `parent.childNodes` SHALL contain `[child1, child2]` in order
- **AND** `child1` and `child2` SHALL have their `_parent` reference pointing to `parent`

#### Scenario: Inserting before a reference node
- **WHEN** `parent.insertBefore(child3, child2)` is called
- **THEN** `parent.childNodes` SHALL contain `[child1, child3, child2]` in order

#### Scenario: Replacing a child node
- **WHEN** `parent.replaceChild(new_child, child1)` is called
- **THEN** `new_child` SHALL occupy `child1`'s original position in `parent.childNodes`
- **AND** `parent.childNodes` SHALL no longer contain `child1`

#### Scenario: Removing a child from the virtual tree
- **WHEN** `parent.removeChild(child1)` is called
- **THEN** `parent.childNodes` SHALL no longer contain `child1`

#### Scenario: Removing a node from its parent
- **WHEN** `child.remove()` is called
- **THEN** `child` SHALL be removed from its parent's `childNodes`

### MODIFIED: VirtualDOMNode shall store attributes and events

`VirtualDOMNode.setAttribute(name, value)` SHALL store the attribute. `getAttribute(name)` SHALL return the stored value or `None`. `removeAttribute(name)` SHALL remove it. `hasAttribute(name)` SHALL return `True` if stored. `getAttributeNames()` SHALL return all stored attribute names.

`VirtualDOMNode.addEventListener(event, handler)` SHALL record the event-handler pair. `removeEventListener(event, handler)` SHALL remove it by identity. `VirtualDOMNode.dispatchEvent(event: DOMEvent)` SHALL fire stored handlers and propagate through ancestors per standard DOM event phase semantics.

#### Scenario: Setting and reading attributes on a virtual node
- **WHEN** `node.setAttribute("id", "my-id")` is called
- **THEN** `node.getAttribute("id")` SHALL return `"my-id"`
- **AND** `node.hasAttribute("id")` SHALL return `True`
- **AND** `node.getAttributeNames()` SHALL include `"id"`

#### Scenario: Registering event listeners on a virtual node
- **WHEN** `node.addEventListener("click", handler)` is called
- **THEN** the handler SHALL be recorded
- **WHEN** `node.removeEventListener("click", handler)` is called
- **THEN** the handler SHALL no longer be recorded

### MODIFIED: VirtualDOMEvent shall satisfy the DOMEvent Protocol

`VirtualDOMEvent` SHALL be a concrete class satisfying the `DOMEvent` Protocol defined in `packages/webcompy/src/webcompy/ports/_dom.py`. It SHALL provide `type`, `bubbles`, `cancelable`, `target`, `currentTarget`, `defaultPrevented`, `eventPhase`, `timeStamp`, `preventDefault()`, and `stopPropagation()`. It SHALL live in `packages/webcompy-server/src/webcompy_server/ports/_virtual_dom.py` (formerly `packages/webcompy/src/webcompy/ports/_server/_virtual_dom.py`) alongside `VirtualDOMNode`.

#### Scenario: Constructing a VirtualDOMEvent
- **WHEN** `VirtualDOMEvent("click")` is created
- **THEN** `event.type` SHALL be `"click"`
- **AND** `event.bubbles` SHALL be `False` (default)
- **AND** `event.cancelable` SHALL be `False` (default)
- **AND** `event.defaultPrevented` SHALL be `False`
- **AND** `event.eventPhase` SHALL be `0` (NONE)
- **AND** `event.target` SHALL be `None` (set by `dispatchEvent`)

#### Scenario: Constructing a bubbling cancelable event
- **WHEN** `VirtualDOMEvent("submit", bubbles=True, cancelable=True)` is created
- **THEN** `event.bubbles` SHALL be `True`
- **AND** `event.cancelable` SHALL be `True`

#### Scenario: preventDefault on a cancelable event
- **WHEN** `event = VirtualDOMEvent("click", cancelable=True)` and `event.preventDefault()` is called
- **THEN** `event.defaultPrevented` SHALL be `True`

#### Scenario: preventDefault on a non-cancelable event is ignored
- **WHEN** `event = VirtualDOMEvent("click", cancelable=False)` and `event.preventDefault()` is called
- **THEN** `event.defaultPrevented` SHALL remain `False`

#### Scenario: stopPropagation
- **WHEN** `event.stopPropagation()` is called during `dispatchEvent` handler execution
- **THEN** further ancestor traversal SHALL be stopped

### MODIFIED: VirtualDOMNode.dispatchEvent() shall implement standard event propagation

`VirtualDOMNode.dispatchEvent(event: DOMEvent) -> bool` SHALL execute the at-target phase followed by the bubbling phase (if `event.bubbles` is `True`). During the at-target phase, `event.eventPhase` SHALL be `2` (AT_TARGET) and `event.target` and `event.currentTarget` SHALL both reference the dispatch target. Handlers registered via `addEventListener` with matching `event.type` SHALL be invoked synchronously. During the bubbling phase, `event.eventPhase` SHALL be `3` (BUBBLING) and `event.currentTarget` SHALL reference each ancestor. Propagation SHALL stop if `event.stopPropagation()` is called. The return value SHALL be `False` if `event.defaultPrevented` is `True` after all handlers have run, `True` otherwise. The capturing phase SHALL NOT be implemented (WebComPy event handlers always use `False` for `useCapture`).

#### Scenario: Dispatching a non-bubbling event on the target
- **WHEN** `node.addEventListener("click", handler)` is called
- **AND** `event = VirtualDOMEvent("click", bubbles=False)` is created
- **AND** `node.dispatchEvent(event)` is called
- **THEN** `event.target` SHALL reference `node`
- **AND** `event.currentTarget` SHALL reference `node`
- **AND** `event.eventPhase` SHALL be `2` (AT_TARGET)
- **AND** `handler` SHALL be invoked with `event`
- **AND** no ancestor handlers SHALL be invoked

#### Scenario: Dispatching a bubbling event through ancestors
- **WHEN** `child.appendChild(grandchild)` builds a tree
- **AND** `parent.addEventListener("click", parent_handler)` is registered
- **AND** `child.addEventListener("click", child_handler)` is registered
- **AND** `event = VirtualDOMEvent("click", bubbles=True)` is created
- **AND** `grandchild.dispatchEvent(event)` is called
- **THEN** `grandchild_handler` SHALL be invoked (at-target)
- **AND** `child_handler` SHALL be invoked (bubbling, currentTarget = child)
- **AND** `parent_handler` SHALL be invoked (bubbling, currentTarget = parent)
- **AND** handlers SHALL be invoked in that order

#### Scenario: stopPropagation during bubbling
- **WHEN** `child.addEventListener("click", lambda e: e.stopPropagation())` is registered
- **AND** `grandchild.dispatchEvent(VirtualDOMEvent("click", bubbles=True))` is called
- **THEN** `parent_handler` SHALL NOT be invoked

#### Scenario: dispatchEvent returns bool indicating default prevented
- **WHEN** `event = VirtualDOMEvent("click", cancelable=True)` and a handler calls `event.preventDefault()`
- **AND** `result = node.dispatchEvent(event)` is called
- **THEN** `result` SHALL be `False`
- **WHEN** no handler calls `preventDefault()`
- **AND** `result = node.dispatchEvent(event)` is called
- **THEN** `result` SHALL be `True`

### MODIFIED: ServerDOMPort.render_html() shall serialize VirtualDOMNode trees to HTML

`ServerDOMPort.render_html(node: DOMNode) -> str` SHALL traverse a virtual DOM tree and produce a valid HTML string. Attributes SHALL be HTML-escaped. Text content SHALL be HTML-escaped. Void elements (br, hr, img, input, link, meta, etc.) SHALL be self-closing. The output SHALL match the element system's expected HTML structure. `ServerDOMPort` is importable from `webcompy_server.ports` (formerly `webcompy.ports._server._dom`).

#### Scenario: Serializing a simple element tree
- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree with `div > h1("Hello")`
- **THEN** the output SHALL be `<div><h1>Hello</h1></div>`

#### Scenario: Serializing elements with attributes
- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual `<a href="https://example.com">Click</a>`
- **THEN** the output SHALL include `href="https://example.com"` in the opening tag

#### Scenario: Serializing void elements
- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual `<br>` element
- **THEN** the output SHALL be `<br>` (self-closing, no children)

#### Scenario: HTML-escaping text content
- **WHEN** a text node contains `<script>alert("xss")</script>`
- **THEN** `render_html()` SHALL escape `<`, `>`, `&`, `"` characters
- **AND** the output SHALL NOT contain executable HTML

### MODIFIED: VirtualDOMNode shall not require FFI proxy wrapping

Event handlers stored on `VirtualDOMNode` SHALL be plain Python callables without FFI proxy wrapping. `ServerFFIPort.create_proxy(handler)` SHALL return `handler` directly. `ServerFFIPort.destroy_proxy()` SHALL be a no-op.

#### Scenario: Event handler on server-side node uses plain callable
- **WHEN** `node.addEventListener("click", my_handler)` is called on a `VirtualDOMNode`
- **THEN** `my_handler` SHALL be stored as-is without `create_proxy` wrapping
- **AND** the handler SHALL be inspectable in tests

### ADDED: VirtualDOMNode and VirtualDOMEvent shall be importable from webcompy_server.ports

`VirtualDOMNode`, `VirtualDOMEvent`, and `ServerDOMPort` SHALL be importable directly from `webcompy_server.ports`. The module file lives at `webcompy_server/ports/_virtual_dom.py`.

#### Scenario: Importing VirtualDOMNode from new path
- **WHEN** a developer writes `from webcompy_server.ports import VirtualDOMNode, VirtualDOMEvent`
- **THEN** the import SHALL succeed
- **AND** the objects SHALL be the same as those previously available at `webcompy.ports._server._virtual_dom`

#### Scenario: Importing ServerDOMPort from new path
- **WHEN** a developer writes `from webcompy_server.ports._dom import ServerDOMPort`
- **THEN** the import SHALL succeed