# Tasks: RenderContext Request Isolation

## 1. Signal Graph ContextVar Migration

- [x] 1.1 Convert `_active_consumer` from module-level `SignalNode | None` to `ContextVar[SignalNode | None]` with module-level fallback `_active_consumer_global` in `webcompy/signal/_graph.py`; update `set_active_consumer()` and `get_active_consumer()` to try ContextVar first (`.get()`) and fall back to global when ContextVar is unset
- [x] 1.2 Convert `_in_notification_phase` from module-level `bool` to `ContextVar[bool]` with module-level fallback `_in_notification_phase_global` in `webcompy/signal/_graph.py`; update all direct reads/writes of `_in_notification_phase` to use the accessor
- [x] 1.3 Remove `reset_graph_state()` function from `webcompy/signal/_graph.py` and remove all call sites that invoke it elsewhere in the codebase — epoch is now monotonic (never reset), ContextVar values clean up automatically on async task completion
- [x] 1.4 Update ALL read/write sites throughout the signal module where `_active_consumer` or `_in_notification_phase` are accessed directly (not through `get_active_consumer`/`set_active_consumer`): `producer_accessed()` (line 80-83), `consumer_before_computation()` (line 155-157), `consumer_after_computation()` (line 165-166), `producer_notify_consumers()` (line 96-97)
- [x] 1.5 Run existing signal tests (`pytest tests/ -k "signal"`) to verify no regressions

## 2. RenderContext Class

- [x] 2.1 Create `webcompy/app/_render_context.py` with `RenderContext` class skeleton: `__init__(app, path)`, `render_html(...)`, `dispose()` method signatures; store back-reference to `_app` (immutable WebComPyApp)
- [x] 2.2 Implement `RenderContext.__init__`: create fresh `DIScope()`, enter it with `__enter__()` for server (enter+exit per request) or enter-without-exit for browser; create fresh `ComponentStore()` and provide it; call `_register_deferred_components()` which reads `app._component_generators` (immutable dict on WebComPyApp) and re-registers all generators into the new store; create Server ports (or Browser ports) and provide them; create `HeadPropsStore()` and provide it; create Router instance from `app._router_pages/_router_mode/_router_base_url` and provide it; create `AppDocumentRoot`; call `_on_render_context_init` on plugins
- [x] 2.3 Implement `RenderContext.render_html(**kwargs)`: enter DI scope context (`with self._di_scope:`), set `_active_app_context` to `self`, set `_app_instance` to `self`, call `self._root.render()`, call `set_path(path)` on router, delegate to `generate_html()` helper with `self` as parameter, return HTML string
- [x] 2.4 Implement `RenderContext.dispose()`: exit DI scope via `__exit__()` (for server context where __enter__ was called), call `DIScope.dispose()` (which cascades to children), dispose EffectScopes, clear references (`_root`, `_di_scope`, `_component_store`, `_router`) to allow GC; do NOT reset `_epoch`
- [x] 2.5 Add `RenderContext` property forwarding from its `AppDocumentRoot`: `head` (property), `style` (property), `scripts` (property), `routes` (property), `router_mode` (property), `set_path` (method), `set_title` (method), `set_meta` (method), `append_link` (method), `append_script` (method), `set_head` (method), `update_head` (method), `set_html_attr` (method), `remove_html_attr` (method), `html_attrs` (property)
- [x] 2.6 Add `config` property to `RenderContext` that forwards `self._app.config` for backward compatibility with old `on_app_ready(self, app)` plugins that access `app.config`
- [x] 2.7 Add `@property` `_defer_depth`, `_deferred_callbacks`, and `profile_data` to `RenderContext` (moved/forwarded from `WebComPyApp`)

## 3. WebComPyApp Refactoring

