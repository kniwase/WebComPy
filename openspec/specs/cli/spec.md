# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
Running `python -m webcompy start --dev` SHALL start a Starlette+uvicorn server that serves the application and automatically reloads the browser when source files change.

#### Scenario: Developing with hot-reload
- **WHEN** a developer runs the dev server and edits a Python file
- **THEN** the browser SHALL detect the change via an SSE connection and reload automatically

### Requirement: The dev server shall serve application packages
The dev server SHALL build Python wheel packages for both the webcompy framework and the application, and serve them at the `/_webcompy-app-package/` endpoint so that PyScript can load them in the browser.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build webcompy and app wheel packages on startup
- **AND** serve them at `/_webcompy-app-package/{filename}`
- **AND** the browser SHALL be able to import the application code

### Requirement: The generate command shall produce deployable static files
Running `python -m webcompy generate` SHALL produce a complete static site in the `dist/` directory, ready for deployment to any static hosting service.

#### Scenario: Generating a multi-page application with history mode
- **WHEN** routes are defined with history mode
- **THEN** an `index.html` SHALL be generated for each route path
- **AND** a `404.html` SHALL be generated for unmatched paths
- **AND** wheel packages SHALL be placed in `dist/_webcompy-app-package/`
- **AND** static files SHALL be copied from the configured directory
- **AND** a `.nojekyll` file SHALL be created for GitHub Pages compatibility

#### Scenario: Generating a single-page application with hash mode
- **WHEN** no router or hash mode is used
- **THEN** a single `index.html` SHALL be generated at the dist root
- **AND** all other assets SHALL be included as in the history mode case

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including a bootstrap file, static directory, and configuration template.

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created

### Requirement: Application configuration shall be discovered dynamically
The CLI SHALL dynamically import a `webcompy_config` module from the project directory to obtain the `WebComPyConfig` instance, including settings for the app package path, base URL, port, static files, and dependencies.

#### Scenario: Configuring an application
- **WHEN** a developer creates a `webcompy_config.py` with `config = WebComPyConfig(app_package="myapp", base="/app/")`
- **THEN** the CLI SHALL discover and use this configuration
- **AND** the base URL SHALL be normalized to `/app/`

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`