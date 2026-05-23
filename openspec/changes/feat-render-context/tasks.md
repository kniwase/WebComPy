## 1. Signal Graph ContextVar Migration

- [ ] 1.1 Convert `_active_consumer` in `webcompy/signal/_graph.py` from module-level global to `ContextVar[SignalNode | None]`
- [ ] 1.2 Convert `_in_notification_phase` in `webcompy/signal/_graph.py` from module-level global to `ContextVar[bool]`
- [ ] 1.3 Update all references to `_active_consumer` and `_in_notification_phase` throughout the signal module (`_graph.py`, `_effect.py`, `_computed.py`, `_base.py`, `_state.py`, etc.) to use `.get()` and `.set()` instead of direct read/write
- [ ] 1.4 Ensure `reset_graph_state()` resets both ContextVars and `_epoch`
- [ ] 1.5 Run existing signal tests to verify no regressions

## 2. RenderContext Class

- [ ] 2.1 Create `webcompy/app/_render_context.py` with the `RenderContext` class skeleton: `__init__`, `render_html`, `dispose` method signatures
- [ ] 2.2 Implement `RenderContext.__init__`: create fresh DIScope, Server ports (or Browser ports), ComponentStore, HeadPropsStore, Router, AppDocumentRoot; set Signal graph state; call `on_render_context_init` on plugins
- [ ] 2.3 Implement `RenderContext.render_html`: enter DI scope context, render component tree, generate HTML output (extract logic from `webcompy/cli/_html.py`)
- [ ] 2.4 Implement `RenderContext.dispose`: dispose DI scope children, dispose EffectScopes, call `reset_graph_state()`, clear references to allow GC
- [ ] 2.5 Implement `RenderContext` property forwarding for `head`, `style`, `scripts`, `routes`, `router_mode`, `set_path`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`, `html_attrs`

## 3. WebComPyApp Refactoring

- [ ] 3.1 Move mutable state out of `WebComPyApp`: remove `_di_scope`, `_root`, `_component_store`, `_defer_depth`, `_deferred_callbacks`, `_profile_data` from `__init__`; store only immutable definitions (`_config`, `_root_component_def`, `_router_pages`, `_router_mode`, `_router_base_url`, `_plugin_classes`, `_plugin_scripts`)
- [ ] 3.2 Implement `WebComPyApp.create_render_context(path="")` that creates a new `RenderContext` with all request-scoped state
- [ ] 3.3 Update `WebComPyApp.run()` to create a `RenderContext` internally and delegate to it; preserve existing browser behavior
- [ ] 3.4 Update `WebComPyApp.__init__` to perform plugin discovery only (no DI scope, no ports, no AppDocumentRoot creation)
- [ ] 3.5 Update `WebComPyApp` property forwarding to delegate to the active `RenderContext` (browser) or document that server code uses `RenderContext` directly

## 4. Plugin System Update

- [ ] 4.1 Add `on_render_context_init(self, ctx: RenderContext)` hook to `WebComPyPlugin` base class (default no-op)
- [ ] 4.2 Change `on_app_ready(self, app: WebComPyApp)` signature to `on_app_ready(self, ctx: RenderContext)` with deprecation warning for old signature
- [ ] 4.3 Update `PluginManager.init_all()` to split into app-level init (`on_app_init`) and render-context-level init (`on_render_context_init`)
- [ ] 4.4 Update `PluginManager.call_on_app_ready()` to receive `RenderContext` instead of `WebComPyApp`
- [ ] 4.5 Update `PluginManager` to store `_plugin_classes` on `WebComPyApp` and call `on_render_context_init` during `RenderContext` creation

## 5. Server Path Update

- [ ] 5.1 Update `webcompy/cli/_server.py` `create_asgi_app()` to use `app.create_render_context(path)` per request in the `send_html` handler for history mode
- [ ] 5.2 Update hash mode SSR to use `app.create_render_context("/")` for initial render, then cache the HTML result
- [ ] 5.3 Update `generate_html()` in `webcompy/cli/_html.py` to accept `RenderContext` instead of `WebComPyApp`
- [ ] 5.4 Ensure `RenderContext.dispose()` is called in a `finally` block after HTML generation

## 6. SSG Path Update

- [ ] 6.1 Update `webcompy/cli/_generate.py` (or equivalent SSG code) to create a `RenderContext` per route and dispose it after generation
- [ ] 6.2 Verify that SSG output is identical before and after the change

## 7. Tests

- [ ] 7.1 Add test: concurrent SSR requests produce isolated HTML output (no cross-contamination)
- [ ] 7.2 Add test: `RenderContext.dispose()` cleans up Signal graph state (no memory leak in signal nodes)
- [ ] 7.3 Add test: `RenderContext.dispose()` cleans up DI scope children and EffectScopes
- [ ] 7.4 Add test: `app.create_render_context()` creates independent contexts from the same `WebComPyApp`
- [ ] 7.5 Add test: plugin `on_render_context_init` is called per request on server and once in browser
- [ ] 7.6 Add test: deprecation warning for `on_app_ready(self, app)` old signature
- [ ] 7.7 Verify existing tests pass (signal, component, router, DI, app, plugin, SSR)

## 8. Documentation and Spec Sync

- [ ] 8.1 Update `openspec/specs/app-lifecycle/spec.md` with RenderContext lifecycle requirements
- [ ] 8.2 Update `openspec/specs/plugin-system/spec.md` with per-request plugin hooks
- [ ] 8.3 Update `openspec/specs/architecture/spec.md` with dual-environment RenderContext model
- [ ] 8.4 Update `.opencode/agents/ci-review.md` file→spec mapping to include `render-context` spec and `webcompy/app/_render_context.py` mapping
- [ ] 8.5 Update `AGENTS.md` file→spec mapping table