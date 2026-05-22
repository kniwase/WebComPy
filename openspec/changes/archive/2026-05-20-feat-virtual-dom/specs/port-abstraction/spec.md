# Port Abstraction (delta)

## MODIFIED Requirements

### Requirement: Server port implementations shall provide equivalent behavior

Server port implementations SHALL provide the same method signatures and return types as browser implementations. ServerDOMPort SHALL construct a virtual DOM tree via `VirtualDOMNode` instances instead of raising exceptions. `ServerDOMPort.create_element()` SHALL return a `VirtualDOMNode`. `ServerDOMPort.create_text_node()` SHALL return a virtual text node. `ServerDOMPort.query_selector()` and `get_element_by_id()` SHALL return `None` (SSG does not query existing DOM). `ServerDOMPort.set_title()` SHALL be a no-op. `ServerDOMPort.schedule_macro_task()` SHALL execute the callback synchronously.

ServerDOMPort SHALL additionally provide `render_html(node: DOMNode) -> str` for serializing virtual trees to HTML strings.

#### Scenario: ServerDOMPort creates elements for virtual tree
- **WHEN** `ServerDOMPort.create_element("div")` is called on the server
- **THEN** a `VirtualDOMNode` SHALL be returned instead of raising an exception
- **AND** the node SHALL have `nodeName == "DIV"` and `nodeType == 1`

#### Scenario: ServerDOMPort serializes virtual tree to HTML
- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree
- **THEN** a valid HTML string SHALL be returned
- **AND** void elements SHALL be self-closing and text SHALL be escaped

## ADDED Requirements

### Requirement: DOMPort shall provide an event factory method

`DOMPort.create_event(event_type: str, *, bubbles: bool = False, cancelable: bool = False) -> DOMEvent` SHALL create a DOM event object satisfying the `DOMEvent` Protocol. `BrowserDOMPort.create_event()` SHALL create a native JavaScript `Event` (via `new Event(type, {bubbles, cancelable})` or equivalent). `ServerDOMPort.create_event()` SHALL return a `VirtualDOMEvent` with the given type, bubbles, and cancelable settings.

#### Scenario: BrowserDOMPort creates a native JS event
- **WHEN** `BrowserDOMPort.create_event("click", bubbles=True, cancelable=True)` is called in the browser
- **THEN** a native JS `Event` object SHALL be returned
- **AND** `event.type` SHALL be `"click"`
- **AND** `event.bubbles` SHALL be `True`
- **AND** `event.cancelable` SHALL be `True`

#### Scenario: ServerDOMPort creates a VirtualDOMEvent
- **WHEN** `ServerDOMPort.create_event("change", bubbles=False, cancelable=False)` is called on the server
- **THEN** a `VirtualDOMEvent` with `type == "change"` SHALL be returned
- **AND** `event.bubbles` SHALL be `False`
- **AND** `event.cancelable` SHALL be `False`

### Requirement: DOMNode Protocol shall include dispatchEvent

`DOMNode.dispatchEvent(event: DOMEvent) -> bool` SHALL be added to the `DOMNode` Protocol. In the browser, `BrowserDOMNode.dispatchEvent()` SHALL delegate to the native JS `node.dispatchEvent()`. On the server, `VirtualDOMNode.dispatchEvent()` SHALL execute at-target and bubbling phase handler invocation per standard DOM event semantics.

#### Scenario: dispatchEvent is callable on any DOMNode via Protocol
- **WHEN** code calls `node.dispatchEvent(event)` through the `DOMNode` Protocol
- **THEN** the operation SHALL work on both `BrowserDOMNode` (delegates to native JS) and `VirtualDOMNode` (synchronous Python handler invocation)

### Requirement: DOMEvent Protocol shall live in ports/_dom.py

The `DOMEvent` Protocol SHALL be moved from `webcompy/elements/_dom_objs.py` to `webcompy/ports/_dom.py`. `webcompy/elements/_dom_objs.py` SHALL re-export it for backwards compatibility. The Protocol SHALL define `type`, `bubbles`, `cancelable`, `target`, `currentTarget`, `defaultPrevented`, `eventPhase`, `timeStamp`, `preventDefault()`, and `stopPropagation()`.

#### Scenario: DOMEvent is importable from ports._dom
- **WHEN** `from webcompy.ports._dom import DOMEvent` is executed
- **THEN** the `DOMEvent` Protocol SHALL be available
- **AND** `webcompy.elements._dom_objs.DOMEvent` SHALL re-export the same Protocol
