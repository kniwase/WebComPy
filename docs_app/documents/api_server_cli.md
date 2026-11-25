---
title: Server, CLI, RPC & Ports API
description: API reference for webcompy_server, webcompy_cli, webcompy.rpc, webcompy.hydration, and webcompy.ports.
---

# Server, CLI, RPC & Ports API

<!-- author:start:intro -->
API reference for server integration (`webcompy_server`), CLI build and server configuration (`webcompy_cli`), typed RPC client/server APIs (`webcompy.rpc`, `webcompy_server.rpc`), SSR hydration/transfer metadata (`webcompy.hydration`), and environment port interfaces (`webcompy.ports`, `webcompy_server.ports`).
<!-- author:end:intro -->

<!-- generated:start -->

## Server & CLI Configuration

### configure_server_context

```python
def configure_server_context(
    app: WebComPyApp,
    *,
    resource_port: ServerResourcePort | None = None,
    root_app: ASGIApp | None = None,
) -> None
```

Key: `webcompy_server:configure_server_context` · Exports: `from webcompy_server import configure_server_context`

Switch a `WebComPyApp` to server-side rendering.

Sets `ServerRenderContext` as the application's render context class and installs a fresh `ServerFetchPort`, preserving any external HTTP client configured on a previously installed server fetch port.

**Args:**

- `app`: Application to switch to server-side rendering.
- `resource_port`: Optional `ServerResourcePort` serving app-package resources; when `None`, any existing resource port is left unchanged.
- `root_app`: Optional host ASGI application used for self-site fetches. When given, page routes under the configured base URL are blocked during SSR to prevent recursive self-fetches, and the fetch port is marked as embedded.

### create_asgi_app

```python
def create_asgi_app(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    mode: Literal['prod', 'dev'] = 'prod',
) -> _ServingApp
```

Key: `webcompy_cli._server:create_asgi_app` · Exports: `from webcompy_cli import create_asgi_app`

Create the ASGI application for serving the WebComPy app.

Resolves build artifacts, wires static, asset, and resource routes, and mounts the HTML and optional RPC and dev-reload routes.

**Args:**

- `app`: Application instance to serve.
- `build_config`: Build configuration controlling artifact resolution.
- `mode`: Serving mode, `"prod"` or `"dev"`.

**Returns:** A `_ServingApp` wrapping the ASGI app and its artifacts.

### discover_config

```python
def discover_config(module_path: str | None = None) -> WebComPyBuildConfig
```

Key: `webcompy_cli._utils:discover_config` · Exports: `from webcompy_cli import discover_config`

Discover and return the build configuration.

**Args:**

- `module_path`: Dotted import path of the config module. When `None`, `webcompy_config` is imported.

**Returns:** The `WebComPyBuildConfig` instance found in the module.

**Raises:**

- `WebComPyCliException`: If the module cannot be imported, or the `config` attribute is missing or has the wrong type.

### generate_html

```python
async def generate_html(
    ctx: RenderContext,
    app_package_name: str,
    dev_mode: bool,
    prerender: bool,
    wheel_filename: str,
    pyodide_package_names: list[str] | None = None,
    wasm_local_urls: dict[str, str] | None = None,
    lockfile_url: str | None = None,
    runtime_serving: str = 'cdn',
    extra_wheel_filenames: list[str] | None = None,
    app_package_path: Path | None = None,
    pwa_enabled: bool = False,
)
```

Key: `webcompy_server._html:generate_html` · Exports: `from webcompy_server import generate_html`

Generate the full HTML document for the application.

**Args:**

- `ctx`: Render context providing app config and DI scope.
- `app_package_name`: Importable name of the app package.
- `dev_mode`: Whether to inject dev-server reload support.
- `prerender`: Whether to prerender the app root and inject hydration data.
- `wheel_filename`: Filename of the app package wheel.
- `pyodide_package_names`: Extra Pyodide packages to include.
- `wasm_local_urls`: Mapping of package names to local WASM URLs.
- `lockfile_url`: URL of the Pyodide lock file when serving remotely.
- `runtime_serving`: How the PyScript runtime is served.
- `extra_wheel_filenames`: Additional wheel filenames to preload.
- `app_package_path`: Filesystem path of the app package for template resolution.
- `pwa_enabled`: Whether to inject PWA manifest and worker registration.

**Returns:** Rendered HTML string for the document.

### generate_static_site

```python
async def generate_static_site(app: WebComPyApp | None = None)
```

Key: `webcompy_cli._generate:generate_static_site` · Exports: `from webcompy_cli import generate_static_site`

Generate static HTML files for the application.

Builds the wheel and assets, copies static and resource files, and fetches each route via the ASGI app to write `index.html` files into the distribution directory.

**Args:**

- `app`: Application instance to generate. When `None`, the configuration is discovered via `discover_config` and CLI flags override the build options.

### LockfileSyncConfig

```python
class LockfileSyncConfig:
    requirements_path: str | None = None
    sync_group: str | None = None
```

Key: `webcompy_cli.config._server_config:LockfileSyncConfig` · Exports: `from webcompy_cli.config import LockfileSyncConfig`

Configuration for syncing the lock file with project manifests.

**Args:**

- `requirements_path`: Path to the `requirements.txt` file used for `sync` and `export`, or `None` to auto-discover.
- `sync_group`: Optional dependency group name in `pyproject.toml` to compare against the lock file.

**Attributes:**

- `requirements_path`: Path to the `requirements.txt` file used for `sync` and `export`, or `None` to auto-discover.
- `sync_group`: Optional dependency group name in `pyproject.toml` to compare against the lock file.

### ManifestConfig

```python
class ManifestConfig:
    name: str
    short_name: str | None = None
    icons: list[ManifestIcon] = field(default_factory=list)
    display: str = 'standalone'
    theme_color: str | None = None
    background_color: str | None = None
    start_url: str | None = None
    scope: str | None = None
```

Key: `webcompy_cli.config._pwa_config:ManifestConfig` · Exports: `from webcompy_cli.config import ManifestConfig`

Web App Manifest metadata serialized to `manifest.webmanifest`.

**Args:**

- `name`: Human-readable application name.
- `short_name`: Optional shortened name for launchers.
- `icons`: Icon entries referenced by the manifest.
- `display`: Display mode; one of `fullscreen`, `standalone`, `minimal-ui` or `browser`.
- `theme_color`: Optional default theme color.
- `background_color`: Optional splash background color.
- `start_url`: Optional start URL; defaults to the app base URL.
- `scope`: Optional navigation scope; defaults to the app base URL.

**Attributes:**

- `name`: Human-readable application name.
- `short_name`: Optional shortened name for launchers.
- `icons`: Icon entries referenced by the manifest.
- `display`: Display mode.
- `theme_color`: Optional default theme color.
- `background_color`: Optional splash background color.
- `start_url`: Optional start URL; defaults to the app base URL.
- `scope`: Optional navigation scope; defaults to the app base URL.

### ManifestIcon

```python
class ManifestIcon:
    src: str
    sizes: str
    type: str | None = None
    purpose: str | None = None
```

Key: `webcompy_cli.config._pwa_config:ManifestIcon` · Exports: `from webcompy_cli.config import ManifestIcon`

An icon entry in the Web App Manifest.

**Args:**

- `src`: URL of the icon, resolved relative to the application base URL. Typically a path inside the static files directory.
- `sizes`: Space-separated icon sizes (e.g. `"192x192 512x512"`).
- `type`: Optional MIME type of the icon resource.
- `purpose`: Optional icon purpose (e.g. `"maskable"`).

**Attributes:**

- `src`: URL of the icon, resolved relative to the application base URL.
- `sizes`: Space-separated icon sizes.
- `type`: Optional MIME type of the icon resource.
- `purpose`: Optional icon purpose.

### PWAConfig

```python
class PWAConfig:
    enabled: bool = False
    manifest: ManifestConfig | None = None
    precache: Literal['auto', 'none'] = 'auto'
    precache_runtime: bool = False
    runtime: list[RuntimeCachingRule] = field(default_factory=list)
    fallback_path: str | None = None
```

Key: `webcompy_cli.config._pwa_config:PWAConfig` · Exports: `from webcompy_cli.config import PWAConfig`

Progressive Web App build configuration (disabled by default).

**Args:**

- `enabled`: Whether PWA support is active; defaults to `False`.
- `manifest`: Manifest metadata; required when `enabled` is true.
- `precache`: Precache mode, `"auto"` (enumerate build output) or `"none"` (empty precache manifest).
- `precache_runtime`: Opt-in to precaching the Python runtime files, which logs a build-time size warning.
- `runtime`: Runtime caching rules applied to same-origin requests.
- `fallback_path`: Optional path (relative to the static files directory) of an offline fallback page overriding the framework default.

**Attributes:**

- `enabled`: Whether PWA support is active.
- `manifest`: Manifest metadata; `None` when not configured.
- `precache`: Precache mode (`"auto"` or `"none"`).
- `precache_runtime`: Whether the Python runtime is precached.
- `runtime`: Runtime caching rules.
- `fallback_path`: Optional offline fallback page path.

#### Members

**`validate`** (method)

```python
def validate(self, *, app_package_path: Path, static_files_dir: str) -> None
```

Validate this configuration at build start.

**Args:**

- `app_package_path`: Filesystem path of the application package, used to resolve the static files directory.
- `static_files_dir`: Static files directory relative to the application package path.

**Raises:**

- `WebComPyException`: If any configured value is invalid or an inconsistent combination is used.

### run_inspect

```python
def run_inspect() -> None
```

Key: `webcompy_cli._inspect:run_inspect` · Exports: `from webcompy_cli import run_inspect`

Run the `webcompy inspect` CLI command.

Parses `sys.argv` for the inspect subcommands and dispatches to the selected handler.

**Returns:** `None`.

### run_server

```python
def run_server(app: WebComPyApp | None = None)
```

Key: `webcompy_cli._server:run_server` · Exports: `from webcompy_cli import run_server`

Run the development or production ASGI server.

**Args:**

- `app`: Application instance to serve. When `None`, the configuration is discovered via `discover_config` and CLI flags override the build and server options.

### RuntimeCachingRule

```python
class RuntimeCachingRule:
    pattern: str
    strategy: RuntimeCachingStrategy
    max_entries: int | None = None
    max_age: int | None = None
```

Key: `webcompy_cli.config._pwa_config:RuntimeCachingRule` · Exports: `from webcompy_cli.config import RuntimeCachingRule`

A runtime caching rule matched against same-origin requests.

**Args:**

- `pattern`: Same-origin URL pattern; a path prefix or a glob with `*` (single segment) and `**` (any depth). Matched against the request path relative to the app scope (always starting with `/`); a missing leading slash is added at generation time. Matching uses the full URL, so different query strings are cached independently.
- `strategy`: Caching strategy applied to matching requests; one of `cache-first`, `network-first` or `stale-while-revalidate`.
- `max_entries`: Optional maximum number of entries kept in the rule's cache before eviction trims it.
- `max_age`: Optional maximum cached entry age in seconds; enforced best-effort within a worker lifetime.

**Attributes:**

- `pattern`: Same-origin URL pattern.
- `strategy`: Caching strategy applied to matching requests.
- `max_entries`: Optional maximum number of cached entries.
- `max_age`: Optional maximum cached entry age in seconds.

### RuntimeCachingStrategy

```python
RuntimeCachingStrategy: TypeAlias = Literal['cache-first', 'network-first', 'stale-while-revalidate']
```

Key: `webcompy_cli.config._pwa_config:RuntimeCachingStrategy` · Exports: `from webcompy_cli.config import RuntimeCachingStrategy`

Caching strategy applied to requests matching a runtime caching rule.

### ServerRenderContext

```python
class ServerRenderContext(RenderContext)
```

Key: `webcompy_server._context:ServerRenderContext` · Exports: `from webcompy_server import ServerRenderContext`

Server-side `RenderContext` that provides server port implementations.

#### Members

**`get_pending_set_cookie_headers`** (method)

```python
def get_pending_set_cookie_headers(self) -> list[str]
```

Collect pending `Set-Cookie` header values.

**Returns:** List of serialized `Set-Cookie` header strings pending for the response.

**`render_html`** (async_method)

```python
async def render_html(self, **kwargs: Any) -> str
```

Render the application to an HTML string.

**Args:**

- `**kwargs`: Forwarded to `generate_html`.

**Returns:** Rendered HTML string.

### WebComPyBuildConfig

```python
class WebComPyBuildConfig:
    app_module: ModuleType
    app_var: str = 'app'
    dependencies: list[str] | None = None
    dependencies_from: str | None = None
    resources: list[str] | None = None
    resource_exclude: list[str] | None = None
    version: str | None = None
    serve_all_deps: bool = True
    wasm_serving: Literal['cdn', 'local'] | None = None
    runtime_serving: Literal['cdn', 'local'] | None = None
    standalone: bool = False
    wheel_mode: Literal['bundled', 'split'] = 'bundled'
    resource_transfer: Literal['used', 'all-text'] = 'used'
    dist: str = 'dist'
    static_files_dir: str = 'static'
    lockfile_sync_config: LockfileSyncConfig | None = None
    server: WebComPyServerConfig = field(default_factory=WebComPyServerConfig)
    pwa: PWAConfig = field(default_factory=PWAConfig)
```

Key: `webcompy_cli.config._build_config:WebComPyBuildConfig` · Exports: `from webcompy_cli.config import WebComPyBuildConfig`

Build configuration for a WebComPy application package.

Collects all options controlling dependency resolution, wheel building, resource handling, and serving. `app_package_path` and `app` are derived from `app_module`/`app_var` in `__post_init__`.

**Args:**

- `app_module`: Python module containing the application instance.
- `app_var`: Attribute name of the application inside `app_module`.
- `dependencies`: Explicit browser dependency names, or `None` to discover from `pyproject.toml`.
- `dependencies_from`: Optional dependency group name in `pyproject.toml` to resolve `dependencies` from.
- `resources`: Glob patterns selecting resource files, or `None` for the default includes. An empty list disables resources.
- `resource_exclude`: Glob patterns excluding resource files.
- `version`: Application version string, or `None` for `"0.0.0"`.
- `serve_all_deps`: Whether to bundle all pure-Python dependencies into the app wheel.
- `wasm_serving`: How WASM packages are served, or `None` to resolve from `standalone`.
- `runtime_serving`: How the PyScript/Pyodide runtime is served, or `None` to resolve from `standalone`.
- `standalone`: Whether to serve all assets locally.
- `wheel_mode`: Wheel bundling mode.
- `resource_transfer`: How resource files are transferred to the browser.
- `dist`: Output directory for the static site.
- `static_files_dir`: Directory housing static files relative to the app package path.
- `lockfile_sync_config`: Configuration for lock file synchronization.
- `server`: Server configuration.
- `pwa`: Progressive Web App build configuration.

