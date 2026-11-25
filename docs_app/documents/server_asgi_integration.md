---
title: ASGI Integration
description: Embed WebComPy inside an existing FastAPI or Starlette host ASGI application with base_url alignment, or mount child ASGI apps under WebComPy.
---

# ASGI Integration

WebComPy runs on standard ASGI (`Starlette` and `uvicorn`). You can integrate it in two directions: **embedding** a WebComPy UI under a path prefix inside an existing FastAPI or Starlette backend, or **mounting** backend API ASGI apps under WebComPy's own server via `WebComPyServerConfig.mounts`.

Choose host embedding when an existing FastAPI/Starlette application already owns authentication, API routes, lifespan hooks, and deployment; choose `WebComPyServerConfig.mounts` when WebComPy owns the primary server process and you want in-process API routes alongside SSR pages.

## Embedding WebComPy in a FastAPI or Starlette host

To mount a WebComPy UI at `/admin` inside an existing FastAPI host application:

1. Pair `WebComPyAppConfig(base_url="/admin/")` with the host mount prefix `/admin`.
2. Build the serving ASGI application with `create_asgi_app(admin_app, build_config, mode="prod")`.
3. Mount `serving.asgi` onto the host at `"/admin"`.
4. Call `configure_server_context(admin_app, root_app=host)` **after** `create_asgi_app()` so self-site SSR fetches dispatch against `host` in-process.

```python
from fastapi import FastAPI
from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router
from webcompy_cli import create_asgi_app
from webcompy_cli.config import WebComPyBuildConfig
from webcompy_server import configure_server_context

import my_admin_app as app_module


@define_component()
def AdminHome(context: ComponentContext[None]):
    return html.H1({}, "Admin Dashboard")


admin_router = Router(
    {"path": "/", "component": AdminHome},
    mode="history",
)

admin_app = WebComPyApp(
    root_component=AdminHome,
    router=admin_router,
    config=WebComPyAppConfig(base_url="/admin/"),
)

build_config = WebComPyBuildConfig(app_module, app_var="admin_app")
serving = create_asgi_app(admin_app, build_config, mode="prod")

host = FastAPI()


@host.get("/api/items")
async def list_items():
    return {"items": [{"id": 1, "name": "Widget"}]}


host.mount("/admin", serving.asgi)
configure_server_context(admin_app, root_app=host)
```

In embedded mode, the host application owns the ASGI server process (`uvicorn host:host` or your production runner) — do **not** call `run_server()`. Calling `configure_server_context(admin_app, root_app=host)` *after* `create_asgi_app()` is important because `create_asgi_app()` wires a standalone `ServerFetchPort` pointing to `serving.asgi`; re-invoking `configure_server_context` with `root_app=host` rewires SSR self-site fetches to route through `host` instead while keeping `serving.artifacts` and existing port settings intact.

## URL prefixing, `base_url`, and blocked paths

When embedding under a prefix such as `/admin`, `WebComPyAppConfig.base_url` and the host's mount path are a required pairing:

| Concern | Effect of `base_url="/admin/"` + `mount("/admin", ...)` |
|---|---|
| `<base>` and asset links | Generated HTML emits `<base href="/admin/">` and prefixes wheels, UI CSS (`/_webcompy-ui/...`), runtime assets, and `/_webcompy-resource/...` under `/admin/` |
| Client router URLs | History-mode `RouterLink` navigation and guard redirects update `window.location` under `/admin/...` |
| Host API fetches during SSR | Calling `HttpClient.get("/api/items")` inside a component runs in-process against `host` via `httpx.ASGITransport` and embeds the response into `#__webcompy_data__` |
| Page recursion guard (`blocked_paths`) | Only WebComPy page routes prefixed with `/admin` (for example `/admin/users`) are blocked from self-site SSR fetches; host routes like `/api/items` remain reachable |
| Standalone host routes | Requests directly to `/api/items` hit the FastAPI/Starlette host unaffected |

If `base_url` and the host mount prefix disagree, emitted script URLs, resource endpoints, or client history updates resolve outside the mount prefix. Always update both together (and see [SSR & SSG](/documents/advanced/ssr-and-ssg#self-site-fetches-and-blocked-paths) for full `blocked_paths` matching details).

## Mounting ASGI apps under WebComPy

When WebComPy owns the process (`python -m webcompy start`), mount sibling ASGI apps — such as a REST API built with Starlette or FastAPI — through `WebComPyServerConfig.mounts` in `webcompy_config.py`:

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import my_app.app as app_module
from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig


async def list_tasks(request):
    return JSONResponse({"tasks": ["ship", "verify"]})


def build_mounts():
    return {
        "/api": Starlette(routes=[Route("/tasks", endpoint=list_tasks)]),
    }


config = WebComPyBuildConfig(
    app_module,
    server=WebComPyServerConfig(
        port=8080,
        mounts=build_mounts,
    ),
)
```

### Mount validation and routing behavior

At startup, `create_asgi_app()` validates every entry returned by `mounts()`:

- **Non-dict return value** or conflicting prefixes raise `WebComPyException` before the server begins accepting requests.
- Mounting at `"/"` is rejected (it would shadow every WebComPy page route).
- Prefixes starting with `"/_webcompy"` are reserved by the framework and rejected.
- Static prefix collisions with any declared route in `app.routes` (such as mounting `/users` when `/users/:id` exists) are rejected.

During SSR, self-site `HttpClient` calls targeting a configured mount prefix (for example `/api/tasks`) are dispatched in-process without prepending `base_url` and are excluded from `blocked_paths`.

### Interaction with static site generation (`webcompy generate`)

During `webcompy generate`, `generate_static_site()` calls `create_asgi_app()` internally, so components pre-rendered into static HTML can still fetch initial data from configured `mounts` via `ASGITransport` and store the snapshot inside `<script id="__webcompy_data__">`. However, `webcompy generate` does **not** export mounted API routes into static files under `dist/` — subsequent browser mutations (`POST`, `PATCH`, `DELETE`, or uncached client fetches) against `/api/...` require a live server in production.

## Next steps

- Follow how `create_asgi_app()` isolates each SSR request and builds `blocked_paths` in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Inspect `WebComPyBuildConfig` and `WebComPyServerConfig` fields in [Project Configuration](/documents/server/project-configuration).
- Run `python -m webcompy start` or `generate` against mounted configs in [CLI Reference](/documents/server/cli-reference).
- Test ASGI apps and SSR HTML output without Playwright using `create_test_asgi_app` in [Testing](/documents/server/testing).
- Migrating an existing server-rendered app piece by piece? Follow the strangler guide in [Migrating from Jinja2 + FastAPI](/documents/migration/from-jinja2-fastapi).
- Full API: [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
