# Demo IFrame Isolation

## Purpose

Demos run in isolated iframe PyScript contexts with independent dependencies, loaded on demand via a single shared HTML shell. The wheel URL is resolved from the parent DOM and packages are specified via a whitelist. This avoids downloading heavy WASM packages (numpy, matplotlib) before any page renders — the nav shell loads with only the WebComPy framework, and heavy demos load their own dependencies on demand.

## Requirements

### Requirement: Demos SHALL run in isolated iframe contexts
Each demo SHALL execute in its own `<iframe>` element with an independent PyScript runtime context. The parent (nav shell) page SHALL NOT load numpy or matplotlib as global dependencies. Each iframe SHALL declare only the packages required by that specific demo.

#### Scenario: Nav shell loads without heavy dependencies
- **WHEN** a user visits the docs_app home page
- **THEN** the PyScript config SHALL NOT include numpy or matplotlib in its packages list
- **AND** the nav shell SHALL render without waiting for numpy or matplotlib to download

#### Scenario: Lightweight demo iframe starts fast
- **WHEN** a user navigates to `/sample/helloworld`
- **THEN** the page SHALL render an iframe whose `src` points to `/_demos/standard.html?app=helloworld`
- **AND** the iframe SHALL only load the WebComPy framework wheel as a Pyodide package

#### Scenario: Heavy demo iframe loads additional packages from CDN
- **WHEN** a user navigates to `/sample/matplotlib`
- **THEN** the iframe SHALL include `"numpy"` and `"matplotlib"` CDN package names in its PyScript packages list
- **AND** these SHALL be loaded from CDN while the WebComPy framework wheel is loaded from local origin

### Requirement: Demo shell SHALL be a single static HTML with dynamic attribute injection
A single static HTML file (standard.html) SHALL serve all demo variations. It SHALL:
1. Declare an empty `<script type="py">` first
2. Use an inline `<script>` to validate app name, resolve wheel URL, `core.js`, `core.css`, and (when present for local runtime serving) `interpreter` and `lockFileURL` from the parent DOM against allowlisted URL prefixes, set `src` + `config` attributes on the `<script type="py">` element, and append `<link rel="stylesheet">` (`core.css`) to `<head>`
3. Dynamically append `<script type="module" src="...">` (`core.js`) to `<body>` after `<script type="py">` attributes are populated so PyScript initializes with the resolved versioned runtime URLs

#### Scenario: App name is validated against a whitelist
- **WHEN** `standard.html?app=evil` is loaded
- **THEN** JS SHALL reject the app name
- **AND** display "Invalid app name."
- **AND** Pyodide SHALL NOT be initialized

#### Scenario: Wheel URL is resolved from parent DOM
- **WHEN** `standard.html` loads
- **THEN** JS SHALL access `window.parent.document.querySelector('script[type="py"][config]')`
- **AND** SHALL parse the JSON config and extract the package containing "webcompy-"
- **AND** if not found, display "Wheel URL not found."

#### Scenario: Parent runtime URLs are validated before injection
- **WHEN** `standard.html` loads with a valid app and wheel URL
- **THEN** JS SHALL extract the parent `core.js` script `src` and `core.css` stylesheet `href`
- **AND** validate both against allowed prefixes (`/_webcompy-assets/<version>/...` or `https://pyscript.net/releases/<version>/...`)
- **AND** if a valid `core.js` URL is not found, display "Runtime URL not found." without loading PyScript

#### Scenario: Extra packages come from a hardcoded whitelist
- **WHEN** `?app=helloworld` is loaded
- **THEN** packages SHALL be `[wheel_url]`
- **WHEN** `?app=matplotlib_sample` is loaded
- **THEN** packages SHALL be `[wheel_url, "numpy", "matplotlib"]`

#### Scenario: PyScript config uses JSON via script attribute
- **WHEN** the `<script type="py">` element has its `config` attribute set
- **THEN** the value SHALL be a valid JSON string with `packages`, `experimental_create_proxy`, and (for local-runtime lightweight demos) `interpreter` and `lockFileURL`
- **AND** SHALL NOT use `<py-config>` tags or TOML format

#### Scenario: DOM order ensures attributes are populated before PyScript
- **WHEN** the HTML is parsed
- **THEN** `<script type="py">` SHALL appear before the config-injecting inline `<script>`
- **AND** the inline `<script>` SHALL set `src` and `config` synchronously before appending `<script type="module" src="...">` so PyScript observes the populated attributes