**Attributes:**

- `app_module`: Python module containing the application instance.
- `app_var`: Attribute name of the application inside `app_module`.
- `app`: The application instance resolved from `app_module`/ `app_var`.
- `app_package_path`: Directory containing the application package, derived from `app_module`.
- `dependencies`: Explicit browser dependency names, or `None` to discover from `pyproject.toml`.
- `dependencies_from`: Optional dependency group name in `pyproject.toml` to resolve `dependencies` from.
- `resources`: Glob patterns selecting resource files, or `None` for the default includes.
- `resource_exclude`: Glob patterns excluding resource files.
- `version`: Application version string, or `None` for `"0.0.0"`.
- `serve_all_deps`: Whether to bundle all pure-Python dependencies into the app wheel.
- `wasm_serving`: How WASM packages are served.
- `runtime_serving`: How the PyScript/Pyodide runtime is served.
- `standalone`: Whether to serve all assets locally.
- `wheel_mode`: Wheel bundling mode.
- `resource_transfer`: How resource files are transferred.
- `dist`: Output directory for the static site.
- `static_files_dir`: Directory housing static files.
- `lockfile_sync_config`: Configuration for lock file synchronization.
- `server`: Server configuration.
- `pwa`: Progressive Web App build configuration.

#### Members

**`resolve_standalone`** (method)

```python
def resolve_standalone(self)
```

Resolve implicit serving modes from the `standalone` flag.

### WebComPyServerConfig

```python
class WebComPyServerConfig:
    port: int = 8080
    dev: bool = False
    mounts: Callable[[], dict[str, ASGIApp]] | None = None
```

Key: `webcompy_cli.config._server_config:WebComPyServerConfig` · Exports: `from webcompy_cli.config import WebComPyServerConfig`

Configuration for the development server and ASGI mounts.

**Args:**

- `port`: TCP port the server listens on.
- `dev`: Whether to run in development mode with live reload.
- `mounts`: Callable returning additional `{prefix: app}` ASGI mounts.

**Attributes:**

- `port`: TCP port the server listens on.
- `dev`: Whether to run in development mode with live reload.
- `mounts`: Callable returning additional `{prefix: app}` ASGI mounts.

## Typed RPC (Client & Server)

### add_rpc_middleware

```python
def add_rpc_middleware(middleware: RpcMiddleware) -> None
```

Key: `webcompy.rpc._middleware:add_rpc_middleware` · Exports: `from webcompy.rpc import add_rpc_middleware`

Append *middleware* to the active RPC middleware registry.

Registrations are consulted at each HTTP RPC operation, so they take effect on subsequent calls. Ordering is `middlewares[0]` outermost.

**Args:**

- `middleware`: Callable invoked with the procedure context and a `next` handle.

**Raises:**

- `RuntimeError`: If no registry is available in the current scope (no active render context).

### batch

```python
async def batch(
    *calls: RpcCall[Any, Any],
    return_exceptions: bool = False,
) -> tuple[Any, ...]
```

Key: `webcompy.rpc._contracts:batch` · Exports: `from webcompy.rpc import batch`

Await several RPC calls issued through the same transport and return their results.

`return_exceptions=False` (default) propagates the first failure; with `True` each failure is collected as an `RpcError` in the result tuple. Each occurrence of an `RpcCall` in the argument list is dispatched as its own request; reusing a call that was already awaited elsewhere raises `RuntimeError`.

**Args:**

- `*calls`: RPC calls created from the same transport instance.
- `return_exceptions`: When `True`, collect failures as `RpcError` entries instead of raising on the first one.

**Returns:** A tuple holding each call's result in call order; entries are `RpcError` instances when `return_exceptions` is `True`.

**Raises:**

- `RuntimeError`: If any call was already awaited.
- `RpcError`: If the calls are invalid, use different transports, target an unsupported or non-open connection, or the batch response is malformed.

### create_dispatcher_app

```python
def create_dispatcher_app(registry: ProcedureRegistry)
```

Key: `webcompy_server.rpc._dispatcher:create_dispatcher_app` · Exports: `from webcompy_server.rpc import create_dispatcher_app`

Return the JSON-RPC dispatcher as a class-based ASGI application.

The returned app is usable directly as an ASGI application or as the endpoint of a Starlette `Route` (which dispatches to class-based ASGI apps verbatim). It serves ordinary JSON-RPC responses as `application/json` and single `"stream": true` calls to streaming procedures as `text/event-stream`.

**Args:**

- `registry`: Procedure registry serving the dispatched calls.

**Returns:** The dispatcher ASGI app.

### create_rpc_ws_endpoint

```python
def create_rpc_ws_endpoint(registry: ProcedureRegistry)
```

Key: `webcompy_server.rpc._ws_endpoint:create_rpc_ws_endpoint` · Exports: `from webcompy_server.rpc import create_rpc_ws_endpoint`

Return the JSON-RPC WebSocket endpoint handler for `registry`.

The endpoint accepts a WebSocket, feeds each incoming text frame through the shared transport-neutral dispatch core (`dispatch_payload`) and writes each response back as a text frame via a per-connection send queue (single FIFO path guarantees response → replay → live ordering for subscriptions). Reserved `_webcompy.*` methods are handled here: ping is answered with pong, close closes the socket with code 1011 so the client reconnect loop engages, subscribe/unsubscribe drive the subscription hub, and stream-cancel stops a per-call stream. Single `"stream": true` calls to streaming procedures are answered with a `stream_id` and streamed by the `StreamCallHub`. Starlette is imported lazily so this module stays importable outside a Starlette context.

**Args:**

- `registry`: Procedure registry serving the dispatched calls and backing the subscription/stream hubs.

**Returns:** The async Starlette WebSocket endpoint handler for `registry`.

### dispatch_payload

```python
async def dispatch_payload(
    payload: Any,
    registry: ProcedureRegistry,
) -> dict[str, Any] | list[dict[str, Any]] | None
```

Key: `webcompy_server.rpc._dispatcher:dispatch_payload` · Exports: `from webcompy_server.rpc import dispatch_payload`

Dispatch a parsed JSON-RPC payload (transport-neutral).

`payload` is either a single request object or a batch array. Returns the response object(s) as plain JSON-serializable dictionaries, or `None` when there is nothing to respond (e.g. notifications only). HTTP and WebSocket transports serialize the result to their own wire format.

**Args:**

- `payload`: Parsed JSON-RPC request object, or a batch array of them.
- `registry`: Procedure registry resolving method names to handlers.

**Returns:** The JSON-RPC response object, list of responses, or None if no response.

### notify

```python
async def notify(*calls: RpcCall[Any, Any]) -> None
```

Key: `webcompy.rpc._contracts:notify` · Exports: `from webcompy.rpc import notify`

Send JSON-RPC notifications for the given calls without waiting.

**Args:**

- `*calls`: RPC calls created from the same transport instance.

**Raises:**

- `RuntimeError`: If any call was already awaited.
- `RpcError`: If the calls are invalid or use different transports.

### Procedure

```python
class Procedure:
    def __init__(self, name: str, params_type: type[P], result_type: type[R]) -> None
```

Key: `webcompy.rpc._contracts:Procedure` · Exports: `from webcompy.rpc import Procedure`

Declaration of a request/response RPC method.

Calling a procedure with a transport and parameters builds an awaitable `RpcCall`.

**Args:**

- `name`: Name of the RPC method.
- `params_type`: Dataclass type of the request parameters.
- `result_type`: Dataclass type of the response.

**Attributes:**

- `name`: Name this declaration was created with.
- `params_type`: Dataclass type of the request parameters.
- `result_type`: Dataclass type of the response.

#### Members

**`name`** (property)

```python
@property
def name(self) -> str
```

The RPC method name.

**Returns:** The name this declaration was created with.

**`params_type`** (property)

```python
@property
def params_type(self) -> type[P]
```

The dataclass type of the request parameters.

**Returns:** The parameters dataclass type.

**`result_type`** (property)

```python
@property
def result_type(self) -> type[R]
```

The dataclass type of the response.

**Returns:** The result dataclass type.

### ProcedureRegistry

```python
class ProcedureRegistry:
    def __init__(self, *, base_url: str = '/') -> None
```

Key: `webcompy.rpc._registry:ProcedureRegistry` · Exports: `from webcompy.rpc import ProcedureRegistry`

Registry of RPC procedures and subscriptions for an application.

**Args:**

- `base_url`: Base URL path used to compute the HTTP endpoint.

**Attributes:**

- `path`: The absolute URL path serving the RPC endpoint.
- `endpoint_url`: The base URL joined with the endpoint path.
- `has_procedures`: `True` when at least one procedure or subscription is registered.
- `meta_encoders`: Mapping of Python types to `(tag, encoder)` pairs.
- `meta_decoders`: Mapping of meta tags to decoder callables.

#### Members

**`bind`** (method)

```python
def bind(self, contract: Any, impl: Callable[..., Any] | None = None) -> Any
```

Register an implementation for an RPC contract.

**Args:**

- `contract`: A `Procedure`, `StreamingProcedure`, or `Subscription` declaring the contract.
- `impl`: The implementation function, or `None` to use as a decorator factory.

**Returns:** `None` when binding directly, or a decorator that registers `impl` when called without one.

**Raises:**

- `TypeError`: If `contract` is not a recognized RPC contract type.
- `WebComPyException`: If the implementation does not satisfy the contract's requirements.

**`endpoint_url`** (property)

```python
@property
def endpoint_url(self) -> str
```

The full RPC endpoint URL.

**Returns:** The base URL joined with the endpoint path.

**`get`** (method)

```python
def get(self, name: str) -> ProcedureInfo | None
```

Return the registered procedure with the given name.

**Args:**

- `name`: Name of the procedure.

**Returns:** The `ProcedureInfo` for `name`, or `None` if unknown.

**`get_subscription`** (method)

```python
def get_subscription(self, name: str) -> SubscriptionInfo | None
```

Return the registered subscription with the given name.

**Args:**

- `name`: Name of the subscription.

**Returns:** The `SubscriptionInfo` for `name`, or `None` if unknown.

**`has_procedures`** (property)

```python
@property
def has_procedures(self) -> bool
```

Whether any procedure or subscription is registered.

**Returns:** `True` if at least one procedure or subscription is registered.

**`is_known_meta_tag`** (method)

```python
def is_known_meta_tag(self, tag: str) -> bool
```

Whether a meta tag is builtin or registered.

**Args:**

- `tag`: The meta tag to check.

**Returns:** `True` if `tag` is a builtin meta tag or a registered type tag.

**`meta_decoders`** (property)

```python
@property
def meta_decoders(self) -> dict[str, Callable[[Any], Any]]
```

The registered type decoders.

**Returns:** A mapping from meta tags to decoder callables.

**`meta_encoders`** (property)

```python
@property
def meta_encoders(self) -> dict[type, tuple[str, Callable[[Any], Any]]]
```

The registered type encoders.

**Returns:** A mapping from custom types to `(tag, encoder)` pairs.

**`next_id`** (method)

```python
def next_id(self) -> int
```

Return the next monotonic JSON-RPC request id.

**Returns:** The next available request id.

**`path`** (property)

```python
@property
def path(self) -> str
```

The RPC endpoint path.

**Returns:** The absolute URL path serving the RPC endpoint.

**`register_type_handler`** (method)

```python
def register_type_handler(
    self,
    cls: type,
    encoder: Callable[[Any], Any],
    decoder: Callable[[Any], Any],
) -> None
```

Register a custom codec for RPC parameter and result values.

**Args:**

- `cls`: Custom type handled by this codec.
- `encoder`: Converts an instance of `cls` to a JSON-serializable value.
- `decoder`: Restores an instance of `cls` from the encoded value.

**`set_path`** (method)

```python
def set_path(self, path: str) -> None
```

Set the RPC endpoint path.

**Args:**

- `path`: An absolute, non-root URL path.

**Raises:**

- `WebComPyException`: If `path` is not an absolute non-root path.

### RpcBatchEntry

```python
class RpcBatchEntry:
    method: str
    params: Any
    result_type: Any
```

Key: `webcompy.rpc._middleware:RpcBatchEntry` · Exports: `from webcompy.rpc import RpcBatchEntry`

One procedure invocation inside a batch dispatched through middleware.

**Attributes:**

- `method`: RPC method name.
- `params`: Typed parameters before encoding; middleware MAY replace.
- `result_type`: Type the result is deserialized as.

### RpcCall

```python
class RpcCall:
    def __init__(
        self,
        name: str,
        params: P,
        result_type: type[R],
        transport: RpcTransport,
    ) -> None
```

Key: `webcompy.rpc._contracts:RpcCall` · Exports: `from webcompy.rpc import RpcCall`

An awaitable describing one typed JSON-RPC call.

Awaiting the instance issues the call through its transport and yields the typed result. Instances are single-use: awaiting one twice, or passing the same instance to a batch twice, raises `RuntimeError`.

**Args:**

- `name`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: Type the result is deserialized as.
- `transport`: Transport executing the call.

### RpcContext

```python
class RpcContext:
    method: str = ''
    params: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    result_type: Any = None
    is_batch: bool = False
    batch_entries: list[RpcBatchEntry] | None = None
```

Key: `webcompy.rpc._middleware:RpcContext` · Exports: `from webcompy.rpc import RpcContext`

Mutable view of an outgoing JSON-RPC operation handled by middleware.

For single calls `method`/`params`/`result_type` describe the operation and `is_batch` is `False`. For batch dispatches `is_batch` is `True`, `method` is empty, and `batch_entries` lists every invocation in order; middleware MAY replace any entry's `params` before the envelopes are encoded. `headers` starts empty and is merged onto the fixed transport headers.

**Args:**

- `method`: RPC method name (empty for batches).
- `params`: Typed parameters before encoding.
- `headers`: Extra request headers contributed by middleware.
- `result_type`: Type the result is deserialized as.
- `is_batch`: Whether this context wraps a batch dispatch.
- `batch_entries`: Per-invocation view when `is_batch` is `True`.

**Attributes:**

- `method`: RPC method name (empty for batches).
- `params`: Typed parameters before encoding.
- `headers`: Extra request headers contributed by middleware.
- `result_type`: Type the result is deserialized as.
- `is_batch`: Whether this context wraps a batch dispatch.
- `batch_entries`: Per-invocation view when `is_batch` is `True`.

