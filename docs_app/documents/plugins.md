---
title: Plugins
description: Extend WebComPy applications with WebComPyPlugin subclasses — lifecycle hooks, DI providers, fetch and RPC middleware aggregation, and conditional PluginScript tags.
---

# Plugins

`WebComPyPlugin` lets you package cross-cutting capabilities — debug toolbars, authentication guards, analytics trackers, HTTP/RPC middleware, and conditional external `<script>` tags — into reusable classes registered via `WebComPyAppConfig.plugins`. `PluginManager` discovers each plugin class by module path, runs hooks in deterministic declaration order across app startup and per-request render contexts, and collects script descriptors for HTML output.

## When to use

- **Packaging reusable telemetry, auth guards, middleware bundles, or browser scripts across apps** — implement a `WebComPyPlugin`.
- **Wiring a single service or override inside one application or test** — call `app.provide(...)` or `DIScope(...)` directly (see [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive)).
- **Registering ad-hoc request interceptors inside a component** — call `add_fetch_middleware` / `add_rpc_middleware` directly (see [Middleware](/documents/advanced/middleware)).

## Setup

Create a `WebComPyPlugin` subclass (`from webcompy.plugin import WebComPyPlugin` or `from webcompy.app import WebComPyPlugin`) and list its `"module.path:ClassName"` string in `WebComPyAppConfig(plugins=[...])`:

```python
# my_app/plugins.py
from webcompy.app import WebComPyApp, WebComPyPlugin, RenderContext
from webcompy.di import InjectKey

AnalyticsKey = InjectKey[str]("analytics-id")


class AnalyticsPlugin(WebComPyPlugin):
    name = "analytics"
    version = "0.1.0"

    @staticmethod
    def get_providers() -> dict[object, object]:
        return {AnalyticsKey: "ua-demo-001"}

    def on_app_init(self, app: WebComPyApp) -> None:
        if app.router is not None:
            app.router.after_route_change.append(lambda path: print("Track view:", path))
```

```python
# my_app/bootstrap.py
from webcompy.app import WebComPyApp, WebComPyAppConfig

app = WebComPyApp(
    root_component=AppShell,
    config=WebComPyAppConfig(
        plugins=["my_app.plugins:AnalyticsPlugin"],
    ),
)
```

## Recipes

### 1. Bundle middlewares, providers, and router hooks in one plugin

Override `get_fetch_middlewares()`, `get_rpc_middlewares()`, `get_providers()`, `on_app_init()`, `on_render_context_init()`, and `on_app_ready()` on the same plugin class:

```python
from webcompy.app import WebComPyApp, WebComPyPlugin, RenderContext
from webcompy.ports import FetchNext, FetchRequest
from webcompy.rpc import RpcContext


class AuthIntegrationPlugin(WebComPyPlugin):
    name = "auth-integration"
    version = "1.0.0"

    @staticmethod
    def get_fetch_middlewares():
        async def add_session_header(request: FetchRequest, next: FetchNext):
            request.headers = {**(request.headers or {}), "X-App-Client": "webcompy"}
            return await next(request)

        return [add_session_header]

    @staticmethod
    def get_rpc_middlewares():
        async def add_rpc_header(ctx: RpcContext, next):
            ctx.headers["X-App-Client"] = "webcompy"
            return await next(ctx)

        return [add_rpc_header]

    def on_app_init(self, app: WebComPyApp) -> None:
        if app.router is not None:
            app.router.before_route_change.append(lambda _from, to: to != "/forbidden")

    def on_app_ready(self, ctx: RenderContext) -> None:
        # Runs only in the browser inside app.run(), right before first render/hydration
        print("Browser app mounted with root scope:", ctx.di_scope)
```

### 2. Inject static or runtime-conditional `<script>` tags with `PluginScript`

Return `PluginScript` descriptors (`from webcompy.app import PluginScript`) from `get_scripts()` (or attach them via `WebComPyAppConfig.scripts`). When `condition=None`, WebComPy emits an ordinary `<script>` tag; when `condition` is a JavaScript expression string, WebComPy emits a small self-contained wrapper script that dynamically loads `<script>` or executes inline `script=` only when the expression evaluates truthy at runtime:

