---
title: Migrating from Jinja2 + FastAPI
description: Architecture guide, ASGI strangler integration, live before/after comparison, and phase-by-phase checklist for teams migrating from Jinja2 templates and FastAPI.
---

# Migrating from Jinja2 + FastAPI

WebComPy lets Python teams replace request-scoped Jinja2 views and ad-hoc JavaScript with reactive Python components while keeping an existing FastAPI backend running throughout the transition.

> **Important framing**: WebComPy's [`render_template()`](/documents/basic/template-html) compiles an intentional reactive subset — it is **not** a drop-in Jinja2 engine. Inheritance directives (`{% extends %}`, `{% block %}`, `{% macro %}`, `{% include %}`, `{% set %}`) raise `WebComPyException` at compile time because Python components, props, and slots take over composition. See [Jinja2 Compatibility Notes](/documents/migration/compatibility-notes) for every exact error string and replacement.

## Architecture shift

Moving from Jinja2 + FastAPI to WebComPy changes *where* UI composition happens, *how* state evolves after initial load, and *how* server routes collaborate with templates:

| Concern | Jinja2 + FastAPI | WebComPy |
|---|---|---|
| Rendering lifecycle | Request-scoped: server renders HTML string per HTTP request | Dual-environment: same Python components pre-render SSR/SSG HTML on server and hydrate into live PyScript DOM in browser |
| Template composition | `{% extends %}`, `{% block %}`, `{% include %}`, `{% macro %}` | `@define_component()` functions, typed `props`, `slots`, and `RouterView()` |
| Local state & updates | Stateless strings on server; manual JS/HTMX mutations in browser | Reactive `Signal`, `Computed`, `ReactiveList`, `ReactiveDict`, `use_*` composables |
| URL routing | FastAPI `@app.get("/...")` returning `TemplateResponse` | Backend keeps `/api/*` routes; frontend owns page routes via `Router` and `RouterLink` |
| Initial page data | Context `dict` passed directly into `templates.TemplateResponse(...)` | Component fetches `/api/*` via `HttpClient` / `use_async_result()` (or typed RPC), baked into `#__webcompy_data__` during SSR |
| Forms & mutations | HTML form `POST` + server validation + HTTP 303 redirect (PRG) | Client validation with `use_field()` / `use_form()` + `:bind`, submitting asynchronously to JSON/RPC endpoints |
| Styling | Global CSS stylesheets referenced in `<head>` | Per-component `scoped_style` dicts or `css_text()` in `webcompy-scope` + theme tokens |
| Automated tests | FastAPI `TestClient` checking response HTML strings | Browserless `TestRenderer` + `create_test_asgi_app()` + real-browser Playwright E2E |

## Choosing an integration strategy

Pick the hosting topology that matches how much of your application is moving to WebComPy right now:

| Strategy | Process owner | When to choose | Trade-offs |
|---|---|---|---|
| **1. Standalone WebComPy** | `python -m webcompy start` or static host (`webcompy generate`) | New frontend with external APIs or pure static/client-side app | Simplest setup; backend routes live in another service or are mocked via middleware |
| **2. Mount backend under WebComPy** | WebComPy CLI (`WebComPyServerConfig.mounts`) | Green-field or UI-first app that only needs a handful of lightweight ASGI API endpoints | WebComPy owns server lifecycle and `generate` SSR fetches; mounted apps cannot shadow `/` or `/_webcompy*` |
| **3. Host mounts WebComPy (Recommended for migration)** | Existing FastAPI host (`uvicorn host:app`) | Migrating an existing FastAPI + Jinja2 monolith cleanly route by route | Zero disruption to auth, DB pools, middleware, background tasks, or legacy HTML routes |

### Strategy 1: Standalone WebComPy

When a frontend only talks to already-deployed JSON services or runs fully statically, configure your project normally with `WebComPyApp` and serve via `webcompy start` or `webcompy generate`:

