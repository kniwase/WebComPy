# Package Topology

## Purpose

WebComPy is split into four independently-installable packages under a uv workspace, enabling each component to carry only its own dependencies. This separation allows the browser-facing core to be published to PyPI as a zero-dependency package suitable for PyScript's `py-config.packages` consumption, while server-side rendering, CLI tooling, and testing utilities remain installable on demand.

## Requirements

### Requirement: The workspace shall contain four packages

The workspace SHALL contain four packages: `webcompy` (browser-facing core), `webcompy-server` (server-side rendering), `webcompy-cli` (command-line tools), and `webcompy-testing` (test utilities). All packages SHALL reside under a `packages/` directory and use uv workspace management.

#### Scenario: Workspace structure discovery
- **WHEN** a developer navigates the repository root
- **THEN** `packages/webcompy/`, `packages/webcompy-server/`, `packages/webcompy-cli/`, and `packages/webcompy-testing/` SHALL each contain their own `pyproject.toml` and `src/` directory

#### Scenario: uv workspace resolution
- **WHEN** `uv sync` is run from the workspace root
- **THEN** all four packages SHALL be resolved and their dependencies installed
- **AND** cross-package references SHALL use workspace sources (`{ workspace = true }`)

### Requirement: Core package shall have zero external dependencies

The `webcompy` core package SHALL have no runtime dependencies beyond the Python standard library. It SHALL NOT depend on `starlette`, `uvicorn`, `httpx`, `sse-starlette`, `aiofiles`, `beautifulsoup4`, or any other third-party package.

#### Scenario: Installing core alone
- **WHEN** a user runs `pip install webcompy`
- **THEN** only the Python standard library packages SHALL be installed
- **AND** `import webcompy` SHALL succeed without any import errors

#### Scenario: Core import in browser
- **WHEN** PyScript loads `webcompy` via `py-config.packages`
- **THEN** all core imports (`webcompy.signal`, `webcompy.components`, `webcompy.elements`, `webcompy.router`, `webcompy.app`, `webcompy.ui`) SHALL resolve
- **AND** no server-only dependencies SHALL be required

### Requirement: Server package shall depend on core and httpx

The `webcompy-server` package SHALL depend on `webcompy` (core) and `httpx`. It SHALL NOT depend on `starlette`, `uvicorn`, `sse-starlette`, `aiofiles`, or `playwright`.

#### Scenario: Installing server package
- **WHEN** a user runs `pip install webcompy-server`
- **THEN** `webcompy` and `httpx` SHALL be installed as dependencies
- **AND** `starlette` and `uvicorn` SHALL NOT be installed

### Requirement: CLI package shall depend on core, server, and web server dependencies

The `webcompy-cli` package SHALL depend on `webcompy`, `webcompy-server`, `starlette`, `uvicorn`, `sse-starlette`, and `aiofiles`. `playwright` SHALL be an optional dependency (only needed for `inspect` subcommands). `packaging` SHALL be an optional dependency (gracefully degraded when absent).

#### Scenario: Installing CLI package
- **WHEN** a user runs `pip install webcompy-cli`
- **THEN** `webcompy`, `webcompy-server`, `starlette`, `uvicorn`, `sse-starlette`, and `aiofiles` SHALL be installed as dependencies

#### Scenario: CLI without playwright
- **WHEN** `playwright` is not installed
- **THEN** `webcompy start` and `webcompy generate` SHALL work normally
- **AND** `webcompy inspect` SHALL produce a clear error message instructing the user to install `webcompy-cli[inspect]`

### Requirement: Testing package shall depend on core, server, starlette, and beautifulsoup4

The `webcompy-testing` package SHALL depend on `webcompy`, `webcompy-server`, `starlette`, and `beautifulsoup4`.

#### Scenario: Installing testing package
- **WHEN** a user runs `pip install webcompy-testing`
- **THEN** `webcompy`, `webcompy-server`, `starlette`, and `beautifulsoup4` SHALL be installed as dependencies

### Requirement: Each package shall have distinct public API boundaries

Core SHALL export only browser-runtime and shared abstractions: `signal`, `di`, `ports` (ABCs + browser impls), `aio`, `ajax`, `elements`, `components`, `router`, `plugin`, `app`, `ui` (theme, code block, composables), `exception`, `utils`. Server SHALL export server-side port implementations and HTML generation. CLI SHALL export `create_asgi_app`, `run_server`, `generate_static_site`, `discover_config`, `run_inspect`, config classes, and lockfile utilities. Testing SHALL export `TestRenderer`, fake ports, scope helpers, and ASGI utilities.

#### Scenario: Core public API does not expose server-only symbols
- **WHEN** a developer runs `from webcompy import *` in a browser environment
- **THEN** no `WebComPyBuildConfig`, `create_asgi_app`, `TestRenderer`, or `ServerDOMPort` SHALL be importable from `webcompy`

#### Scenario: Server public API exposes VirtualDOM
- **WHEN** a developer runs `from webcompy_server.ports import VirtualDOMNode, VirtualDOMEvent`
- **THEN** both classes SHALL be importable

### Requirement: Core shall provide extras for installing other packages

The `webcompy` core package SHALL define `[project.optional-dependencies]` extras: `server` (installs `webcompy-server`), `cli` (installs `webcompy-cli`), `testing` (installs `webcompy-testing`), and `full` (installs all three). Installing `webcompy` without extras SHALL install only the core.

#### Scenario: Installing full stack via extras
- **WHEN** a user runs `pip install webcompy[full]`
- **THEN** `webcompy-server`, `webcompy-cli`, and `webcompy-testing` SHALL be installed

#### Scenario: Installing server subset via extras
- **WHEN** a user runs `pip install webcompy[server]`
- **THEN** only `webcompy-server` SHALL be installed (not `webcompy-cli` or `webcompy-testing`)
