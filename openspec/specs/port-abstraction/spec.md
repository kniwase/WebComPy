# Port Abstraction

## Purpose

Port ABCs provide a typed, injectable abstraction layer for browser and server runtime operations (DOM manipulation, window operations, FFI bridging, HTTP fetching, cookie management, and history navigation). They replace direct access to the monolithic `browser` object, enabling testable, swappable implementations via dependency injection. Ports are organized around distinct browser API surfaces: `DOMPort` for document-level operations, `HostPort` for general window-level operations, and dedicated ports for specific sub-APIs (`CookiePort`, `HistoryPort`, `FetchPort`) or non-web-platform concerns (`FFIPort`).

## Requirements

### Requirement: Port ABC definitions exist
The system SHALL provide abstract base classes for DOM, host (window), FFI, fetch, cookie, and history operations in the `webcompy.ports` package. Each ABC SHALL declare abstract methods for its specific concern. `HistoryPort` SHALL extend `SignalBase[str]` to enable reactive path state.

#### Scenario: All ABCs are importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** all 6 port ABCs (DOMPort, HostPort, FFIPort, FetchPort, CookiePort, HistoryPort) and DOMNode are accessible

#### Scenario: ABCs cannot be instantiated directly
- **WHEN** a developer attempts to instantiate any port ABC directly
- **THEN** Python raises TypeError due to abstract methods

### Requirement: Browser port implementations exist
The system SHALL provide browser implementations for all 6 ports using `pyscript.context` and `pyscript.ffi`. These SHALL be located in `webcompy.ports._browser`.

#### Scenario: BrowserDOMPort creates real DOM elements
- **WHEN** `BrowserDOMPort.create_element("div")` is called in a PyScript environment
- **THEN** a raw browser `HTMLDivElement` is returned
- **AND** `BrowserDOMPort.create_text_node("hello")` SHALL return a raw browser `Text` node
- **AND** both SHALL satisfy the `DOMNode` Protocol structurally (no nominal inheritance required)

#### Scenario: BrowserFFIPort uses pyscript.ffi
- **WHEN** `BrowserFFIPort.create_proxy(some_func)` is called
- **THEN** `pyscript.ffi.create_proxy(some_func)` is invoked

#### Scenario: BrowserHistoryPort reads from window.location
- **WHEN** a `BrowserHistoryPort` is constructed in a PyScript environment with mode="history"
- **THEN** its `value` property returns the current `window.location.pathname`

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

#### Scenario: ServerFetchPort uses httpx
- **WHEN** `ServerFetchPort.fetch("https://example.com/api")` is called
- **THEN** an httpx request is sent and a `Response` object is returned

#### Scenario: ServerHistoryPort stores path internally
- **WHEN** `ServerHistoryPort.navigate("/test")` is called
- **THEN** the port's `value` property returns "/test"

#### Scenario: ServerCookiePort ignores Set-Cookie attributes (current limitation)
- **WHEN** `ServerCookiePort.set(name, value, max_age=3600, secure=True, samesite="Strict")` is called on the server
- **THEN** only the name/value pair is stored in the internal dict
- **AND** the `max_age`, `secure`, `httponly`, `path`, and `samesite` parameters are discarded
- **NOTE**: When embedded API server or RPC functionality is implemented in a future change, cookie attributes SHALL be propagated via `Set-Cookie` response headers. The current internal-state implementation is sufficient for SSR/SSG where cookies are read-only.

### Requirement: DI keys are defined
The system SHALL define DI injection keys in `webcompy.ports._keys` for all 6 ports.

#### Scenario: Keys are importable and unique
- **WHEN** all 6 port keys are imported from `webcompy.ports._keys`
- **THEN** each key is a distinct `InjectKey` instance usable with `inject()` and `provide()`

### Requirement: DOMNode Protocol methods are available
The `DOMNode` Protocol SHALL expose tree manipulation (`appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove`), attribute methods (`setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`), event methods (`addEventListener`, `removeEventListener`), content properties (`textContent`, `childNodes` (returns `DOMNodeList`), `parentNode`, `nodeName`, `nodeType`), and WebComPy markers (`__webcompy_node__`, `__webcompy_prerendered_node__`). Any object — raw JS node or `VirtualDOMNode` — that structurally satisfies these members SHALL be accepted as a `DOMNode`.

