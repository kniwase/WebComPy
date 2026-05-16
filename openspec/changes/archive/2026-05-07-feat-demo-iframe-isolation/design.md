## Context

The docs_app currently embeds demo components directly within the same PyScript application instance. This means all browser dependencies declared in `pyproject.toml` (`browser = ["numpy", "matplotlib"]`) are loaded into Pyodide before any page renders. Total download is ~66 MB (Pyodide 11MB + numpy 15MB + matplotlib 40MB plus transitive deps).

The proposal identifies IFrame isolation as the solution: each demo becomes an independent PyScript application running in its own iframe, sharing cached assets from the parent page's origin.

Current state of the docs_app:
- `docs_app/webcompy_config.py` uses `WebComPyBuildConfig` with `dependencies=[]` and `wheel_mode="split"`
- `standalone=True` — all runtime files served locally
- Demos are page components (`pages/demo/*.py`) rendered in iframes via `DemoDisplay`
- `DemoDisplay` renders an iframe and fetches source code for syntax-highlighted display

## Goals / Non-Goals

**Goals:**
- Remove numpy/matplotlib from docs_app global dependencies so the nav shell loads with only WebComPy core
- Each demo runs in an isolated iframe with only the dependencies it actually needs
- All assets (PyScript runtime, Pyodide, WebComPy wheel, WASM wheels) are served from the same origin and shared via browser cache
- Demo source code display remains visible on the shell page alongside the iframe
- The system works in both `webcompy start --dev` and `webcompy generate`
- No framework modifications or post-processing scripts required

**Non-Goals:**
- MicroPython interpreter support for demos
- External sandbox integration (pykernel, CodeSandbox, etc.)
- Changing the docs_app shell build method (remains CLI-based split+standalone)
- Auto-resizing iframes to match demo content height
- Bidirectional communication between shell and iframe (postMessage bridge)

## Decisions

### Decision 1: Split wheel mode for iframe sharing

The parent page and iframe pages all reference the same WebComPy framework wheel URL at `/_webcompy-app-package/webcompy-0+sha.*.whl`. Because URLs are identical, the browser cache serves the iframe request from cache with zero network cost.

Split mode is already configured (`wheel_mode="split"`). The framework wheel is served with long cache headers (`Cache-Control: max-age=86400`).

**Alternatives considered:**
- Bundled mode: the `docs_app` wheel includes all shell code (pages, layouts, navigation). Iframes would import unnecessary code. Rejected.
- CDN-direct model 2: would require publishing the wheel externally, adding latency and CDN dependency. Rejected per non-goals.

### Decision 2: Static HTML file with client-side `src` + `config` injection

A single static HTML file (`docs_app/static/_demos/standard.html`) serves as the iframe shell. It contains:

1. An empty `<script type="py">` tag (declared first)
2. An inline `<script>` that:
   - Parses `?app=` from the URL (whitelist-validated)
   - Reads the parent page's `<script type="py" config="...">` via `window.parent.document` to extract the WebComPy framework wheel URL
   - Constructs the PyScript config JSON with packages, interpreter, and lockFileURL
   - Sets `config` attribute on the `<script type="py">` element
   - Sets `src` attribute pointing directly to `/_demos/{app}/app.py`
3. A `<script type="module" src="/_webcompy-assets/core.js">` at body's end

This order guarantees that PyScript (which loads asynchronously as a deferred module) discovers the `<script type="py">` tag with both `src` and `config` already populated. The `config` attribute uses JSON format (not TOML), avoiding custom element lifecycle issues with `<py-config>`.

**Alternatives considered:**
- `<py-config>` tag with TOML: relied on custom element `connectedCallback` timing. Pyodide's TOML parser also caused issues with JSON-encoded values. Rejected.
- `srcdoc` with inline code: `about:srcdoc` origin broke `files` path resolution. Rejected.
- Blob URL via `browser.window.Blob.new()`: Pyodide's FFI cannot call JavaScript constructors that require `new`. Rejected.
- Data URL with base64: `<script type="module">` does not execute from `data:` origins. Rejected.
- `importlib.import_module` in inline Python: required `files` config and `pyscript`/`js` imports that failed in iframe context. Rejected in favor of `src` attribute.

### Decision 3: Demo app.py as self-contained module

Each `_demos/<name>/app.py` is a complete, self-contained WebComPy application. It defines a root component and calls `app.run()` at module level. No bootstrap.py, no router, no pages/ directory.

```python
# _demos/helloworld/app.py
from webcompy.app import WebComPyApp
from webcompy.elements import html
from webcompy.components import ComponentContext, define_component

@define_component
def App(_: ComponentContext[None]):
    return html.DIV({}, html.H1({}, "Hello WebComPy!"))

app = WebComPyApp(root_component=App)
app.run()
```

**Alternatives considered:**
- Shell contains `WebComPyApp` construction: would require the shell HTML to know component details. Rejected — keeping app logic in app.py makes the demo copy-pasteable and self-documenting.

### Decision 4: Wheel URL resolved from parent DOM in JavaScript

At runtime, JS in the iframe (`standard.html`) reads the parent page's `<script type="py" config="...">` via `window.parent.document.querySelector`. This is a same-origin access (both parent and iframe are on the same domain). The config JSON is parsed, and the WebComPy framework wheel URL is extracted by matching `"webcompy-"` in the package path.

Package names for numpy/matplotlib are stored in a whitelist (`APP_PACKAGES`) within the JS, mapped by the `app` name from the query parameter. Only known app names are accepted.

**Alternatives considered:**
- Query parameter `?wheel=` for wheel URL: would allow injection of arbitrary wheel URLs. Rejected.
- Base64-encoded `?packages=` query param: could be tampered. Rejected.
- Python-side extraction via `from js import window`: worked but required Python-side query parsing and `pyscript.location` which failed. Rejected.

