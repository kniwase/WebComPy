# Application Bootstrapping

## Overview

`WebComPyApp` is the entry point that ties together the root component, router, and document head management. It is instantiated by the user's `bootstrap.py` and discovered by the CLI.

## WebComPyApp

- Constructor: `WebComPyApp(*, root_component, router=None)`
- `root_component`: A `ComponentGenerator[None]` (component with no props)
- `router`: Optional `Router` instance
- **`__component__`**: Returns the `AppDocumentRoot` instance
- Delegates head management: `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`

## AppDocumentRoot

- Extends `Component`, wrapping `AppRootComponent`
- `AppRootComponent` is a `NonPropsComponentBase` with template: `html.DIV({"id": "webcompy-app"}, context.slots("root"))`
- If a router is provided, sets `RouterView.__set_router__` and `TypedRouterLink.__set_router__`
- **In browser**: Sets up `Component._head_props.title` watcher to update `browser.document.title`
- **Loading indicator**: On first `_render()`, removes `#webcompy-loading` DOM element
- **Hydration**: `_init_node()` finds `#webcompy-app`, marks it and all children as pre-rendered
- `_mount_node()` is a no-op (root is already in DOM)
- Manages head props: `titles` (ReactiveDict), `head_metas` (ReactiveDict)
- **`style`** property: Returns concatenated scoped CSS from all registered component generators
- **`_render_html()`**: Sets `hidden=True` on the app div during SSG

## Head Management

- `Component._head_props` is a class-level `HeadPropsStore` (singleton across all components)
  - `titles`: `ReactiveDict[UUID, str]` — keyed by component instance ID
  - `head_metas`: `ReactiveDict[UUID, dict[str, dict[str, str]]]` — keyed by component instance ID
- `HeadPropsStore.title`: `computed_property` returning the last title value
- `HeadPropsStore.head_meta`: `computed_property` flattening all meta dicts
- Components set titles/metas via `Component._set_title` / `Component._set_meta`, which store by instance UUID
- On component destruction, the UUID key is removed from both dicts

## Bootstrap Flow (Browser)

1. PyScript loads the webcompy wheel and app wheel packages
2. The bootstrap script runs: `from app_package.bootstrap import app; app.__component__.render()`
3. `AppDocumentRoot._render()` iterates children and renders them
4. Each Element creates/reuses DOM nodes, sets attributes, binds events
5. `#webcompy-loading` div is removed after first render

## Bootstrap Flow (SSG)

1. CLI discovers the `WebComPyApp` via `get_app(config)`
2. For each route, `AppDocumentRoot._render_html()` generates the HTML string
3. The generated HTML includes `<script type="module" src="pyscript core.js">`, a loading screen, and the app div with `hidden=True`

## Design Constraints

- `AppDocumentRoot._get_belonging_component()` returns empty string (root has no component scope)
- `AppDocumentRoot._get_belonging_components()` returns `(self,)` (root is its own component scope)
- Head props use UUID keyed by component instance ID — removed on component destruction