## ADDED Requirements

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

### Requirement: Demo shell HTML SHALL be a single static file with dynamic attribute injection
A single static HTML file (`_demos/standard.html`) SHALL serve all demo variations. The file SHALL contain:
1. An empty `<script type="py">` tag — declared first in the body
2. An inline `<script>` that reads query params, validates the app name, resolves the wheel URL from the parent DOM, and sets `src` and `config` attributes on the `<script type="py">`
3. A `<script type="module" src="core.js">` tag — placed at the very end of body

#### Scenario: Shell app name is validated against a whitelist
- **WHEN** `standard.html?app=evil` is loaded
- **THEN** JS SHALL reject the app name
- **AND** the page SHALL display "Invalid app name."
- **AND** Pyodide SHALL NOT be initialized

#### Scenario: Wheel URL is resolved from parent DOM at runtime
- **WHEN** `standard.html` loads
- **THEN** JS SHALL access `window.parent.document.querySelector('script[type="py"][config]')`
- **AND** SHALL parse the JSON config and extract the package whose filename contains `"webcompy-"`
- **AND** if the wheel is not found, the page SHALL display "Wheel URL not found."
- **AND** if found, SHALL include it in the PyScript packages list

#### Scenario: Extra packages come from a hardcoded whitelist
- **WHEN** `standard.html?app=helloworld` is loaded
- **THEN** the packages list SHALL be `[wheel_url]`
- **WHEN** `standard.html?app=matplotlib_sample` is loaded
- **THEN** the packages list SHALL be `[wheel_url, "numpy", "matplotlib"]`

#### Scenario: PyScript config uses JSON format via config attribute
- **WHEN** the `<script type="py">` element has its `config` attribute set
- **THEN** the value SHALL be a valid JSON string containing `packages`, `experimental_create_proxy`, `interpreter`, `lockFileURL`
- **AND** SHALL NOT use `<py-config>` tags or TOML format

#### Scenario: DOM order ensures PyScript discovers populated attributes
- **WHEN** the HTML is parsed
- **THEN** `<script type="py">` SHALL appear first, followed by the config-injecting `<script>`, followed by `<script type="module" src="core.js">`
- **AND** the inline `<script>` SHALL set `src` and `config` attributes synchronously during HTML parsing, before the deferred module script (`core.js`) executes

### Requirement: Demo app SHALL be loaded via src attribute, not importlib
The `<script type="py">` SHALL have its `src` attribute set to the absolute path of the demo app file (`/_demos/{app}/app.py`). No `importlib.import_module` or inline Python code SHALL be used. No `files` PyScript config SHALL be included.

#### Scenario: app.py is loaded directly by PyScript
- **WHEN** the iframe's PyScript initializes
- **THEN** it SHALL fetch and execute `/_demos/{app}/app.py` via the `src` attribute
- **AND** the `app.py` SHALL construct `WebComPyApp(root_component=...)` and call `app.run()` at module level
- **AND** the component SHALL render inside the iframe's `#webcompy-app` div

### Requirement: No files config in iframe PyScript config
The `files` key SHALL NOT appear in the iframe's PyScript config. Data file access (e.g., `/_demos/fetch_sample/sample.json`) SHALL use absolute URLs via `HttpClient.get()`. The demo app code SHALL be loaded via the `src` attribute, not via Python import from the virtual filesystem.

#### Scenario: Data files are accessed via absolute HTTP URLs
- **WHEN** the fetch sample demo runs
- **THEN** it SHALL use `HttpClient.get("/_demos/fetch_sample/sample.json")`
- **AND** SHALL NOT rely on PyScript's `files` virtual filesystem mapping

### Requirement: Demo source code SHALL be fetched for display
The demo source code SHALL be fetched from `demo_path` via `HttpClient.get` at runtime for the SyntaxHighlighting code display. No source code SHALL be embedded as string literals in page components.

#### Scenario: Source code is displayed alongside iframe
- **WHEN** a user visits `/sample/helloworld`
- **THEN** the page SHALL contain an iframe with `src="/_demos/standard.html?app=helloworld"`
- **AND** the page SHALL contain a syntax-highlighted code block showing the HelloWorld source
- **AND** the source code SHALL be fetched from `/_demos/helloworld/app.py`
- **AND** the page component SHALL NOT contain any source code string literal

### Requirement: IFrame assets SHALL be shared via browser cache
All iframe assets (PyScript core.js, core.css, Pyodide runtime files, WebComPy framework wheel, WASM packages) SHALL be served from identical URLs as the parent page. The browser cache SHALL serve iframe requests from cache after the parent page has loaded them.

#### Scenario: Framework wheel is cached for iframe use
- **WHEN** the parent page loads the WebComPy framework wheel at `/_webcompy-app-package/webcompy-0+sha.*.whl`
- **AND** an iframe requests the same URL
- **THEN** the browser SHALL serve the wheel from cache without a network request

#### Scenario: PyScript core.js is cached for iframe use
- **WHEN** the parent page loads `core.js` from `/_webcompy-assets/core.js`
- **AND** an iframe requests the same URL
- **THEN** the browser SHALL serve `core.js` from cache without a network request

### Requirement: Lightweight demos SHALL use local Pyodide; heavy demos SHALL use CDN Pyodide
Demo iframes with no extra packages SHALL include `interpreter` and `lockFileURL` pointing to locally-served Pyodide assets, enabling browser cache sharing with the parent page. Demos with extra packages (numpy, matplotlib) SHALL omit `interpreter` and `lockFileURL`, causing PyScript to use CDN Pyodide where bare package names resolve correctly.

#### Scenario: Lightweight demo uses local Pyodide
- **WHEN** `standard.html?app=helloworld` loads
- **THEN** the config SHALL include `interpreter: "/_webcompy-assets/pyodide/pyodide.mjs"`
- **AND** the config SHALL include `lockFileURL: "/_webcompy-assets/pyodide/pyodide-lock.json"`
- **AND** Pyodide SHALL initialize from the same origin, using browser cache

#### Scenario: Heavy demo uses CDN Pyodide
- **WHEN** `standard.html?app=matplotlib_sample` loads
- **THEN** the config SHALL NOT include `interpreter` or `lockFileURL`
- **AND** PyScript SHALL use default CDN Pyodide
- **AND** bare package names `"numpy"` and `"matplotlib"` SHALL resolve from the CDN

### Requirement: Demo iframes SHALL display a loading screen during Pyodide initialization
Each demo iframe SHALL display a loading screen overlay (spinner on semi-transparent background) immediately when the iframe loads, before Pyodide initializes. The loading screen SHALL be automatically removed by the framework when `AppDocumentRoot._render()` completes its first render.

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
- **WHEN** a user views a demo page on a wide screen (> 1320px)
- **THEN** the demo page content SHALL have a `max-width` of 1320px (Bootstrap `.container` default)
- **AND** the content width SHALL match the home page content width