```python
from webcompy.app import WebComPyApp

app = WebComPyApp(root_component=AppRoot, router=router)
```

### Strategy 2: Mount FastAPI under WebComPy (`mounts`)

When WebComPy already owns the server command, attach FastAPI routers under an `/api` prefix in `webcompy_config.py` using `WebComPyServerConfig.mounts`:

```python
from fastapi import FastAPI
from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

import my_app.app as app_module

api = FastAPI()


@api.get("/health")
def health():
    return {"status": "ok"}


config = WebComPyBuildConfig(
    app_module,
    server=WebComPyServerConfig(port=8080, mounts=lambda: {"/api": api}),
)
```

See [Mounting ASGI apps under WebComPy](/documents/server/asgi-integration#mounting-asgi-apps-under-webcompy) for validation rules and static generation interaction.

### Strategy 3: Host mounts WebComPy (Strangler pattern)

When migrating an active Jinja2 + FastAPI app, keep FastAPI in charge and mount WebComPy under a dedicated prefix such as `/app` first, while legacy Jinja2 routes continue serving untouched paths:

```python
from fastapi import FastAPI
from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy_cli import create_asgi_app
from webcompy_cli.config import WebComPyBuildConfig
from webcompy_server import configure_server_context

import frontend.app as app_module

frontend_app = WebComPyApp(
    root_component=AppRoot,
    router=frontend_router,
    config=WebComPyAppConfig(base_url="/app/"),
)

serving = create_asgi_app(frontend_app, WebComPyBuildConfig(app_module, app_var="frontend_app"), mode="prod")

host = FastAPI()


@host.get("/api/users")
async def list_users():
    return [...]


host.mount("/app", serving.asgi)
configure_server_context(frontend_app, root_app=host)
```

> **Pair `base_url` with the mount prefix**: `WebComPyAppConfig(base_url="/app/")` MUST match `host.mount("/app", ...)`. If they drift, emitted `<base>` tags, PyScript wheel URLs, `/_webcompy-ui/` stylesheets, and history-mode router links resolve outside the mount prefix. See the complete runnable host-mount snippet and checklist in [Embedding WebComPy in a FastAPI or Starlette host](/documents/server/asgi-integration#embedding-webcompy-in-a-fastapi-or-starlette-host).

## Live before/after: user-list search

Below is a small user-directory page implemented the traditional Jinja2 + FastAPI way (`Before`), followed immediately by its reactive WebComPy equivalent running live in your browser (`After`). Both share the exact same `/api/users` data contract.

### Before: Jinja2 templates + FastAPI route

```html
<!-- templates/base.html  [1] -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}App{% endblock %}</title>
    <link rel="stylesheet" href="/static/app.css"> <!-- [6] -->
</head>
<body>
    <header class="shell-header">
        <h1>{% block heading %}Directory{% endblock %}</h1>
    </header>
    <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

```html
<!-- templates/users.html  [2] -->
{% extends "base.html" %}
{% block title %}Team Directory{% endblock %}
{% block heading %}Team Directory{% endblock %}

{% block content %}
<form method="get" action="/users" class="controls"> <!-- [3] -->
    <input type="search" name="q" value="{{ q }}" placeholder="Filter by name or email...">
    <input type="hidden" name="role" value="{{ role }}">
    <button type="submit">Filter</button>
</form>

{% for user in users %} <!-- [5] -->
    <p>{{ user.name }} ({{ user.role | title }})</p>
{% else %}
    <p class="empty-state">No matching users.</p>
{% endfor %}
{% endblock %}
```

```python
# main.py  [4]
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

USERS = [
    {"id": 1, "name": "Alice Chen", "email": "alice@example.com", "role": "admin", "active": True},
    {"id": 2, "name": "Bob Martinez", "email": "bob@example.com", "role": "editor", "active": True},
]


@app.get("/users")
def users_page(request: Request, q: str = "", role: str = "all"):
    matched = [
        u
        for u in USERS
        if (role == "all" or u["role"] == role)
        and (not q or q.lower() in u["name"].lower() or q.lower() in u["email"].lower())
    ]
    return templates.TemplateResponse(
        request,
        "users.html",
        {"users": matched, "q": q, "role": role},
    )


@app.get("/api/users")
def list_users_api():
    return USERS
```

The interactive WebComPy version below replaces `TemplateResponse` with `PageShell`, `use_async_result`, `HttpClient.get("/api/users", response_type=list[User])`, and `:bind` + `Computed`. On this static documentation site, `create_users_mock()` intercepts `/api/users` through `FetchMiddleware` so filtering and reloads complete locally with zero failing network requests.

## Why each line changed

Each numbered callout in the "Before" code corresponds directly to a pattern in the WebComPy source shown under **Code** above:

1. **`base.html` → `PageShell` component with `slots` `[1]`**: Instead of HTML file inheritance, layout structure becomes a typed Python `@define_component()` that places `context.slots("default")` inside `<main>`. During SSR/SSG and client routing, the shell renders real Light DOM wrappers without re-parsing shared HTML fragments.
2. **`{% extends %}` / `{% block %}` → parent wrapper call `[2]`**: `MigrationUsersApp` calls `PageShell({"title": "Team Directory"}, slots={"default": ...})`. Multi-page apps go one step further and put a persistent nav shell around [`RouterView()`](/documents/basic/routing).
3. **`<form method="get">` full-page reload → `:bind` + `Computed` `[3]`**: Typing into the search input updates `query` immediately through `:bind="query"`. Recomputing `filtered_users` refreshes only the matching list rows in the DOM without any HTTP round-trip or page flicker.
4. **`TemplateResponse` context dict → `HttpClient` + `use_async_result()` `[4]`**: The backend simplifies to a typed JSON endpoint (`@app.get("/api/users")`), while the component loads data asynchronously via `HttpClient.get("/api/users", response_type=list[User])`. Notice that keeping `/api/users` mocked via [`FetchMiddleware`](/documents/examples/fetch-middleware) lets the demo and unit tests run offline before rewiring to FastAPI.
5. **`{% for %}...{% else %}` → reactive `{% for %}` loop + sibling `{% if not filtered_users %}` `[5]`**: WebComPy rejects `{% else %}` directly inside `{% for %}` (`{% else %} outside of {% if %} block`). Rendering the `<ul class="user-list">` loop alongside a separate `{% if not filtered_users %}...{% endif %}` guard inside [`render_template()`](/documents/basic/template-html) keeps the reactive list mounted while toggling the empty-state message cleanly whenever filters match zero rows.
6. **Global `app.css` → `PageShell.scoped_style` / `MigrationUsersApp.scoped_style` `[6]`**: Component CSS classes are isolated automatically in `webcompy-scope`, preventing selector leaks across migrated and unmigrated screens.

## Directive-by-directive conversion table

Use this quick lookup while porting `.html` templates into components and `render_template()`:

| Jinja2 construct | Status | WebComPy replacement | Reference |
|---|---|---|---|
| `{% extends "base.html" %}` | **Rejected** | Root layout component wrapping `RouterView()` or shell component with `slots` | [Components](/documents/basic/components) / [Routing](/documents/basic/routing) |
| `{% block body %}...{% endblock %}` | **Rejected** | Named/default entries in `slots={"body": lambda: ...}` read via `context.slots(...)` | [Components](/documents/basic/components#props-and-slots) |
| `{% include "part.html" %}` | **Rejected** | Extract a `@define_component()` and render via Python call or `<my-part>` tag | [HTML Templates](/documents/basic/template-html#component-tags-in-templates) |
| `{% macro %}` / `{% call %}` | **Rejected** | Define a helper function returning `html.*` or a `@define_component()` with slots | [Components](/documents/basic/components) |
| `{% import %}` / `{% from ... import %}` | **Rejected** | Standard Python `import` statements at module or setup scope | [Components](/documents/basic/components) |
| `{% set x = ... %}` / `{% with %}` | **Rejected** | Python local variables or `Computed(...)` / `use_computed(...)` signals passed in context | [Reactive State](/documents/basic/reactive-state) |
| `{% filter upper %}...{% endfilter %}` | **Rejected** | Apply expression filter `{{ text \| upper }}` or Python helper function | [Compatibility Notes](/documents/migration/compatibility-notes#built-in-filters-and-filter-differences) |
| `{{ val \| upper }}` (16 core filters) | **Supported / Renamed** | Built-in filter pipe (`trim`, `length`, `join`, `default`, etc.) or Python helper in context | [Compatibility Notes](/documents/migration/compatibility-notes#built-in-filters-and-filter-differences) |
| `{% if %}` / `{% elif %}` / `{% else %}` | **Supported** | Same directive syntax; binds reactive `SwitchElement` when reading a `Signal` | [HTML Templates](/documents/basic/template-html#conditionals-and-loops) |
| `{% for x in items %}` & `loop.*` | **Supported** | Same loop syntax + `loop.index`, `index0`, `revindex`, `revindex0`, `first`, `last`, `length` | [HTML Templates](/documents/basic/template-html#loops-for-and-loop-metadata) |
| `{% for x in items %}...{% else %}` | **Rejected** | Reactive `{% for ... %}{% endfor %}` loop paired with a sibling `{% if not items %}` empty-state guard | [Compatibility Notes](/documents/migration/compatibility-notes#rejected-directives-and-exact-errors) |
| `{# comment #}` & `{% raw %}` | **Supported** | Stripped comments and verbatim `{% raw %}...{% endraw %}` blocks work identically | [HTML Templates](/documents/basic/template-html#comments-and-raw-blocks) |
| `{{ val \| safe }}` | **Rejected** | `raw_html(...)` element helper for sanitized HTML | [Elements & Events](/documents/basic/elements-and-events) |
| `{{ url_for("name", id=1) }}` | **Replaced** | `RouterLink(to="/items/{id}", path_params=...)` + `WebComPyAppConfig.base_url` | [Routing](/documents/basic/routing) |
| `{% trans %}` / `{% pluralize %}` | **Rejected** | `use_i18n()` translation catalog and cookie locale helpers | [Internationalization](/documents/advanced/i18n) |

## Concern-by-concern migration

### 1. Routing split: pages vs data routes

Separate browser navigation from HTTP data APIs cleanly:

- Keep FastAPI endpoints under JSON prefixes such as `/api/...`, health checks (`/healthz`), webhooks, and OAuth callbacks on the host.
- Move HTML page routes (`GET /dashboard`, `GET /users/{id}`) into WebComPy's client `Router` using `mode="history"`. During host embedding at `/app`, client routes map `/app/` → `"/"` and `/app/users/{id}` → `"/users/{id}"` inside WebComPy once `base_url="/app/"` is paired with `host.mount("/app", ...)`.
- Learn flat routing and query/path params in [Routing](/documents/basic/routing), and nested layouts, navigation guards (`before_route_change`), and `lazy()` code splitting in [Routing Deep Dive](/documents/advanced/routing-deep-dive).

### 2. Context dicts → `HttpClient`, typed RPC, and hydration baking

In FastAPI + Jinja2, your route handler prepares a `dict` synchronously and passes it to `TemplateResponse`. In WebComPy, components request data themselves with `HttpClient.get(...)` + `use_async_result()` or declarative [RPC Contracts](/documents/advanced/rpc-contracts):

1. During SSR on the server, `configure_server_context(app, root_app=host)` routes internal `HttpClient` requests (such as `/api/users`) **in-process** directly against your FastAPI `host` via ASGI transport — zero loopback TCP overhead.
2. Resolved `AsyncResult` states, HTTP response caches, and `use_*` signal values are baked into `<script id="__webcompy_data__">` inside the SSR HTML.
3. When PyScript boots in the browser, initial components hydrate immediately from that baked payload without re-fetching `/api/users` on initial load.

Read [HTTP & Async](/documents/basic/http-and-async) for client calls and [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer) for payload gating, factory skip rules, and collision-safe transfer IDs.

### 3. Forms: POST-Redirect-GET → `use_field` / `use_form` + `:bind`

Replace server form postbacks and flash redirects with typed reactive validation and JSON submission:

```python
@host.post("/api/users")
async def create_user(payload: CreateUserPayload):
    ...
```

Bind fields interactively using `use_field(use_state(...), validators=[...])`, aggregate with `use_form(...)`, wire inputs with `:bind` or `webcompy.ui` controls (`Input`, `FormField`, `Select`, `Checkbox`), and call `HttpClient.post("/api/users", json=values)` inside `form.submit(...)`. See [Forms](/documents/basic/forms) and [UI Primitives](/documents/basic/ui-primitives).

### 4. Global CSS → component `scoped_style` and cascade layers

Break monolithic global CSS files into per-component `scoped_style` dictionaries (or multi-rule CSS strings parsed via `css_text()`):

- Styles attached to `Component.scoped_style` isolate selectors by `webcompy-cid-*` attribute inside the `webcompy-scope` layer.
- Shared typography, spacing, and color tokens come from `--color-*` and `--space-*` CSS variables documented in [Styling & Themes](/documents/basic/styling-and-themes) and [Styling Deep Dive](/documents/advanced/styling-deep-dive).

### 5. Auth and sessions via cookies + middleware headers

Existing cookie-based sessions and bearer headers carry straight over because WebComPy runs on the same origin under your FastAPI host:

- **HttpOnly session cookies**: Browser `fetch()` sends same-origin cookies automatically; during SSR, `ServerFetchPort` forwards request context cleanly against `root_app=host`.
- **Bearer / CSRF headers**: Register one shared `FetchMiddleware` (or `RpcMiddleware` for typed RPC calls) inside root setup/plugin setup to attach `Authorization` or `X-CSRF-Token` headers uniformly on every client request. See [Middleware](/documents/advanced/middleware).

### 6. Reusing FastAPI SSE and WebSocket endpoints

Existing FastAPI `StreamingResponse(..., media_type="text/event-stream")` and `@app.websocket("/ws")` endpoints need zero rewrite on the backend — consume them directly with `use_event_source()` and `use_websocket()` in WebComPy components. See [Server-Sent Events](/documents/advanced/event-source) and [WebSocket](/documents/advanced/websocket).

## Phased strangler checklist

Migrate safely in incremental deploys, verifying exit criteria before moving to the next phase:

| Phase | Goal | Key mechanics & docs | Exit criteria |
|---|---|---|---|
| **Phase 0: Host mount smoke** | Mount empty shell at `/app` beside untouched Jinja2 routes | [ASGI Integration](/documents/server/asgi-integration#embedding-webcompy-in-a-fastapi-or-starlette-host) | `uvicorn host:app` serves legacy `/` normally and `/app/` returns 200 SSR HTML + hydrates without console errors |
| **Phase 1: Shell & first read-only view** | Port `base.html` to layout component + one read-only page | [Components](/documents/basic/components), [Routing](/documents/basic/routing) | Page shell matches visual chrome; `RouterLink` navigation works client-side and refreshes directly at `/app/<route>` |
| **Phase 2: Data routes & SSR transfer** | Move route context dict into FastAPI `/api/*` endpoint + `use_async_result()` | [HTTP & Async](/documents/basic/http-and-async), [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer) | Initial HTML includes `#__webcompy_data__`; browser does not issue a duplicate `GET /api/...` on first load |
| **Phase 3: Interactive forms** | Convert PRG forms to `use_form()` + `:bind` + JSON POST/PATCH | [Forms](/documents/basic/forms), [Middleware](/documents/advanced/middleware) | Inline client validation runs before request; auth/CSRF headers attach via middleware; server mutation updates reactive view |
| **Phase 4: Realtime & typed RPC** | Connect live dashboards/feeds to SSE/WebSocket or typed RPC contracts | [Server-Sent Events](/documents/advanced/event-source), [RPC Contracts](/documents/advanced/rpc-contracts) | Shared FastAPI SSE/WebSocket endpoints stream cleanly into `use_event_source` / `use_websocket` with reconnect recovery |
| **Phase N: Cut over `base_url="/"`** | Flip WebComPy mount to root once Jinja2 page routes are empty | [ASGI Integration](/documents/server/asgi-integration), [Serving Modes](/documents/server/serving-modes) | Remove `Jinja2Templates` dependency for UI routes; update `WebComPyAppConfig(base_url="/")` and mount `serving.asgi` at `"/"` |

## Gotchas and what stays server-side

### Common migration gotchas

- **Self-site recursion guards (`blocked_paths`)**: During SSR, WebComPy blocks `HttpClient` from fetching WebComPy's own HTML page paths (`blocked_paths`), preventing recursive render loops. Always fetch JSON `/api/*` endpoints hosted by FastAPI rather than HTML routes — see [`blocked_paths` matching rules](/documents/advanced/ssr-and-ssg#self-site-fetches-and-blocked-paths).
- **`base_url` / mount prefix mismatch**: Never change `host.mount("/app", ...)` without updating `WebComPyAppConfig(base_url="/app/")` in lockstep — see [URL prefixing, `base_url`, and blocked paths](/documents/server/asgi-integration#url-prefixing-base_url-and-blocked-paths).
- **Hyphenated component tag derivation**: Calling a component declaratively inside `render_template()` requires a hyphenated tag matching the PascalCase function name (`<page-shell>` → `PageShell`). Unmatched hyphenated tags raise `WebComPyException` immediately; non-hyphenated tags stay plain HTML elements. See [Component tags in templates](/documents/basic/template-html#component-tags-in-templates).
- **Avoid passing `locals()` as template context**: Jinja2 teams sometimes pass `{**locals()}` in prototypes. In WebComPy, pass an explicit context dictionary containing only the `Signal`s, `Computed`s, plain data, and event handlers the template references so temporary setup variables never leak and `KeyError` catches typos cleanly.

### What stays server-side (honest scope note)

WebComPy is an interactive browser SPA + pre-rendering framework — **not** a general-purpose string template library. Keep Jinja2 (or plain Python formatting/f-strings) on your FastAPI server for:

- **Transactional email bodies** (multipart HTML/plain emails sent by background workers)
- **PDF, invoice, and downloadable report generation** fed to WeasyPrint / wkhtmltopdf
- **XML feeds, RSS, sitemaps, and server-to-server webhook payloads**
- **Static email/fragment partials that never execute Python in the browser**

> **Coming from Django templates?** Django template syntax shares many constructs with Jinja2 (`{{ var }}`, `{% if %}`, `{% for %}`, filters, `extends`/`block`/`include`). The conversion tables above apply conceptually to Django templates too, though Django ORM views and WSGI adapters are outside this guide's FastAPI + ASGI scope.

## Next steps

- Look up every rejected Jinja2 directive, filter edge case, and exact error string in [Jinja2 Compatibility Notes](/documents/migration/compatibility-notes).
- Read the complete, copy-pasteable host-mount example in [ASGI Integration](/documents/server/asgi-integration).
- Deep-dive on [`render_template()`](/documents/basic/template-html), [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer), and [Middleware](/documents/advanced/middleware).
- Browse exact signatures in [Template & Markdown API](/documents/api/template-and-markdown) and [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
