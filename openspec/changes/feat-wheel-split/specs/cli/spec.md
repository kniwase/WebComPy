# CLI — Delta: feat-wheel-split

## MODIFIED Requirements

### Requirement: The dev server and SSG shall produce two separate wheels
The dev server and SSG SHALL build two separate Python wheels: a browser-only webcompy framework wheel excluding `webcompy/cli/`, and an application wheel containing app code and bundled pure-Python dependencies. The generated HTML PyScript config SHALL reference both wheel URLs plus C-extension/Pyodide built-in package names (not pure-Python dependencies).

#### Scenario: Starting the dev server with two-wheel architecture
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build two wheels: a framework wheel and an app wheel
- **AND** the generated HTML SHALL reference both wheel URLs in the PyScript configuration
- **AND** pure-Python dependencies SHALL NOT appear in `py-config.packages`

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

### Requirement: Pure-Python dependencies shall be bundled into the app wheel
Pure-Python dependencies listed in `AppConfig.dependencies` SHALL be bundled into the app wheel. Only C-extension and Pyodide built-in packages SHALL remain in `py-config.packages`.

#### Scenario: Bundling pure-Python dependencies
- **WHEN** `AppConfig.dependencies=["httpx", "numpy"]` and `httpx` is pure-Python while `numpy` is a C-extension
- **THEN** `httpx` SHALL be bundled into the app wheel
- **AND** `numpy` SHALL appear in `py-config.packages` in the generated HTML