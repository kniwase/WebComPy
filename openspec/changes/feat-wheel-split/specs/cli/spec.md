# CLI — Delta: feat-wheel-split

## MODIFIED Requirements

### Requirement: The dev server and SSG shall produce two separate wheels
The dev server and SSG SHALL build two separate Python wheels: a browser-only webcompy framework wheel excluding `webcompy/cli/`, and an application wheel containing app code and bundled pure-Python dependencies. The generated HTML PyScript config SHALL reference both wheel URLs plus Pyodide CDN package names (not bundled pure-Python dependencies).

#### Scenario: Starting the dev server with two-wheel architecture
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build two wheels: a framework wheel and an app wheel
- **AND** the generated HTML SHALL reference both wheel URLs in the PyScript configuration
- **AND** pure-Python dependencies bundled in the app wheel SHALL NOT appear in `py-config.packages`
- **AND** Pyodide CDN package names SHALL appear in `py-config.packages`

#### Scenario: Generating a static site with two-wheel architecture
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** both a framework wheel and an app wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** the generated HTML SHALL reference both wheel URLs

## ADDED Requirements

### Requirement: Wheel files shall have cache-appropriate HTTP headers
The dev server SHALL set `Cache-Control` headers appropriate to each wheel type.

#### Scenario: Framework wheel caching
- **WHEN** the dev server serves the framework wheel
- **THEN** the response SHALL include `Cache-Control: max-age=86400, must-revalidate`

#### Scenario: App wheel caching in dev mode
- **WHEN** the dev server serves the app wheel in dev mode
- **THEN** the response SHALL include `Cache-Control: no-cache`

### Requirement: Wheel URLs shall be stable and version-independent
Wheel URLs SHALL NOT include version suffixes. The framework wheel SHALL be served at `/_webcompy-app-package/webcompy-py3-none-any.whl`. The app wheel SHALL be served at `/_webcompy-app-package/{app_name}-py3-none-any.whl`.

#### Scenario: Framework wheel URL
- **WHEN** the browser requests the framework wheel
- **THEN** the URL SHALL be `/_webcompy-app-package/webcompy-py3-none-any.whl`
- **AND** no version suffix SHALL appear in the URL

#### Scenario: App wheel URL
- **WHEN** the browser requests the app wheel for an app named `myapp`
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
- **WHEN** `AppConfig.dependencies=["some_c_ext"]` and `some_c_ext` is not in the Pyodide CDN and contains `.so` files
- **THEN** an error SHALL be reported indicating the package is a C extension not available in Pyodide

#### Scenario: Packages in Pyodide CDN
- **WHEN** `AppConfig.dependencies=["numpy"]` and `numpy` is in the Pyodide CDN
- **THEN** `numpy` SHALL appear in `py-config.packages` as a plain package name
- **AND** `numpy` SHALL NOT be bundled into the app wheel

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