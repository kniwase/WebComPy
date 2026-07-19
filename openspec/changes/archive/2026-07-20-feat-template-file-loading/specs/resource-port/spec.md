## ADDED Requirements

### Requirement: A `ResourcePort` ABC provides async access to application resource files

The framework SHALL provide a `ResourcePort` abstract base class in `webcompy/ports/_resource.py`. The class SHALL expose two asynchronous methods:

```python
class ResourcePort(ABC):
    async def load_text(self, path: str) -> str: ...
    async def load_bytes(self, path: str) -> bytes: ...
```

`path` SHALL be a package-relative POSIX-style path (forward slashes, no leading slash, no `..` segments). Implementations SHALL raise `ResourceNotFoundError` when `path` is invalid or the resource does not exist.

#### Scenario: ABC cannot be instantiated directly
- **WHEN** a developer calls `ResourcePort()`
- **THEN** `TypeError` SHALL be raised due to the abstract `load_text` and `load_bytes` methods

#### Scenario: Successful text load returns UTF-8 decoded str
- **WHEN** `await port.load_text("templates/card.html")` is called on a port implementation with the resource available
- **THEN** the file's UTF-8 decoded text contents SHALL be returned as `str`

#### Scenario: Successful bytes load returns raw bytes
- **WHEN** `await port.load_bytes("assets/icons/star.png")` is called on a port implementation with the resource available
- **THEN** the file's raw bytes SHALL be returned as `bytes`
- **AND** no decoding SHALL be performed

#### Scenario: Resource not found
- **WHEN** `await port.load_text("missing.html")` is called and the resource does not exist
- **THEN** `ResourceNotFoundError` SHALL be raised with a message that includes the requested path

#### Scenario: Invalid path rejected
- **WHEN** `await port.load_text("/etc/passwd")` or `await port.load_text("../secret.txt")` is called
- **THEN** `ResourceNotFoundError` SHALL be raised before any filesystem, payload, or fetch access occurs

### Requirement: A `RESOURCE_PORT_KEY` is provided for DI lookup

`webcompy/ports/_keys.py` SHALL define `RESOURCE_PORT_KEY = InjectKey[ResourcePort]("webcompy-port-resource")`. The key SHALL be importable from `webcompy.ports` and SHALL be usable with both `inject()` and `provide()`.

#### Scenario: Key uniqueness
- **WHEN** `RESOURCE_PORT_KEY` is imported alongside the other port keys
- **THEN** it SHALL be a distinct `InjectKey` instance from the existing port keys

#### Scenario: Key injection
- **WHEN** `inject(RESOURCE_PORT_KEY)` is called in a `RenderContext` that has registered the port
- **THEN** the registered port instance SHALL be returned

### Requirement: `ServerResourcePort` reads resources from the application package directory on disk

`webcompy_server/ports/_resource.py` SHALL provide `class ServerResourcePort(ResourcePort)`. Its constructor SHALL accept `app_package_path: pathlib.Path` and `allow_list: frozenset[str]` (set of allow-listed package-relative paths).

`async load_text(path)` SHALL resolve `path` against `app_package_path`, validate the resolved path stays inside the package directory via `realpath` containment, validate membership in the allow-list, and read with `Path.read_text(encoding="utf-8")` on every call. `async load_bytes(path)` SHALL do the same with `Path.read_bytes()`.

`ServerResourcePort` SHALL additionally record every successful `(path, bytes)` read into a per-`RenderContext` accumulator exposed via a `get_recorded_resources() -> dict[str, bytes]` method (used by the SSR payload generator to populate the hydration `resources` field).

#### Scenario: Reading a server-side resource
- **WHEN** `await ServerResourcePort(root=Path("/srv/myapp"), allow_list=frozenset({"templates/card.html"})).load_text("templates/card.html")` is called
- **AND** the file `/srv/myapp/templates/card.html` exists
- **THEN** the file's UTF-8 decoded contents SHALL be returned

#### Scenario: Reading outside the allow-list raises
- **WHEN** `await port.load_text("secrets/webcompy_config.py")` is called
- **AND** `secrets/webcompy_config.py` is not in the allow-list
- **THEN** `ResourceNotFoundError` SHALL be raised without touching the filesystem

