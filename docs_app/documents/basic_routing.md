---
title: Routing
description: Configure client-side routes with Router, RouterView, RouterLink, route parameters, query strings, hash vs history modes, and use_router().
---

# Routing

WebComPy includes a built-in client-side router under `webcompy.router` so single-page applications can map URLs to page components without full-page reloads. URL changes flow into reactive signals that automatically update the active view and navigation links.

## At a glance

Define a flat `Router`, mount `RouterView()` in your root layout, and navigate with `RouterLink`:

```python
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router, RouterContext, RouterLink, RouterView


@define_component()
def HomePage(context: ComponentContext[RouterContext]):
    return html.DIV(
        {},
        html.H1({}, "Home"),
        RouterLink(to="/users/42", text=["View User 42"]),
    )


@define_component()
def UserPage(context: ComponentContext[RouterContext]):
    user_id = context.props.path_params.get("id", "")
    return html.H1({}, f"User #{user_id}")


@define_component()
def NotFoundPage(context: ComponentContext[RouterContext]):
    return html.H1({}, "Page not found")


@define_component()
def AppRoot(context: ComponentContext[None]):
    return html.DIV(
        {},
        html.NAV(
            {},
            RouterLink(to="/", text=["Home"], active_class="active", exact=True),
            RouterLink(to="/users/42", text=["Sample User"], active_class="active"),
        ),
        html.MAIN({}, RouterView()),
    )


router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/users/{id}", "component": UserPage},
    default=NotFoundPage,
    mode="history",
)

app = WebComPyApp(root_component=AppRoot, router=router)
```

## Flat route table and `RouterView`

Pass one or more route dictionaries (`{"path": ..., "component": ...}`) to `Router(...)`, plus an optional `default=` fallback component for unmatched paths:

| Option | Purpose | Default |
|---|---|---|
| `*pages` | Route mappings with `"path"` and `"component"` (plus optional `"path_params"` for SSG enumeration) | — |
| `default` | Component rendered when no route matches | Built-in `"Not Found"` fallback |
| `mode` | `"hash"` (`#/path`) or `"history"` (`/path`) | `"hash"` |
| `base_url` | Subpath prefix stripped when hosting `"history"` apps below domain root | `""` |

Place `RouterView()` wherever matched page components should render inside your root layout.

## Routing modes: hash vs history

- **Hash mode (`mode="hash"`, default)**: URLs look like `#/users/42`. Hash changes stay inside the browser, so hash apps work on any static file host with zero server rewrite configuration.
- **History mode (`mode="history"`)**: produces clean URLs like `/users/42`. Use history mode when serving through `webcompy-cli` / ASGI SSR or deploying static files generated per route with `webcompy generate`. When hosting under a subdirectory (such as GitHub Pages project sites), set `base_url="/repo-name"`.

## Dynamic parameters, query strings, and navigation state

Annotate routed page components with `ComponentContext[RouterContext]` to inspect the matched route through `context.props`:

```python
@define_component()
def SearchPage(context: ComponentContext[RouterContext]):
    page = context.props.query.get("page", "1")
    tag = context.props.path_params.get("tag", "all")
    filter_state = context.props.params
    return html.P({}, f"Tag={tag}, page={page}, state={filter_state}")
```

| `RouterContext` attribute | Type | Meaning |
|---|---|---|
| `context.props.path` | `str` | Current matched app path |
| `context.props.path_params` | `dict[str, str]` | Values captured from `{param}` segments in the route pattern |
| `context.props.query` | `dict[str, str]` | Parsed URL query string parameters (non-empty values) |
| `context.props.params` | `dict[str, Any]` | JSON-serializable navigation state stored in `history.state` |

## `RouterLink` and active styling

`RouterLink` renders an `<a>` element that intercepts left-clicks for SPA navigation while keeping valid `href` attributes for copy-link, open-in-new-tab, and SSR output:

```python
from webcompy.router import RouterLink
from webcompy.signal import use_state

user_params = use_state(lambda: {"id": "42"})
query_params = use_state(lambda: {"tab": "activity"})

RouterLink(
    to="/users/{id}",
    text=["Activity"],
    path_params=user_params,
    query=query_params,
    active_class="is-active",
    exact=True,
)
```

- Pass `text=[...]` as a list of strings and/or signals (`list[str | SignalBase[Any]]`).
- Pass `path_params`, `query`, or `params` as `Signal`s when parameterized targets or history state change dynamically.
- When `active_class` is set and the link matches the active URL (`exact=False` matches child prefixes by default; `exact=True` requires an exact match), `RouterLink` appends `active_class` to `class` and sets `aria-current="page"`.

## Reading the active match with `use_router()`

Inside any component under the router scope, call `use_router()` to inject the active `Router` and read `router.current_match` reactively:

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import use_router


@define_component()
def BreadcrumbBar(context: ComponentContext[None]):
    router = use_router()
    current_path = use_computed(lambda: router.current_match.value.path if router.current_match.value else "/")
    return html.SPAN({}, current_path)
```

For imperative navigation triggered by application setup or callbacks where an `app` instance is in scope, use `app.set_path("/about")`.

## Notes & caveats

- `RouterLink` requires `"text"` as a list (`text=["Home"]`), not a bare string.
- Always pass non-empty query values when constructing `query` signals — empty-valued query parameters (`?tab=`) are omitted during query parsing.

## Next steps

- Try nested workspace layouts and route guards interactively in the [Routing](/documents/examples/routing) example.
- Build validated forms and controls in [Forms](/documents/basic/forms).
- Load remote data for routed views in [HTTP & Async](/documents/basic/http-and-async).
- Understand how history-mode routes pre-render on the server and block recursive self-fetches in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Continue to [Routing Deep Dive](/documents/advanced/routing-deep-dive) for nested child routes (`children` + index routes), `lazy()` code splitting, navigation guards (`before_route_change` / `after_route_change` / `on_route_error`), and scroll restoration.
- Full API: [Elements, Routing & DI API](/documents/api/elements-and-routing).
