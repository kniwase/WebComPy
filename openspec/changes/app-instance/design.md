## Context

WebComPy's `WebComPyApp` is a thin wrapper around `AppDocumentRoot`, accessed via `app.__component__`. Server-side code (dev server, SSG) calls internal methods like `app.__component__.routes`, `app.__component__.set_path()`, etc. Configuration lives in a separate `webcompy_config.py` as `WebComPyConfig`, and the CLI discovers both via `import_module` heuristics.

The DI system (`feat/provide-inject`) is now merged, eliminating `Router._instance`, `Component._head_props` ClassVar, `__set_router__` methods, and the `@_instantiate` decorator on `ComponentStore`. DI-based injection is working for `Router`, `HeadPropsStore`, and `ComponentStore` (via `_default_component_store` bridge).

Remaining singletons and module-level globals that prevent full multi-app isolation:

- **`RouterView._instance`** — singleton enforcement still blocks multiple RouterViews
- **`_default_component_store`** — module-level singleton shared across all apps; `ComponentGenerator.__init__` registers into it at import time
- **`_root_di_scope`** — module global overwritten by the last `AppDocumentRoot.__init__`; breaks multi-app
- **`_defer_after_rendering_depth` / `_deferred_after_rendering_callbacks`** — module globals, not scoped to any app
- **`WebComPyConfig`** — disconnected from the app instance, requires `webcompy_config.py`
- **`_html.py`** — generates `app.__component__.render()` instead of `app.run()`

The DI scope hierarchy (`DIScope` parent-child tree) is established and working. `WebComPyApp` creates a root `DIScope` and provides `_ROUTER_KEY`, `_HEAD_PROPS_KEY`, and `_COMPONENT_STORE_KEY` into it. Components inherit this scope and create child scopes on `provide()`.

## Goals / Non-Goals

**Goals:**
- Make `WebComPyApp` the single, central application object with clear public API (`app.run()`, `app.serve()`, `app.asgi_app`, `app.generate()`)
- Enable `app.run(selector)` for browser mounting with configurable selector (default `#webcompy-app`)
- Enable `app.serve()` and `app.asgi_app` for server-side usage, including ASGI mounting into other frameworks
- Enable `app.generate()` for programmatic static site generation
- Introduce type-safe configuration objects (`AppConfig`, `ServerConfig`, `GenerateConfig`) to replace `WebComPyConfig`
- Forward `AppDocumentRoot` properties through `WebComPyApp` to eliminate `__component__` access
- Remove `RouterView._instance` singleton to enable multiple app instances
- Move `ComponentStore` to truly per-app ownership (eliminate `_default_component_store` bridge)
- Remove `_root_di_scope` module global (each app manages its own scope lifecycle)
- Move `_defer_*` globals to per-app scope
- Maintain backward compatibility with deprecation warnings for old APIs

**Non-Goals:**
- Implement Provide/Inject (DI) — already completed in `feat/provide-inject`
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

### Decision 4: Server entry points are module-level functions, not app methods

**Choice:** `create_asgi_app(app, config, dev_mode)`, `run_server(app=None)`, and `generate_static_site(app=None)` are module-level functions in `webcompy/cli`. They accept a `WebComPyApp` instance directly.

**Alternative considered:** `app.serve()`, `app.asgi_app`, and `app.generate()` as methods on `WebComPyApp`.

**Rationale:** Making server/SSG entry points methods on `WebComPyApp` would cause import errors in the browser environment (PyScript/Emscripten) because `starlette`, `uvicorn`, `aiofiles`, and other server-only dependencies are unavailable. By keeping them as module-level functions in `webcompy/cli/`, the browser-side `WebComPyApp` import stays lightweight. The CLI module is only imported when `platform.system() != "Emscripten"`.

### Decision 5: `AppConfig` is the user-facing configuration, `WebComPyConfig` is internal

**Choice:** `AppConfig` (with `app_package`, `base_url`, `dependencies`, `assets`) is the developer-facing dataclass. `WebComPyConfig` is retained internally for CLI/server/SSG compatibility but emits `DeprecationWarning`.

**Rationale:** `AppConfig` contains only the settings that affect both browser and server (base URL, dependencies, assets). Settings like `app_package_path`, `server_port`, and `dist` are server-deployment concerns, handled by `WebComPyConfig` internally or derived from `AppConfig`. This keeps the developer API simple while maintaining backward compatibility.

### Decision 7: ComponentStore — truly per-app with import-time registration

**Choice:** Each `WebComPyApp` creates its own `ComponentStore`. `ComponentGenerator.__init__` registers into whichever store is available via DI (`inject(_COMPONENT_STORE_KEY, default=None)`). When no DI scope exists (import time, before any app is created), registration is deferred — the component stores its info locally and registers lazily when first accessed within an app scope. The `_default_component_store` module global is removed.

