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

`ServerCookiePort.set()` SHALL retain the full attribute set (`max_age`, `expires`, `path`, `domain`, `secure`, `httponly`, `samesite`) associated with each cookie write. Cookie writes performed during SSR SHALL be accumulated per render context and SHALL be emitted as `Set-Cookie` response headers on the HTML page response, preserving all attributes. In hash-mode serving, the HTML shell is pre-rendered once and cached; accumulated cookie writes SHALL NOT be emitted on hash-mode responses. During SSG (`webcompy generate`), cookie writes SHALL be silently ignored (a static artifact cannot carry response headers); this SHALL NOT be treated as an error. The read path (`get()`, request `Cookie` header parsing) SHALL remain unchanged.

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
- **THEN** the previous limitation documented by this scenario (attributes discarded) SHALL be considered retired
- **AND** the full attribute set SHALL be retained and emitted via `Set-Cookie` response headers, as specified by the "ServerCookiePort propagates attributes via Set-Cookie during SSR" scenario

#### Scenario: ServerCookiePort propagates attributes via Set-Cookie during SSR
- **WHEN** `ServerCookiePort.set("session", "abc", max_age=3600, secure=True, samesite="Strict", httponly=True, path="/")` is called during SSR
- **THEN** the HTML page response SHALL include a `Set-Cookie` header for `session=abc`
- **AND** the header SHALL preserve `Max-Age=3600`, `Secure`, `SameSite=Strict`, `HttpOnly`, and `Path=/`

#### Scenario: Multiple cookie writes produce multiple Set-Cookie headers
- **WHEN** two different cookies are set during a single SSR request
- **THEN** the HTML page response SHALL include one `Set-Cookie` header per cookie write
- **AND** cookie writes from concurrent render contexts SHALL NOT leak into each other's responses

#### Scenario: Cookie writes during SSG are ignored
- **WHEN** `ServerCookiePort.set(...)` is called while `webcompy generate` renders a page
- **THEN** no error SHALL be raised
- **AND** the generated static HTML SHALL be unaffected

#### Scenario: Cookie writes are not emitted in hash mode
- **WHEN** `ServerCookiePort.set(...)` is called during the hash-mode pre-render
- **THEN** the cached shell response SHALL NOT include a `Set-Cookie` header

#### Scenario: ServerCookiePort.delete() emits an expiring Set-Cookie during SSR
- **WHEN** `ServerCookiePort.delete("session", path="/")` is called during SSR
- **THEN** the HTML page response SHALL include a `Set-Cookie` header for `session` with `Max-Age=0`
- **AND** the cookie SHALL be removed from the port's read path (`get()` returns `None`)

### Requirement: CookiePort.set() shall support expires and domain attributes
`CookiePort.set()` SHALL accept keyword-only `expires: datetime | None = None` and `domain: str | None = None` parameters in addition to the existing attributes. Calls omitting them SHALL behave exactly as before this change. `BrowserCookiePort.set()` SHALL apply `expires` (formatted as a UTC date string) and `domain` to `document.cookie` alongside the existing attributes. `ServerCookiePort.set()` SHALL retain both for `Set-Cookie` emission.

#### Scenario: Backward compatibility for existing call sites
- **WHEN** `CookiePort.set(name, value, max_age=3600)` is called without `expires` or `domain`
- **THEN** behavior SHALL be identical to before this change

#### Scenario: Browser port applies expires and domain
- **WHEN** `BrowserCookiePort.set("session", "abc", expires=dt, domain="example.com")` is called in the browser
- **THEN** the `document.cookie` write SHALL include the `expires` attribute as a UTC date string and `domain=example.com`