- [x] 3.1 Move mutable state out of `WebComPyApp.__init__`: remove `self._di_scope` (and DI scope creation), `self._root`, `self._component_store`, `self._defer_depth`, `self._deferred_callbacks`, `self._profile_data`; store only immutable state: `self._config`, `self._root_component_def`, `self._router_pages`, `self._router_mode`, `self._router_base_url`, `self._plugin_manager` (stores `_plugin_classes` and `_plugin_instances`), `self._profile`, `self._hydrate`
- [x] 3.2 Implement `WebComPyApp.create_render_context(path="") -> RenderContext`: instantiate `RenderContext(self, path)`, return it
- [x] 3.3 Update `WebComPyApp.__init__` to perform only: store config, store root component definition, store router definition (pages/mode/base_url), create `PluginManager`, call `discover()` and `init_all()` (with DI scope access deferred — `init_all` no longer calls `app.di_scope.provide()`; static providers are registered per RenderContext)
- [x] 3.4 Update `WebComPyApp.run()`: create `RenderContext` via `self.create_render_context()`, enter DI scope (without exit for browser lifetime), call `on_render_context_init` on plugins, call `on_app_ready(ctx)`, call `ctx._root.render()`, store `_active_app_context` and `_app_instance` to the RenderContext
- [x] 3.5 Update `WebComPyApp` property forwarding in browser: `routes`/`router_mode`/`set_path`/`head`/`style`/`scripts`/`set_title`/`set_meta`/`append_link`/`append_script`/`set_head`/`update_head`/`set_html_attr`/`remove_html_attr`/`html_attrs`/`profile_data` — all delegate to `self._render_context` (the RenderContext created by `run()`); if no `_render_context` exists, raise informative error
- [x] 3.6 Server-side `app.di_scope` property: raise `AttributeError` with message directing to `RenderContext.di_scope`; server code MUST use `ctx.di_scope` not `app.di_scope`
- [x] 3.7 Update `_active_app_context` and `_app_instance`: `_active_app_context` now references the `RenderContext` (not `WebComPyApp`); `_set_app_instance()` sets the module-level `_app_instance` to the RenderContext; update `start_defer_after_rendering()` and `end_defer_after_rendering()` to access `RenderContext._defer_depth`/`._deferred_callbacks` via `_active_app_context`/`_app_instance`

## 4. Plugin System Update

- [x] 4.1 Add `on_render_context_init(self, ctx: RenderContext) -> None` method to `WebComPyPlugin` base class (default no-op) in `webcompy/plugin/_plugin.py`
- [x] 4.2 Change `on_app_ready(self, app: WebComPyApp)` signature to `on_app_ready(self, ctx: RenderContext)`; use `inspect.signature()` to detect old signature and issue `warnings.warn("`on_app_ready(self, app)` is deprecated, use `on_app_ready(self, ctx)` instead", DeprecationWarning)` when old signature is detected
- [x] 4.3 Update `PluginManager.init_all()`: remove `self._app.di_scope.provide(...)` call — static providers are collected but not registered yet; `on_app_init(app)` still called; store `_plugin_instances` list
- [x] 4.4 Add `PluginManager.init_render_context(ctx: RenderContext)`: iterate `_plugin_classes`, register each class's `get_providers()` into `ctx.di_scope`; call `on_render_context_init(ctx)` on each `_plugin_instances`
- [x] 4.5 Update `PluginManager.call_on_app_ready(ctx: RenderContext)`: iterate `_plugin_instances`, detect old/new signature via `inspect`, call with RenderContext, issue deprecation warning for old signature
- [x] 4.6 Update `_plugin.py` imports to use `TYPE_CHECKING` for `RenderContext` (forward reference)

## 5. Server Path Update

- [x] 5.1 Update `webcompy/cli/_server.py` `create_asgi_app()` history-mode `send_html` handler: replace `with app.di_scope:` block with `ctx = app.create_render_context(requested_path)`, `try: return HTMLResponse(generate_html(ctx, ...))`, `finally: ctx.dispose()`
- [x] 5.2 Update `webcompy/cli/_server.py` hash-mode: create `ctx = app.create_render_context("/")`, generate HTML once, cache result, `ctx.dispose()` after
- [x] 5.3 Update `generate_html()` in `webcompy/cli/_html.py` to accept `RenderContext` instead of `WebComPyApp`; access app config via `ctx._app.config` or `ctx.config`; access head/style/scripts via `ctx.head`/`ctx.style`/`ctx.scripts`; access root component via `ctx._root`; access plugin scripts via `ctx._app._plugin_manager.scripts`
- [x] 5.4 Add `finally: ctx.dispose()` in the `send_html` handler to guarantee cleanup even on render errors
- [x] 5.5 Update `_get_app_di_scope()` / `_set_app_di_scope()` in `webcompy/di/_scope.py` to work with RenderContext; on the server, `_set_app_di_scope` should be called with the RenderContext's DI scope during rendering