#### Scenario: Path traversal rejected
- **WHEN** `await port.load_text("../escape.txt")` is called
- **THEN** `ResourceNotFoundError` SHALL be raised before any filesystem access

#### Scenario: Reads are not cached
- **WHEN** `await port.load_text(...)` is called twice on the same path with the file modified between the two calls
- **THEN** the second call SHALL return the updated contents (no internal cache layer)

#### Scenario: Successful loads are recorded
- **WHEN** `await port.load_text("a.html")` and `await port.load_bytes("b.png")` succeed
- **THEN** `port.get_recorded_resources()` SHALL return a dict containing both keys mapped to their raw bytes

#### Scenario: Failed loads are not recorded
- **WHEN** `await port.load_text("missing.html")` raises `ResourceNotFoundError`
- **THEN** `port.get_recorded_resources()` SHALL NOT contain `missing.html`

### Requirement: `BrowserResourcePort` reads resources from the hydration payload, then fetches from the resource endpoint

`webcompy/ports/_browser/_resource.py` SHALL provide `class BrowserResourcePort(ResourcePort)`. Both `load_text` and `load_bytes` SHALL:

1. Read `RESOURCE_DATA_KEY` from the DI scope (`InjectKey[dict[str, str]]`, base64-encoded bytes keyed by package-relative path). If the path is present, decode and return the content (text or bytes based on the called method).
2. Otherwise, fetch `GET {base_url}_webcompy-resource/{path}` via the existing `FetchPort` (URL prefix comes from `WebComPyAppConfig.base_url`). On HTTP success, return the response body (text or bytes based on the called method).
3. On HTTP non-2xx, missing payload entry, or fetch error, raise `ResourceNotFoundError` with a message identifying the path and the steps attempted.

#### Scenario: Embedded resource returned from payload
- **WHEN** `BrowserResourcePort()` is constructed inside a `RenderContext` where `RESOURCE_DATA_KEY` is provided with `{"templates/card.html": base64("...")}`
- **AND** `await port.load_text("templates/card.html")` is called
- **THEN** the embedded decoded content SHALL be returned
- **AND** no fetch SHALL be issued

#### Scenario: Embedded bytes returned from payload
- **WHEN** `RESOURCE_DATA_KEY` is provided with `{"icons/star.png": base64(raw_bytes)}`
- **AND** `await port.load_bytes("icons/star.png")` is called
- **THEN** the decoded raw bytes SHALL be returned

#### Scenario: Resource not in payload triggers fetch
- **WHEN** `RESOURCE_DATA_KEY` does not contain `"templates/late.html"`
- **AND** `await port.load_text("templates/late.html")` is called
- **THEN** a GET request SHALL be issued to `{base_url}_webcompy-resource/templates/late.html`
- **AND** on HTTP 200, the response body SHALL be returned as text

#### Scenario: Fetch failure raises ResourceNotFoundError
- **WHEN** the fetched endpoint returns HTTP 404 or the fetch raises
- **THEN** `ResourceNotFoundError` SHALL be raised
- **AND** the message SHALL indicate both the payload miss and the fetch failure

#### Scenario: Browser environment required
- **WHEN** `BrowserResourcePort()` is instantiated outside a PyScript/Emscripten environment (`ENVIRONMENT != "pyscript"`)
- **THEN** a clear exception SHALL be raised indicating the port is browser-only

### Requirement: `RenderContext` provides the appropriate `ResourcePort` implementation

`ServerRenderContext._register_ports` SHALL read `app._server_resource_port` (an optional attribute populated by `configure_server_context(app, *, resource_port=...)`); when non-`None`, it SHALL provide it via `RESOURCE_PORT_KEY`. When `None` (e.g., test helpers that don't pass `resource_port`), the key is not provided and `inject(RESOURCE_PORT_KEY, default=None)` returns `None` cleanly. `BrowserRenderContext._register_ports` SHALL provide `RESOURCE_PORT_KEY` with a `BrowserResourcePort(base_url)` (constructed with the context's `self._config.base_url`) and populate `RESOURCE_DATA_KEY` from the hydration payload's `resources` field if available.