### RpcError

```python
class RpcError(WebComPyException):
    def __init__(self, code: int, message: str, data: Any = None) -> None
```

Key: `webcompy.rpc._errors:RpcError` · Exports: `from webcompy.rpc import RpcError`

A JSON-RPC error returned by the server or raised by the client.

**Args:**

- `code`: JSON-RPC error code, e.g. `SERVER_ERROR`.
- `message`: Human-readable error message.
- `data`: Optional error payload supplied by the server.

**Attributes:**

- `code`: JSON-RPC error code carried by the error.
- `message`: Human-readable error message.
- `data`: Optional error payload; `None` when absent.

### RpcHttpClient

```python
class RpcHttpClient:
    def __init__(self) -> None
```

Key: `webcompy.rpc._contracts:RpcHttpClient` · Exports: `from webcompy.rpc import RpcHttpClient`

JSON-RPC transport dispatching calls over HTTP.

Streams are delivered over SSE; subscriptions are not supported and always raise `RpcError`.

#### Members

**`call`** (async_method)

```python
async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any
```

Perform a request/response JSON-RPC call over HTTP.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize the result as this type.

**Returns:** The method result.

**`notify`** (async_method)

```python
async def notify(self, method: str, params: Any = None) -> None
```

Send a JSON-RPC notification over HTTP.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.

**`stream`** (method)

```python
def stream(
    self,
    method: str,
    params: Any = None,
    *,
    result_type: Any = None,
) -> RpcStream[Any]
```

Start a finite streaming JSON-RPC call over HTTP.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize each item as this type.

**Returns:** A `RpcStream` of items from the server.

**`subscribe`** (method)

```python
def subscribe(self, method: str, params: Any = None, *, event_type: Any = None) -> Any
```

Unavailable on the HTTP transport.

**Args:**

- `method`: Name of the subscription method.
- `params`: Parameters object for the subscription.
- `event_type`: Type of the expected events.

**Returns:** Never; this method always raises.

**Raises:**

- `RpcError`: Always, because subscriptions require a WebSocket.

### RpcMiddleware

```python
RpcMiddleware: TypeAlias = Callable[[RpcContext, RpcNext], Awaitable[Any]]
```

Key: `webcompy.rpc._middleware:RpcMiddleware` · Exports: `from webcompy.rpc import RpcMiddleware`

Async callable that wraps one HTTP JSON-RPC operation.

Receives the typed procedure context and a `next` handle whose synthetic `response` short-circuits the wire while keeping schema validation.

### RpcMiddlewareRegistry

```python
class RpcMiddlewareRegistry:
    def __init__(self) -> None
```

Key: `webcompy.rpc._middleware:RpcMiddlewareRegistry` · Exports: `from webcompy.rpc import RpcMiddlewareRegistry`

Ordered, additively mutated collection of RPC middlewares.

One instance is provided per render context under `RPC_MIDDLEWARE_KEY`. Middlewares are consulted at each operation, so registrations made after installation take effect on subsequent calls.

#### Members

**`middlewares`** (property)

```python
@property
def middlewares(self) -> tuple[RpcMiddleware, ...]
```

Snapshot of registered middlewares in registration order.

**Returns:** Middlewares ordered so index `0` is the outermost layer.

**`use`** (method)

```python
def use(self, middleware: RpcMiddleware) -> None
```

Append *middleware* to the registry.

**Args:**

- `middleware`: Async callable invoked with the operation context and a `next` callable.

### RpcStream

```python
class RpcStream(Generic[T]):
    def __init__(
        self,
        *,
        cancel: Callable[[], None] | None = None,
        decode: Callable[[Any, Any], T] | None = None,
        closed: bool = False,
    ) -> None
```

Key: `webcompy.rpc._stream:RpcStream` · Exports: `from webcompy.rpc import RpcStream`

An async iterator over a finite, call-scoped RPC stream.

`.state` is a `Signal[RpcStreamState]`: `OPEN` while the stream is active, `CLOSED` after normal exhaustion or explicit close, and `FAILED` when the stream failed. `.close()` is idempotent, terminates the stream, and cancels the underlying transport. Streams created inside component setup are closed automatically on component destroy.

**Args:**

- `cancel`: Optional callback cancelling the underlying transport.
- `decode`: Optional two-argument function decoding each raw item.
- `closed`: When `True`, the stream starts already closed.

**Attributes:**

- `state`: `Signal[RpcStreamState]` — `OPEN` while active, `CLOSED` after normal exhaustion or explicit close, and `FAILED` when the stream failed.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

Terminate the stream and cancel the underlying transport.

### RpcStreamState

```python
class RpcStreamState(Enum)
```

Key: `webcompy.rpc._stream:RpcStreamState` · Exports: `from webcompy.rpc import RpcStreamState`

Lifecycle stages of an `RpcStream`.

`OPEN` while active, `CLOSED` after normal exhaustion or explicit closure, and `FAILED` when the stream failed.

### RpcSubscription

```python
class RpcSubscription(Generic[E]):
    def __init__(
        self,
        client: RpcWsClient,
        method: str,
        params: Any,
        event_type: type[E] | None,
        *,
        closed: bool = False,
    ) -> None
```

Key: `webcompy.rpc._ws_client:RpcSubscription` · Exports: `from webcompy import RpcSubscription`, `from webcompy.rpc import RpcSubscription`

An async iterator of server events for one subscription.

`.state` is a `Signal[RpcSubscriptionState]`: `PENDING` until the server confirms, `ACTIVE` while events flow, `RESYNC_REQUIRED` when the server reports the replay buffer overflowed (the caller should refetch authoritative state and resubscribe), and `CLOSED` after unsubscribe or close. `.last_cursor` is a `Signal[int | None]` tracking the last received cursor, used for automatic rejoin after reconnects.

**Args:**

- `client`: The client this subscription belongs to.
- `method`: Name of the subscription method.
- `params`: Parameters object for the subscription.
- `event_type`: When given, deserialize events as this type.
- `closed`: When `True`, the subscription starts already closed.

**Attributes:**

- `state`: `Signal[RpcSubscriptionState]` tracking the subscription lifecycle.
- `last_cursor`: `Signal[int | None]` tracking the last received cursor, used for automatic rejoin after reconnects.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

End the subscription and detach it from the client.

### RpcSubscriptionState

```python
class RpcSubscriptionState(Enum)
```

Key: `webcompy.rpc._ws_client:RpcSubscriptionState` · Exports: `from webcompy import RpcSubscriptionState`, `from webcompy.rpc import RpcSubscriptionState`

Lifecycle stages of an `RpcSubscription`.

`PENDING` until the server confirms, `ACTIVE` while events flow, `RESYNC_REQUIRED` when the server's replay buffer overflowed, and `CLOSED` after unsubscribe or close.

### RpcTransport

```python
class RpcTransport(Protocol)
```

Key: `webcompy.rpc._contracts:RpcTransport` · Exports: `from webcompy.rpc import RpcTransport`

Transport-neutral JSON-RPC operations implemented by RPC clients.

Contract classes invoke these methods to issue calls, notifications, streams, and subscriptions through whichever client they are bound to.

#### Members

**`call`** (async_method)

```python
async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any
```

Perform a request/response JSON-RPC call.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize the result as this type.

**Returns:** The method result.

**`notify`** (async_method)

```python
async def notify(self, method: str, params: Any = None) -> None
```

Send a JSON-RPC notification without waiting for a result.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.

**`stream`** (method)

```python
def stream(self, method: str, params: Any = None, *, result_type: Any = None) -> Any
```

Start a finite streaming JSON-RPC call.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize each item as this type.

**Returns:** A stream of items from the server.

**`subscribe`** (method)

```python
def subscribe(self, method: str, params: Any = None, *, event_type: Any = None) -> Any
```

Subscribe to a server-side event stream.

**Args:**

- `method`: Name of the subscription method.
- `params`: Parameters object for the subscription.
- `event_type`: When given, deserialize each event as this type.

**Returns:** A subscription yielding server events.

### RpcWsClient

```python
class RpcWsClient:
    def __init__(
        self,
        url: str | None = None,
        *,
        heartbeat_interval: float | None = 30.0,
        heartbeat_timeout: float = 10.0,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
        reconnect_max_attempts: int | None = None,
        max_queue: int | None = None,
    ) -> None
```

Key: `webcompy.rpc._ws_client:RpcWsClient` · Exports: `from webcompy import RpcWsClient`, `from webcompy.rpc import RpcWsClient`

JSON-RPC 2.0 over a shared, auto-reconnecting WebSocket.

Calls correlate responses by `id` and raise `RpcError` on error or disconnect (never silently retried). `subscribe` returns an `RpcSubscription` async iterator that automatically rejoins with the last received cursor after reconnects. Optional application-level heartbeat detects dead connections and forces an abnormal close so the reconnect loop engages. Browser-runtime only: outside the browser a warning is emitted and no socket work is performed.

Create the client inside component setup so its subscriptions and the shared socket are released automatically on component destroy. When the client is held outside a component (e.g. a module-level service), call `close()` explicitly to release the connection.

**Args:**

- `url`: WebSocket endpoint URL. Defaults to the app's RPC endpoint.
- `heartbeat_interval`: Seconds between application-level pings, or `None` to disable the heartbeat. Defaults to 30.
- `heartbeat_timeout`: Seconds without any frame after which the connection is force-closed. Defaults to 10.
- `reconnect_base_delay`: Base delay in seconds before reconnecting. Defaults to 1.
- `reconnect_max_delay`: Maximum delay in seconds before reconnecting. Defaults to 30.
- `reconnect_max_attempts`: Optional bound on the number of reconnection attempts.
- `max_queue`: Optional bound on the per-subscription message queue.

**Attributes:**

- `state`: Signal holding the `ConnectionState` of the underlying WebSocket connection.
- `last_error`: Signal holding the most recent decode or protocol error, or `None`.

#### Members

**`call`** (async_method)

```python
async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any
```

Perform a request/response JSON-RPC call over the WebSocket.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize the result as this type.

**Returns:** The method result.

**Raises:**

- `RpcError`: If the client is unusable or the connection is not open.

**`close`** (method)

```python
def close(self) -> None
```

Close the client and all its streams and subscriptions.

**`last_error`** (property)

```python
@property
def last_error(self) -> Signal[Exception | None]
```

The most recent decode or protocol error, if any.

**Returns:** A signal holding the last error, or `None`.

**`notify`** (async_method)

```python
async def notify(self, method: str, params: Any = None) -> None
```

Send a JSON-RPC notification over the WebSocket.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.

**Raises:**

- `RpcError`: If the client is unusable or the connection is not open.

**`state`** (property)

```python
@property
def state(self) -> Signal[ConnectionState]
```

The state of the underlying WebSocket connection.

**Returns:** A signal holding `ConnectionState`.

**`stream`** (method)

```python
def stream(
    self,
    method: str,
    params: Any = None,
    *,
    result_type: Any = None,
) -> RpcStream[Any]
```

Start a finite streaming JSON-RPC call over the WebSocket.

**Args:**

- `method`: Name of the RPC method.
- `params`: Parameters object for the method.
- `result_type`: When given, deserialize each item as this type.

**Returns:** An `RpcStream` items from the server. Outside the browser an already closed stream is returned.

**Raises:**

- `RpcError`: If the client is unusable or the connection is not open.

**`subscribe`** (method)

```python
def subscribe(
    self,
    method: str,
    params: Any = None,
    *,
    event_type: type[E] | None = None,
) -> RpcSubscription[E]
```

Subscribe to server-side events over the WebSocket.

**Args:**

- `method`: Name of the subscription method.
- `params`: Parameters object for the subscription.
- `event_type`: When given, deserialize events as this type.

**Returns:** An `RpcSubscription` yielding the server's events.

### StreamingProcedure

```python
class StreamingProcedure:
    def __init__(self, name: str, params_type: type[P], result_type: type[T]) -> None
```

Key: `webcompy.rpc._contracts:StreamingProcedure` · Exports: `from webcompy.rpc import StreamingProcedure`

Declaration of a finite streaming RPC method.

Calling a streaming procedure with a transport and parameters starts a call-scoped `RpcStream`.

**Args:**

- `name`: Name of the RPC method.
- `params_type`: Dataclass type of the request parameters.
- `result_type`: Dataclass type of each stream item.

**Attributes:**

- `name`: Name this declaration was created with.
- `params_type`: Dataclass type of the request parameters.
- `result_type`: Dataclass type of each stream item.

#### Members

**`name`** (property)

```python
@property
def name(self) -> str
```

The RPC method name.

**Returns:** The name this declaration was created with.

**`params_type`** (property)

```python
@property
def params_type(self) -> type[P]
```

The dataclass type of the request parameters.

**Returns:** The parameters dataclass type.

**`result_type`** (property)

```python
@property
def result_type(self) -> type[T]
```

The dataclass type of each stream item.

**Returns:** The item dataclass type.

### Subscription

```python
class Subscription:
    def __init__(
        self,
        name: str,
        params_type: type[P],
        event_type: type[E],
        replay_size: int = 256,
    ) -> None
```

Key: `webcompy.rpc._contracts:Subscription` · Exports: `from webcompy.rpc import Subscription`

Declaration of a server-side event subscription.

Calling a subscription with a transport and parameters starts an `RpcSubscription` yielding typed events.

**Args:**

- `name`: Name of the subscription method.
- `params_type`: Dataclass type of the request parameters.
- `event_type`: Dataclass type of each event.
- `replay_size`: Suggested number of events the server replays to a rejoining client. Defaults to 256.

**Raises:**

- `ValueError`: If `replay_size` is less than 1.

**Attributes:**

- `name`: Name this declaration was created with.
- `params_type`: Dataclass type of the request parameters.
- `event_type`: Dataclass type of each event.
- `replay_size`: Suggested number of events the server replays to a rejoining client.

#### Members

**`event_type`** (property)

```python
@property
def event_type(self) -> type[E]
```

The dataclass type of each event.

**Returns:** The event dataclass type.

**`name`** (property)

```python
@property
def name(self) -> str
```

The RPC method name.

**Returns:** The name this declaration was created with.

**`params_type`** (property)

```python
@property
def params_type(self) -> type[P]
```

The dataclass type of the request parameters.

**Returns:** The parameters dataclass type.

**`replay_size`** (property)

```python
@property
def replay_size(self) -> int
```

The suggested event replay size for rejoin.

**Returns:** The configured replay size.

## Hydration & State Transfer

