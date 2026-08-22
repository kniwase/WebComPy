## ADDED Requirements

### Requirement: The profiling summary shall include startup cost clusters beyond the core phases

When profiling is enabled (`profile=True`), `WebComPyApp._record_phase` SHALL also record two additional startup phases that account for the measured cost clusters: a custom-element bulk-registration phase named `custom_elements_defined` recorded after the hydration-time bulk `customElements.define` pass completes, and a lazy-preload phase named `lazy_preloaded` recorded when the router's lazy-route preload batch finishes executing (in the browser this is inside the scheduled macro task; on the server it is after the synchronous preload loop). Phases SHALL be recorded at most once each (the first occurrence wins). In the browser the formatted summary SHALL be emitted via a scheduled macro task (rather than synchronously at loading-indicator removal) so that any scheduled lazy-preload batch has completed before the summary prints; the elapsed time between these phases and their adjacent phases SHALL be shown alongside the core lifecycle phases. A pair whose end timestamp precedes its start timestamp SHALL NOT be shown.

#### Scenario: Profiling summary includes the custom-element bulk-registration phase

- **WHEN** an app runs in the browser with `WebComPyAppConfig(profile=True)` and named components are registered before hydration
- **THEN** `app._profile_data` SHALL contain a phase recorded around the bulk custom-element registration pass
- **AND** the formatted profile summary SHALL show the elapsed time associated with that phase

#### Scenario: Profiling summary includes the lazy-preload phase

- **WHEN** an app with lazy routes runs with `profile=True` and `preload=True` (default)
- **THEN** `app._profile_data` SHALL contain a phase recorded around the lazy-route preload batch
- **AND** the formatted profile summary SHALL show the elapsed time associated with that phase

#### Scenario: Phases are recorded at most once

- **WHEN** a profiled phase's recording site is reached more than once during a run
- **THEN** only the first occurrence SHALL be recorded in `app._profile_data`

#### Scenario: Profiling remains disabled by default

- **WHEN** `profile=False` (the default) and an app runs
- **THEN** no new phase timestamps SHALL be recorded, preserving the zero-overhead default behavior

## MODIFIED Requirements

### Requirement: The application shall provide a browser entry point via app.run()
In the browser (PyScript) environment, `app.run(selector)` SHALL mount and render the application into the DOM element matching the given CSS selector. Calling `run()` in a non-PyScript (server) environment SHALL raise `WebComPyException`. `app.run()` SHALL internally create a single `RenderContext` via `create_render_context()`, which owns the DI scope, Router, AppDocumentRoot, and all rendering state. The `RenderContext`'s DI scope SHALL remain active for the app's lifetime. `on_render_context_init(ctx)` and `on_app_ready(ctx)` SHALL be called on plugins before the first render.

#### Scenario: Running an app with profiling enabled
- **WHEN** a developer creates `WebComPyAppConfig(profile=True)` and calls `app.run()` in the browser
- **THEN** the application SHALL record timestamps for each startup phase (`pyscript_ready`, `init_start`, `imports_done`, `init_done`, `run_start`, `custom_elements_defined`, `run_done`, `loading_removed`, `lazy_preloaded`)
- **AND** a formatted profile summary SHALL be printed to the browser console after the loading indicator is removed (in the browser, via a scheduled macro task so any pending lazy-preload batch completes first)
- **AND** `WebComPyApp._record_phase(name)` SHALL record `time.perf_counter()` into `_profile_data` only when `_profile` is True, and SHALL keep only the first occurrence of each phase name
- **AND** `_profile_data` SHALL be owned by the `WebComPyApp` instance (created in `WebComPyApp.__init__`) so that the generated bootstrap script can assign `app._profile_data["pyscript_ready"]` before any RenderContext exists; `RenderContext` SHALL NOT own profile state
- **AND** `WebComPyApp._emit_profile_summary()` SHALL format and output the profile summary — in Emscripten via `browser.console.log()`, otherwise via `print()`
- **AND** the summary SHALL show elapsed time between phases (`pyscript_ready → imports_done`, `imports_done → init_done`, `init_done → custom_elements_defined`, `custom_elements_defined → run_done`, `run_done → loading_removed`, `run_done → lazy_preloaded`) plus a total; a pair whose end timestamp precedes its start timestamp SHALL NOT be shown

#### Scenario: Accessing profile data
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=True`
- **THEN** the recorded timestamps dict SHALL be returned
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=False`
- **THEN** `None` SHALL be returned

#### Scenario: Running an app with hydration disabled
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False)` in the browser
- **THEN** the application SHALL recreate all DOM nodes from scratch
- **AND** no prerendered DOM node reuse SHALL occur during initial render

#### Scenario: Running an app with hydration enabled (default)
- **WHEN** a developer creates `WebComPyApp(..., hydrate=True)` or uses the default in the browser
- **THEN** the application SHALL attempt to reuse prerendered DOM nodes via `_hydrate_node()`
- **AND** only unmatched nodes SHALL be created via `_init_node()`

#### Scenario: Rendering children with hydration and matching prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` and prerendered nodes exist
- **THEN** each child SHALL use `_hydrate_node()` to adopt or create nodes
- **AND** children with matching prerendered nodes SHALL be adopted

#### Scenario: Rendering children with hydration but no prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` but no prerendered nodes exist for some children
- **THEN** unmatched children SHALL fall back to normal `_render()` for DOM creation and mounting

#### Scenario: Running an app with default selector
- **WHEN** a developer calls `app.run()` in the browser
- **THEN** the application SHALL mount into the element with `id="webcompy-app"`
- **AND** pre-rendered DOM nodes SHALL be hydrated
- **AND** the loading indicator SHALL be removed after the first render

#### Scenario: Prerendered app root is visible on page load
- **WHEN** the CLI generates HTML with prerendering enabled
- **THEN** the `#webcompy-app` div SHALL NOT have a `hidden` attribute
- **AND** the pre-rendered content SHALL be visible beneath the semi-transparent loading overlay

#### Scenario: Non-prerendered app root is hidden on page load
- **WHEN** the CLI generates HTML with prerendering disabled
- **THEN** the `#webcompy-app` div SHALL have a `hidden` attribute
- **AND** the content SHALL remain invisible until PyScript initializes

#### Scenario: Running an app with custom selector
- **WHEN** a developer calls `app.run("#my-container")` in the browser
- **THEN** the application SHALL mount into the element matching `#my-container`
- **AND** all reactivity, routing, and head management SHALL work as if mounted at the default selector

#### Scenario: Calling run() in a non-browser environment
- **WHEN** a developer calls `app.run()` in a server (non-PyScript) environment
- **THEN** a `WebComPyException` SHALL be raised indicating that `run()` is only available in the browser

#### Scenario: Mounting into a non-existent element
- **WHEN** a developer calls `app.run("#nonexistent")` and no element matches
- **THEN** a `WebComPyException` SHALL be raised indicating the mount point was not found

### MODIFIED: SSR/SSG render path skips hydration
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