### Decision 5: Page components pass app_name and demo_path

Each `docs_app/pages/demo/<name>.py` passes four props to `DemoDisplay`:
- `title`: display title for the card
- `app_name`: segment for the iframe URL (`"helloworld"`, `"matplotlib_sample"`)
- `demo_path`: URL to the source `.py` file for code display (`"/_demos/helloworld/app.py"`)
- `packages`: list of extra package names (`["numpy", "matplotlib"]` for matplotlib, `[]` for others)

The page component no longer embeds any source code strings — the source is fetched at runtime from `demo_path` for display.

### Decision 6: Single static HTML file

A single `docs_app/static/_demos/standard.html` serves all demo variations. The `app`, `wheel` URL, and extra packages are:

- `app`: from query parameter `?app=`. Whitelist-validated against `APP_PACKAGES`.
- `wheel` URL: from `window.parent.document.querySelector('script[type="py"][config]')`. Same-origin.
- Extra packages: from the `APP_PACKAGES[app]` whitelist in the JS.

No `files` config is needed because the app code is loaded via the `<script type="py">` `src` attribute, not via Python `import`.

**Alternatives considered:**
- Per-demo HTML files: would require duplicating the JS logic. Rejected.
- `files` config mapping `./_demos/`: relative path resolution failed for iframe at `/_demos/standard.html`. Rejected.

### Decision 7: No `files` PyScript config

`files` is not included in the iframe config because:

1. The `app.py` is loaded via `<script type="py" src="/_demos/{app}/app.py">` — PyScript fetches it independently of `files`.
2. The `app.py` code imports `webcompy.*` from the installed wheel — no filesystem dependency.
3. Data files (e.g., `sample.json`) are accessed via `HttpClient.get("/_demos/...")` with absolute URLs — no `files` mapping needed.
4. `files` relative paths (`./_demos/`) fail because the iframe's URL is `/_demos/standard.html`, making `./_demos/` resolve to `/_demos/_demos/` which does not exist.

### Decision 8: Conditional Pyodide interpreter — local for light demos, CDN for heavy demos

When `interpreter` is set to a local path (`/_webcompy-assets/pyodide/pyodide.mjs`), Pyodide resolves bare package names (e.g., `"numpy"`, `"matplotlib"`) from the local directory. Since `dependencies=[]` in the docs_app config, no WASM wheels are downloaded locally for numpy/matplotlib, causing `ModuleNotFoundError` at iframe import time.

The fix: `interpreter` and `lockFileURL` are only included in the config when the demo has no extra packages (`extra.length === 0`). Lightweight demos (helloworld, fizzbuzz, todo, fetch_sample) use local Pyodide for fast startup via browser cache sharing with the parent page. Heavy demos (matplotlib_sample) omit `interpreter` and `lockFileURL`, causing PyScript to use the default CDN Pyodide where `"numpy"` and `"matplotlib"` resolve correctly.

**Alternatives considered:**
- Download numpy/matplotlib WASM wheels locally: violates the goal of keeping heavy packages out of the parent build. Rejected.
- Always use CDN Pyodide: loses browser cache benefits for lightweight demos. Rejected.

### Decision 9: Browser runtime scoped style injection with SSR duplication prevention

Scoped component styles (`scoped_style`) were only injected into HTML at SSR time via `_html.py:generate_html()`. The browser runtime's `AppDocumentRoot._render()` had no mechanism to inject scoped CSS into the DOM. This meant demo iframes — which create a fresh `WebComPyApp` at runtime with no SSR — had no scoped styles.

The fix operates at two levels:

1. **SSR side** (`_html.py`): The `<style>` tag generated during SSR now includes `id="webcompy-scoped-styles"`.
2. **Browser runtime** (`_root_component.py`): During the first render (`if self.__loading`), the code checks `document.getElementById("webcompy-scoped-styles")`. If the element doesn't exist (no SSR), it creates a `<style>` element with that id, sets its `textContent` to `self.style`, and appends it to `document.head`.

This prevents duplication: parent pages with SSR already have the `<style>` tag in the HTML, so `getElementById` finds it and skips injection. Demo iframes without SSR don't have it, so the runtime creates one.

## Risks / Trade-offs

- **Separate Pyodide per iframe**: Each iframe initializes its own Pyodide instance (~11MB WASM parse, ~200ms). With 5 demos open, total memory is ~55MB for Pyodide alone. **Mitigation**: Browsers typically keep only one iframe active at a time. WASM engine may share compiled code across instances.

- **No SSR for iframe content**: The iframe's HTML is a static shell with no pre-rendered demo content. The demo component only renders after Pyodide initializes. **Mitigation**: Acceptable trade-off. SSR would require running Python in the generate process for each demo.

- **Source code duplication**: Each page component embeds a full source code string for `SyntaxHighlighting`. **Mitigation**: The source is fetched at runtime from the actual `app.py` file. No duplicate strings in page components.

- **Split mode requirement**: The design requires `wheel_mode="split"` for the framework wheel sharing to work. **Mitigation**: docs_app config already uses split mode.

- **DOM order sensitivity**: The iframe HTML must declare `<script type="py">` before the config-injecting `<script>`, and `<script type="module">` (core.js) must be at the very end. If this order is violated, PyScript may initialize before config and `src` attributes are set. **Mitigation**: The HTML structure enforces this order by design.

- **`window.parent.document` access**: Requires same-origin parent and iframe. If deployed on different origins (e.g., cross-origin iframe), the wheel URL resolution fails. **Mitigation**: all demos are served from the same origin as the parent docs_app.
