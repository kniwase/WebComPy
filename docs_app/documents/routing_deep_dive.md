---
title: Routing Deep Dive
description: Build multi-level layouts and guarded navigation with nested RouterPage children, RouterView depth reuse, lazy() preloading, async route guards, and automatic scroll restoration.
---

# Routing Deep Dive

WebComPy's router scales from flat page tables to multi-level application shells without rewriting links or URL structure. Nested `RouterPage` children compose parent layouts cleanly via `RouterView`, `lazy()` defers code imports until navigation or idle/hover preload, navigation guards run synchronously or asynchronously with redirect loops capped, and manual browser scroll restoration preserves Back/Forward positions automatically.

For basic single-level route declarations, path/query params, and `RouterLink`, start with [Routing](/documents/basic/routing).

## When to use

- **Declaring simple flat routes, path parameters, or hash/history basics** — start with [Routing](/documents/basic/routing).
- **Sharing persistent parent chrome across child routes (`children` + index `""`)** — configure nested `RouterPage` trees on `Router`.
- **Splitting large sections behind dynamic imports (`lazy()`) or protecting routes with auth checks (`before_route_change`)** — use the deep-dive APIs below.
- **Inspecting SSR path blocking rules for history routes** — see [SSR & SSG](/documents/advanced/ssr-and-ssg).

## Setup

Define nested routes using `children` (and an optional `""` index child), wrap child views in a layout `RouterView()`, and attach `lazy()` components with absolute module paths:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router, RouterContext, RouterLink, RouterView, lazy


@define_component()
def AdminLayout(context: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "admin-shell"},
        html.NAV(
            {},
            RouterLink(to="/admin", text=["Overview"], active_class="active", exact=True),
            RouterLink(to="/admin/users", text=["Users"], active_class="active"),
        ),
        html.MAIN({}, RouterView()),  # depth 1 renders matched child route
    )


@define_component()
def AdminIndex(context: ComponentContext[RouterContext]):
    return html.H2({}, "Admin Overview")


router = Router(
    {
        "path": "/admin",
        "component": AdminLayout,
        "children": [
            {"path": "", "component": AdminIndex},
            {"path": "/users", "component": lazy("my_app.pages.admin_users:AdminUsersPage", __file__)},
            {"path": "/users/{uid}", "component": lazy("my_app.pages.user_detail:UserDetailPage", __file__)},
        ],
    },
    mode="history",
    preload=True,
)
```

Notice the root page component uses `RouterView()` at depth 0 for `AdminLayout`, while `AdminLayout` renders an inner `RouterView()` at depth 1 for `AdminIndex`, `AdminUsersPage`, or `UserDetailPage`.

## Recipes

### 1. Guard an admin console with async checks, redirects, and error hooks

Append callables to `router.before_route_change`, `router.after_route_change`, and `router.on_route_error` during app initialization (or from `WebComPyPlugin.on_app_init`). A guard receives `(from_path, to_path)`: returning `False` cancels navigation, returning a path string (such as `"/login"`) redirects and replaces history instead of pushing, and returning `True` or `None` allows navigation to proceed:

```python
from webcompy.exception import WebComPyException


async def require_admin(from_path: str, to_path: str) -> bool | str | None:
    if to_path.startswith("/admin") and not await is_authenticated():
        return "/login"  # redirects via history replace_url
    return None


def track_navigation(new_path: str) -> None:
    print("Navigated to:", new_path)


def handle_route_error(err: Exception) -> bool:
    if isinstance(err, WebComPyException):
        print("Routing error handled:", err)
        return True  # suppresses propagation
    return False


router.before_route_change.append(require_admin)
router.after_route_change.append(track_navigation)
router.on_route_error.append(handle_route_error)
```

Guards receive clean app-internal paths (`base_url` and `#` prefix stripped, trailing slashes normalized) in both `"history"` and `"hash"` modes.

### 2. Defer bundle imports with `lazy()` and control preloading

Wrap heavy route components in `lazy("package.module:AttributeName", __file__)`. Relative import paths (starting with `.`) and missing `:` separators raise `WebComPyRouterException` immediately when `lazy()` is called:

```python
from webcompy.router import Router, lazy

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/reports", "component": lazy("my_app.pages.reports:ReportsPage", __file__)},
    preload=True,  # default
)
```

With `preload=True`:

- In the **browser**, WebComPy schedules unresolved lazy imports via `setTimeout(0)` after the initial render finishes and the loading screen clears, and hovering any `RouterLink` pointing to a lazy component also preloads on `mouseenter`.
- During **SSR/SSG**, `Router.preload_lazy_routes()` resolves lazy routes immediately so static HTML pre-rendering covers all routes.
- Set `preload=False` to defer module loading strictly until navigation (or `RouterLink` hover).