### Requirement: Demo app code SHALL be loaded via src attribute
The `<script type="py">` SHALL have its `src` attribute set to `/_demos/{app}/app.py`. No `importlib.import_module`, no `files` PyScript config, no inline Python code SHALL be used.

#### Scenario: app.py is loaded directly by PyScript
- **WHEN** the iframe's PyScript initializes
- **THEN** it SHALL fetch and execute `/_demos/{app}/app.py` via the `src` attribute
- **AND** `app.py` SHALL construct `WebComPyApp(root_component=...)` and call `app.run()` at module level
- **AND** the component SHALL render inside the iframe's `#webcompy-app` div

### Requirement: No files config in iframe
The `files` key SHALL NOT appear in the iframe's PyScript config. Data file access SHALL use absolute HTTP URLs such as `HttpClient.get("/_demos/fetch_sample/sample.json")`.

#### Scenario: Data files are accessed via absolute HTTP URLs
- **WHEN** the fetch sample demo runs
- **THEN** it SHALL use `HttpClient.get("/_demos/fetch_sample/sample.json")`
- **AND** SHALL NOT rely on PyScript's `files` virtual filesystem mapping

### Requirement: Demo source code SHALL be fetched for display
The demo source code SHALL be fetched from `demo_path` via `HttpClient.get` at runtime for the SyntaxHighlighting code display. No source code strings SHALL be embedded in page components.

#### Scenario: Source code is displayed alongside iframe
- **WHEN** a user visits `/sample/helloworld`
- **THEN** the page SHALL contain an iframe with `src="/_demos/standard.html?app=helloworld"`
- **AND** the page SHALL contain a syntax-highlighted code block showing the source fetched from `/_demos/helloworld/app.py`
- **AND** the page component SHALL NOT contain any source code string literal

### Requirement: IFrame assets SHALL be shared via browser cache
All iframe assets SHALL be served from identical versioned URLs as the parent page. The browser cache SHALL serve iframe requests from cache after the parent page has loaded them.

#### Scenario: Framework wheel is cached for iframe use
- **WHEN** the parent page loads the WebComPy framework wheel
- **AND** an iframe requests the same URL
- **THEN** the browser SHALL serve the wheel from cache without a network request

#### Scenario: PyScript core.js is cached for iframe use
- **WHEN** the parent page loads `core.js` from `/_webcompy-assets/{PYSCRIPT_VERSION}/core.js`
- **AND** an iframe requests the identical inherited `core.js` URL
- **THEN** the browser SHALL serve `core.js` from cache without a network request

### Requirement: Lightweight demos SHALL use local Pyodide; heavy demos SHALL use CDN Pyodide
Demo iframes with no extra packages SHALL inherit `interpreter` and `lockFileURL` from the parent document pointing to locally-served versioned Pyodide assets, enabling browser cache sharing with the parent page. Demos with extra packages (numpy, matplotlib) SHALL omit `interpreter` and `lockFileURL`, causing PyScript to use CDN Pyodide where bare package names resolve correctly.

#### Scenario: Lightweight demo uses local Pyodide
- **WHEN** `standard.html?app=helloworld` loads under a parent page served with `runtime_serving="local"`
- **THEN** the config SHALL include `interpreter: "/_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide.mjs"`
- **AND** the config SHALL include `lockFileURL: "/_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide-lock.json"`
- **AND** Pyodide SHALL initialize from the same origin, using browser cache

#### Scenario: Heavy demo uses CDN Pyodide
- **WHEN** `standard.html?app=matplotlib_sample` loads
- **THEN** the config SHALL NOT include `interpreter` or `lockFileURL`
- **AND** PyScript SHALL use default CDN Pyodide
- **AND** bare package names `"numpy"` and `"matplotlib"` SHALL resolve from the CDN

### Requirement: Demo iframes SHALL display a loading screen during Pyodide initialization
Each demo iframe SHALL display a loading screen overlay immediately when the iframe loads, before Pyodide initializes. The demo loading screen SHALL visually match the framework's refined default `overlay` presentation (compact spinner on a lightly translucent backdrop) while keeping the `#webcompy-loading` element contract. The loading screen SHALL be automatically removed by the framework when `AppDocumentRoot._render()` completes its first render.

#### Scenario: Loading screen appears before Pyodide starts
- **WHEN** an iframe loads `standard.html`
- **THEN** a `<div id="webcompy-loading">` SHALL be present in the static HTML
- **AND** the loading overlay SHALL be visible immediately without waiting for JavaScript

