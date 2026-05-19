# Virtual DOM

## Purpose

WebComPy uses a `DOMNode` Protocol to abstract DOM operations. In the browser, `BrowserDOMNode` wraps a real JavaScript DOM node. On the server, `VirtualDOMNode` builds an in-memory DOM tree that satisfies the same Protocol. This enables a single rendering code path that works identically in both environments — the element system calls `dom_port.create_element()` and operates on the returned `DOMNode` without knowing whether it's real or virtual.

The virtual tree can be serialized to HTML for static site generation and inspected in tests to verify exact DOM structure.

## ADDED Requirements

### Requirement: VirtualDOMNode shall satisfy the DOMNode Protocol

`VirtualDOMNode` SHALL be a concrete class that satisfies the `DOMNode` Protocol. It SHALL store tag name, attributes, children, event listeners, text content, and `__webcompy_node__` marker in Python data structures without any browser API access.

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

### Requirement: VirtualDOMNode tree operations shall match DOM semantics

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

### Requirement: VirtualDOMNode shall store attributes and events

`VirtualDOMNode.setAttribute(name, value)` SHALL store the attribute. `getAttribute(name)` SHALL return the stored value or `None`. `removeAttribute(name)` SHALL remove it. `hasAttribute(name)` SHALL return `True` if stored. `getAttributeNames()` SHALL return all stored attribute names.

`VirtualDOMNode.addEventListener(event, handler)` SHALL record the event-handler pair. `removeEventListener(event, handler)` SHALL remove it by identity. `VirtualDOMNode.dispatchEvent(event: VirtualDOMEvent)` SHALL fire all stored handlers matching `event.type` synchronously.

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

#### Scenario: Dispatching an event on a virtual node
- **WHEN** `node.addEventListener("click", handler)` is called
- **AND** `node.dispatchEvent(VirtualDOMEvent("click"))` is called
- **THEN** `handler` SHALL be invoked with the `VirtualDOMEvent` argument

### Requirement: VirtualDOMEvent shall provide minimal event fields

`VirtualDOMEvent` SHALL be a simple class with `type` (event name string), `target` (the node), `currentTarget` (the node), and `preventDefault` (no-op). It SHALL live in `webcompy/ports/_server/_virtual_dom.py` alongside `VirtualDOMNode`.

#### Scenario: Constructing a VirtualDOMEvent
- **WHEN** `VirtualDOMEvent("click")` is created
- **THEN** `event.type` SHALL be `"click"`
- **AND** `event.preventDefault()` SHALL be a no-op

### Requirement: ServerDOMPort.render_html() shall serialize VirtualDOMNode trees to HTML

`ServerDOMPort.render_html(node: DOMNode) -> str` SHALL traverse a virtual DOM tree and produce a valid HTML string. Attributes SHALL be HTML-escaped. Text content SHALL be HTML-escaped. Void elements (br, hr, img, input, link, meta, etc.) SHALL be self-closing. The output SHALL match the element system's expected HTML structure.

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

### Requirement: VirtualDOMNode shall not require FFI proxy wrapping

Event handlers stored on `VirtualDOMNode` SHALL be plain Python callables without FFI proxy wrapping. `ServerFFIPort.create_proxy(handler)` SHALL return `handler` directly. `ServerFFIPort.destroy_proxy()` SHALL be a no-op.

#### Scenario: Event handler on server-side node uses plain callable
- **WHEN** `node.addEventListener("click", my_handler)` is called on a `VirtualDOMNode`
- **THEN** `my_handler` SHALL be stored as-is without `create_proxy` wrapping
- **AND** the handler SHALL be inspectable in tests
