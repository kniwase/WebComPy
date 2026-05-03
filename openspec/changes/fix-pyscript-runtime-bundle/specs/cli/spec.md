## MODIFIED Requirements

### Requirement: The generate command shall produce deployable static files

Static site generation SHALL be available via `python -m webcompy generate` or `generate_static_site(app, generate_config=None)`. Both SHALL produce a complete static site in the configured output directory. The SSG process SHALL enter the app's DI scope for the entire generation pipeline to ensure `inject()` calls during route rendering succeed. A single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`.

When `runtime_serving="local"`, the generate command SHALL download and extract the PyScript offline bundle, placing all `.js` and `.css` files from the `pyscript/` directory (excluding `.map`, `.d.ts`, `micropython/`, `pyodide/`, `service-worker.js`, `mini-coi-fd.js`, `xterm.css`, and `index.html`) into `dist/_webcompy-assets/`.

#### Scenario: Generating static site with runtime_serving=local

- **WHEN** a developer runs `python -m webcompy generate` with `runtime_serving="local"` (or `standalone=True`)
- **THEN** the generate command SHALL download the PyScript offline bundle if not cached
- **AND** place all PyScript core bundle `.js` and `.css` files in `dist/_webcompy-assets/`
- **AND** place all Pyodide runtime files in `dist/_webcompy-assets/pyodide/`
- **AND** the generated HTML SHALL reference `/_webcompy-assets/core.js` for PyScript initialization

### Requirement: The dev server shall serve runtime assets locally

When `runtime_serving="local"`, the dev server SHALL serve all PyScript core bundle files and Pyodide runtime files from memory. This includes all `.js` and `.css` files extracted from the PyScript offline bundle.

#### Scenario: Dev server with runtime_serving=local serves all PyScript bundle files

- **WHEN** a developer starts the dev server with `runtime_serving="local"`
- **THEN** all PyScript core bundle `.js` and `.css` files SHALL be available at `/_webcompy-assets/{filename}`
- **AND** the browser SHALL be able to resolve all relative `import()` paths within the PyScript bundle