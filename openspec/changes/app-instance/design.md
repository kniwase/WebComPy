## Context

WebComPy's current `WebComPyApp` is a thin wrapper around `AppDocumentRoot`, which inherits from `Component` and handles all the real work. The app object is accessed via `app.__component__` — a private-looking dunder attribute — to reach routes, head management, rendering, etc. Meanwhile, deployment configuration lives in a separate `webcompy_config.py` file as a `WebComPyConfig` instance, and the CLI discovers both through `import_module` heuristics.

Six global singletons underpin the system: `Router._instance`, `RouterView._instance`, `RouterView._router`, `TypedRouterLink._router`, `Component._head_props`, and `ComponentStore`. Module-level globals `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` manage rendering batching. This makes testing require explicit cleanup (`conftest.py` resets singletons per test) and prevents multiple app instances from coexisting.

The Provide/Inject (DI) system is planned as a separate change. This design accounts for that dependency by using temporary internal bridges where DI is not yet available, while structuring the API so that DI-based injection can replace those bridges seamlessly later.

## Goals / Non-Goals

**Goals:**
- Make `WebComPyApp` the single, central application object with clear public API (`app.run()`, `app.serve()`, `app.asgi_app`, `app.generate()`)
- Enable `app.run(selector)` for browser mounting with configurable selector (default `#webcompy-app`)
- Enable `app.serve()` and `app.asgi_app` for server-side usage, including ASGI mounting into other frameworks
- Enable `app.generate()` for programmatic static site generation
- Introduce type-safe configuration objects (`AppConfig`, `ServerConfig`, `GenerateConfig`) to replace `WebComPyConfig`
- Forward `AppDocumentRoot` properties through `WebComPyApp` to eliminate `__component__` access
- Remove singleton constraints from `Router` and `RouterView` to enable multiple app instances
- Move `ComponentStore`, `HeadPropsStore`, and `_defer_*` globals to per-app scope
- Maintain backward compatibility with deprecation warnings for old APIs

**Non-Goals:**
- Implement Provide/Inject (DI) — that is a separate change
- Fully remove deprecated APIs (reserved for a future major version)
- Change the component definition API (`@define_component`, context, props, slots)
- Implement fine-grained DOM patching or a virtual DOM

## Decisions

### Decision 1: Delegation pattern — WebComPyApp does NOT inherit Component

**Choice:** WebComPyApp owns an `AppDocumentRoot` instance and delegates to it via properties/methods.