### apply_transfer_meta

```python
def apply_transfer_meta(
    data: Any,
    meta: Mapping[str, str] | None,
    *,
    strict: bool = False,
    decoders: Mapping[str, Callable[[Any], Any]] | None = None,
) -> Any
```

Key: `webcompy.hydration._transfer_meta:apply_transfer_meta` · Exports: `from webcompy.hydration import apply_transfer_meta`

Apply transfer meta type tags to decoded JSON data.

Walks the meta map in order of path depth and decodes each tagged value, rebuilding the structure without mutating `data`.

**Args:**

- `data`: JSON-decoded response value.
- `meta`: Map of JSON Pointer paths to type tags, or `None` for a no-op.
- `strict`: Whether unknown tags raise instead of warning.
- `decoders`: Optional mapping of type tags to decoder callables, merged over the built-in decoders.

**Returns:** The decoded value with tagged entries converted.

**Raises:**

- `ValueError`: If `meta` is not a mapping or a meta path does not exist in `data`.

### decode

```python
def decode(value: Any) -> Any
```

Key: `webcompy.hydration._codec:decode` · Exports: `from webcompy.hydration import decode`

Decode an encoded structure back into Python values.

Type-tagged dicts are decoded through the registered handlers; plain dicts and lists are decoded recursively.

**Args:**

- `value`: Encoded JSON-compatible value.

**Returns:** The decoded Python value.

### encode

```python
def encode(
    value: Any,
    _seen: set[int] | None = None,
    _flag: _FailureFlag | None = None,
) -> Any
```

Key: `webcompy.hydration._codec:encode` · Exports: `from webcompy.hydration import encode`

Encode a value into a JSON-compatible structure with type tags.

Values covered by JSON pass through unchanged; dicts and lists are encoded recursively; supported Python types become `__webcompy_` tagged envelopes. Unencodable values are dropped and reported via logging.

**Args:**

- `value`: Value to encode.
- `_seen`: Object ids currently being encoded, for cycle detection.
- `_flag`: Failure flag marking the payload as lossy when a value cannot be encoded.

**Returns:** A JSON-compatible representation of `value`.

### encode_with_meta

```python
def encode_with_meta(
    value: Any,
    *,
    type_handlers: Mapping[type, tuple[str, Callable[[Any], Any]]] | None = None,
) -> tuple[Any, dict[str, str]]
```

Key: `webcompy.hydration._transfer_meta:encode_with_meta` · Exports: `from webcompy.hydration import encode_with_meta`

Encode a value for JSON alongside a map of type-tag metadata.

Non-JSON types are converted into JSON-friendly forms, and each conversion is recorded as a JSON Pointer path-to-type-tag entry in the returned metadata map.

**Args:**

- `value`: Value to encode.
- `type_handlers`: Optional mapping of types to `(tag, encoder)` pairs for custom types.

**Returns:** A tuple of the encoded JSON-friendly value and the metadata map of JSON Pointer paths to type tags.

### has_resolved_data

```python
def has_resolved_data(component_id: str) -> bool
```

Key: `webcompy.hydration:has_resolved_data` · Exports: `from webcompy.hydration import has_resolved_data`

Return whether hydration payload data exists for a component.

**Args:**

- `component_id`: Transfer ID of the component.

**Returns:** `True` when the injected hydration payload contains data for `component_id`.

### HydrationMismatchRecord

```python
class HydrationMismatchRecord:
    kind: MismatchKind
    expected: Any
    actual: Any
    component_id: str = ''
```

Key: `webcompy.hydration._report:HydrationMismatchRecord` · Exports: `from webcompy.hydration import HydrationMismatchRecord`

One server/client hydration mismatch observation.

**Args:**

- `kind`: Kind of mismatch observed.
- `expected`: Server-rendered value the client expected.
- `actual`: Value actually found in the client DOM.
- `component_id`: Component the mismatch occurred in, when known.

**Attributes:**

- `kind`: Kind of mismatch observed.
- `expected`: Server-rendered value the client expected.
- `actual`: Value actually found in the client DOM.
- `component_id`: Component the mismatch occurred in, when known.

### merge_meta_into_body

```python
def merge_meta_into_body(json_data: Any, meta: Mapping[str, str]) -> dict[str, Any]
```

Key: `webcompy.hydration._transfer_meta:merge_meta_into_body` · Exports: `from webcompy.hydration import merge_meta_into_body`

Merge the transfer meta map into a JSON response body.

Body mode requires a top-level JSON object so the meta map can be embedded under `META_BODY_KEY`.

**Args:**

- `json_data`: Response body to attach the meta map to.
- `meta`: Map of JSON Pointer paths to type tags.

**Returns:** A dict combining `json_data` with the embedded meta map.

**Raises:**

- `WebComPyException`: If `json_data` is not a dict.

### META_BODY_KEY

```python
META_BODY_KEY = '__webcompy_transfer_meta__'
```

Key: `webcompy.hydration._transfer_meta:META_BODY_KEY` · Exports: `from webcompy.hydration import META_BODY_KEY`

Body key carrying the transfer meta map in body mode.

### META_HEADER_NAME

```python
META_HEADER_NAME = 'X-WebComPy-Transfer-Meta'
```

Key: `webcompy.hydration._transfer_meta:META_HEADER_NAME` · Exports: `from webcompy.hydration import META_HEADER_NAME`

HTTP header carrying the transfer meta map in header mode.

### record_mismatch

```python
def record_mismatch(
    kind: MismatchKind,
    expected: Any,
    actual: Any,
    component_id: str = '',
) -> None
```

Key: `webcompy.hydration._report:record_mismatch` · Exports: `from webcompy.hydration import record_mismatch`

Record a hydration mismatch with the active reporter, if any.

Mismatches observed outside an active hydration window are ignored.

**Args:**

- `kind`: Kind of mismatch observed.
- `expected`: Server-rendered value the client expected.
- `actual`: Value actually found in the client DOM.
- `component_id`: Component the mismatch occurred in, when known.

### register_type_handler

```python
def register_type_handler(
    cls: type,
    encoder: Callable[[Any], Any],
    decoder: Callable[[Any], Any],
) -> None
```

Key: `webcompy.hydration._codec:register_type_handler` · Exports: `from webcompy.hydration import register_type_handler`

Register a custom encoder/decoder pair for a type in the transfer codec.

**Args:**

- `cls`: Type whose instances the handlers apply to.
- `encoder`: Callable turning an instance into an encodable payload.
- `decoder`: Callable turning the encoded payload back into a value.

## Port Interfaces & Server Implementations

### add_fetch_middleware

```python
def add_fetch_middleware(middleware: FetchMiddleware) -> None
```

Key: `webcompy.ports._middleware:add_fetch_middleware` · Exports: `from webcompy.ports import add_fetch_middleware`

Append *middleware* to the active fetch middleware registry.

The call is threaded through the current DI scope. Registrations remain visible to subsequent fetch operations (including streaming); ordering is `middlewares[0]` outermost.

**Args:**

- `middleware`: Callable invoked with the request view and a `next` handle.

**Raises:**

- `RuntimeError`: If no registry is available in the current scope (no active render context).

### ASYNC_SCHEDULER_PORT_KEY

```python
ASYNC_SCHEDULER_PORT_KEY = InjectKey[AsyncSchedulerPort]('webcompy-port-async-scheduler')
```

Key: `webcompy.ports._keys:ASYNC_SCHEDULER_PORT_KEY` · Exports: `from webcompy.ports import ASYNC_SCHEDULER_PORT_KEY`

Injection key for the `AsyncSchedulerPort` implementation.

### AsyncSchedulerPort

```python
class AsyncSchedulerPort(ABC)
```

Key: `webcompy.ports._async_scheduler:AsyncSchedulerPort` · Exports: `from webcompy.ports import AsyncSchedulerPort`

Scheduling and draining surface for background and render tasks.

Implementations wrap the `asyncio` event loop of the current runtime. Browser implementations run tasks fire-and-forget on the persistent page event loop; server implementations additionally keep a registry so rendering can await pending work before the render context is disposed.

#### Members

**`await_pending`** (async_method)

```python
async def await_pending(self, *, only_render: bool = False) -> None
```

Await all currently scheduled tasks.

**Args:**

- `only_render`: When true, only await tasks scheduled with `schedule(coro, render=True)`. Tasks scheduled without the flag SHALL NOT block the call.

**`schedule`** (method)

```python
def schedule(
    self,
    coro: Coroutine[Any, Any, Any],
    *,
    render: bool = False,
) -> asyncio.Task[Any]
```

Schedule a coroutine as an `asyncio.Task`.

**Args:**

- `coro`: The coroutine to schedule.
- `render`: Whether the task is a hydration/render task that must complete before the browser hydration reveal (awaitable via `await_pending(only_render=True)`).

**Returns:** The `asyncio.Task` wrapping the scheduled coroutine.

### COOKIE_PORT_KEY

```python
COOKIE_PORT_KEY = InjectKey[CookiePort]('webcompy-port-cookie')
```

Key: `webcompy.ports._keys:COOKIE_PORT_KEY` · Exports: `from webcompy.ports import COOKIE_PORT_KEY`

Injection key for the `CookiePort` implementation.

### CookiePort

```python
class CookiePort(ABC)
```

Key: `webcompy.ports._cookie:CookiePort` · Exports: `from webcompy.ports import CookiePort`

Cookie read/write surface.

Browser implementations serialize to and parse from `document.cookie`; server implementations may operate on plain stores.

#### Members

**`delete`** (method)

```python
def delete(self, name: str, path: str = '/') -> None
```

Delete a cookie by setting its `max-age` to 0.

**Args:**

- `name`: Cookie name.
- `path`: Path scope of the cookie to delete (must match `set`).

**`get`** (method)

```python
def get(self, name: str) -> str | None
```

Read a single cookie value by name.

**Args:**

- `name`: Cookie name.

**Returns:** Cookie value, or `None` if not set.

**`get_all`** (method)

```python
def get_all(self) -> dict[str, str]
```

Read all cookies as a dict.

**Returns:** Mapping of cookie names to values.

**`set`** (method)

```python
def set(
    self,
    name: str,
    value: str,
    *,
    max_age: int | None = None,
    expires: datetime | None = None,
    path: str = '/',
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str | None = None,
) -> None
```

Set a cookie.

**Args:**

- `name`: Cookie name.
- `value`: Cookie value.
- `max_age`: Lifetime in seconds.
- `expires`: Absolute expiry timestamp (converted to a UTC date string).
- `path`: URL path scope (default `"/"`).
- `domain`: Domain scope for the cookie.
- `secure`: Restrict to HTTPS.
- `httponly`: Prevent JavaScript access via `document.cookie`.
- `samesite`: SameSite attribute (`"Strict"`, `"Lax"`, `"None"`).

### CUSTOM_ELEMENT_PORT_KEY

```python
CUSTOM_ELEMENT_PORT_KEY = InjectKey[CustomElementPort]('webcompy-port-custom-element')
```

Key: `webcompy.ports._keys:CUSTOM_ELEMENT_PORT_KEY` · Exports: `from webcompy.ports import CUSTOM_ELEMENT_PORT_KEY`

Injection key for the `CustomElementPort` implementation.

### CustomElementPort

```python
class CustomElementPort(ABC)
```

Key: `webcompy.ports._custom_element:CustomElementPort` · Exports: `from webcompy.ports import CustomElementPort`

Port for custom-element registration and per-node binding.

The browser implementation defines `HTMLElement` subclasses and forwards lifecycle and attribute reactions to the callables supplied at `bind()` time. Server and testing implementations no-op or record instead.

#### Members

**`bind`** (method)

```python
def bind(
    self,
    node: DOMNode,
    *,
    observed_attributes: tuple[str, ...],
    on_connected: Callable[[], None],
    on_disconnected: Callable[[], None],
    on_attribute_changed: Callable[[str, str | None], None],
) -> CustomElementBinding
```

Bind a node to custom-element reaction callbacks.

**Args:**

- `node`: DOM node to bind.
- `observed_attributes`: Attribute names whose changes are reported through `on_attribute_changed`.
- `on_connected`: Called when the node becomes connected.
- `on_disconnected`: Called when the node is disconnected.
- `on_attribute_changed`: Called with `(attribute_name, new_value)`; `new_value` is `None` when the attribute was removed.

**Returns:** A `CustomElementBinding` handle that releases the FFI proxies on `dispose()`.

**`ensure_defined`** (method)

```python
def ensure_defined(
    self,
    name: str,
    observed_attributes: tuple[str, ...],
    definition_key: str,
) -> None
```

Ensure `name` is defined in the document's custom-element registry.

**Args:**

- `name`: Custom element name to define.
- `observed_attributes`: Attribute names observed by the generated element class and forwarded to bound reactions.
- `definition_key`: Key identifying the WebComPy definition, used to detect incompatible redefinitions.

**`is_document_connected`** (method)

```python
def is_document_connected(self, node: DOMNode) -> bool
```

Return whether `node` is currently connected to a document.

**Args:**

- `node`: DOM node to inspect.

**Returns:** True if `node` is connected to a document, False otherwise.

### DOM_PORT_KEY

```python
DOM_PORT_KEY = InjectKey[DOMPort]('webcompy-port-dom')
```

Key: `webcompy.ports._keys:DOM_PORT_KEY` · Exports: `from webcompy.ports import DOM_PORT_KEY`

Injection key for the `DOMPort` implementation.

### DOMEvent

```python
class DOMEvent(Protocol)
```

Key: `webcompy.ports._dom:DOMEvent` · Exports: `from webcompy.elements import DOMEvent`

Event abstraction mirroring the read-only surface of a native DOM event.

**Attributes:**

- `bubbles`: Whether the event bubbles up through the DOM tree.
- `cancelable`: Whether the event can be canceled via `preventDefault()`.
- `currentTarget`: Node whose listener is currently processing the event.
- `defaultPrevented`: Whether `preventDefault()` has already been called.
- `eventPhase`: Numeric phase the event flow is in (capturing, at target, or bubbling).
- `target`: Node the event was originally dispatched to, or `None`.
- `timeStamp`: Time (in milliseconds) at which the event was created.
- `type`: Event type name (e.g. `"click"`).

#### Members

**`bubbles`** (property)

```python
@property
def bubbles(self) -> bool
```

Whether the event bubbles up through the DOM tree.

**`cancelable`** (property)

```python
@property
def cancelable(self) -> bool
```

Whether the event can be canceled via `preventDefault()`.

**`currentTarget`** (property)

```python
@property
def currentTarget(self) -> DOMNode | None
```