#### Scenario: Raw JS nodes satisfy DOMNode Protocol
- **WHEN** a raw `document.createElement("div")` value is returned from `BrowserDOMPort.create_element()`
- **THEN** it SHALL satisfy the `DOMNode` Protocol structurally
- **AND** the elements layer SHALL operate on it without `cast` wrappers

#### Scenario: DOMNodeList provides length and indexing
- **WHEN** code accesses `node.childNodes` on a DOMNode
- **THEN** it SHALL return a `DOMNodeList` instance
- **AND** `DOMNodeList` SHALL support `.length` (int) and `[index]` access returning `DOMNode`

### Requirement: Port responsibilities are scoped by browser API surface
Ports SHALL be organized around distinct browser API surfaces rather than arbitrary groupings. `DOMPort` SHALL handle document-level operations (`document.createElement`, `document.querySelector`, `document.title`, `document.addEventListener`). `HostPort` SHALL handle general window-level operations (JS global object access via `getattr(window, name, None)`, `window.setTimeout` for macro-task scheduling). Additional port ABCs SHALL be introduced when a new category of browser API surface is identified, following MDN's classification of browser features. This ensures each port has a clear, narrow responsibility and prevents ports from becoming monolithic catch-all abstractions.

Existing ports already demonstrate this principle:
- `CookiePort` is an independent port for `document.cookie`, separate from `DOMPort`'s broader document operations.
- `HistoryPort` is an independent port for `window.location` and `window.history`, separate from `HostPort`'s general window operations.
- `FetchPort` is an independent port for the global `fetch()` API, which belongs to neither document nor window.
- `FFIPort` is an independent port for the PyScript/Emscripten Python-to-JS bridge — not a web platform API at all, but its own distinct concern.

#### Scenario: Document operations belong to DOMPort
- **WHEN** a framework operation interacts with `document` (element creation, selector queries, title, document event listeners)
- **THEN** it SHALL use `DOMPort`

#### Scenario: Window operations belong to HostPort
- **WHEN** a framework operation interacts with `window` (JS globals, `setTimeout`)
- **THEN** it SHALL use `HostPort`

#### Scenario: Specific document or window sub-APIs get their own ports
- **WHEN** a browser API surface under `document` or `window` has sufficient scope to warrant independent abstraction (e.g., `document.cookie` → `CookiePort`, `window.location` + `window.history` → `HistoryPort`)
- **THEN** a dedicated port SHALL be introduced for that sub-API
- **AND** the general port (`DOMPort` or `HostPort`) SHALL NOT absorb it

#### Scenario: APIs outside document/window get their own ports
- **WHEN** a browser API surface does not belong to `document` or `window` (e.g., `fetch()` → `FetchPort`, `navigator` in the future)
- **THEN** a dedicated port SHALL be introduced for that API surface

#### Scenario: Non-web-platform concerns get their own ports
- **WHEN** a concern is not a web platform API but a runtime bridge or tooling abstraction (e.g., PyScript/Emscripten FFI → `FFIPort`)
- **THEN** it MAY have its own dedicated port

#### Scenario: Scope creep is rejected
- **WHEN** a need arises for a browser API surface that does not fit an existing port's scope
- **THEN** a new port SHALL be introduced rather than extending an existing port
- **AND** the existing port ABCs SHALL NOT be extended with methods outside their scope

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
The `DOMEvent` Protocol SHALL be moved from `packages/webcompy/src/webcompy/elements/_dom_objs.py` to `packages/webcompy/src/webcompy/ports/_dom.py`. `packages/webcompy/src/webcompy/elements/_dom_objs.py` SHALL re-export it for backwards compatibility. The Protocol SHALL define `type`, `bubbles`, `cancelable`, `target`, `currentTarget`, `defaultPrevented`, `eventPhase`, `timeStamp`, `preventDefault()`, and `stopPropagation()`.

#### Scenario: DOMEvent is importable from ports._dom
- **WHEN** `from webcompy.ports._dom import DOMEvent` is executed
- **THEN** the `DOMEvent` Protocol SHALL be available
- **AND** `webcompy.elements._dom_objs.DOMEvent` SHALL re-export the same Protocol