#### Scenario: Set-Cookie preserves Expires and Domain during SSR
- **WHEN** `ServerCookiePort.set("session", "abc", expires=dt, domain="example.com")` is called during SSR
- **THEN** the HTML page response's `Set-Cookie` header SHALL preserve the `Expires` and `Domain` attributes

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
Ports SHALL be organized around distinct browser API surfaces rather than arbitrary groupings. `DOMPort` SHALL handle document-level operations (`document.createElement`, `document.querySelector`, `document.title`, `document.addEventListener`). `HostPort` SHALL handle general window-level operations (JS global object access via `getattr(window, name, None)`, `window.setTimeout` for macro-task scheduling, `window.addEventListener`/`window.removeEventListener` for window event listeners). Additional port ABCs SHALL be introduced when a new category of browser API surface is identified, following MDN's classification of browser features. This ensures each port has a clear, narrow responsibility and prevents ports from becoming monolithic catch-all abstractions.

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

### Requirement: AsyncSchedulerPort shall be a port ABC in the port hierarchy

`AsyncSchedulerPort` SHALL be an abstract base class in `packages/webcompy/src/webcompy/ports/_async_scheduler.py`, following the same pattern as `DOMPort`, `FetchPort`, `HostPort`, and other existing ports. It SHALL define `schedule(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]` and `await_pending(self) -> Awaitable[None]` as abstract methods.

#### Scenario: AsyncSchedulerPort ABC definition
- **WHEN** the port hierarchy is inspected
- **THEN** `AsyncSchedulerPort` SHALL be present as an ABC in the `webcompy.ports` package
- **AND** it SHALL define `schedule` and `await_pending` as abstract methods

### Requirement: BrowserAsyncSchedulerPort and ServerAsyncSchedulerPort shall implement AsyncSchedulerPort

`BrowserAsyncSchedulerPort` SHALL be defined in `packages/webcompy/src/webcompy/ports/_browser/_async_scheduler.py` and SHALL only be instantiable when `ENVIRONMENT == "pyscript"`. `ServerAsyncSchedulerPort` SHALL be defined in `packages/webcompy-server/src/webcompy_server/ports/_async_scheduler.py` and SHALL only be used in server environments.

#### Scenario: Browser port instantiation
- **WHEN** `BrowserAsyncSchedulerPort()` is constructed in the pyscript environment
- **THEN** the instance SHALL be created successfully

#### Scenario: Browser port instantiation outside browser
- **WHEN** `BrowserAsyncSchedulerPort()` is constructed in a non-pyscript environment
- **THEN** a `WebComPyException` SHALL be raised

### Requirement: MarkdownPort ABC shall exist

The system SHALL provide a `MarkdownPort` abstract base class in `webcompy.ports` with a single abstract method `render(source: str) -> str` that converts Markdown text to HTML.

#### Scenario: MarkdownPort is importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** `MarkdownPort` SHALL be accessible

#### Scenario: MarkdownPort cannot be instantiated directly
- **WHEN** a developer attempts to instantiate `MarkdownPort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract method `render`

#### Scenario: BrowserRenderContext provides default MarkdownPort
- **WHEN** a `BrowserRenderContext` is created
- **THEN** `MARKDOWN_PORT_KEY` SHALL be provided with a `DefaultMarkdownParser` instance

#### Scenario: ServerRenderContext provides default MarkdownPort
- **WHEN** a `ServerRenderContext` is created
- **THEN** `MARKDOWN_PORT_KEY` SHALL be provided with a `DefaultMarkdownParser` instance

#### Scenario: Custom parser injection
- **WHEN** a user calls `app.provide(MARKDOWN_PORT_KEY, CustomParser())`
- **THEN** `inject(MARKDOWN_PORT_KEY)` SHALL return the custom parser instance

### Requirement: HistoryPort shall expose a navigation-classification hook

`HistoryPort` SHALL provide `set_scroll_manager(manager | None)` accepting an object with `on_push(from_path, to_path)` and `on_pop(from_path, to_path)` methods (default `None`). `HistoryPort.navigate()` SHALL invoke `on_push` exactly once per effective navigation (after the value change; same-value early-return navigations SHALL NOT invoke it). `BrowserHistoryPort`'s popstate handling SHALL invoke `on_pop` exactly once per popstate-driven navigation, on both the default dispatch path and the `set_navigation_callback` override path. When no manager is registered, behavior SHALL be identical to before.

#### Scenario: Push classification
- **WHEN** a scroll manager is registered and `navigate("/b")` changes the path from `/a`
- **THEN** `on_push("/a", "/b")` SHALL be called exactly once

#### Scenario: Pop classification
- **WHEN** a scroll manager is registered and a popstate event moves the path from `/b` to `/a`
- **THEN** `on_pop("/b", "/a")` SHALL be called exactly once

#### Scenario: Same-value navigation does not notify
- **WHEN** `navigate()` is called with the current path and identical state
- **THEN** neither `on_push` nor `on_pop` SHALL be called

#### Scenario: No manager registered
- **WHEN** navigations occur with no manager registered
- **THEN** `HistoryPort` behavior SHALL be unchanged from before this capability existed

### Requirement: HistoryPort shall own browser URL updates

`HistoryPort` SHALL provide `push_url(path, state)` and `replace_url(path, state)` methods. The base implementations SHALL be no-ops (server environments perform no URL manipulation). `BrowserHistoryPort` SHALL implement them via `window.history.pushState` / `replaceState`, building the browser-visible URL from the app-internal path by applying the router mode (`#` prefix in hash mode) and the app `base_url` prefix in history mode; to support this, `BrowserHistoryPort` SHALL accept an optional `base_url` constructor parameter. Non-JSON-serializable `state` SHALL be passed as `None` to the browser with a logged warning. Testing fakes SHOULD record invocations for assertions.

