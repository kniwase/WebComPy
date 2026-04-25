# CLI — Delta: feat-dependency-bundling

## MODIFIED Requirements

### Requirement: The dev server and SSG shall produce a single bundled wheel
The dev server and SSG SHALL build a single Python wheel containing the webcompy framework (excluding `webcompy/cli/`), application code, and all bundled pure-Python dependencies. Pure-Python packages available in the Pyodide CDN SHALL also be bundled and served from the WebComPy server. Only WASM packages SHALL be loaded from the Pyodide CDN. The generated HTML PyScript config SHALL reference the single wheel URL plus Pyodide CDN package names for WASM packages only.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single wheel containing webcompy (excl. cli), app code, and all pure-Python dependencies
- **AND** only WASM Pyodide CDN packages SHALL appear in `py-config.packages`

#### Scenario: Generating a static site
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** a single wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference the single wheel URL

## ADDED Requirements

### Requirement: Wheel files shall have cache-appropriate HTTP headers
The dev server SHALL set `Cache-Control` headers for the wheel file.

#### Scenario: App wheel caching in dev mode
- **WHEN** the dev server serves the wheel in dev mode
- **THEN** the response SHALL include `Cache-Control: no-cache`

### Requirement: Wheel URLs shall be stable and version-independent
The wheel URL SHALL NOT include a version suffix. The wheel SHALL be served at `/_webcompy-app-package/{app_name}-py3-none-any.whl`.

#### Scenario: App wheel URL
- **WHEN** the browser requests the wheel for an app named `myapp`
- **THEN** the URL SHALL be `/_webcompy-app-package/myapp-py3-none-any.whl`
- **AND** no version suffix SHALL appear in the URL

### Requirement: Dependencies shall be classified via lock file resolution
Dependencies listed in `AppConfig.dependencies` SHALL be classified using Pyodide lock data and local package inspection. Packages available in the Pyodide CDN SHALL be listed in `py-config.packages` by name. Pure-Python packages not in the Pyodide CDN SHALL be bundled into the app wheel. C-extension packages not in the Pyodide CDN SHALL cause an error.

#### Scenario: Bundling pure-Python dependencies not in Pyodide CDN
- **WHEN** `AppConfig.dependencies=["flask"]` and `flask` is pure-Python and not in the Pyodide CDN
- **AND** `flask`'s transitive dependency `click` is also pure-Python and not in the Pyodide CDN
- **THEN** `flask` and `click` SHALL be bundled into the app wheel
- **AND** `flask` SHALL be marked as `source="explicit"` in the lock file
- **AND** `click` SHALL be marked as `source="transitive"` in the lock file

#### Scenario: C extension not available in Pyodide
- **WHEN** `AppConfig.dependencies=["some_c_ext"]` and `some_c_ext` is not in the Pyodide CDN and contains `.so`, `.pyd`, or `.dylib` files
- **THEN** an error SHALL be reported indicating the package is a C extension not available in Pyodide

#### Scenario: Packages in Pyodide CDN
- **WHEN** `AppConfig.dependencies=["numpy"]` and `numpy` is in the Pyodide CDN
- **AND** `numpy` is a WASM package
- **THEN** `numpy` SHALL appear in `py-config.packages` as a plain package name
- **AND** `numpy` SHALL NOT be bundled into the app wheel

#### Scenario: Pure Python package in Pyodide CDN
- **WHEN** `AppConfig.dependencies=["httpx"]` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL be bundled into the app wheel and served from the WebComPy server
- **AND** `httpx` SHALL NOT appear in `py-config.packages`

### Requirement: The `webcompy lock` command shall generate or update the lock file
Running `webcompy lock` SHALL generate or update `webcompy-lock.json` in the project root. The lock file records Pyodide CDN package versions, bundled package versions and sources, and the Pyodide/PyScript versions used for classification.

#### Scenario: Generating a lock file
- **WHEN** a developer runs `webcompy lock` in a project with `AppConfig.dependencies=["flask", "numpy"]`
- **THEN** `webcompy-lock.json` SHALL be created in the project root
- **AND** it SHALL contain `pyodide_packages` with `numpy` and its CDN version
- **AND** it SHALL contain `bundled_packages` with `flask`, `click` (transitive), and their local versions

#### Scenario: Lock file already exists and dependencies unchanged
- **WHEN** `webcompy-lock.json` exists and `AppConfig.dependencies` matches
- **THEN** the existing lock file SHALL be validated and reused without network requests

#### Scenario: Lock file is stale
- **WHEN** `webcompy-lock.json` exists but `AppConfig.dependencies` has changed
- **THEN** the lock file SHALL be regenerated

### Requirement: The lock file shall be auto-generated on start and generate
The `webcompy start` and `webcompy generate` commands SHALL auto-generate `webcompy-lock.json` if it does not exist or is stale.

#### Scenario: Starting dev server without lock file
- **WHEN** a developer runs `python -m webcompy start --dev` without a `webcompy-lock.json`
- **THEN** the lock file SHALL be automatically generated before building wheels

#### Scenario: Generating static site with stale lock file
- **WHEN** a developer runs `python -m webcompy generate` and the lock file is stale
- **THEN** the lock file SHALL be regenerated before building wheels