**Alternative considered:** WebComPyApp inherits from Component (or a mixin of Component's functionality).

**Rationale:** `Component` has browser-specific methods (`_init_node`, `_mount_node`, `_render`) that call `browser.document.*` APIs. `WebComPyApp` also has server-specific methods (`serve`, `generate`). Inheriting Component would put browser-only and server-only code on the same class, violating the dual-environment principle. Delegation keeps the concerns separated while providing a clean public API.

### Decision 2: Three-tier configuration objects

**Choice:** `AppConfig` (shared browser+server), `ServerConfig` (dev server only), `GenerateConfig` (SSG only).

```
AppConfig                     — browser + server
  base_url: str = "/"
  dependencies: list[str] = []
  assets: dict[str, str] | None = None

ServerConfig                  — dev server only
  port: int = 8080
  dev: bool = False
  static_files_dir: str = "static"

GenerateConfig               — SSG only
  dist: str = "dist"
  cname: str = ""
  static_files_dir: str = "static"
```

**Alternative considered:** Single monolithic config class.

**Rationale:** `base_url` and `dependencies` affect browser-side routing and PyScript config, so they belong in `AppConfig` (shared). `port` and `dist` are purely server-side deployment concerns. Separating them avoids passing irrelevant config to the browser and makes each object's purpose clear. All use `@dataclass` for type safety and validation via `__post_init__`.

### Decision 3: `app.run(selector)` with default `#webcompy-app`

**Choice:** `app.run(selector="#webcompy-app")` as the browser entry point.

**Implementation:**
- `AppDocumentRoot._init_node()` changes from hardcoded `getElementById("webcompy-app")` to using `querySelector(selector)`
- The selector is stored on the `WebComPyApp` instance during `run()`
- SSG/HTML generation continues to use fixed `id="webcompy-app"` for the mount element
- `app.run()` without arguments uses the default selector, matching current behavior

**Alternative considered:** Store `mount_selector` in `AppConfig`.

**Rationale:** The selector is a runtime concern (where to mount in the browser), not a build/deploy concern. It doesn't affect SSG output. Putting it in `AppConfig` would mean passing browser-specific runtime config to the server, violating separation of concerns. The `run()` parameter is the right place.

### Decision 4: `app.serve()` wraps uvicorn internally

**Choice:** `app.serve(port=8080, dev=False, **kwargs)` calls `uvicorn.run(self.asgi_app, ...)`.

**Alternative considered:** `app.serve()` only configures, user must call `uvicorn.run()` separately.

**Rationale:** FastAPI's pattern (`uvicorn.run(app)`) works because FastAPI apps are ASGI-compatible directly. WebComPy needs to build a Starlette app from the WebComPyApp config (wheel packaging, static files, routes). Wrapping this in `serve()` provides the best developer experience while `app.asgi_app` provides escape-hatch flexibility for advanced use cases (mounting into existing Starlette/FastAPI apps).

### Decision 5: `app.asgi_app` property lazily builds the Starlette app

**Choice:** `app.asgi_app` is a `@property` that calls `create_asgi_app(self, self._config, ...)` and caches the result.

**Alternative considered:** Build the ASGI app eagerly in `__init__`.

**Rationale:** ASGI app construction involves wheel building and file I/O. This should only happen when actually needed (server startup or ASGI mounting). Lazy construction also avoids import issues in the browser environment where `uvicorn` and `starlette` are unavailable.

### Decision 6: `app.generate()` as instance method

**Choice:** `app.generate(dist="dist", cname="", static_files_dir="static")` or `app.generate(config=GenerateConfig(...))`.

**Alternative considered:** Keep `generate_static_site()` as a free function that takes an `app`.

**Rationale:** An instance method is more discoverable and follows the FastAPI pattern. It also gives the method access to `self._config` and `self._root` without parameter passing.

### Decision 7: ComponentStore — per-app instance with auto-registration bridge

**Choice:** `ComponentStore` becomes a regular class (remove `@_instantiate`). Each `WebComPyApp` owns a `ComponentStore` instance. `ComponentGenerator.__init__` auto-registers into a default global store (for backward compatibility), but `AppDocumentRoot` uses the app-specific store for style collection.

**Transition plan:**
1. Remove `@_instantiate` decorator; `ComponentStore` becomes a normal class
2. Add a module-level `_default_component_store` singleton for backward compatibility during `ComponentGenerator.__init__` auto-registration
3. `WebComPyApp.__init__` creates its own `ComponentStore` and passes it to `AppDocumentRoot`
4. `AppDocumentRoot.style` reads from app-specific store
5. After DI is implemented, `ComponentGenerator` can register into the active app's store via context

### Decision 8: HeadPropsStore — per-app instance

**Choice:** `HeadPropsStore` moves from `Component._head_props` ClassVar to a per-app instance owned by `WebComPyApp`. Components access it through an app context reference.

**Transition plan:**
1. `WebComPyApp.__init__` creates `HeadPropsStore` instance
2. `Component` stores a reference to its app's `HeadPropsStore` (set during `Component.__init__` via the existing `_active_component_context` ContextVar or a new `_active_app_context` ContextVar)
3. `_set_title`, `_set_meta`, title/meta getters all use the instance reference instead of `Component._head_props`
4. `AppDocumentRoot.head` uses its app's `HeadPropsStore`

### Decision 9: `_defer_*` globals — per-app scope

**Choice:** `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` move to the `WebComPyApp` instance. `start_defer_after_rendering()` and `end_defer_after_rendering()` need the app context (via ContextVar or passed reference).

**Transition plan:**
1. Move state to `WebComPyApp` as instance attributes
2. `start_defer_after_rendering()` and `end_defer_after_rendering()` receive the app reference from `_active_app_context` ContextVar
3. `SwitchElement._refresh()` and other callers use the context

### Decision 10: Router and RouterView — singleton removal

**Choice:** Remove `Router._instance` and `RouterView._instance` ClassVar singletons.

**Transition plan:**
1. Remove `if Router._instance: raise` guard from `Router.__init__`
2. Remove `if RouterView._instance: raise` guard from `RouterView.__init__`
3. `RouterView.__init__` receives `Router` reference from app context instead of `RouterView._router` ClassVar
4. `TypedRouterLink.__init__` receives `Router` reference similarly
5. `__set_router__` methods remain temporarily with `DeprecationWarning`; they will be removed after DI integration

### Decision 11: `_asgi_app.py` — deprecation path

**Choice:** `_asgi_app.py` continues to work but emits `DeprecationWarning`. The module-level `app` variable is replaced by calling `get_app(config).asgi_app`. New code uses `app.serve()` or `app.asgi_app` directly.

### Decision 12: Transparent property forwarding

**Choice:** `WebComPyApp` forwards these properties from `AppDocumentRoot`:

| WebComPyApp property | Delegates to |
|---|---|
| `routes` | `self._root.routes` |
| `router_mode` | `self._root.router_mode` |
| `set_path(path)` | `self._root.set_path(path)` |
| `head` | `self._root.head` |
| `style` | `self._root.style` |
| `scripts` | `self._root.scripts` |
| `set_title(title)` | `self._root.set_title(title)` |
| `set_meta(key, attrs)` | `self._root.set_meta(key, attrs)` |
| `append_link(attrs)` | `self._root.append_link(attrs)` |
| `append_script(attrs, script, in_head)` | `self._root.append_script(attrs, script, in_head)` |
| `set_head(head)` | `self._root.set_head(head)` |
| `update_head(head)` | `self._root.update_head(head)` |

`app.__component__` emits `DeprecationWarning` and returns `self._root`.

## Risks / Trade-offs

**[Risk: ComponentStore auto-registration dual-path is confusing]** → During the transition period, `ComponentGenerator.__init__` registers into a module-level default store AND the app's store may need explicit registration. Mitigation: document clearly that this is temporary until DI provides scoped registration. The default store exists only for backward compatibility.

**[Risk: Per-app HeadPropsStore requires Component to know its app]** → Components need a reference to their app's HeadPropsStore. Without DI, this requires a ContextVar (`_active_app_context`) set during app initialization. Mitigation: This ContextVar is already the pattern used for `_active_component_context`. It's a well-understood mechanism in this codebase.

**[Risk: SSG and dev server test coverage is limited]** → The CLI code currently has no unit tests for dispatch, server startup, or SSG pipeline. Refactoring `serve()` and `generate()` into instance methods changes the code but doesn't add test coverage. Mitigation: Add integration tests for the new API paths before deprecating old ones.

**[Risk: Breaking change for users who import Router._instance]** → Any external code that relies on `Router._instance` will break. Mitigation: This is an internal implementation detail not part of the public API. Document in the changelog.

**[Risk: `app.asgi_app` property does I/O on first access]** → Building the ASGI app involves wheel packaging. If accessed unexpectedly (e.g., during import), it triggers I/O. Mitigation: Make it a lazy `@cached_property` and document that it should only be called when actually serving.

**[Trade-off: Deprecation period length]** → `__component__`, `__set_router__`, `WebComPyConfig`, and `_asgi_app.py` will emit `DeprecationWarning` but remain functional. This keeps backward compatibility but means we carry both old and new code paths. The payoff is a smooth migration for existing projects.

## Migration Plan

1. **Phase A — Non-breaking API addition** (can be done before DI):
   - Add `AppConfig`, `ServerConfig`, `GenerateConfig` dataclasses
   - Add `app.run()`, `app.serve()`, `app.asgi_app`, `app.generate()`
   - Add transparent property forwarding
   - Update `_html.py` to generate `app.run()` bootstrap code
   - Update project template (`bootstrap.py` → `app.py` pattern)

2. **Phase B — Singleton removal + per-app state** (best done after DI, but possible with ContextVar bridge):
   - Remove `Router._instance` and `RouterView._instance` singleton enforcement
   - Move `HeadPropsStore` to per-app
   - Move `ComponentStore` to per-app
   - Move `_defer_*` to per-app
   - Add `_active_app_context` ContextVar for Component access

3. **Phase C — Deprecation warnings**:
   - `app.__component__` → DeprecationWarning
   - `RouterView.__set_router__()` → DeprecationWarning
   - `TypedRouterLink.__set_router__()` → DeprecationWarning
   - `WebComPyConfig` → DeprecationWarning (point to `AppConfig`)
   - `_asgi_app.py` → DeprecationWarning

4. **Rollback**: Each phase is independently deployable. If issues arise, revert that phase's commit while keeping others.

## Open Questions

- **`AppConfig.base_url` vs `Router(base_url=...)`**: Currently `Router.__init__` accepts a `base_url` parameter. If `AppConfig` also has `base_url`, which takes precedence? Proposal: `AppConfig.base_url` is the source of truth; the Router should receive it from the app, not independently. But this means `Router.__init__` might need to drop its `base_url` parameter, or the app must validate consistency.
- **`app_package_path` replacement**: Currently `WebComPyConfig.app_package_path` tells the CLI where the app code lives. With `AppConfig`, this is replaced by the fact that the app instance itself IS the import target. But `app.serve()` still needs to know the app package name for wheel building. Should this be derived from `__module__`, or explicitly configured?
- **ComponentStore per-app timing**: `ComponentGenerator` instances are created at module import time (when `@define_component` runs), which is before `WebComPyApp.__init__`. Until DI provides a way to register into a specific app's store, `ComponentGenerator` must still register somewhere at import time. The `_default_component_store` bridge handles this, but it means the first app created gets all components from all imported modules. Is this acceptable during the transition?