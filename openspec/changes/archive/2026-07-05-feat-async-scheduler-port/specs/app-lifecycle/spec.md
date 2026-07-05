## ADDED Requirements

### Requirement: SSR/SSG entry points shall await pending tasks before context disposal

All server-side rendering entry points (`generate_html()` in `webcompy_server._html`, the ASGI HTML handler in `webcompy_cli._server`, and the SSG route fetch loop in `webcompy_cli._generate`) SHALL call `await scheduler.await_pending()` after the render tree completes (`await ctx._root._render()`) and before `ctx.dispose()`. The scheduler SHALL be obtained from the render context's DI scope via `inject(ASYNC_SCHEDULER_PORT_KEY)`. This guarantees that all tasks scheduled during the render (via `aio_run`, `DynamicElement._hydrate_node`, `SuspenseElement`, etc.) complete before the DI scope is torn down.

#### Scenario: generate_html drains tasks before disposal
- **WHEN** `generate_html()` is called during SSR or SSG
- **THEN** after `await ctx._root._render()` completes
- **AND** before `ctx.dispose()` is called
- **AND** `await scheduler.await_pending()` SHALL be invoked to drain all registered tasks

#### Scenario: ASGI handler drains tasks before disposal
- **WHEN** the ASGI HTML handler processes a request
- **THEN** after the render tree completes
- **AND** before `ctx.dispose()` is called
- **AND** `await scheduler.await_pending()` SHALL be invoked

### Requirement: app._hydrate shall remain environment-guarded as defense-in-depth

`WebComPyApp.__init__` SHALL set `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`. This guard remains in place as a defense-in-depth measure. The `AsyncSchedulerPort` provides the primary structural guarantee (task completion before disposal), and the environment guard ensures hydration-related scheduling is never attempted on the server even if the port's drain is bypassed.

#### Scenario: Hydration disabled on server
- **WHEN** a `WebComPyApp` is created in a non-pyscript environment with `WebComPyAppConfig(hydrate=True)`
- **THEN** `app._hydrate` SHALL be `False`
- **AND** `AppDocumentRoot._render()` SHALL skip the `_hydrate_node()` recursion
- **AND** all children SHALL be rendered via the synchronous `await child._render()` path