## 6. SSG Path Update

- [x] 6.1 Update `webcompy/cli/_generate.py` `generate_static_site()`: replace `with app.di_scope:` block with per-route `ctx = app.create_render_context(path)`, generate HTML, `ctx.dispose()`
- [x] 6.2 Update `generate_html()` calls in SSG to pass `ctx` (RenderContext) instead of `app` (WebComPyApp)
- [x] 6.3 Verify SSG output is identical before and after the change (existing SSR/SSG tests pass with updated APIs)

## 7. Component System Adaptation

- [x] 7.1 Update `_active_app_context` and `_app_instance` in `webcompy/components/_component.py`: `_active_app_context` now typed as `ContextVar[RenderContext | None]`; `_app_instance` now holds a `RenderContext | None`
- [x] 7.2 Update `start_defer_after_rendering()` to access `ctx._defer_depth` where `ctx = _active_app_context.get() or _get_app_instance()`
- [x] 7.3 Update `end_defer_after_rendering()` to access `ctx._defer_depth` and `ctx._deferred_callbacks` where `ctx = _active_app_context.get() or _get_app_instance()`
- [x] 7.4 Update `Component._render()` to access `_active_app_context.get()` (now a RenderContext) for defer-after-rendering logic

## 8. AppDocumentRoot Adaptation

- [x] 8.1 Update `AppDocumentRoot.__init__` to accept `app: WebComPyApp | None` (immutable app for config access) and `di_scope: DIScope` (the RenderContext's DI scope)
- [x] 8.2 Update `AppDocumentRoot._render()` to set `_active_app_context` to the `RenderContext` (not `WebComPyApp`) — receive context via constructor or via `_active_di_scope`/DI injection
- [x] 8.3 Ensure `AppDocumentRoot` no longer stores `_app` for mutable state access — only for immutable config access (`config.selector`, `config.base_url`)

## 9. Tests

- [x] 9.1 Add test: concurrent SSR requests produce isolated HTML output (no cross-contamination of head props, scripts, links, styles) — `test_request_isolation.py`
- [x] 9.2 Add test: `RenderContext.dispose()` cleans up DI scope children (child scopes from component tree should be disposed) — `test_render_context_dispose.py`
- [x] 9.3 Add test: `app.create_render_context()` creates independent contexts from same `WebComPyApp` (mutating head on one ctx doesn't affect another) — `test_render_context_isolation.py`
- [x] 9.4 Add test: plugin `on_render_context_init` is called per request on server (multiple create_render_context calls trigger hook each time) — `test_plugin_render_context_init.py`
- [x] 9.5 ~~Add test: deprecation warning for `on_app_ready(self, app)` old signature~~ — removed: no backward compatibility (pre-stable)
- [x] 9.6 Add test: `app.di_scope` raises `AttributeError` on server (non-browser) environment — `test_app_di_scope_server_error.py`
- [x] 9.7 Verify all existing tests pass: `uv run python -m pytest tests/ --tb=short` — 964 passed
- [x] 9.8 Verify existing SSR/SSG tests pass with updated APIs

## 10. Documentation and Spec Sync

- [ ] 10.1 Update `openspec/specs/app-lifecycle/spec.md` (main spec, not change delta) with RenderContext lifecycle requirements after archive
- [ ] 10.2 Update `openspec/specs/plugin-system/spec.md` (main spec) with per-request plugin hooks after archive
- [ ] 10.3 Update `openspec/specs/architecture/spec.md` (main spec) with dual-environment RenderContext model after archive
- [ ] 10.4 Create `openspec/specs/render-context/spec.md` (main spec) from the change delta after archive
- [ ] 10.5 Update `.opencode/agents/ci-review.md` file→spec mapping to include `render-context` spec and `webcompy/app/_render_context.py` mapping
- [ ] 10.6 Update `AGENTS.md` file→spec mapping table to include `webcompy/app/_render_context.py` → `render-context` spec