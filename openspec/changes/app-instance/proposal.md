## Why

WebComPyApp is currently a thin wrapper that delegates almost everything to the internal `AppDocumentRoot` via the private `__component__` property. Server-side code (dev server, SSG) accesses app internals through `app.__component__.routes`, `app.__component__.set_path()`, etc. Meanwhile, application configuration lives in a separate `webcompy_config.py` file as a `WebComPyConfig` instance, disconnected from the app definition. The CLI discovers both via `import_module` heuristics.

With DI (`feat/provide-inject`) now merged, `Router._instance`, `Component._head_props`, and `__set_router__` have been eliminated. `HeadPropsStore` and `Router` are DI-provided per app. However, several singletons and module-level globals still prevent multiple app instances from coexisting independently:

- **`RouterView._instance`** still enforces a single RouterView globally
- **`_default_component_store`** is a module-level singleton shared across all apps
- **`_root_di_scope`** is a module-level variable overwritten by the last app created
- **`_defer_after_rendering_depth` / `_deferred_after_rendering_callbacks`** are module globals
- **`WebComPyConfig`** is disconnected from the app instance and requires `webcompy_config.py`
- **`_html.py`** generates `app.__component__.render()` instead of `app.run()`

Adopting a FastAPI-style application instance — where the app object owns its configuration, state, and lifecycle methods — will centralize the developer-facing API, enable programmatic server startup, and complete the per-app isolation that DI started.

## Prerequisite

- **Provide/Inject (DI) system** (`feat/provide-inject`) — MERGED. `Router`, `HeadPropsStore`, `ComponentStore` (bridge), `Context.provide()`, and `useRouter()` are all DI-integrated. This change builds on that foundation.

## What Changes

- **`WebComPyApp` becomes the central application object** with the browser entry point (`run`) and transparent property forwarding, instead of being a thin wrapper accessed via `__component__`
- **`app.run(selector)`**: Browser entry point — mounts and renders the app into the specified DOM selector (default `#webcompy-app`), replacing `app.__component__.render()`
- **`create_asgi_app(app)`**: Module-level function that returns a Starlette ASGI app for serving the application
- **`run_server(app=None)`**: Module-level function that starts the dev server, accepting an optional `WebComPyApp` instance
- **`generate_static_site(app=None)`**: Module-level function for SSG, accepting an optional `WebComPyApp` instance
- **Type-safe configuration object**: `AppConfig` (with `app_package`, `base_url`, `dependencies`, `assets`) replaces `WebComPyConfig` for browser+server shared settings
- **Transparent property forwarding**: `app.routes`, `app.router_mode`, `app.set_path()`, `app.head`, `app.style`, `app.set_title()`, `app.set_meta()`, etc. — replace `app.__component__.*` access pattern
- **`RouterView._instance` singleton removed**: Enables multiple app instances with independent RouterViews
- **`ComponentStore` becomes truly per-app**: Replace `_default_component_store` module-level bridge with per-app `ComponentStore` owned by `WebComPyApp`, solving the import-time registration problem
- **`_root_di_scope` module global removed**: Each app's DI scope is self-contained; no module-level global is needed since server entry points use `app.di_scope` context manager
- **`_defer_*` module globals become per-app**: `_defer_after_rendering_depth` and `_defered_after_rendering_callbacks` move to the `WebComPyApp` instance
- **CLI backward compatibility**: `python -m webcompy start` and `python -m webcompy generate` continue to work by discovering app instance from bootstrap module (with deprecation warnings), while also supporting direct `run_server(app)` / `generate_static_site(app)` invocation
- **`webcompy_config.py` deprecated**: Settings migrate to `AppConfig` passed to `WebComPyApp`; old `WebComPyConfig` continues to work with `DeprecationWarning`

## Capabilities

### New Capabilities
- `app-config`: Type-safe configuration object (`AppConfig`) for application settings shared between browser and server
- `app-lifecycle`: Browser entry point (`app.run()`), server entry points (`create_asgi_app`, `run_server`, `generate_static_site`) as module-level functions that accept a `WebComPyApp`

### Modified Capabilities
- `app`: WebComPyApp gains transparent property forwarding, `run()` method, and config; `__component__` access deprecated; app is fully isolated and multi-app-capable
- `cli`: CLI functions accept optional `WebComPyApp` argument; `WebComPyConfig` deprecated in favor of `AppConfig`
- `architecture`: Remaining singletons removed (`RouterView._instance`, `_default_component_store` bridge, `_root_di_scope` global); app instance is the scope boundary for all shared state
- `components`: `ComponentStore` becomes truly per-app (no shared default); `_defer_*` globals move to app scope

## Impact

- **`webcompy/app/_app.py`**: Expansion — `run()` method, transparent properties, config acceptance, per-app ComponentStore, per-app `_defer_*` state
- **`webcompy/app/_root_component.py`**: Selector-based mounting, remove `_set_root_di_scope` call, use app-owned state
- **`webcompy/app/_config.py`** (new): AppConfig dataclass
- **`webcompy/cli/_server.py`**: `create_asgi_app` and `run_server` accept optional `WebComPyApp`
- **`webcompy/cli/_generate.py`**: `generate_static_site` accepts optional `WebComPyApp`
- **`webcompy/cli/_config.py`**: Deprecate `WebComPyConfig` in favor of `AppConfig`
- **`webcompy/cli/_utils.py`**: Update `get_app()` to support new patterns
- **`webcompy/cli/_html.py`**: Update generated PyScript bootstrap to use `app.run()`
- **`webcompy/cli/template_data/`**: Update project template
- **`webcompy/router/_view.py`**: Remove `_instance` singleton constraint
- **`webcompy/components/_generator.py`**: `ComponentStore` becomes truly per-app (remove `_default_component_store` global bridge)
- **`webcompy/components/_component.py`**: `_defer_*` globals move to app scope
- **`webcompy/di/_scope.py`**: Remove `_root_di_scope` module global and `_set_root_di_scope` / `_get_root_di_scope` functions
- **`webcompy/di/__init__.py`**: Update `provide()` / `inject()` fallback logic (remove `_root_di_scope`)
- **`tests/conftest.py`**: Remove `reset_di_scope` fixture (no longer needed once `_root_di_scope` is gone)
- **`tests/e2e/`**: Update bootstrap files to use `app.run()` pattern

## Known Issues Addressed

- `RouterView._instance` singleton — removed, enabling multiple apps
- `_default_component_store` global bridge — replaced with per-app ComponentStore
- `_root_di_scope` module global — removed, each app manages its own scope
- `_defer_*` module globals — moved to app instance scope
- Location popstate proxy must be manually destroy()ed — related to Router scope isolation

## Non-goals

- **Provide/Inject (DI) system implementation**: Already completed in `feat/provide-inject`. This change builds on the existing DI infrastructure.
- **Complete removal of `__component__`**: It will be deprecated with `DeprecationWarning` but not yet removed (removal reserved for a future major version).
- **Fine-grained DOM patching**: Not related to this change.
- **Plugin system**: Out of scope.
- **Changing the component definition API**: `@define_component`, `context.props`, `context.slots()` remain unchanged.