Node whose listener is currently processing the event.

**`defaultPrevented`** (property)

```python
@property
def defaultPrevented(self) -> bool
```

Whether `preventDefault()` has already been called.

**`eventPhase`** (property)

```python
@property
def eventPhase(self) -> int
```

Numeric phase the event flow is in (capturing, at target, or bubbling).

**`preventDefault`** (method)

```python
def preventDefault(self) -> None
```

Cancel the event if it is cancelable.

**`stopPropagation`** (method)

```python
def stopPropagation(self) -> None
```

Prevent further propagation of the event in the DOM tree.

**`target`** (property)

```python
@property
def target(self) -> DOMNode | None
```

Node the event was originally dispatched to.

**`timeStamp`** (property)

```python
@property
def timeStamp(self) -> int
```

Time (in milliseconds) at which the event was created.

**`type`** (property)

```python
@property
def type(self) -> str
```

Event type name (e.g. `"click"`).

### DOMNode

```python
class DOMNode(Protocol)
```

Key: `webcompy.ports._dom:DOMNode` · Exports: `from webcompy.elements import DOMNode`, `from webcompy.ports import DOMNode`

Node abstraction mirroring the DOM interfaces the framework consumes.

**Attributes:**

- `__webcompy_node__`: Marker flag identifying nodes created by the virtual DOM layer.
- `__webcompy_prerendered_node__`: Marker flag identifying nodes adopted from pre-rendered (SSG/SSR) markup.

#### Members

**`addEventListener`** (method)

```python
def addEventListener(
    self,
    event_type: str,
    handler: Any,
    options_or_capture: Any = False,
) -> None
```

Register an event listener on this node.

**Args:**

- `event_type`: Event type name (e.g. `"click"`).
- `handler`: Callback invoked when the event fires.
- `options_or_capture`: Listener options object or capture boolean (default `False`).

**`appendChild`** (method)

```python
def appendChild(self, child: DOMNode) -> None
```

Append `child` as the last child of this node.

**Args:**

- `child`: Node to append.

**`childNodes`** (property)

```python
@property
def childNodes(self) -> DOMNodeList
```

Live list of this node's child nodes.

**`dispatchEvent`** (method)

```python
def dispatchEvent(self, event: DOMEvent) -> bool
```

Dispatch an event on this node.

**Args:**

- `event`: Event to dispatch.

**Returns:** `False` if the event was canceled via `preventDefault()`.

**`getAttribute`** (method)

```python
def getAttribute(self, name: str) -> str | None
```

Return the value of an attribute.

**Args:**

- `name`: Attribute name.

**Returns:** The attribute value, or `None` if not present.

**`getAttributeNames`** (method)

```python
def getAttributeNames(self) -> list[str]
```

Return the names of all attributes on this node.

**Returns:** List of attribute names.

**`hasAttribute`** (method)

```python
def hasAttribute(self, name: str) -> bool
```

Return whether the attribute exists on this node.

**Args:**

- `name`: Attribute name.

**Returns:** `True` if the attribute is present.

**`insertBefore`** (method)

```python
def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None
```

Insert `new_node` immediately before `ref_node`.

**Args:**

- `new_node`: Node to insert.
- `ref_node`: Reference node the new node is inserted before.

**`nodeName`** (property)

```python
@property
def nodeName(self) -> str
```

Name of this node (e.g. the tag name of an element).

**`nodeType`** (property)

```python
@property
def nodeType(self) -> int
```

Numeric node type constant of this node.

**`parentNode`** (property)

```python
@property
def parentNode(self) -> DOMNode | None
```

Parent node of this node, or `None` if it has no parent.

**`remove`** (method)

```python
def remove(self) -> None
```

Remove this node from its parent.

**`removeAttribute`** (method)

```python
def removeAttribute(self, name: str) -> None
```

Remove an attribute from this node.

**Args:**

- `name`: Attribute name.

**`removeChild`** (method)

```python
def removeChild(self, child: DOMNode) -> None
```

Remove `child` from this node's children.

**Args:**

- `child`: Child node to remove.

**`removeEventListener`** (method)

```python
def removeEventListener(
    self,
    event_type: str,
    handler: Any,
    options_or_capture: Any = False,
) -> None
```

Remove a previously registered event listener.

**Args:**

- `event_type`: Event type name the listener was registered for.
- `handler`: The callback to remove.
- `options_or_capture`: Listener options object or capture boolean used at registration.

**`replaceChild`** (method)

```python
def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None
```

Replace `old_node` with `new_node`.

**Args:**

- `new_node`: Replacement node.
- `old_node`: Node being replaced.

**`setAttribute`** (method)

```python
def setAttribute(self, name: str, value: str | None) -> None
```

Set an attribute on this node (`None` removes it).

**Args:**

- `name`: Attribute name.
- `value`: Attribute value, or `None` to remove the attribute.

**`textContent`** (property)

```python
@property
def textContent(self) -> str | None
```

Text content of this node and its descendants.

### DOMNodeList

```python
class DOMNodeList:
    def __init__(self, nodes: list[DOMNode]) -> None
```

Key: `webcompy.ports._dom:DOMNodeList` · Exports: `from webcompy.ports import DOMNodeList`

Immutable sequence wrapper over child DOM nodes.

**Args:**

- `nodes`: The child nodes, in document order.

**Attributes:**

- `length`: Number of nodes in the list.

#### Members

**`length`** (property)

```python
@property
def length(self) -> int
```

Number of nodes in the list.

### DOMPort

```python
class DOMPort(ABC)
```

Key: `webcompy.ports._dom:DOMPort` · Exports: `from webcompy.ports import DOMPort`

DOM element construction and document-query surface.

Implementations create real or virtual DOM nodes: the browser port returns live PyScript element proxies, the server port builds virtual DOM trees.

#### Members

**`add_document_event_listener`** (method)

```python
def add_document_event_listener(
    self,
    event_type: str,
    handler: Any,
    *,
    capture: bool = False,
) -> Callable[[], None]
```

Register a document-level event listener via `document.addEventListener`.

**Args:**

- `event_type`: Event name (e.g. `"click"`, `"keydown"`).
- `handler`: Callback invoked when the event fires.
- `capture`: Register the listener for the capture phase instead of bubbling; capture listeners run before the target's own handlers and observe clicks stopped during bubbling.

**Returns:** A cleanup function; call it to remove the listener.

**`create_comment`** (method)

```python
def create_comment(self, data: str) -> DOMNode
```

Create a comment node.

**Args:**

- `data`: Comment data. Callers must supply comment-safe data (no `--` sequence).

**Returns:** A new comment node.

**`create_element`** (method)

```python
def create_element(self, tag: str) -> DOMNode
```

Create an HTML element.

**Args:**

- `tag`: HTML tag name (e.g. `"div"`, `"span"`, `"p"`).

**Returns:** A new DOM element.

**`create_event`** (method)

```python
def create_event(
    self,
    event_type: str,
    *,
    bubbles: bool = False,
    cancelable: bool = False,
) -> DOMEvent
```

Create a DOM event object.

**Args:**

- `event_type`: Event type string (e.g. `"click"`, `"submit"`).
- `bubbles`: Whether the event bubbles up through the DOM.
- `cancelable`: Whether the event can be canceled via `preventDefault()`.

**Returns:** A new DOM event object.

**`create_text_node`** (method)

```python
def create_text_node(self, text: str) -> DOMNode
```

Create a text node.

**Args:**

- `text`: Text content for the node.

**Returns:** A new text node.

**`get_element_by_id`** (method)

```python
def get_element_by_id(self, element_id: str) -> DOMNode | None
```

Retrieve an element by its `id` attribute.

**Args:**

- `element_id`: The element's `id` value.

**Returns:** The matching element, or `None` if not found.

**`query_selector`** (method)

```python
def query_selector(self, selector: str) -> DOMNode | None
```

Query the document for the first element matching a CSS selector.

**Args:**

- `selector`: CSS selector string.

**Returns:** The first matching element, or `None` if none found.

**`query_selector_all`** (method)

```python
def query_selector_all(self, selector: str, *, root: DOMNode | None = None) -> list[DOMNode]
```

Query for all elements matching a CSS selector.

**Args:**

- `selector`: CSS selector string.
- `root`: Optional subtree root to scope the query to. When `None`, the document root is searched.

**Returns:** Matching element nodes in document order.

**`set_title`** (method)

```python
def set_title(self, title: str) -> None
```

Set the document title (`document.title`).

**Args:**

- `title`: New document title.

### EVENT_SOURCE_PORT_KEY

```python
EVENT_SOURCE_PORT_KEY = InjectKey[EventSourcePort]('webcompy-port-event-source')
```

Key: `webcompy.ports._keys:EVENT_SOURCE_PORT_KEY` · Exports: `from webcompy.ports import EVENT_SOURCE_PORT_KEY`

Injection key for the `EventSourcePort` implementation.

### EventSourcePort

```python
class EventSourcePort(ABC)
```

Key: `webcompy.ports._event_source:EventSourcePort` · Exports: `from webcompy.ports import EventSourcePort`

Port for Server-Sent Events connections (callback surface).

Implementations open a connection for the given URL and event types and deliver lifecycle transitions and received events to the supplied callbacks. The returned cleanup callable closes the connection. The port has no component knowledge; all subscriber fan-out is owned by the caller.

#### Members

**`open`** (method)

```python
def open(
    self,
    url: str,
    *,
    events: tuple[str, ...],
    on_open: Callable[[], None],
    on_message: Callable[[str, str, str], None],
    on_error: Callable[[], None],
    on_close: Callable[[], None],
) -> Callable[[], None]
```

Open an SSE connection for `url` and the named `events`.

**Args:**

- `url`: SSE endpoint URL to connect to.
- `events`: Named event types delivered through `on_message`.
- `on_open`: Called when the connection is established.
- `on_message`: Called with `(event_type, data, last_event_id)` for each received event.
- `on_error`: Called when a connection-level error occurs.
- `on_close`: Called when the connection closes.

**Returns:** A cleanup callable closing the underlying connection.

### FETCH_MIDDLEWARE_KEY

```python
FETCH_MIDDLEWARE_KEY = InjectKey[FetchMiddlewareRegistry]('webcompy-fetch-middleware')
```

Key: `webcompy.ports._keys:FETCH_MIDDLEWARE_KEY` · Exports: `from webcompy.ports import FETCH_MIDDLEWARE_KEY`

Injection key for the per-context `FetchMiddlewareRegistry`.

### FETCH_PORT_KEY

```python
FETCH_PORT_KEY = InjectKey[FetchPort]('webcompy-port-fetch')
```

Key: `webcompy.ports._keys:FETCH_PORT_KEY` · Exports: `from webcompy.ports import FETCH_PORT_KEY`

Injection key for the `FetchPort` implementation.

### FetchMiddleware

```python
FetchMiddleware: TypeAlias = ...
```

Key: `webcompy.ports._middleware:FetchMiddleware` · Exports: `from webcompy.ports import FetchMiddleware`

Async callable that wraps one fetch or streaming HTTP request.

Receives the mutable request view and a `next` handle whose synthetic `response` short-circuits the inner port. Middleware at index `0` runs outermost.

### FetchMiddlewareRegistry

```python
class FetchMiddlewareRegistry:
    def __init__(self) -> None
```

Key: `webcompy.ports._middleware:FetchMiddlewareRegistry` · Exports: `from webcompy.ports import FetchMiddlewareRegistry`

Ordered, additively mutated collection of fetch middlewares.

One instance is provided per render context under `FETCH_MIDDLEWARE_KEY`. `use` appends a middleware and advances `generation` so an installed chain wrapper can rebuild its cached sub-chains lazily on the next request.

#### Members

**`generation`** (property)

```python
@property
def generation(self) -> int
```

Counter advanced on every registration.

**Returns:** Current generation value.

**`middlewares`** (property)

```python
@property
def middlewares(self) -> tuple[FetchMiddleware, ...]
```

Snapshot of registered middlewares in registration order.

**Returns:** Middlewares ordered so index `0` is the outermost layer.

**`use`** (method)

```python
def use(self, middleware: FetchMiddleware) -> None
```

Append *middleware* to the registry and advance `generation`.

**Args:**

- `middleware`: Async callable invoked with the request view and a `next` callable.

### FetchNext

```python
class FetchNext(Protocol)
```

Key: `webcompy.ports._middleware:FetchNext` · Exports: `from webcompy.ports import FetchNext`

Invokes the next middleware layer or the terminal dispatch.

Calling with only `request` proceeds normally. Supplying `response` short-circuits every remaining layer and the inner port: the supplied object becomes the result of the operation without any network access. On the streaming path the supplied object is a `FetchStream` whose metadata is already committed.

### FetchPort

```python
class FetchPort(ABC)
```

Key: `webcompy.ports._fetch:FetchPort` · Exports: `from webcompy.ports import FetchPort`

HTTP client surface for buffered and streaming requests.

Implementations perform real network requests (browser `fetch`) or go through an in-process transport (server-side ASGI self-fetch).

#### Members

**`fetch`** (async_method)

```python
async def fetch(
    self,
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> Response
```

Perform an HTTP request.

**Args:**

- `url`: Target URL.
- `method`: HTTP method (default `"GET"`).
- `headers`: Optional request headers.
- `body`: Optional request body as text or bytes.

**Returns:** A `Response` object with text, headers, and status.

**`is_self_site_url`** (method)

```python
def is_self_site_url(self, url: str) -> bool
```

Return whether *url* is a self-site URL (relative to the same application).

**Args:**

- `url`: URL to classify.

**Returns:** True if `url` is a self-site URL, False otherwise.

**`stream`** (async_method)

```python
async def stream(
    self,
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> FetchStream
```

Open a streaming HTTP request.

**Args:**

- `url`: Target URL.
- `method`: HTTP method (default `"GET"`).
- `headers`: Optional request headers.
- `body`: Optional request body as text or bytes.

**Returns:** A `FetchStream` with response metadata and an async iterator of body text chunks.

### FetchRequest

```python
class FetchRequest:
    url: str
    method: str
    headers: dict[str, str] | None
    body: str | bytes | None
```

Key: `webcompy.ports._middleware:FetchRequest` · Exports: `from webcompy.ports import FetchRequest`

Mutable view of an outgoing HTTP request handled by fetch middleware.

Middleware MAY mutate any field in place, or hand a replacement `FetchRequest` to `next`, before invoking the next layer.

**Args:**

- `url`: Target URL.
- `method`: HTTP method.
- `headers`: Mutable request headers, or `None`.
- `body`: Request body as text or bytes, or `None`.

