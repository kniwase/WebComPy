# Demo IFrame Isolation

## MODIFIED Requirements

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
