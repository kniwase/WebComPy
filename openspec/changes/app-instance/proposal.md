## Why

WebComPyApp is currently a thin wrapper that delegates almost everything to the internal `AppDocumentRoot` via the private `__component__` property. Server-side code (dev server, SSG) accesses app internals through `app.__component__.routes`, `app.__component__.set_path()`, etc. Meanwhile, application configuration lives in a separate `webcompy_config.py` file as a `WebComPyConfig` instance, disconnected from the app definition. The CLI discovers both via `import_module` heuristics, and bootstrapping relies on module-level global singletons (`Router._instance`, `RouterView._router`, `Component._head_props`, `ComponentStore`). This fragmented architecture makes the framework harder to learn, harder to test, and prevents multiple app instances from coexisting. Adopting a FastAPI-style application instance — where the app object owns its configuration, state, and lifecycle methods — will centralize the developer-facing API, enable programmatic server startup, and lay the groundwork for isolating app scope per instance.

## What Changes

- **`WebComPyApp` becomes the central application object** with lifecycle methods (`run`, `serve`, `generate`) instead of being a thin wrapper accessed via `__component__`
- **`app.run(selector)`**: Browser entry point — mounts and renders the app into the specified DOM selector (default `#webcompy-app`), replacing the current `app.__component__.render()` pattern
- **`app.serve(config)`**: Server entry point — starts the dev server (replaces `python -m webcompy start` as the sole invocation method)
- **`app.asgi_app`**: ASGI application property — returns a Starlette app that can be mounted into other ASGI frameworks (replaces `_asgi_app.py` module-level pattern)
- **`app.generate(config)`**: SSG entry point — generates static site output (replaces `python -m webcompy generate` as the sole invocation method)
- **Type-safe configuration objects**: `AppConfig` (browser+server), `ServerConfig` (dev server), `GenerateConfig` (SSG) replace `WebComPyConfig`, passed into `WebComPyApp.__init__` or lifecycle methods
- **Transparent property forwarding**: `app.routes`, `app.router_mode`, `app.set_path()`, `app.head`, `app.style`, `app.set_title()`, `app.set_meta()`, etc. — replace `app.__component__.*` access pattern
- **Multiple app instances possible**: Remove `Router._instance` singleton constraint, `RouterView._instance` singleton constraint — enabling app-scoped isolation and easier testing
- **`ComponentStore` becomes per-app**: Move from global `@_instantiate` singleton to app-owned instance, enabling test isolation and multi-app coexistence
- **`Component._head_props` becomes per-app**: Move from `ClassVar` to app-owned `HeadPropsStore`, injected through DI or app context
- **`_defer_*` module globals become per-app**: `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` move to app-scope
- **CLI backward compatibility**: `python -m webcompy start` and `python -m webcompy generate` continue to work by discovering app instance from bootstrap module (with deprecation warnings), while also supporting direct `app.serve()` / `app.generate()` invocation
- **`webcompy_config.py` deprecated**: Settings migrate to `AppConfig` passed to `WebComPyApp`; old `WebComPyConfig` continues to work with `DeprecationWarning`

## Capabilities

### New Capabilities
- `app-config`: Type-safe configuration objects (AppConfig, ServerConfig, GenerateConfig) for application and deployment settings
- `app-lifecycle`: Application lifecycle methods (run, serve, asgi_app, generate) for browser, server, and SSG entry points

### Modified Capabilities
- `app`: WebComPyApp gains transparent property forwarding and lifecycle methods; `__component__` access deprecated
- `cli`: CLI commands support direct app instance invocation in addition to existing config discovery; `WebComPyConfig` deprecated in favor of `AppConfig`
- `architecture`: Singletons removed; app instance becomes the scope boundary for shared state
- `components`: `ComponentStore` and `_head_props` become per-app instead of global; `_defer_*` globals move to app scope

## Impact

- **`webcompy/app/_app.py`**: Major expansion — lifecycle methods, transparent properties, config acceptance
- **`webcompy/app/_root_component.py`**: Selector-based mounting, per-app state injection
- **`webcompy/app/_config.py`** (new): AppConfig, ServerConfig, GenerateConfig dataclasses
- **`webcompy/cli/_server.py`**: Refactor to use `app.serve()` / `app.asgi_app`
- **`webcompy/cli/_asgi_app.py`**: Deprecate in favor of `app.asgi_app`
- **`webcompy/cli/_generate.py`**: Refactor to use `app.generate()`
- **`webcompy/cli/_config.py`**: Deprecate `WebComPyConfig` in favor of `AppConfig`
- **`webcompy/cli/_utils.py`**: Update `get_app()` to support new patterns
- **`webcompy/cli/_html.py`**: Update generated PyScript bootstrap to use `app.run()`
- **`webcompy/cli/template_data/`**: Update project template
- **`webcompy/router/_router.py`**: Remove `_instance` singleton constraint
- **`webcompy/router/_view.py`**: Remove `_instance` singleton constraint
- **`webcompy/components/_generator.py`**: `ComponentStore` becomes per-app (breaking change to `@_instantiate` pattern)
- **`webcompy/components/_component.py`**: `_head_props` becomes per-app; `_defer_*` globals move to app scope
- **`tests/conftest.py`**: Remove singleton reset fixtures (no longer needed)
- **`tests/test_router_advanced.py`**: Remove `Router._instance = None` workarounds
- **`tests/e2e/`**: Update bootstrap files

## Known Issues Addressed

- Multiple global singletons (Router, RouterView, ComponentStore, Component._head_props) — resolved by making all state per-app
- Router singleton makes testing require explicit cleanup — resolved by removing singleton constraint
- Location popstate proxy must be manually destroy()ed — related to Router scope isolation

## Non-goals

- **Provide/Inject (DI) system implementation**: This change focuses on the app instance architecture. DI will be implemented in a separate change (`feat/provide-inject`) and is a prerequisite for fully wiring per-app state through the component tree. During this change, `__set_router__` and similar patterns may be retained as internal bridges until DI is available.
- **Complete removal of `__component__` and `__set_router__`**: These will be deprecated with `DeprecationWarning` but not yet removed (removal reserved for a future major version).
- **Fine-grained DOM patching**: Not related to this change.
- **Plugin system**: Out of scope.
- **Changing the component definition API**: `@define_component`, `context.props`, `context.slots()` remain unchanged.