**Attributes:**

- `url`: Target URL.
- `method`: HTTP method.
- `headers`: Mutable request headers, or `None`.
- `body`: Request body as text or bytes, or `None`.

### FetchStream

```python
class FetchStream(ABC):
    def __init__(self, status_code: int, headers: dict[str, str], ok: bool) -> None
```

Key: `webcompy.ports._fetch:FetchStream` · Exports: `from webcompy.ports import FetchStream`

A streaming HTTP response.

Metadata (`status_code`, `headers`, `ok`) is available immediately after the request is opened, without consuming the response body. Iteration yields text chunks whose concatenation equals the complete body text. `close()` and `aclose()` abort the underlying request, are idempotent, and finish in-flight iteration without yielding further chunks.

**Args:**

- `status_code`: HTTP status code of the streamed response.
- `headers`: Response headers.
- `ok`: Whether the response status code indicates success.

**Attributes:**

- `status_code`: HTTP status code of the streamed response.
- `headers`: Response headers.
- `ok`: Whether the response status code indicates success.

#### Members

**`aclose`** (async_method)

```python
async def aclose(self) -> None
```

Asynchronous counterpart of `close()`.

**`close`** (method)

```python
def close(self) -> None
```

Abort the underlying request and mark the stream closed.

### FFI_PORT_KEY

```python
FFI_PORT_KEY = InjectKey[FFIPort]('webcompy-port-ffi')
```

Key: `webcompy.ports._keys:FFI_PORT_KEY` · Exports: `from webcompy.ports import FFI_PORT_KEY`

Injection key for the `FFIPort` implementation.

### FFIPort

```python
class FFIPort(ABC)
```

Key: `webcompy.ports._ffi:FFIPort` · Exports: `from webcompy.ports import FFIPort`

FFI bridge between Python callables and JavaScript values.

Implementations wrap the runtime's FFI layer (Pyodide/PyScript FFI in the browser) for proxy creation, destruction, null checks, and ordinary object conversion.

#### Members

**`assign`** (method)

```python
def assign(self, target: Any, source: Any) -> None
```

Copy properties from `source` to `target`.

**Args:**

- `target`: Destination JavaScript object.
- `source`: Source JavaScript object whose properties are copied.

**`create_proxy`** (method)

```python
def create_proxy(self, obj: Any) -> Any
```

Wrap a Python callable for use in JavaScript.

**Args:**

- `obj`: Python callable (or any object) to proxy.

**Returns:** A JS-side proxy reference.

**`destroy_proxy`** (method)

```python
def destroy_proxy(self, proxy: Any) -> None
```

Release a proxy created by `create_proxy`.

**Args:**

- `proxy`: The proxy object returned by `create_proxy`.

**`is_none`** (method)

```python
def is_none(self, obj: Any) -> bool
```

Check whether a value represents JavaScript `null` or `undefined`.

**Args:**

- `obj`: Value to inspect.

**Returns:** `True` if the value is `None` (JS null/undefined).

**`to_js`** (method)

```python
def to_js(self, obj: Any) -> Any
```

Convert a Python dict to a plain JavaScript object.

**Args:**

- `obj`: Python dictionary to convert.

**Returns:** JavaScript object equivalent.

### HISTORY_PORT_KEY

```python
HISTORY_PORT_KEY = InjectKey[HistoryPort]('webcompy-port-history')
```

Key: `webcompy.ports._keys:HISTORY_PORT_KEY` · Exports: `from webcompy.ports import HISTORY_PORT_KEY`

Injection key for the `HistoryPort` implementation.

### HistoryPort

```python
class HistoryPort(SignalBase[str]):
    def __init__(self, initial_path: str, *, mode: Literal['hash', 'history']) -> None
```

Key: `webcompy.ports._history:HistoryPort` · Exports: `from webcompy.ports import HistoryPort`

Reactive view of the current route path with history integration.

Wraps a `SignalBase[str]` holding the current path and adds browser history support: push/replace operations, popstate reaction, navigation state, and scroll-management hooks. Browser implementations perform real `history` manipulation; the base class is a portable no-op used by server and testing runtimes.

**Args:**

- `initial_path`: Path value the signal starts with.
- `mode`: Routing mode (`"hash"` or `"history"`).

**Attributes:**

- `mode`: Configured routing mode (`"hash"` or `"history"`).
- `value`: Current path value (reactive).
- `state`: State dict associated with the current navigation, or `None`.

#### Members

**`current_search`** (method)

```python
def current_search(self) -> str
```

Return `window.location.search` (query string including `?`).

**Returns:** The current query string (`""` if none).

**`history_state`** (method)

```python
def history_state(self) -> object | None
```

Return `window.history.state`.

**Returns:** The state object associated with the current history entry, or `None`.

**`mode`** (property)

```python
@property
def mode(self) -> Literal['hash', 'history']
```

Configured routing mode (`"hash"` or `"history"`).

**`navigate`** (method)

```python
def navigate(self, path: str, state: dict[str, Any] | None = None) -> None
```

Update the signal value and optionally store route state.

**Args:**

- `path`: Target URL path.
- `state`: Optional state dict to store alongside the path.

**`push_url`** (method)

```python
def push_url(self, path: str, state: dict[str, Any] | None = None) -> None
```

Update the browser address bar via `history.pushState`.

**Args:**

- `path`: App-internal path (no mode prefix, no base_url).
- `state`: Optional history state dict.

**`refresh_from_window`** (method)

```python
def refresh_from_window(self) -> None
```

Re-read the current URL from `window.location` and update the signal value, triggering reactivity.

**`replace_url`** (method)

```python
def replace_url(self, path: str, state: dict[str, Any] | None = None) -> None
```

Update the browser address bar via `history.replaceState`.

**Args:**

- `path`: App-internal path (no mode prefix, no base_url).
- `state`: Optional history state dict.

**`set_navigation_callback`** (method)

```python
def set_navigation_callback(
    self,
    callback: Callable[[str, dict[str, Any] | None], None] | None,
) -> None
```

Set a callback invoked on popstate events instead of the default `_do_navigate()` path.

**Args:**

- `callback`: A callable receiving `(path, state)` when the browser popstate event fires, or `None` to clear.

**`set_scroll_manager`** (method)

```python
def set_scroll_manager(self, manager: ScrollManager | None) -> None
```

Register an object notified on push/pop navigation classification.

**Args:**

- `manager`: An object with `on_push(from_path, to_path)` and `on_pop(from_path, to_path)` methods, or `None` to clear.

**`state`** (property)

```python
@property
def state(self) -> dict[str, Any] | None
```

Return the current route state.

**Returns:** State dict associated with the current navigation, or `None`.

**`value`** (property)

```python
@property
def value(self) -> str
```

Current path value (reactive).

### HOST_PORT_KEY

```python
HOST_PORT_KEY = InjectKey[HostPort]('webcompy-port-host')
```

Key: `webcompy.ports._keys:HOST_PORT_KEY` · Exports: `from webcompy.ports import HOST_PORT_KEY`

Injection key for the `HostPort` implementation.

### HostPort

```python
class HostPort(ABC)
```

Key: `webcompy.ports._host:HostPort` · Exports: `from webcompy.ports import HostPort`

Host-level browser APIs (macrotask scheduling, window events, globals).

Browser implementations delegate to `window`; server implementations degrade to no-ops or inert getters so framework code can call the port unconditionally.

#### Members

**`add_window_event_listener`** (method)

```python
def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]
```

Register a window-level event listener via `window.addEventListener`.

**Args:**

- `event_type`: Event name (e.g. `"resize"`, `"scroll"`).
- `handler`: Callback invoked when the event fires.

**Returns:** A cleanup function; call it to remove the listener.

**`create_js_global_getter`** (method)

```python
def create_js_global_getter(
    self,
    name: str,
    *,
    wrapper: Callable[[Any | None], Any] | None = None,
    default: Any = None,
) -> Callable[[], Any]
```

Create a lazy getter for a JavaScript global.

**Args:**

- `name`: Name of the JavaScript global to look up.
- `wrapper`: Optional transformation applied to the resolved value. Always invoked — receives `None` when the global is missing.
- `default`: Fallback value used when the global is missing and no `wrapper` is provided.

**Returns:** A zero-argument callable that returns the resolved (and optionally wrapped) global, `default`, or `None`.

**`schedule_macro_task`** (method)

```python
def schedule_macro_task(self, callback: Callable[..., Any]) -> None
```

Defer a callback to the next macrotask (via `setTimeout(callback, 0)`).

**Args:**

- `callback`: Zero-argument callable to execute.

### MARKDOWN_PORT_KEY

```python
MARKDOWN_PORT_KEY = InjectKey[MarkdownPort]('webcompy-port-markdown')
```

Key: `webcompy.ports._keys:MARKDOWN_PORT_KEY` · Exports: `from webcompy.ports import MARKDOWN_PORT_KEY`, `from webcompy.template import MARKDOWN_PORT_KEY`

Injection key for the `MarkdownPort` implementation.

### MarkdownPort

```python
class MarkdownPort(ABC)
```

Key: `webcompy.ports._markdown:MarkdownPort` · Exports: `from webcompy.ports import MarkdownPort`

Markdown rendering surface.

Implementations convert Markdown source text into HTML exactly once per call; cacheable results are layered by the callers.

#### Members

**`render`** (method)

```python
def render(self, source: str) -> str
```

Render Markdown source text to HTML.

**Args:**

- `source`: Markdown source text.

**Returns:** The rendered HTML.

### MEDIA_QUERY_PORT_KEY

```python
MEDIA_QUERY_PORT_KEY = InjectKey[MediaQueryPort]('webcompy-port-media-query')
```

Key: `webcompy.ports._keys:MEDIA_QUERY_PORT_KEY` · Exports: `from webcompy.ports import MEDIA_QUERY_PORT_KEY`

Injection key for the `MediaQueryPort` implementation.

### MediaQueryPort

```python
class MediaQueryPort(ABC)
```

Key: `webcompy.ports._media_query:MediaQueryPort` · Exports: `from webcompy.ports import MediaQueryPort`

User-preference media queries (dark color scheme and reduced motion).

#### Members

**`prefers_dark`** (method)

```python
def prefers_dark(self) -> bool
```

Return whether the user prefers a dark color scheme.

**`prefers_reduced_motion`** (method)

```python
def prefers_reduced_motion(self) -> bool
```

Return whether the user prefers reduced motion.

### RESOURCE_PORT_KEY

```python
RESOURCE_PORT_KEY = InjectKey[ResourcePort]('webcompy-port-resource')
```

Key: `webcompy.ports._keys:RESOURCE_PORT_KEY` · Exports: `from webcompy.ports import RESOURCE_PORT_KEY`

Injection key for the `ResourcePort` implementation.

### ResourceNotFoundError

```python
class ResourceNotFoundError(Exception):
    def __init__(self, path: str, context: str, reason: str = '') -> None
```

Key: `webcompy.ports._resource:ResourceNotFoundError` · Exports: `from webcompy.ports import ResourceNotFoundError`

Raised when a resource cannot be loaded by a `ResourcePort` implementation.

The message includes the requested package-relative path and the implementation context (e.g., `"server"` or `"browser"`).

**Args:**

- `path`: Requested package-relative resource path.
- `context`: Implementation context the load failed in.
- `reason`: Reason the resource could not be loaded.

**Attributes:**

- `path`: Requested package-relative resource path.
- `context`: Implementation context the load failed in. `reason` is consumed only while building the message and is not kept as an attribute.

### ResourcePort

```python
class ResourcePort(ABC)
```

Key: `webcompy.ports._resource:ResourcePort` · Exports: `from webcompy.ports import ResourcePort`

Abstract async port for accessing application package resources.

Resources are identified by package-relative POSIX-style paths (forward slashes, no leading slash, no `..` segments). Implementations resolve the path to content (text or bytes) appropriate for the runtime environment and raise `ResourceNotFoundError` when the resource cannot be obtained.

#### Members

**`load_bytes`** (async_method)

```python
async def load_bytes(self, path: str) -> bytes
```

Load a resource as raw bytes.

**`load_text`** (async_method)

```python
async def load_text(self, path: str) -> str
```

Load a resource as UTF-8 text.

**`preload`** (async_method)

```python
async def preload(self, paths: Iterable[str]) -> None
```

Prime client-side caches for the given resource paths.

### Response

```python
class Response:
    text: str
    headers: dict[str, str]
    status_code: int
    status_text: str
    ok: bool
    content: bytes = b''
```

Key: `webcompy.ports._fetch:Response` · Exports: `from webcompy.ports import Response`

A buffered HTTP response returned by `FetchPort.fetch`.

**Args:**

- `text`: Response body decoded as text.
- `headers`: Response headers.
- `status_code`: HTTP status code.
- `status_text`: HTTP status text.
- `ok`: Whether the response is successful.
- `content`: Raw response body as bytes.

**Attributes:**

- `text`: Response body decoded as text.
- `headers`: Response headers.
- `status_code`: HTTP status code.
- `status_text`: HTTP status text.
- `ok`: Whether the response is successful.
- `content`: Raw response body as bytes.

#### Members

**`json`** (method)

```python
def json(self, **kwargs: Any) -> Any
```

Decode the response body as JSON.

**Args:**

- `**kwargs`: Extra keyword arguments forwarded to `json.loads`.

**Returns:** The decoded JSON value.

**`raise_for_status`** (method)

```python
def raise_for_status(self) -> None
```

Raise an exception when the response is not successful.

**Raises:**

- `Exception`: If the response status is not successful.

### ServerAsyncSchedulerPort

```python
class ServerAsyncSchedulerPort(AsyncSchedulerPort):
    def __init__(self) -> None
```

Key: `webcompy_server.ports._async_scheduler:ServerAsyncSchedulerPort` · Exports: `from webcompy_server.ports import ServerAsyncSchedulerPort`

Server-side async task scheduler for SSR.

Tracks scheduled tasks and drains them during `await_pending`.

#### Members

**`await_pending`** (async_method)

```python
async def await_pending(self, *, only_render: bool = False) -> None
```

Wait for pending scheduled tasks to complete.

**Args:**

- `only_render`: If `True`, wait only for render-scoped tasks.

**Returns:** `None`.

**`schedule`** (method)

```python
def schedule(
    self,
    coro: Coroutine[Any, Any, Any],
    *,
    render: bool = False,
) -> asyncio.Task[Any]
```

Schedule a coroutine for execution.

**Args:**

- `coro`: Coroutine to schedule.
- `render`: Whether the task is render-scoped.

