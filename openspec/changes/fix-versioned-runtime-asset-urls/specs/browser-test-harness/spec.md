# Browser Test Harness

## MODIFIED Requirements

### Requirement: Harness server shall serve local PyScript runtime and harness endpoints

The harness server SHALL be a Starlette application launched by the browser-test session fixture on an ephemeral port. It SHALL serve `/_webcompy-assets/{pyscript_version}/*` from the existing `runtime-assets/{pyscript_version}/` cache (including `core.js`, `core.css`, `pyodide/pyodide.mjs`, and `pyodide/pyodide-lock.json`). It SHALL serve `/_webcompy-test/config.json` (the generated harness py-config with `experimental_create_proxy: "auto"` and the same `interpreter`/`lockFileURL` shape as `webcompy_server._html` when `runtime_serving == "local"`), `/_webcompy-test/manifest.json` (test module inventory), and `/testharness` (the harness HTML). The harness HTML SHALL load `core.js`/`core.css` from the local versioned assets, declare a single `<script type="py" config="...">` bootstrapping the in-page runner, and provide a mount container that per-test fixtures own.

#### Scenario: Harness server exposes required routes
- **WHEN** the browser-test session starts for `pyscript_version` (defaulting to `PYSCRIPT_VERSION`)
- **THEN** the harness server SHALL respond `200` to `/_webcompy-assets/{pyscript_version}/core.js`, `/_webcompy-assets/{pyscript_version}/pyodide/pyodide.mjs`, `/_webcompy-test/config.json`, `/_webcompy-test/manifest.json`, and `/testharness`

#### Scenario: Runtime version parity
- **WHEN** the harness py-config is generated
- **THEN** its `interpreter` and `lockFileURL` values SHALL match the shape produced by `webcompy_server._html` for `runtime_serving == "local"` at the same `PYSCRIPT_VERSION`
