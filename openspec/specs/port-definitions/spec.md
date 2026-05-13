## Purpose

Port ABCs provide a typed, injectable abstraction layer for browser and server runtime operations (DOM manipulation, FFI bridging, HTTP fetching, cookie management, and history navigation). They replace direct access to the monolithic `browser` object, enabling testable, swappable implementations via dependency injection.

## Requirements

### Requirement: Port ABC definitions exist
The system SHALL provide abstract base classes for DOM, FFI, fetch, cookie, and history operations in the `webcompy.ports` package. Each ABC SHALL declare abstract methods for its specific concern. `HistoryPort` SHALL extend `SignalBase[str]` to enable reactive path state.

#### Scenario: All ABCs are importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** all 5 port ABCs (DOMPort, FFIPort, FetchPort, CookiePort, HistoryPort) and DOMNode are accessible

#### Scenario: ABCs cannot be instantiated directly
- **WHEN** a developer attempts to instantiate any port ABC directly
- **THEN** Python raises TypeError due to abstract methods

### Requirement: Browser port implementations exist
The system SHALL provide browser implementations for all 5 ports using `pyscript.context` and `pyscript.ffi`. These SHALL be located in `webcompy.ports._browser`.

#### Scenario: BrowserDOMPort creates real DOM elements
- **WHEN** `BrowserDOMPort.create_element("div")` is called in a PyScript environment
- **THEN** a `BrowserDOMNode` wrapping a real browser `HTMLDivElement` is returned

#### Scenario: BrowserFFIPort uses pyscript.ffi
- **WHEN** `BrowserFFIPort.create_proxy(some_func)` is called
- **THEN** `pyscript.ffi.create_proxy(some_func)` is invoked

#### Scenario: BrowserHistoryPort reads from window.location
- **WHEN** a `BrowserHistoryPort` is constructed in a PyScript environment with mode="history"
- **THEN** its `value` property returns the current `window.location.pathname`

### Requirement: Server port implementations exist
The system SHALL provide server implementations for all 5 ports. FetchPort SHALL use `httpx`. Other ports SHALL use internal state. These SHALL be located in `webcompy.ports._server`. ServerDOMPort SHALL raise `WebComPyException` on DOM node creation.

#### Scenario: ServerDOMPort rejects DOM creation
- **WHEN** `ServerDOMPort.create_element("div")` or `create_text_node(...)` is called on the server
- **THEN** it SHALL raise `WebComPyException` with a message indicating DOM operations are not available outside the browser

#### Scenario: ServerFetchPort uses httpx
- **WHEN** `ServerFetchPort.fetch("https://example.com/api")` is called
- **THEN** an httpx request is sent and a `Response` object is returned

#### Scenario: ServerHistoryPort stores path internally
- **WHEN** `ServerHistoryPort.navigate("/test")` is called
- **THEN** the port's `value` property returns "/test"

### Requirement: DI keys are defined
The system SHALL define DI injection keys in `webcompy.ports._keys` for all 5 ports.

#### Scenario: Keys are importable and unique
- **WHEN** all 5 port keys are imported from `webcompy.ports._keys`
- **THEN** each key is a distinct `InjectKey` instance usable with `inject()` and `provide()`

### Requirement: DOMNode ABC methods are available
The `DOMNode` ABC SHALL expose tree manipulation (`appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove`), attribute methods (`setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`), event methods (`addEventListener`, `removeEventListener`), content properties (`textContent`, `childNodes` (returns `DOMNodeList`), `nodeName`, `nodeType`), and WebComPy markers (`__webcompy_node__`, `__webcompy_prerendered_node__`).

#### Scenario: BrowserDOMNode delegates to real DOM
- **WHEN** `BrowserDOMNode(real_element).setAttribute("class", "foo")` is called
- **THEN** the underlying browser element's class attribute is set to "foo"

#### Scenario: DOMNodeList provides length and indexing
- **WHEN** code accesses `node.childNodes` on a DOMNode
- **THEN** it SHALL return a `DOMNodeList` instance
- **AND** `DOMNodeList` SHALL support `.length` (int) and `[index]` access returning `DOMNode`