**Returns:** Created `asyncio.Task`.

### ServerCookiePort

```python
class ServerCookiePort(CookiePort):
    def __init__(self, cookie_header: str = '') -> None
```

Key: `webcompy_server.ports._cookie:ServerCookiePort` · Exports: `from webcompy_server.ports import ServerCookiePort`

Server-side cookie storage backed by request headers and pending writes.

**Args:**

- `cookie_header`: Raw `Cookie` header value from the request.

#### Members

**`delete`** (method)

```python
def delete(self, name: str, path: str = '/') -> None
```

Delete a cookie and record a clearing `Set-Cookie` header.

**Args:**

- `name`: Cookie name.
- `path`: Cookie path.

**Returns:** `None`.

**`get`** (method)

```python
def get(self, name: str) -> str | None
```

Return the value of `name` if present.

**Args:**

- `name`: Cookie name.

**Returns:** Cookie value or `None` when not set.

**`get_all`** (method)

```python
def get_all(self) -> dict[str, str]
```

Return a copy of all cookies.

**Returns:** Mapping of cookie names to values.

**`get_pending_set_cookie_headers`** (method)

```python
def get_pending_set_cookie_headers(self) -> list[str]
```

Build pending `Set-Cookie` header strings.

**Returns:** List of serialized `Set-Cookie` header values.

**`set`** (method)

```python
def set(
    self,
    name: str,
    value: str,
    *,
    max_age: int | None = None,
    expires: datetime | None = None,
    path: str = '/',
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str | None = None,
) -> None
```

Set a cookie and record a pending `Set-Cookie` header.

**Args:**

- `name`: Cookie name.
- `value`: Cookie value.
- `max_age`: Max-Age in seconds.
- `expires`: Expiration datetime.
- `path`: Cookie path.
- `domain`: Cookie domain.
- `secure`: Whether to set the `Secure` flag.
- `httponly`: Whether to set the `HttpOnly` flag.
- `samesite`: `SameSite` attribute value.

**Returns:** `None`.

### ServerCustomElementPort

```python
class ServerCustomElementPort(CustomElementPort)
```

Key: `webcompy_server.ports._custom_element:ServerCustomElementPort` · Exports: `from webcompy_server.ports import ServerCustomElementPort`

Server-side no-op custom element port.

#### Members

**`bind`** (method)

```python
def bind(
    self,
    node: DOMNode,
    *,
    observed_attributes: tuple[str, ...],
    on_connected: Callable[[], None],
    on_disconnected: Callable[[], None],
    on_attribute_changed: Callable[[str, str | None], None],
) -> CustomElementBinding
```

Bind lifecycle callbacks to `node`.

**Args:**

- `node`: DOM node to bind.
- `observed_attributes`: Attributes to observe.
- `on_connected`: Callback when the element connects.
- `on_disconnected`: Callback when the element disconnects.
- `on_attribute_changed`: Callback for attribute changes.

**Returns:** Binding handle whose `dispose` disconnects the callbacks.

**`ensure_defined`** (method)

```python
def ensure_defined(
    self,
    name: str,
    observed_attributes: tuple[str, ...],
    definition_key: str,
) -> None
```

Ensure a custom element definition is registered.

**Args:**

- `name`: Tag name of the custom element.
- `observed_attributes`: Attributes to observe.
- `definition_key`: Deduplication key for the definition.

**Returns:** `None`.

**`is_document_connected`** (method)

```python
def is_document_connected(self, node: DOMNode) -> bool
```

Return whether `node` is connected to the document.

**Args:**

- `node`: Node to check.

**Returns:** `False` on the server.

### ServerDOMPort

```python
class ServerDOMPort(DOMPort):
    def __init__(self) -> None
```

Key: `webcompy_server.ports._dom:ServerDOMPort` · Exports: `from webcompy_server.ports import ServerDOMPort`

Server-side DOM port that creates virtual nodes and serializes HTML.

#### Members

**`add_document_event_listener`** (method)

```python
def add_document_event_listener(
    self,
    event_type: str,
    handler: Any,
    *,
    capture: bool = False,
) -> Callable[[], None]
```

Add a document-level event listener.

**Args:**

- `event_type`: Event type.
- `handler`: Event handler.
- `capture`: Ignored on the server; accepted for interface parity with the browser port.

**Returns:** Callable that removes the listener.

**`create_comment`** (method)

```python
def create_comment(self, data: str) -> DOMNode
```

Create a comment node.

**Args:**

- `data`: Comment data.

**Returns:** New virtual comment node.

**`create_element`** (method)

```python
def create_element(self, tag: str) -> DOMNode
```

Create an element node for `tag`.

**Args:**

- `tag`: Tag name.

**Returns:** New virtual element node.

**`create_event`** (method)

```python
def create_event(
    self,
    event_type: str,
    *,
    bubbles: bool = False,
    cancelable: bool = False,
) -> DOMEvent
```

Create a virtual DOM event.

**Args:**

- `event_type`: Event type name.
- `bubbles`: Whether the event bubbles.
- `cancelable`: Whether the event is cancelable.

**Returns:** New virtual event.

**`create_text_node`** (method)

```python
def create_text_node(self, text: str) -> DOMNode
```

Create a text node.

**Args:**

- `text`: Text content.

**Returns:** New virtual text node.

**`get_element_by_id`** (method)

```python
def get_element_by_id(self, element_id: str) -> DOMNode | None
```

Return the element with `element_id`.

**Args:**

- `element_id`: Element ID.

**Returns:** `None` on the server.

**`query_selector`** (method)

```python
def query_selector(self, selector: str) -> DOMNode | None
```

Query the attached document tree for `selector`.

**Args:**

- `selector`: CSS selector from the supported subset.

**Returns:** First matching node, or `None` when nothing matches or no document tree has been attached yet.

**Raises:**

- `ValueError`: When the selector uses unsupported syntax.

**`query_selector_all`** (method)

```python
def query_selector_all(self, selector: str, *, root: DOMNode | None = None) -> list[DOMNode]
```

Query for all matching nodes, scoped to `root` when given.

**Args:**

- `selector`: CSS selector string.
- `root`: Optional subtree root.

**Returns:** Matching element nodes in document order.

**`render_html`** (method)

```python
def render_html(self, node: DOMNode) -> str
```

Serialize `node` to HTML.

**Args:**

- `node`: Virtual DOM node to serialize.

**Returns:** HTML string for `node`.

**`set_title`** (method)

```python
def set_title(self, title: str) -> None
```

Set the document title.

**Args:**

- `title`: Title to set.

**Returns:** `None`.

### ServerEventSourcePort

```python
class ServerEventSourcePort(EventSourcePort)
```

Key: `webcompy_server.ports._event_source:ServerEventSourcePort` · Exports: `from webcompy_server.ports import ServerEventSourcePort`

Server-side no-op `EventSourcePort`.

`noop = True` marks this port as a pure no-op: `use_event_source` uses it as the signal that SSR/SSG degradation (warning + empty closed handle) applies, rather than opening a connection through the port.

#### Members

**`open`** (method)

```python
def open(
    self,
    url: str,
    *,
    events: tuple[str, ...],
    on_open: Callable[[], None],
    on_message: Callable[[str, str, str], None],
    on_error: Callable[[], None],
    on_close: Callable[[], None],
) -> Callable[[], None]
```

Open an event source connection.

**Args:**

- `url`: Event source URL.
- `events`: Event types to listen for.
- `on_open`: Callback when the connection opens.
- `on_message`: Callback for incoming messages.
- `on_error`: Callback for errors.
- `on_close`: Callback when the connection closes.

**Returns:** Callable that closes the connection.

### ServerFetchPort

```python
class ServerFetchPort(FetchPort):
    def __init__(self, external_client: httpx.AsyncClient | None = None) -> None
```

Key: `webcompy_server.ports._fetch:ServerFetchPort` · Exports: `from webcompy_server import ServerFetchPort`, `from webcompy_server.ports import ServerFetchPort`

Server-side `FetchPort`.

`noop = True` marks this port as a pure no-op for realtime connections: `use_event_source` (non-GET) uses it as the signal that SSR/SSG degradation (warning + empty closed handle) applies, rather than issuing a fetch request through the port. The port itself remains fully functional for ordinary `fetch()` calls during SSR/SSG.

#### Members

**`clear_cache`** (method)

```python
def clear_cache(self) -> None
```

Clear the response cache.

**Returns:** `None`.

**`close`** (async_method)

```python
async def close(self) -> None
```

Close underlying HTTP clients.

**Returns:** `None`.

**`configure`** (method)

```python
def configure(
    self,
    asgi_app: ASGIApp,
    blocked_paths: list[str] | None = None,
    base_url: str | None = None,
    mount_prefixes: list[str] | None = None,
    *,
    embedded: bool = False,
) -> None
```

Configure the ASGI app and routing for self-site fetches.

**Args:**

- `asgi_app`: ASGI application handling self-site requests.
- `blocked_paths`: Page routes blocked during SSR to avoid recursion.
- `base_url`: Base URL prefix for resolving relative paths.
- `mount_prefixes`: Mount prefixes considered self-site.
- `embedded`: Whether the app is embedded under a host app.

**Returns:** `None`.

**Raises:**

- `WebComPyException`: If the port is already configured.

**`fetch`** (async_method)

```python
async def fetch(
    self,
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> Response
```

Fetch `url` via external client or in-process ASGI transport.

**Args:**

- `url`: Target URL.
- `method`: HTTP method.
- `headers`: Optional request headers.
- `body`: Optional request body as text or bytes.

**Returns:** HTTP `Response`.

**`get_transfer_data`** (method)

```python
def get_transfer_data(self) -> dict[str, TransferFetchEntry]
```

Collect cache entries eligible for hydration transfer.

**Returns:** Mapping of cache keys to transfer entries for self-site responses.

**`is_self_site_url`** (method)

```python
def is_self_site_url(self, url: str) -> bool
```

Return whether `url` targets the same site.

**Args:**

- `url`: URL to check.

**Returns:** `True` for relative URLs starting with `/` or `.`.

### ServerFFIPort

```python
class ServerFFIPort(FFIPort)
```

Key: `webcompy_server.ports._ffi:ServerFFIPort` · Exports: `from webcompy_server.ports import ServerFFIPort`

Server-side no-op FFI port.

#### Members

**`assign`** (method)

```python
def assign(self, target: Any, source: Any) -> None
```

Assign properties from `source` to `target`.

**Args:**

- `target`: Target object.
- `source`: Source object.

**Returns:** `None`.

**`create_proxy`** (method)

```python
def create_proxy(self, obj: Any) -> Any
```

Create a proxy for `obj`.

**Args:**

- `obj`: Object to wrap.

**Returns:** `obj` unchanged on the server.

**`destroy_proxy`** (method)

```python
def destroy_proxy(self, proxy: Any) -> None
```

Destroy a previously created proxy.

**Args:**

- `proxy`: Proxy to destroy.

**Returns:** `None`.

**`is_none`** (method)

```python
def is_none(self, obj: Any) -> bool
```

Return whether `obj` is `None`.

**Args:**

- `obj`: Value to check.

**Returns:** `True` if `obj` is `None`.

**`to_js`** (method)

```python
def to_js(self, obj: Any) -> Any
```

Convert `obj` to a JavaScript value.

**Args:**

- `obj`: Value to convert.

**Returns:** `obj` unchanged on the server.

### ServerHistoryPort

```python
class ServerHistoryPort(HistoryPort):
    def __init__(self, *, mode: Literal['hash', 'history'], initial_path: str = '/') -> None
```

Key: `webcompy_server.ports._history:ServerHistoryPort` · Exports: `from webcompy_server.ports import ServerHistoryPort`

Server-side history port without browser navigation.

**Args:**

- `mode`: Routing mode.
- `initial_path`: Initial path.

#### Members

**`current_search`** (method)

```python
def current_search(self) -> str
```

Return the current search string.

**Returns:** Empty string on the server.

**`history_state`** (method)

```python
def history_state(self) -> object | None
```

Return the current history state.

**Returns:** Current state object.

**`refresh_from_window`** (method)

```python
def refresh_from_window(self) -> None
```

Sync history state from the window.

**Returns:** `None`.

### ServerHostPort

```python
class ServerHostPort(HostPort)
```

Key: `webcompy_server.ports._host:ServerHostPort` · Exports: `from webcompy_server.ports import ServerHostPort`

Server-side host port with synchronous task execution.

#### Members

**`add_window_event_listener`** (method)

```python
def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]
```

Add a window event listener.

**Args:**

- `event_type`: Event type.
- `handler`: Event handler.

**Returns:** Callable that removes the listener.

**`create_js_global_getter`** (method)

```python
def create_js_global_getter(
    self,
    name: str,
    *,
    wrapper: Callable[[Any | None], Any] | None = None,
    default: Any = None,
) -> Callable[[], Any]
```

Create a getter for a JavaScript global.

**Args:**

- `name`: Global name.
- `wrapper`: Optional wrapper for the global value.
- `default`: Default value when the global is absent.

**Returns:** Callable that returns the global value or `default`.

**`schedule_macro_task`** (method)

```python
def schedule_macro_task(self, callback: Callable[..., Any]) -> None
```

Schedule `callback` as a macro task.

**Args:**

- `callback`: Callback to execute.

**Returns:** `None`.

### ServerMediaQueryPort

```python
class ServerMediaQueryPort(MediaQueryPort)
```

Key: `webcompy_server.ports._media_query:ServerMediaQueryPort` · Exports: `from webcompy_server.ports import ServerMediaQueryPort`

Server-side media query port returning defaults.

#### Members

**`prefers_dark`** (method)

```python
def prefers_dark(self) -> bool
```

Return whether the user prefers a dark theme.

**Returns:** `False` on the server.

**`prefers_reduced_motion`** (method)

```python
def prefers_reduced_motion(self) -> bool
```

Return whether the user prefers reduced motion.

**Returns:** `False` on the server.

### ServerResourcePort

```python
class ServerResourcePort(ResourcePort):
    def __init__(self, app_package_path: Path, allow_list: frozenset[str]) -> None
```

Key: `webcompy_server.ports._resource:ServerResourcePort` · Exports: `from webcompy_server import ServerResourcePort`, `from webcompy_server.ports import ServerResourcePort`

Server-side resource loader that reads files from the app package.

**Args:**

- `app_package_path`: Filesystem path of the app package root.
- `allow_list`: Set of allowed relative resource paths.

#### Members

**`fresh`** (method)

```python
def fresh(self) -> ServerResourcePort
```

