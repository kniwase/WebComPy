# Router

## Overview

WebComPy provides client-side routing with hash mode and history mode. The router is integrated with the reactive system — `Location` extends `ReactiveBase[str]`, so route changes propagate reactively.

## Router (Singleton)

- **Only one instance allowed** (`_instance` class variable; raises `WebComPyComponentException` on duplicate)
- **Modes**: `"hash"` (`#/path`) or `"history"` (`/path`)
- **`base_url`**: For sub-path deployment (normalized with leading/trailing slashes)
- **Route definition**: `RouterPage` TypedDict with `path` (required), `component`, optional `path_params`, `meta`
- **Path matching**: Routes compiled to regex patterns; `{param}` syntax for path params (e.g., `/users/{id}`)
- **`__cases__`**: A `computed_property` that evaluates `SwitchElement` cases for all routes — integrates the router directly with `SwitchElement` for reactive route matching
- **`__default__`**: Returns a 404 component or `"Not Found"` string
- **`_generate_router_context()`**: Creates a `TypedRouterContext` with path, query params, path params, and state

## Location (`_change_event_handler.py`)

- Extends `ReactiveBase[str]`
- Wraps `browser.window.location` (hash or pathname+search)
- Registers a `popstate` event listener via `browser.pyscript.ffi.create_proxy` on init
- **`value`** property: reactive, uses `_get_evnet` for dependency tracking
- **`state`** property: reactive, returns `history.state` parsed via `to_dict()`
- **`set_mode(mode)`**: Changes mode and refreshes path (decorated with `_change_event`)
- **`__set_path__(path, state)`**: Updates path and state (decorated with `_change_event`)
- **`destroy()`**: Removes event listener and proxy

## RouterLink

- Extends `Element`, renders as `<a>` tag
- **`_href`**: `computed_property` that builds the URL (hash-prefixed for hash mode, path-based for history mode) with query params and path params
- **`_on_click()`**: Prevents default, pushes state via `browser.window.history.pushState()`, calls `Router.__set_path__`
- validates that `query` and `params` are dicts of the correct types
- **`_refresh()`**: On reactive `to` change, regenerates attrs and children, re-renders

## RouterView (Singleton)

- **Only one instance allowed** (raises `WebComPyComponentException` on duplicate)
- Renders a `SwitchElement` with `Router.__cases__` and `Router.__default__`
- Sets `webcompy-routerview` attribute on the container div
- `__set_router__(router)`: Class method to inject the router instance

## TypedRouterContext

- Generic context for route props: `TypedRouterContext[ParamsType, QueryParamsType, PathParamsType]`
- Cannot be constructed directly (`__init__` raises `NotImplementedError`)
- Created via `TypedRouterContext.__create_instance__(path=, state=, query_params=, path_params=)`
- Properties: `path`, `params` (state), `query`, `path_params`
- **`RouterContext`** type alias: `TypedRouterContext[dict[str, Any], dict[str, str], dict[str, str]]`

## RoutedComponent

- `TypedComponentBase(RouterContext)` — base class for page components that receive router context as props

## create_typed_route()

- Returns a tuple of typed context and link classes: `(TypedRouterContext[...], TypedRouterLink[...])`
- Allows specifying custom types for params, query, and path_params

## Design Constraints

- Router and RouterView are both singletons (enforced at runtime)
- `Router.__cases__` is a `computed_property` — route matching is reactively computed
- `Location.__set_path__` is the central path update mechanism, decorated with `_change_event`
- Path params use `{param}` syntax (similar to Flask)
- Query parameters are URL-decoded; path segments are URL-encoded
- `base_url` stripping uses regex in history mode
- `popstate` proxy must be `destroy()`ed on cleanup