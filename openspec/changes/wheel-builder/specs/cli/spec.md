## MODIFIED Requirements

### Requirement: The dev server shall serve application packages
The dev server SHALL build a single bundled Python wheel containing both the webcompy framework and the application, and serve it at the `/_webcompy-app-package/` endpoint so that PyScript can load it in the browser.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single bundled wheel containing both webcompy and the application code
- **AND** serve it at `/_webcompy-app-package/{filename}`
- **AND** the browser SHALL be able to import both `webcompy` and the application package

#### Scenario: Dev server with package_data
- **WHEN** a developer configures `package_data={"myapp": ["data/*.json"]}` in `WebComPyConfig`
- **THEN** the bundled wheel SHALL include the matching non-Python files inside the package tree
- **AND** those files SHALL be accessible via `importlib.resources` in the browser

### Requirement: The generate command shall produce deployable static files
Running `python -m webcompy generate` SHALL produce a complete static site in the `dist/` directory, ready for deployment to any static hosting service.

#### Scenario: Generating a multi-page application with history mode
- **WHEN** routes are defined with history mode
- **THEN** an `index.html` SHALL be generated for each route path
- **AND** a `404.html` SHALL be generated for unmatched paths
- **AND** a single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** static files SHALL be copied from the configured directory
- **AND** a `.nojekyll` file SHALL be created for GitHub Pages compatibility

#### Scenario: Generating a single-page application with hash mode
- **WHEN** no router or hash mode is used
- **THEN** a single `index.html` SHALL be generated at the dist root
- **AND** all other assets SHALL be included as in the history mode case

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL
- **AND** `typing_extensions` SHALL NOT appear in the packages list

## ADDED Requirements

### Requirement: Application configuration shall support package_data
`WebComPyConfig` SHALL accept a `package_data` parameter that specifies non-Python files to include in the application wheel, organized by package name with glob patterns.

#### Scenario: Configuring package_data for application resources
- **WHEN** a developer specifies `package_data={"myapp": ["data/*.json", "templates/*.html"]}`
- **THEN** the CLI SHALL include matching files in the bundled wheel inside the `myapp` package tree
- **AND** those files SHALL be accessible via `importlib.resources` in the browser environment

#### Scenario: Omitting package_data
- **WHEN** a developer does not specify `package_data`
- **THEN** only Python source files, stub files, and `py.typed` markers SHALL be included in the wheel