#### Scenario: Server render context injection
- **WHEN** a component runs inside `ServerRenderContext`
- **THEN** `inject(RESOURCE_PORT_KEY)` SHALL return a `ServerResourcePort`

#### Scenario: Browser render context injection
- **WHEN** a component runs inside `BrowserRenderContext`
- **THEN** `inject(RESOURCE_PORT_KEY)` SHALL return a `BrowserResourcePort`
- **AND** `inject(RESOURCE_DATA_KEY)` SHALL return the embedded resource dict from the hydration payload

### Requirement: `load_text` and `load_bytes` are public async helpers exported from `webcompy`

`webcompy.resources.load_text(source: str | pathlib.Path) -> str` and `webcompy.resources.load_bytes(source: str | pathlib.Path) -> bytes` SHALL be async helpers that:

1. Accept either a `str` (used as-is) or a `pathlib.Path` (converted to POSIX-style relative path via `.as_posix()` if the path is relative, or rejected if absolute).
2. Reject paths containing `..` segments before delegating to the port.
3. Internally `inject(RESOURCE_PORT_KEY)` to retrieve the port.
4. Call `await port.load_text(path)` / `await port.load_bytes(path)` and return the result.
5. Raise `WebComPyException` with a clear message if no `RESOURCE_PORT_KEY` is available in the current DI scope.

The functions SHALL also be re-exported from `webcompy` (top-level package) as `load_text` and `load_bytes` for convenience.

#### Scenario: Helper with str path
- **WHEN** `await load_text("templates/card.html")` is called from inside an async component setup with a configured `ResourcePort`
- **THEN** the equivalent of `await port.load_text("templates/card.html")` SHALL be executed
- **AND** the returned string SHALL be passed to `render_template` (the caller's responsibility)

#### Scenario: Helper with relative pathlib.Path
- **WHEN** `await load_text(Path("templates") / "card.html")` is called
- **THEN** the path SHALL be normalized to POSIX form `"templates/card.html"` before being passed to the port

#### Scenario: Helper with absolute pathlib.Path is rejected
- **WHEN** `await load_text(Path("/etc/templates/card.html"))` is called
- **THEN** `WebComPyException` SHALL be raised before contacting the port

#### Scenario: Missing ResourcePort raises WebComPyException
- **WHEN** `await load_text("templates/card.html")` is called outside a `RenderContext` (no `RESOURCE_PORT_KEY` in scope)
- **THEN** `WebComPyException` SHALL be raised with a message identifying the missing DI key

#### Scenario: Usage with render_template in async setup
- **WHEN** a component writes:
  ```python
  @define_component
  async def Card(ctx):
      tpl = await load_text("templates/card.html")
      return render_template(tpl, locals())
  ```
- **THEN** `load_text` SHALL resolve the resource before `render_template` is called
- **AND** the resulting `Element` tree SHALL be returned identically to inline-string usage

#### Scenario: Top-level export accessible
- **WHEN** a developer writes `from webcompy import load_text, load_bytes`
- **THEN** the import SHALL succeed
- **AND** both functions SHALL be coroutines defined in `webcompy.resources`

### Requirement: Resource paths SHALL resolve identically across server and browser

The same `path: str` argument SHALL produce the same logical resource on `ServerResourcePort` and `BrowserResourcePort`. The server resolves against the configured `app_package_path`; the browser URL-fetches the same logical path. The two implementations SHOULD yield content-equal results for the same path under steady-state operation.

#### Scenario: Same path, same content
- **WHEN** `await ServerResourcePort(...).load_text("a/b.html")` returns `"<p>hi</p>"`
- **AND** `await BrowserResourcePort().load_text("a/b.html")` is called in a hydrated context where the same path is embedded in the payload
- **THEN** the browser port SHALL return `"<p>hi</p>"` (or its bytes representation)

#### Scenario: POSIX normalization
- **WHEN** a helper is called with backslash separators
- **THEN** the helper SHALL raise `WebComPyException` before reaching the port (paths are required to be POSIX-style)