**Rationale:** The `_default_component_store` bridge is shared by all apps, breaking isolation. The import-time registration problem only exists during CLI-driven workflows where modules load before `WebComPyApp` is created. In the new `app.run()` / `app.serve()` pattern, the app's DI scope is set during `WebComPyApp.__init__`, which runs before component templates execute. For the CLI path (`python -m webcompy start`), the DI scope is set by `_server.py` / `_generate.py` before rendering, so deferred registration can work by triggering component registration lazily.

**Implementation:**
1. `WebComPyApp.__init__` creates a `ComponentStore()` and provides it into `app._di_scope`
2. Remove `_default_component_store` module global from `_generator.py`
3. `ComponentGenerator.__init__` attempts `inject(_COMPONENT_STORE_KEY, default=None)` — if a scope exists, register immediately; if not, store info locally for deferred registration
4. `AppDocumentRoot.__init__` no longer needs to provide `_default_component_store`
5. `AppDocumentRoot.style` uses `inject(_COMPONENT_STORE_KEY)` without fallback

### Decision 8: HeadPropsStore — already per-app via DI (no change needed)

**Status:** COMPLETED by `feat/provide-inject`.

`AppDocumentRoot.__init__` creates a `HeadPropsStore()` and provides it into the app's DI scope via `_HEAD_PROPS_KEY`. Components access it via `inject(_HEAD_PROPS_KEY)`. Each app has its own `HeadPropsStore` in its own DI scope. No further changes are needed for multi-app isolation.

### Decision 9: `_defer_*` globals — move to app instance

**Choice:** `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` become instance attributes on `WebComPyApp`. `start_defer_after_rendering()` and `end_defer_after_rendering()` receive the app reference from `_active_app_context` ContextVar.

**Alternative considered:** Move to `DIScope` as provided values.

**Rationale:** `_defer_*` state is transient rendering state, not a service that needs DI resolution. It's more naturally owned by the app instance. Moving it to `DIScope` would require every `start_defer_after_rendering()` call to resolve from DI, adding overhead for a simple counter/list pair. The `ContextVar` approach mirrors the established pattern for `_active_component_context` and `_active_di_scope`.

**Implementation:**
1. `WebComPyApp.__init__` initializes `self._defer_depth: int = 0` and `self._deferred_callbacks: list[Callable] = []`
2. Add `_active_app_context: ContextVar[WebComPyApp | None]` to propagate app reference through rendering
3. `start_defer_after_rendering()` and `end_defer_after_rendering()` receive app from `_active_app_context.get()`
4. `SwitchElement._refresh()` uses `_active_app_context` to access the app's defer state
5. `AppDocumentRoot._render()` sets `_active_app_context` before rendering and resets after

### Decision 10: RouterView — remove singleton enforcement

**Choice:** Remove `RouterView._instance` ClassVar and singleton enforcement. `RouterView` obtains its `Router` reference exclusively via DI (`inject(_ROUTER_KEY)`), which already works.

**Rationale:** `RouterView.__init__` already resolves the Router via `inject(_ROUTER_KEY)`. The `_instance` check only prevents creating a second RouterView, which is unnecessary when multiple apps should be able to have their own. Removing it is the final step to enable true multi-app coexistence.

**Implementation:**
1. Remove `RouterView._instance: ClassVar[RouterView | None] = None`
2. Remove the `if RouterView._instance: raise` / `RouterView._instance = self` block from `RouterView.__init__`
3. Remove the `TODO` comment about App Instance migration

### Decision 11: Remove `_root_di_scope` module global

**Choice:** Remove `_root_di_scope`, `_set_root_di_scope()`, and `_get_root_di_scope()` from `webcompy/di/_scope.py`. Remove the fallback path in `provide()` and `inject()` that checks `_root_di_scope`.

**Rationale:** `_root_di_scope` was a workaround for the browser environment where `ContextVar` values are lost in JavaScript event handlers. With `app.run()` as the explicit browser entry point, the DI scope is always set at the start of app initialization. The `_root_di_scope` global is overwritten by the last app created, breaking multi-app support. Since `app.run()`, `app.serve()`, and `app.generate()` all set the DI scope explicitly, the module-level fallback is no longer needed.

**Implementation:**
1. Remove `_root_di_scope`, `_set_root_di_scope`, `_get_root_di_scope` from `webcompy/di/_scope.py`
2. Remove `_root_di_scope` fallback from `provide()` and `inject()` in `webcompy/di/__init__.py`
3. Remove `_set_root_di_scope(di_scope)` call from `AppDocumentRoot.__init__`
4. Remove `_active_di_scope.set(app._di_scope)` from `_server.py` and `_generate.py` — since `app.run()` / `app.serve()` / `app.generate()` will manage scope setup internally
5. Update `provide()` and `inject()` to raise `InjectionError` when no scope is active (no fallback)

