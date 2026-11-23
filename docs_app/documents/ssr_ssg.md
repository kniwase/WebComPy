---
title: SSR & SSG
description: Understand WebComPy's dual-environment render pipeline, dev/prod/generate modes, per-request RenderContext isolation, and self-site fetch handling during pre-rendering.
---

# SSR & SSG

WebComPy runs the same Python component tree in two environments: standard CPython on the server to produce complete HTML during server-side rendering (SSR) and static site generation (SSG), and PyScript/Emscripten in the browser to adopt those DOM nodes and handle live user interaction.

Use SSR when requests need per-visit server rendering or live server endpoints alongside pre-rendered HTML; use SSG (`webcompy generate`) when every route can be pre-rendered into static HTML files for CDN or static hosting. Both paths execute through the exact same `create_asgi_app()` pipeline so server output and static build output match byte for byte.

## The dual-environment pipeline

```text
Server (CPython)
  create_asgi_app(app, build_config, mode="prod" | "dev")
    │
    ▼  (per HTTP request, or via httpx ASGITransport during `webcompy generate`)
  send_html(request)
    ├─► app.create_render_context(path)  ──► fresh ServerRenderContext + Server ports
    ├─► await ctx._root._render()        ──► sequential tree render + Suspense awaiting
    ├─► await scheduler.await_pending()  ──► drain all scheduled async tasks
    ├─► collect_transfer_data(root)      ──► snapshot fetches, signals, async_results, resources
    ├─► generate_html(...)               ──► HTML + scoped CSS + <script id="__webcompy_data__">
    └─► finally: ctx.dispose()           ──► teardown DI scope, EffectScope, signal graph nodes
          │
          ▼  HTML shipped over HTTP / written to dist/{path}/index.html
Browser (PyScript / Emscripten)
  app.run(selector="#webcompy-app")
    ├─► BrowserRenderContext + read & remove <script id="__webcompy_data__">
    ├─► adopt existing SSR DOM nodes & wire reactive bindings
    └─► settle render tasks, close hydration window, remove loading screen ──► live SPA
```

Because `generate_html()` runs after `await_pending()` finishes, async component setup, `Suspense` boundaries, reactive scoped styles, and initial `use_async_result` fetches all appear in the initial HTML rather than flashing empty placeholders.

## Dev, prod, and static generation modes

WebComPy uses one serving assembly (`create_asgi_app`) across local development, production ASGI serving, and static site generation:

| Mode | CLI / API entry point | `mode` | Hot reload SSE | How HTML is produced |
|---|---|---|---|---|
| Dev server | `python -m webcompy start --dev` | `"dev"` | Included (`/_webcompy_reload`) | Per-request `ServerRenderContext` (with no-cache headers on the app wheel) |
| Prod server | `python -m webcompy start` | `"prod"` | Excluded | Per-request for `history` mode; startup cache for `hash` mode |
| Static site (SSG) | `python -m webcompy generate` | `"prod"` | Excluded | In-process requests through `httpx.ASGITransport` |

During static site generation, `generate_static_site()` resolves build artifacts once via `create_asgi_app(app, build_config, mode="prod")`, opens an in-process `httpx.AsyncClient(transport=ASGITransport(app=serving.asgi))`, fetches each declared route, and writes the returned HTML to `dist/`:

- **History mode (`mode="history"`)**: all lazy route components (including parent layouts) are pre-resolved via `_preload()` before fetching routes; each route is written to `dist/{path}/index.html`, plus a `dist/404.html` page for unmatched paths. Dynamic routes can declare concrete parameter sets via `"path_params"` for static enumeration.
- **Hash mode (`mode="hash"`)**: only the root path `/` is pre-rendered and written to `dist/index.html`, because hash routing (`#/path`) resolves sub-paths inside the browser.

> **Note**: Each generated route starts from a fresh `ServerRenderContext` and collects only that route's state, so generated HTML is independent of route generation order. Running `webcompy generate` on the same source produces deterministic per-route output regardless of iteration order.

## Per-request `RenderContext` isolation

`WebComPyApp` itself is an immutable definition holder: it stores configuration, component definitions, router configuration, and plugin classes, and holds **no** mutable per-request state. All mutable runtime state belongs to the active `RenderContext`:

- **DI scope and port instances**: `ServerDOMPort`, `ServerFetchPort` (cloned per context), `ServerResourcePort` (fresh per context), `ServerCookiePort`, and `ServerAsyncSchedulerPort`.
- **Router clone and head state**: each context clones the router definition for the requested `path`, plus its own `HeadPropsStore`, `HeadElement`, and scoped style collector.
- **Signal graph tracking**: `_active_consumer` and notification state live in `ContextVar`s, keeping concurrent async SSR requests completely isolated.
- **Lifecycle teardown**: `send_html()` wraps rendering in `try ... finally: ctx.dispose()`. Even if rendering fails halfway, DI child scopes, `EffectScope`s, and consumer subscriptions are always released.

In hash mode on the server (`create_asgi_app` + `run_server`), `/` is pre-rendered once synchronously before `uvicorn` starts serving requests (`_pre_render_hash_mode_html`). If pre-rendering fails during startup, the exception propagates immediately and the server aborts cleanly instead of starting with broken HTML.

## Self-site fetches and blocked paths

Components calling `HttpClient` during SSR/SSG resolve requests through `ServerFetchPort`:

- **Self-site URLs** (paths starting with `/` or `.`) are routed directly through `httpx.ASGITransport` against the application's ASGI app—no TCP loop or live server is needed during `webcompy generate`.
- **External URLs** (`https://...`, `http://...`) are sent over standard network HTTP.
- **Relative `.` URLs** resolve from the app's configured `base_url` root (so `./api/data` with `base_url="/myapp/"` targets `/myapp/api/data`) rather than relative to the current page path. Prefer leading-slash absolute paths (`/api/data`).

```text
HttpClient.get(url) during SSR/SSG
  ├─ external ("https://...") ──────────────────────► network httpx client
  ├─ under WebComPyServerConfig.mounts (e.g. "/api") ► in-process ASGI mount (no base_url prefix)
  ├─ matches a page route in blocked_paths ──────────► HTTP 500 error (prevents recursion)
  └─ other self-site path (with base_url prefix) ───► in-process ASGI app route
```

To prevent infinite recursion when a page component accidentally fetches its own route or another HTML page route, `ServerFetchPort` builds `blocked_paths` from `app.routes`:

- Enumerated routes block exact concrete paths (e.g. `"/users/42"`).
- Non-enumerated dynamic patterns (e.g. `"/users/:id"`) use **segment-count-aware prefix matching**, blocking `"/users/42"` (2 segments) while leaving `"/users/42/edit"` (3 segments) or `"/api/users"` unaffected.
- Paths under `WebComPyServerConfig.mounts` are never added to `blocked_paths`, and bypass `base_url` prefixing when dispatched.

> **Important**: During SSG, responses fetched from configured ASGI mounts are cached and embedded into each page's hydration payload, while the mount endpoints themselves are **not** exported as static files under `dist/`. Live client-side mutations or uncached runtime fetches against a mount still require a running server in production.

## Embedding into an existing ASGI host

When mounting a WebComPy ASGI app inside a larger Starlette or FastAPI host application, call `configure_server_context(app, root_app=host)` from `webcompy_server`:

- `configure_server_context(app)` wires `ServerRenderContext` and installs `ServerFetchPort` (and optional `ServerResourcePort`).
- Passing `root_app=host` directs self-site SSR fetches through the parent host ASGI app so components can call host API routes during SSR, while blocking WebComPy's own page routes under `app.config.base_url`.

(Step-by-step host-framework mounting recipes will live in the Server & Tooling guide.)

## Behavior notes & pitfalls

- **SSR vs SSG error policies**: When a component raises inside an `ErrorBoundary` during live SSR, the boundary renders its fallback and returns HTTP `200` for the rest of the page (uncontained errors return `500`, and validation `WebComPyException` errors always propagate). During `webcompy generate`, however, any boundary error fails the build immediately so broken static pages never ship.
- **Guarding browser-only code**: Server Python has no DOM, `window`, or `localStorage`. Wrap imperative browser access in `ClientOnly` (for whole subtrees), `@on_mounted` (runs only on DOM connect in the browser), or check `ENVIRONMENT == "pyscript"` from `webcompy.utils`.
- **Single-file `__main__` scripts**: Package-structured apps keep consistent module dotted names across SSR and browser wheels, which hydration state transfer relies on. Always bootstrap via a package module (`my_app.bootstrap:app`).

## Next steps

- Follow the data snapshot from `<script id="__webcompy_data__">` into browser state in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Coordinate async setups across SSR and the browser with `Suspense`, `ClientOnly`, and the scheduler in [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
- Customize the boot-time waiting state before hydration completes in [Loading Screen](/documents/advanced/loading-screen).
- Revisit route declarations and `ErrorBoundary` basics in [Routing](/documents/basic/routing) and [Error Handling](/documents/basic/error-handling).