#### Scenario: History-mode URL building
- **GIVEN** a `BrowserHistoryPort` in history mode with `base_url="/myapp"`
- **WHEN** `push_url("/about", None)` is called
- **THEN** the browser history SHALL receive the URL `/myapp/about/`

#### Scenario: Hash-mode URL building
- **GIVEN** a `BrowserHistoryPort` in hash mode
- **WHEN** `push_url("/about", None)` is called
- **THEN** the browser history SHALL receive the URL `#/about/`

#### Scenario: Server no-op
- **WHEN** `push_url` is called on a server history port during SSR/SSG
- **THEN** no browser API SHALL be accessed and no error SHALL occur

#### Scenario: Redirect uses replace
- **WHEN** the navigation pipeline commits a redirect
- **THEN** `replace_url` SHALL be called instead of `push_url`

### Requirement: CustomElementPort ABC shall exist in the port hierarchy

The framework SHALL provide a `CustomElementPort` abstract base class in `webcompy.ports` for custom-element registry and per-node binding operations. It SHALL define methods for ensuring a custom element is defined and for binding a DOM node to lifecycle and attribute callbacks. The port SHALL NOT import `Component`; component-specific callbacks SHALL be supplied as callables when binding.

#### Scenario: CustomElementPort is importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** `CustomElementPort` SHALL be accessible

#### Scenario: CustomElementPort cannot be instantiated directly
- **WHEN** a developer attempts to instantiate `CustomElementPort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract methods

#### Scenario: Browser implementation creates native custom elements
- **WHEN** the browser `CustomElementPort` ensures a named element is defined
- **THEN** it SHALL register an `HTMLElement` subclass through `customElements.define` (or reuse a compatible existing definition)
- **AND** binding a node SHALL forward lifecycle and observed-attribute reactions to the supplied callbacks

#### Scenario: Port does not depend on the component module
- **WHEN** the custom-element port module is imported
- **THEN** it SHALL not import `webcompy.components._component` or any component class

### Requirement: CustomElementPort shall expose registry conflict behavior

When a custom element name is already defined, the browser `CustomElementPort` SHALL reuse the existing definition only when its WebComPy marker and observed-attribute metadata match. A non-WebComPy definition or an incompatible WebComPy definition SHALL raise `WebComPyComponentException` and SHALL not be replaced.

#### Scenario: Reusing a compatible definition
- **WHEN** two WebComPy definitions request the same custom element name with matching metadata
- **THEN** the second request SHALL reuse the existing browser definition
- **AND** no `customElements.define` call SHALL be issued for the duplicate

#### Scenario: Rejecting an incompatible definition
- **WHEN** a custom element name is already defined by another library or with different observed attributes
- **THEN** `WebComPyComponentException` SHALL be raised
- **AND** the existing browser definition SHALL remain unchanged
