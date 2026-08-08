# Delta Spec: port-abstraction

## ADDED Requirements

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

## MODIFIED Requirements

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