### 3. Configure `RouterLink` active styling and scroll restoration

Pass `active_class=` (and `exact=`) to `RouterLink` for automatic `aria-current="page"` and class updates across client navigations and SSR:

```python
from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.router import RouterLink

# Prefix match (/admin/users keeps "/admin" active), segment-boundary safe ("/adminx" does not match)
nav_link = RouterLink(to="/admin", text=["Admin"], active_class="is-active")

# Exact match ("/" or index tabs)
home_link = RouterLink(to="/", text=["Home"], active_class="is-active", exact=True)

# Disable framework scroll restoration if your app manages scroll manually
app = WebComPyApp(
    root_component=AppShell,
    router=router,
    config=WebComPyAppConfig(scroll_restoration=False),
)
```

By default (`scroll_restoration=True`), WebComPy sets browser `history.scrollRestoration = "manual"`: push navigations scroll to `(0, 0)`, while Back/Forward (`popstate`) restores each left page's saved offset and retries up to 3 macro tasks if async content (`Suspense` / lazy modules) initially leaves the document shorter than the saved offset.

## Behavior notes

- **Wrapper-free `RouterView` depth resolution**: `RouterView` extends `DynamicElement` (emitting no wrapper `<div>`) and determines its level (`0`, `1`, ...) by counting `RouterView` ancestors at match time. A `RouterView` deeper than the matched chain renders nothing without raising. Each `RouterView` subscribes through its own internal `Computed` edge so destroying one nested view removes only its own subscription.
- **Chain level reuse identity**: At each chain level `N`, the mounted component instance (and its signals, scroll, and child state) stays alive across navigations **only when all three match**: the route record at level `N`, the accumulated `path_params` from levels `0..N` (where child params override parent params on collision), and the full `query` dictionary. Any change remounts level `N` and every deeper level `> N` exactly once.
- **Implicit per-level error isolation**: `RouterView` wraps every chain level in an implicit `ErrorBoundary` whose fallback renders nothing and resets on subsequent navigations, so a failing child route does not tear down its parent layout (`AdminLayout` stays mounted).
- **Async guards & latest-wins concurrency**:
  - When all `before_route_change` callbacks are synchronous, `__set_path__` runs guards, updates history/URL, updates `current_match`, and invokes `after_route_change` synchronously before returning.
  - When any guard returns an awaitable, WebComPy tracks a monotonic navigation token so starting a newer navigation supersedes older pending ones (superseded async guards finish executing, but their URL updates and `after_route_change` callbacks are dropped).
  - Redirect chains exceeding 10 hops raise `WebComPyRouterException` through `on_route_error`.
  - Exceptions raised inside any guard cancel the navigation and route to `on_route_error`.
- **Browser history traversal (`popstate`)**: Back/Forward triggers route matching and scroll restoration directly without re-running `before_route_change` guards.
- **Per-request clones & SSG dynamic expansion**: Each `RenderContext` clones hooks from `app.router` via `Router._clone_for_request()` so request-local hook mutations never leak across requests. During `webcompy generate`, nested dynamic parent `path_params` expand as a Cartesian product (child keys win on name collision).

## Pitfalls

- **Parent route with `children` and no `""` index route**: Navigating directly to the bare parent path (e.g., `/admin`) without a `{"path": "", ...}` child falls through to the router's `default` / `"Not Found"` fallback — parent components with `children` never render as leaf routes.
- **Query string changes remount nested levels**: Because `query` is part of match identity, changing `?tab=a` to `?tab=b` remounts the active component chain unless you manage sub-tab state with reactive signals instead of query parameters.
- **Relative `lazy()` paths**: `lazy(".admin:Page", __file__)` is rejected at definition time; always supply an absolute dotted module path (`"my_app.pages.admin:Page"`).
- **Mutating `router.before_route_change` from the injected per-request router**: `Router._clone_for_request()` isolates hook lists per request, so appending guards inside a component only affects that single render context. Register global guards on `app.router` at startup or inside `WebComPyPlugin.on_app_init(app)`.
- **Assuming `before_route_change` intercepts browser Back/Forward**: Browser `popstate` events update location outside app guard chains and do not run `before_route_change`.

## Next steps

- Explore nested child layouts, parameter extraction, and a redirect guard live in the [Routing](/documents/examples/routing) example.
- Review flat route definitions, `use_router()`, and basic navigation in [Routing](/documents/basic/routing).
- Hook `app.router` guards and page tracking cleanly from [Plugins](/documents/advanced/plugins).
- Learn how SSR self-site fetch blocking and async route boundaries work in [SSR & SSG](/documents/advanced/ssr-and-ssg) and [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
- Combine route isolation with [Error Handling](/documents/basic/error-handling).
- Full API: [Elements, Routing & DI API](/documents/api/elements-and-routing).