```python
from webcompy.app import PluginScript, WebComPyPlugin


class DebugToolbarPlugin(WebComPyPlugin):
    name = "debug-toolbar"
    version = "0.1.0"

    @staticmethod
    def get_scripts() -> list[PluginScript]:
        return [
            PluginScript(
                attrs={"type": "text/javascript", "src": "https://cdn.example.com/eruda.min.js"},
                condition="new URLSearchParams(location.search).get('debug') === 'True'",
                script="eruda.init()",
                in_head=False,
            )
        ]
```

If `condition` is given without `"src"` in `attrs`, the inline `script` executes directly inside the condition branch without creating an extra `<script>` element (`in_head=True` places the tag/wrapper in `<head>`, `in_head=False` at the end of `<body>`).

### 3. Provide fresh per-request values in `on_render_context_init()`

Use `on_render_context_init(self, ctx)` whenever each SSR request (or browser boot) needs an isolated instance or port override — it runs **after** `_register_ports()` so plugins can also replace default browser/server ports safely:

```python
import uuid
from webcompy.app import WebComPyPlugin, RenderContext
from webcompy.di import InjectKey

RequestIdKey = InjectKey[str]("request-id")


class RequestTracingPlugin(WebComPyPlugin):
    name = "request-tracing"
    version = "0.1.0"

    def on_render_context_init(self, ctx: RenderContext) -> None:
        ctx.di_scope.provide(RequestIdKey, str(uuid.uuid4()))
```

## Behavior notes

- **Startup & per-context execution order**:
  1. `WebComPyApp.__init__()` resolves `config.plugins` via `PluginManager.discover()`, validates the `"module:Class"` format and `WebComPyPlugin` subclass check, and creates `app.router`.
  2. `PluginManager.init_all()` instantiates each plugin and invokes `on_app_init(app)` in declaration order (before the root component mounts).
  3. On every `app.create_render_context()` (each SSR request, SSG page, or browser `app.run()`), `RenderContext.__init__` first calls `_register_ports()`, then `PluginManager.init_render_context(ctx)`:
     - Registers `get_providers()` into `ctx.di_scope`.
     - Calls `on_render_context_init(ctx)` on each plugin instance.
     - Aggregates `get_fetch_middlewares()` onto `FETCH_MIDDLEWARE_KEY` and `get_rpc_middlewares()` onto `RPC_MIDDLEWARE_KEY` in `WebComPyAppConfig.plugins` declaration order.
  4. In the browser, `app.run()` invokes `on_app_ready(ctx)` once the browser `RenderContext` is ready.
- **Script emission**: `PluginManager.scripts` flattens `get_scripts()` from all discovered plugins and integrates alongside `WebComPyAppConfig.scripts` into `scripts_head` and `scripts_body` during HTML generation.

## Pitfalls

- **Invalid plugin path format**: Omitting `:` or referencing a symbol that is not a subclass of `WebComPyPlugin` raises `WebComPyPluginException` immediately at app creation time.
- **Sharing mutable state on the plugin instance across requests**: One plugin instance lives for the lifetime of `WebComPyApp`. Storing mutable request state on `self` leaks across concurrent SSR requests — put request-scoped values in `ctx.di_scope` inside `on_render_context_init(ctx)` instead.
- **Assuming `on_app_ready(ctx)` runs during SSR/SSG**: `on_app_ready` runs only inside `app.run()` in the browser; code needed on both server and browser belongs in `get_providers()` or `on_render_context_init(ctx)`.
- **Factory providers re-running per component**: Non-class callables inside `get_providers()` follow `DIScope` caching rules — invoked lazily once per `RenderContext` scope, not per `inject()` call.

## Next steps

- Understand how `get_providers()` and `ctx.di_scope` resolve and isolate dependencies in [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
- Learn middleware ordering rules (`middlewares[0]` outermost) in [Middleware](/documents/advanced/middleware).
- Register global route guards cleanly from `on_app_init(app)` in [Routing Deep Dive](/documents/advanced/routing-deep-dive).
- Inspect how generated HTML places `scripts_head` / `scripts_body` in [SSR & SSG](/documents/advanced/ssr-and-ssg).