**Risk:** If Python code runs outside an app context (e.g., in PyScript event handlers), `inject()` will raise instead of falling back to `_root_di_scope`. Mitigation: `app.run()` sets the scope at app initialization time and the scope is inherited by the component tree. Event handlers that call user code will already be within a component context. If this becomes an issue, the scope can be re-established using `with app.di_scope:` in the event handler bridge, which is the correct long-term pattern.

### Decision 12: `_asgi_app.py` — deprecation path

**Choice:** `_asgi_app.py` continues to work but emits `DeprecationWarning`. The module-level `app` variable is replaced by calling `get_app(config).asgi_app`. New code uses `app.serve()` or `app.asgi_app` directly.

### Decision 13: Transparent property forwarding

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

`app.__component__` emits a `DeprecationWarning` and returns `self._root`.

## Risks / Trade-offs

**[Risk: Removing `_root_di_scope` breaks browser event handlers]** → PyScript event handlers may lose the `ContextVar` value. Mitigation: `app.run()` will ensure the scope is set at initialization. If event handlers lose scope, `with app.di_scope:` can be used to re-establish it in the event bridge. This is the correct pattern for multi-app support anyway — each app manages its own scope lifecycle.

**[Risk: ComponentStore import-time registration without `_default_component_store`]** → During CLI-driven workflows (`python -m webcompy start`), modules are imported before `WebComPyApp` is created, so `ComponentGenerator.__init__` runs without a DI scope. Mitigation: The `default=None` approach means component definitions store their info locally. When `WebComPyApp` is created and provides a `ComponentStore`, components can be lazily registered on first resolution. The CLI import sequence ensures `_active_di_scope` is set before rendering, so deferred registration works.

**[Risk: SSG and dev server test coverage is limited]** → The CLI code currently has no unit tests for dispatch, server startup, or SSG pipeline. Refactoring `serve()` and `generate()` into instance methods changes the code but doesn't add test coverage. Mitigation: Add integration tests for the new API paths before deprecating old ones.

**[Risk: Breaking change for `WebComPyConfig` users]** → Any project using `webcompy_config.py` will see `DeprecationWarning` but the old pattern continues to work. Mitigation: `WebComPyConfig` is only used by the CLI, not by runtime code. The deprecation path is clear — migrate to `AppConfig`.

**[Risk: `app.asgi_app` property does I/O on first access]** → Building the ASGI app involves wheel packaging. If accessed unexpectedly (e.g., during import), it triggers I/O. Mitigation: Make it a lazy `@cached_property` and document that it should only be called when actually serving.

**[Trade-off: Deprecation period length]** → `__component__`, `WebComPyConfig`, and `_asgi_app.py` will emit `DeprecationWarning` but remain functional. This keeps backward compatibility but means we carry both old and new code paths. The payoff is a smooth migration for existing projects.

## Migration Plan

1. **Phase A — Non-breaking API addition**:
   - Add `AppConfig` dataclass
   - Add `app.run()`, `app.config`, transparent property forwarding
   - Add `create_asgi_app(app, config)`, `run_server(app)`, `generate_static_site(app)` module-level functions
   - Update `_html.py` to generate `app.run()` bootstrap code
   - Update project template (`bootstrap.py` → `app.py` pattern)

2. **Phase B — Singleton removal + per-app state**:
   - Remove `RouterView._instance` singleton enforcement
   - Move `ComponentStore` to per-app (remove `_default_component_store` bridge)
   - Remove `_root_di_scope` module global and fallback in `provide()`/`inject()`
   - Move `_defer_*` to per-app instance on `WebComPyApp`
   - Add `_active_app_context` ContextVar

3. **Phase C — Deprecation warnings**:
   - `app.__component__` → DeprecationWarning
   - `WebComPyConfig` → DeprecationWarning (point to `AppConfig`)
   - `_asgi_app.py` → DeprecationWarning

4. **Rollback**: Each phase is independently deployable. If issues arise, revert that phase's commit while keeping others.

## Open Questions

- **`AppConfig.base_url` vs `Router(base_url=...)`**: Currently `Router.__init__` accepts a `base_url` parameter. If `AppConfig` also has `base_url`, which takes precedence? Proposal: `AppConfig.base_url` is the source of truth; the Router should receive it from the app, not independently. But this means `Router.__init__` might need to drop its `base_url` parameter, or the app must validate consistency.
- **`app_package_path` replacement**: Currently `WebComPyConfig.app_package_path` tells the CLI where the app code lives. With `AppConfig`, this is replaced by the fact that the app instance itself IS the import target. But `app.serve()` still needs to know the app package name for wheel building. Should this be derived from `__module__`, or explicitly configured?
- **Browser event handler scope re-establishment**: After removing `_root_di_scope`, will PyScript event handlers reliably inherit the `ContextVar` value set by `app.run()`? Need to verify this in the E2E tests. If not, an explicit `with app.di_scope:` wrapper may be needed in the event bridge.