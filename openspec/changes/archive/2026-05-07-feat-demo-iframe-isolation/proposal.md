## Why

The docs_app currently declares `browser = ["numpy", "matplotlib"]` as global Pyodide dependencies, forcing ~66 MB of packages to download and initialize before any page renders — even the home page. By isolating each demo into a separate iframe with its own PyScript context, the nav shell loads with only the WebComPy framework (~11 MB) and heavy demos load on demand.

## What Changes

- **BREAKING**: Remove `numpy` and `matplotlib` from `docs_app` global browser dependencies — the nav shell no longer loads them
- Add a `_demos/` directory under `docs_app/static/` containing per-demo directories with self-contained `app.py` files
- Demo app source code is inserted into iframe via `srcdoc` from a Python string template maintained in `demo_display.py` — no static HTML shell files
- Package URLs (webcompy wheel, numpy, matplotlib, etc.) are resolved at runtime by inspecting the parent page's own `<script type="py">` config via `querySelector` — no hardcoded URLs, no query parameter routing
- Existing demo pages (`pages/demo/*`) become thin wrappers that pass only two props to `DemoDisplay`: `app_name` and `demo_path`
- Same fetched source code is used for both the iframe srcdoc (for live rendering) and `SyntaxHighlighting` (for code display) — single source of truth, no duplication
- All iframe assets (PyScript core, Pyodide runtime, WebComPy wheel, wasm packages) are served from the same origin as the parent page, enabling browser cache sharing — no external CDN dependency
- `AppConfig.dependencies` is set to `[]` explicitly, replacing the auto-populating `dependencies_from` pattern

### Non-goals

- Running WebComPy on MicroPython (stdlib gap is too large for practical migration)
- External sandbox integration (CodePen/StackBlitz/pykernel) — deferred to a future change after `feat-port-abstraction` is complete
- Changing the docs_app shell from CLI-based build (model 1) to CDN-direct (model 2)

## Known Issues Addressed

- **Module-level fallbacks hold only one app reference**: Not directly addressed, but iframe isolation means each demo runs in a completely separate PyScript context, avoiding the single-app limitation for the demo use case

## Capabilities

### New Capabilities

- `demo-iframe-isolation`: Demos run in isolated iframe PyScript contexts with independent dependencies, loaded on demand via a shared HTML shell and query-parameter-based module selection

### Modified Capabilities

- `project-config`: Browser dependency declaration (`dependencies` / `dependencies_from` in AppConfig) behavior for docs_app changes — global deps are minimized and per-demo deps are handled by the iframe shell
- `cli`: Static site generation copies `_demos/` directory from static files, serving demo shells and app.py files as static assets alongside generated HTML

## Impact

- `docs_app/static/` — new `_demos/` directory with per-demo app.py files and sample.json
- `docs_app/pages/demo/*` — rewritten as thin wrappers passing app_name, demo_path, and optional extra_packages to DemoDisplay
- `docs_app/pyproject.toml` — browser dependencies reduced to `[]`
- `docs_app/webcompy_config.py` — `dependencies_from` removed, `dependencies` set explicitly
- `docs_app/components/demo_display.py` — rewritten with Python string template, fetch-based code loading, and srcdoc iframe
- Generated SSG output at `docs_app/dist/` gains `_demos/` directory