Create a fresh port sharing the same configuration.

**Returns:** New `ServerResourcePort` with the same paths.

**`get_recorded_resources`** (method)

```python
def get_recorded_resources(self) -> dict[str, bytes]
```

Return recorded resource contents.

**Returns:** Mapping of paths to recorded byte contents.

**`load_bytes`** (async_method)

```python
async def load_bytes(self, path: str) -> bytes
```

Load a binary resource.

**Args:**

- `path`: Relative resource path.

**Returns:** Binary content of the resource.

**Raises:**

- `ResourceNotFoundError`: If the resource is missing or invalid.

**`load_text`** (async_method)

```python
async def load_text(self, path: str) -> str
```

Load a text resource.

**Args:**

- `path`: Relative resource path.

**Returns:** Text content of the resource.

**Raises:**

- `ResourceNotFoundError`: If the resource is missing or invalid.

### ServerTransitionPort

```python
class ServerTransitionPort(TransitionPort)
```

Key: `webcompy_server.ports._transition:ServerTransitionPort` · Exports: `from webcompy_server.ports import ServerTransitionPort`

Server-side no-op transition port.

**Attributes:**

- `enabled`: Always `False` on the server, so transitions degrade to immediate mount/removal.

#### Members

**`enabled`** (property)

```python
@property
def enabled(self) -> bool
```

Return whether transitions are enabled.

**Returns:** `False` on the server.

**`get_computed_style`** (method)

```python
def get_computed_style(self, node: DOMNode) -> TransitionStyle
```

Return computed style for `node`.

**Args:**

- `node`: DOM node.

**Returns:** Empty transition style on the server.

**`schedule_next_frame`** (method)

```python
def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]
```

Schedule `callback` for the next frame.

**Args:**

- `callback`: Callback to schedule.

**Returns:** Callable that cancels the schedule.

**`schedule_timeout`** (method)

```python
def schedule_timeout(
    self,
    callback: Callable[[], Any],
    delay_ms: float,
) -> Callable[[], None]
```

Schedule `callback` after a delay.

**Args:**

- `callback`: Callback to schedule.
- `delay_ms`: Delay in milliseconds.

**Returns:** Callable that cancels the schedule.

### ServerWebSocketPort

```python
class ServerWebSocketPort(WebSocketPort)
```

Key: `webcompy_server.ports._websocket:ServerWebSocketPort` · Exports: `from webcompy_server.ports import ServerWebSocketPort`

Server-side no-op `WebSocketPort`.

`noop = True` marks this port as a pure no-op: `use_websocket` uses it as the signal that SSR/SSG degradation (warning + empty closed handle) applies, rather than opening a connection through the port.

#### Members

**`open`** (method)

```python
def open(
    self,
    url: str,
    *,
    protocols: tuple[str, ...] = (),
    on_open: Callable[[], None],
    on_message: Callable[[str], None],
    on_binary: Callable[[], None],
    on_error: Callable[[], None],
    on_close: Callable[[int, str, bool], None],
) -> WebSocketConnection
```

Open a websocket connection.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Optional subprotocols.
- `on_open`: Callback when the connection opens.
- `on_message`: Callback for incoming text messages.
- `on_binary`: Callback for incoming binary messages.
- `on_error`: Callback for errors.
- `on_close`: Callback when the connection closes.

**Returns:** No-op connection.

### TRANSITION_PORT_KEY

```python
TRANSITION_PORT_KEY = InjectKey[TransitionPort]('webcompy-port-transition')
```

Key: `webcompy.ports._keys:TRANSITION_PORT_KEY` · Exports: `from webcompy.ports import TRANSITION_PORT_KEY`

Injection key for the `TransitionPort` implementation.

### TransitionPort

```python
class TransitionPort(ABC)
```

Key: `webcompy.ports._transition:TransitionPort` · Exports: `from webcompy.ports import TransitionPort`

Timing and computed-style surface for CSS class transitions.

Owns the browser APIs required by `TransitionElement`: next-frame scheduling (double `requestAnimationFrame`), real-time timeouts with cancellation, and computed-style reads. The server port reports `enabled == False` so transitions degrade to immediate mount/removal.

**Attributes:**

- `enabled`: Whether class sequences can run in this environment; `False` on the server port, where transitions are skipped.

#### Members

**`enabled`** (property)

```python
@property
def enabled(self) -> bool
```

Return whether class sequences can run in this environment.

**`get_computed_style`** (method)

```python
def get_computed_style(self, node: DOMNode) -> TransitionStyle
```

Return a read-only view of `node`'s computed style.

**Args:**

- `node`: The DOM node whose computed style is requested.

**Returns:** A style view exposing `get_property_value(name)`.

**`schedule_next_frame`** (method)

```python
def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]
```

Run `callback` after the next animation frame.

**Args:**

- `callback`: Zero-argument callable to execute.

**Returns:** A cancel function; calling it prevents `callback` from running.

**`schedule_timeout`** (method)

```python
def schedule_timeout(
    self,
    callback: Callable[[], Any],
    delay_ms: float,
) -> Callable[[], None]
```

Run `callback` after `delay_ms` milliseconds.

**Args:**

- `callback`: Zero-argument callable to execute.
- `delay_ms`: Delay in milliseconds.

**Returns:** A cancel function; calling it prevents `callback` from running.

### VirtualDOMEvent

```python
class VirtualDOMEvent:
    def __init__(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> None
```

Key: `webcompy_server.ports._virtual_dom:VirtualDOMEvent` · Exports: `from webcompy_server.ports import VirtualDOMEvent`, `from webcompy_testing import VirtualDOMEvent`

Virtual DOM event for server-side testing and rendering.

**Args:**

- `event_type`: Event type name.
- `bubbles`: Whether the event bubbles.
- `cancelable`: Whether the event is cancelable.

**Attributes:**

- `type`: Event type name.
- `bubbles`: Whether the event bubbles.
- `cancelable`: Whether the event is cancelable.
- `target`: Node the event was dispatched to, or `None`.
- `currentTarget`: Node whose listener is processing the event, or `None`.
- `defaultPrevented`: Whether `preventDefault()` was called.
- `eventPhase`: Current phase of the event flow.
- `timeStamp`: Creation time of the event in milliseconds.

#### Members

**`bubbles`** (property)

```python
@property
def bubbles(self) -> bool
```

Return whether the event bubbles.

**`cancelable`** (property)

```python
@property
def cancelable(self) -> bool
```

Return whether the event is cancelable.

**`currentTarget`** (property)

```python
@property
def currentTarget(self) -> DOMNode | None
```

Return the current event target.

**`defaultPrevented`** (property)

```python
@property
def defaultPrevented(self) -> bool
```

Return whether `preventDefault` was called.

**`eventPhase`** (property)

```python
@property
def eventPhase(self) -> int
```

Return the current event phase.

**`preventDefault`** (method)

```python
def preventDefault(self) -> None
```

Prevent the default action if the event is cancelable.

**Returns:** `None`.

**`stopPropagation`** (method)

```python
def stopPropagation(self) -> None
```

Stop event propagation.

**Returns:** `None`.

**`target`** (property)

```python
@property
def target(self) -> DOMNode | None
```

Return the event target.

**`timeStamp`** (property)

```python
@property
def timeStamp(self) -> int
```

Return the event timestamp.

**`type`** (property)

```python
@property
def type(self) -> str
```

Return the event type.

### VirtualDOMNode

```python
class VirtualDOMNode:
    def __init__(
        self,
        tag_name: str,
        *,
        node_type: int = 1,
        text_content: str | None = None,
    ) -> None
```

Key: `webcompy_server.ports._virtual_dom:VirtualDOMNode` · Exports: `from webcompy_server.ports import VirtualDOMNode`

Virtual DOM node used for server-side rendering.

**Args:**

- `tag_name`: Tag name or `#text`/`#comment` marker.
- `node_type`: DOM node type.
- `text_content`: Initial text content for text/comment nodes.

**Attributes:**

- `__webcompy_node__`: Marker flag identifying framework-created nodes; always `True` on virtual nodes.
- `__webcompy_prerendered_node__`: Marker flag for nodes adopted from pre-rendered markup; always `False` on virtual nodes.
- `nodeName`: Uppercased tag name, or `#text`/`#comment` for text and comment nodes.
- `nodeType`: DOM node type number.
- `textContent`: Concatenated descendant text content; assignment replaces all children of an element node.
- `childNodes`: Child nodes of this node.
- `parentNode`: Parent node, or `None` when unattached.
- `isConnected`: Whether the node is attached to a root document.

#### Members

**`addEventListener`** (method)

```python
def addEventListener(
    self,
    event_type: str,
    handler: Any,
    options_or_capture: Any = False,
) -> None
```

Add an event listener.

**Args:**

- `event_type`: Event type.
- `handler`: Event handler.
- `options_or_capture`: Options or capture flag.

**Returns:** `None`.

**`appendChild`** (method)

```python
def appendChild(self, child: DOMNode) -> None
```

Append `child` as the last child.

**Args:**

- `child`: Node to append.

**Returns:** `None`.

**`childNodes`** (property)

```python
@property
def childNodes(self) -> DOMNodeList
```

Return the child node list.

**`dispatchEvent`** (method)

```python
def dispatchEvent(self, event: DOMEvent) -> bool
```

Dispatch `event` to this node and its ancestors.

**Args:**

- `event`: Event to dispatch.

**Returns:** `False` when `preventDefault` was called.

**`getAttribute`** (method)

```python
def getAttribute(self, name: str) -> str | None
```

Return the value of attribute `name`.

**Args:**

- `name`: Attribute name.

**Returns:** Attribute value or `None` when not present.

**`getAttributeNames`** (method)

```python
def getAttributeNames(self) -> list[str]
```

Return a list of attribute names.

**Returns:** Attribute name list.

**`hasAttribute`** (method)

```python
def hasAttribute(self, name: str) -> bool
```

Return whether attribute `name` exists.

**Args:**

- `name`: Attribute name.

**Returns:** `True` if the attribute exists.

**`insertBefore`** (method)

```python
def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None
```

Insert `new_node` before `ref_node`.

**Args:**

- `new_node`: Node to insert.
- `ref_node`: Reference child node.

**Returns:** `None`.

**Raises:**

- `ValueError`: If `ref_node` is not a child of this node.

**`isConnected`** (property)

```python
@property
def isConnected(self) -> bool
```

Return whether the node is connected to the document.

**`nodeName`** (property)

```python
@property
def nodeName(self) -> str
```

Return the node name.

**`nodeType`** (property)

```python
@property
def nodeType(self) -> int
```

Return the DOM node type.

**`parentNode`** (property)

```python
@property
def parentNode(self) -> DOMNode | None
```

Return the parent node.

**`remove`** (method)

```python
def remove(self) -> None
```

Remove this node from its parent.

**Returns:** `None`.

**`removeAttribute`** (method)

```python
def removeAttribute(self, name: str) -> None
```

Remove attribute `name`.

**Args:**

- `name`: Attribute name.

**Returns:** `None`.

**`removeChild`** (method)

```python
def removeChild(self, child: DOMNode) -> None
```

Remove `child` from this node.

**Args:**

- `child`: Child to remove.

**Returns:** `None`.

**Raises:**

- `ValueError`: If `child` is not a child of this node.

**`removeEventListener`** (method)

```python
def removeEventListener(
    self,
    event_type: str,
    handler: Any,
    options_or_capture: Any = False,
) -> None
```

Remove an event listener.

**Args:**

- `event_type`: Event type.
- `handler`: Event handler.
- `options_or_capture`: Options or capture flag.

**Returns:** `None`.

**`replaceChild`** (method)

```python
def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None
```

Replace `old_node` with `new_node`.

**Args:**

- `new_node`: Replacement node.
- `old_node`: Node to replace.

**Returns:** `None`.

**Raises:**

- `ValueError`: If `old_node` is not a child of this node.

**`setAttribute`** (method)

```python
def setAttribute(self, name: str, value: str | None) -> None
```

Set attribute `name` to `value`.

**Args:**

- `name`: Attribute name.
- `value`: Attribute value or `None` for boolean attributes.

**Returns:** `None`.

**`textContent`** (property)

```python
@property
def textContent(self) -> str | None
```

Return the concatenated text content.

### WEBSOCKET_PORT_KEY

```python
WEBSOCKET_PORT_KEY = InjectKey[WebSocketPort]('webcompy-port-websocket')
```

Key: `webcompy.ports._keys:WEBSOCKET_PORT_KEY` · Exports: `from webcompy.ports import WEBSOCKET_PORT_KEY`

Injection key for the `WebSocketPort` implementation.

### WebSocketConnection

```python
class WebSocketConnection(ABC)
```

Key: `webcompy.ports._websocket:WebSocketConnection` · Exports: `from webcompy.ports import WebSocketConnection`

Handle for an open WebSocket connection.

Implementations wrap a single native (or fake) socket and expose the send and close operations. `send` writes one text frame; `close` closes the socket and removes its listeners. The port has no component knowledge.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

Close the connection and remove its listeners.

**`send`** (method)

```python
def send(self, data: str) -> None
```

Send one text frame.

**Args:**

- `data`: Text payload of the frame to send.

### WebSocketPort

```python
class WebSocketPort(ABC)
```

Key: `webcompy.ports._websocket:WebSocketPort` · Exports: `from webcompy.ports import WebSocketPort`

Port for WebSocket connections (callback surface).

Implementations open a connection for the given URL and optional subprotocols and deliver lifecycle transitions and received frames to the supplied callbacks. The returned handle exposes send/close. All subscriber fan-out is owned by the caller.

#### Members

**`open`** (method)

```python
def open(
    self,
    url: str,
    *,
    protocols: tuple[str, ...] = (),
    on_open: Callable[[], None],
    on_message: Callable[[str], None],
    on_binary: Callable[[], None],
    on_error: Callable[[], None],
    on_close: Callable[[int, str, bool], None],
) -> WebSocketConnection
```

Open a WebSocket connection for `url` and `protocols`.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Server guides: [CLI Reference](/documents/server/cli-reference), [Project Configuration](/documents/server/project-configuration), [ASGI Integration](/documents/server/asgi-integration), and [Serving Modes](/documents/server/serving-modes).
- Advanced guides: [Middleware](/documents/advanced/middleware), [RPC Contracts](/documents/advanced/rpc-contracts), [RPC](/documents/advanced/rpc), [SSR & SSG](/documents/advanced/ssr-and-ssg), [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer), and [Progressive Web App](/documents/advanced/pwa).
<!-- author:end:see-also -->
