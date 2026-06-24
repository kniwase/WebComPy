# SSR/SSG Hydration Skip

## Purpose

Hydration is a browser concept: adopting prerendered DOM nodes in the JS runtime. In non-pyscript environments (SSG and dev server SSR), the server is **generating** the prerendered content, not adopting it. To prevent fire-and-forget render tasks from running after the DI scope is disposed, `WebComPyApp.__init__` SHALL force `self._hydrate = False` in non-pyscript environments, so the synchronous `await child._render()` path is used exclusively.

## MODIFIED Requirements

### Requirement: `hydrate` config field is effective only in the pyscript environment

The `hydrate` field of `WebComPyAppConfig` SHALL be effective only when the framework runs in the `pyscript` environment. `WebComPyApp.__init__` SHALL compute `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`. In the `pyscript` environment, `self._hydrate` SHALL equal the user-supplied config value. In any other environment, `self._hydrate` SHALL be `False` regardless of the user-supplied config value.

#### Scenario: `hydrate=True` in pyscript environment

- **WHEN** the framework runs in `pyscript` and the developer configures `WebComPyAppConfig(hydrate=True)` (or accepts the default)
- **THEN** `WebComPyApp._hydrate` SHALL be `True`
- **AND** `AppDocumentRoot._render()` SHALL call `child._hydrate_node()` and adopt prerendered DOM nodes in the browser

#### Scenario: `hydrate=True` in server environment (SSG / dev server SSR)

- **WHEN** the framework runs in a non-`pyscript` environment (e.g. `webcompy generate`, `webcompy start` SSR handler) and the developer configures `WebComPyAppConfig(hydrate=True)` (or accepts the default)
- **THEN** `WebComPyApp._hydrate` SHALL be `False`
- **AND** `AppDocumentRoot._render()` SHALL skip the `child._hydrate_node()` recursion
- **AND** all children SHALL be rendered via the synchronous `for child in self._children: await child._render()` path
- **AND** the generated HTML SHALL contain the full subtree content (e.g. `HomePage` DIV's children are non-empty in SSG output)

#### Scenario: `hydrate=False` in pyscript environment

- **WHEN** the framework runs in `pyscript` and the developer configures `WebComPyAppConfig(hydrate=False)`
- **THEN** `WebComPyApp._hydrate` SHALL be `False`
- **AND** `AppDocumentRoot._render()` SHALL skip the `child._hydrate_node()` recursion
- **AND** the browser re-renders the entire DOM from scratch

### Requirement: SSR/SSG render path skips hydration

`AppDocumentRoot._render()` SHALL NOT call `child._hydrate_node()` when running in a non-`pyscript` environment. The existing `if self._app and self._app._hydrate and not self.__hydrated:` guard SHALL evaluate `False` in non-pyscript environments because `app._hydrate` is forced to `False` in `WebComPyApp.__init__`. The subsequent `for child in self._children: await child._render()` loop SHALL be the sole render path server-side, and its `await` chain SHALL complete before the caller of `generate_html` proceeds.

#### Scenario: SSG output contains routed page content

- **WHEN** `webcompy generate` produces an HTML file for a route that has a Component child (e.g. `HomePage` inside `RouterView`)
- **THEN** the generated HTML SHALL contain the full component subtree
- **AND** the routed component's DIV SHALL have non-empty children (e.g. `<div webcompy-component="HomePage">...child elements...</div>`)
- **AND** `Component.__init__` for the routed component SHALL execute while the `RenderContext._di_scope` is still active

#### Scenario: Dev server SSR response contains routed page content

- **WHEN** a client requests a route from the dev server (`webcompy start`) and the route has a Component child (e.g. `HomePage` inside `RouterView`)
- **THEN** the HTTP response HTML SHALL contain the full component subtree
- **AND** the routed component's DIV SHALL have non-empty children

### Requirement: Non-pyscript rendering uses the await chain only

In non-pyscript environments, the entire server-side rendering SHALL proceed through the `await` chain. Fire-and-forget `asyncio.ensure_future()` calls SHALL NOT be used for the initial render because the event loop is single-shot and exits as soon as `await generate_html(...)` returns. Any child whose render is scheduled as a fire-and-forget task SHALL NOT complete before `RenderContext.dispose()` runs in non-pyscript environments.

The single render path in non-pyscript environments SHALL be the synchronous `for child in self._children: await child._render()` chain in `AppDocumentRoot._render()`.

#### Scenario: No fire-and-forget render in SSR/SSG

- **WHEN** the framework runs in a non-`pyscript` environment and `AppDocumentRoot._render()` executes
- **THEN** `asyncio.ensure_future(child._render())` SHALL NOT be called for any child
- **AND** the await chain SHALL complete all child renders before returning

## Future work (deferred, out of scope)

The fire-and-forget `asyncio.ensure_future(child._render())` in `DynamicElement._hydrate_node()` remains a code smell in the browser path. Two alternative designs were considered and explicitly deferred:

- **Option B — DOM port abstraction**: Move hydration responsibility into the DOM port layer. `BrowserDOMPort._init_node` SHALL adopt the existing prerendered node; `ServerDOMPort._init_node` SHALL always create a fresh node. `_hydrate_node()` and its `ensure_future` call SHALL be removed. This change touches `port-abstraction`, `elements`, `element-preserve-children`, and `app-lifecycle` specs.

- **Option C — Render scheduler port**: Introduce a `RenderSchedulerPort` (browser: `asyncio.ensure_future`; server: synchronous — the coroutine SHALL be returned to the caller and awaited there). `DynamicElement._hydrate_node()` SHALL call `inject(RENDER_SCHEDULER_PORT_KEY).schedule(child._render())`. This change centralizes the `ensure_future` call behind a port. Mid-sized change.

These alternatives SHALL be considered in a follow-up change if the framework grows more SSR-style features or if the `ensure_future` pattern spreads to other call sites.
