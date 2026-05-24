## MODIFIED Requirements

### Requirement: FakeBrowserDOMPort SHALL extend ServerDOMPort with an internal document tree

`FakeBrowserDOMPort` SHALL be a subclass of `ServerDOMPort` (from `webcompy.ports._server._dom`). It SHALL override `create_element()` to return `FakeDOMNode` instances instead of `VirtualDOMNode`. It SHALL maintain an internal document tree consisting of `<html>`, `<head>`, and `<body>` `FakeDOMNode` instances. The `query_selector()` and `get_element_by_id()` methods SHALL search this internal tree instead of returning `None`. All other `DOMPort` methods (`create_event`, `create_text_node`, `set_title`, `add_document_event_listener`, `render_html`) SHALL be inherited from `ServerDOMPort` without override.

#### Scenario: FakeBrowserDOMPort creates FakeDOMNode elements
- **WHEN** `FakeBrowserDOMPort().create_element("div")` is called
- **THEN** a `FakeDOMNode` with `nodeName == "DIV"` SHALL be returned
- **AND** the returned node SHALL have `__webcompy_prerendered_node__ == False`

#### Scenario: FakeBrowserDOMPort inherits render_html from ServerDOMPort
- **WHEN** `port.render_html(node)` is called on a `FakeBrowserDOMPort` with a `FakeDOMNode`
- **THEN** the serialized HTML string SHALL be returned (inherited from `ServerDOMPort.render_html`)

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

### Requirement: FakeBrowserDOMPort SHALL maintain idempotent state across multiple method calls

The internal document tree SHALL preserve mutations across method calls within the same `FakeBrowserDOMPort` instance. Appending elements to the tree SHALL be visible to subsequent `query_selector` and `get_element_by_id` calls.

#### Scenario: Multiple queries after appendChild see the result
- **WHEN** `port.query_selector("head").appendChild(el)` is called
- **AND** `el.setAttribute("data-webcompy-cid", "abc")` is called
- **THEN** a subsequent `port.query_selector('style[data-webcompy-cid="abc"]')` SHALL return `el`