#### Scenario: Loading screen is removed after demo renders
- **WHEN** the demo's `WebComPyApp` completes `app.run()`
- **THEN** the framework's `_render()` method SHALL remove `#webcompy-loading` from the DOM
- **AND** the demo app content SHALL become visible

### Requirement: Demo pages SHALL use same content width as home page
Each demo page component SHALL wrap its content in a `<div class="container">` so that wide screens see the same constrained content width as the home page. Bootstrap's `.container` provides responsive `max-width` breakpoints.

#### Scenario: Demo page content matches home page width
- **WHEN** a user views a demo page on a wide screen
- **THEN** the demo page content SHALL have responsive `max-width` from Bootstrap `.container`
- **AND** the content width SHALL match the home page content width

### Requirement: Demo iframes SHALL load framework design tokens and synchronize with parent theme changes

The `docs_app/static/_demos/standard.html` shell SHALL load the framework design tokens/base stylesheet (`/_webcompy-ui/index.css`) and mirror the active theme from its same-origin parent document (reading the parent `<style data-webcompy-dynamic>` rule on startup and watching parent style updates via `MutationObserver`, with `webcompy-theme` cookie fallback when opened directly). Both the `#webcompy-loading` screen and the mounted demo app SHALL react immediately when the user toggles the parent site's theme between light, dark, and system modes.

#### Scenario: Live parent theme toggle updates mounted demo iframe

- **WHEN** a user views any docs page with an embedded `/_demos/standard.html?app=...` iframe and toggles the site theme from light to dark (or dark to light)
- **THEN** the iframe's `<style data-webcompy-dynamic>` rule SHALL update automatically to match the parent document without reloading the iframe
- **AND** background, text, border, and form-control colors inside the iframe SHALL switch cleanly to the newly selected theme

#### Scenario: Opening standard.html standalone falls back cleanly

- **WHEN** `standard.html?app=helloworld` is opened without a same-origin parent frame
- **THEN** it SHALL still initialize using `/_webcompy-ui/index.css` and `webcompy-theme` / OS preference without raising JavaScript errors

### Requirement: Demo apps SHALL honor design tokens and fix cross-component scoped styling boundaries

All demo apps under `docs_app/static/_demos/` SHALL derive surface, text, border, and accent colors from theme CSS variables (or define explicit light/dark-safe tokens matching WCAG 2.1 AA contrast `>= 4.5:1`) and SHALL NOT pass parent-only `scoped_style` classes across component `webcompy-cid` boundaries where child components or slotted subtrees would remain unstyled. Furthermore, the `routing` demo SHALL display a non-empty root path (`"/"`) on initial load and style its child route panels cleanly.

#### Scenario: Interactive demos remain legible in dark and OS-inverted themes

- **WHEN** `fetch_sample`, `transition`, `storage_sync`, `todo`, `teleport`, `matplotlib_sample`, `ui_form_controls`, `rpc_middleware_mock`, `fetch_middleware_mock`, `i18n_playground`, and `todo_tutorial/step1..step6` render inside an iframe under both light and dark modes (across OS light and OS dark preferences)
- **THEN** all readable text, status badges, buttons, inputs, modals, and dropdowns SHALL maintain at least 4.5:1 foreground-to-background contrast

#### Scenario: Cross-component styles apply to child routes, slots, and task lists

- **WHEN** `routing` child route views, `migration_users` slotted directory cards/rows, and `todo_tutorial/step3..step6` task lists render in a browser
- **THEN** the rendered elements SHALL carry matching scoped styles on their owning components (or shared demo stylesheet) rather than silently failing due to parent `webcompy-cid` attribute mismatch

### Requirement: Demo iframes SHALL size responsively without vertical clipping

`DemoDisplay` in `docs_app` SHALL size embedded demo iframes based on measured demo content height (via safe same-origin `ResizeObserver` / height synchronization capped/scrolled gracefully on narrow viewports) or sufficient per-demo minimum height so interactive demos taller than `400px` (`forms`, `http-fetch`, `matplotlib_sample`, `i18n-playground`, `migration_users`) are not clipped on initial render.

#### Scenario: Tall demo iframes expand to fit their content

- **WHEN** a user opens `/documents/examples/forms` or `/documents/examples/http-fetch`
- **THEN** the embedded `<iframe>` height SHALL accommodate the rendered demo UI without clipping primary controls below `400px`
