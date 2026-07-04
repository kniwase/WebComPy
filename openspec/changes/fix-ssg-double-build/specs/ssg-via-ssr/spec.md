## ADDED Requirements

### Requirement: _ServingApp shall expose BuildArtifacts via artifacts field

The `_ServingApp` wrapper returned by `create_asgi_app()` SHALL include an `artifacts: BuildArtifacts` typed field containing the resolved build artifacts. This allows callers to access wheel filenames, in-memory file maps, and asset file paths without calling `resolve_build_artifacts()` independently.

#### Scenario: Accessing build artifacts from _ServingApp
- **WHEN** `create_asgi_app()` returns a `_ServingApp` wrapper
- **THEN** the wrapper's `artifacts` field SHALL contain the `BuildArtifacts` instance produced by the internal `resolve_build_artifacts()` call
- **AND** `serving.artifacts.app_package_files` SHALL contain the wheel byte content
- **AND** `serving.artifacts.wheel_filename` SHALL contain the app wheel filename
- **AND** `serving.artifacts` SHALL be accessible after `create_asgi_app()` returns (no cleanup occurs until the wrapper is discarded)

### Requirement: generate_app_version() shall produce deterministic output when no explicit version is configured

When `generate_app_version()` is called without an explicit version string, it SHALL return a deterministic, stable value. It SHALL NOT use wall-clock time, random values, or other non-deterministic sources. The intermediate version is an implementation detail used only for initial wheel construction before `_content_hash_wheel()` replaces it with the content-based hash.

#### Scenario: Calling generate_app_version() twice with no explicit version
- **WHEN** `generate_app_version()` is called twice with `app_version=None`
- **THEN** both calls SHALL return the same value

#### Scenario: Calling generate_app_version() with an explicit version
- **WHEN** `generate_app_version(app_version="1.2.3")` is called
- **THEN** it SHALL return `"1.2.3"` unchanged

## MODIFIED Requirements

### Requirement: Shared setup logic shall be extracted into _resolve_build_artifacts()

Dependency resolution, lockfile handling, WASM/runtime asset management, and wheel building logic SHALL be extracted from `_generate.py` and `_server.py` into a shared `resolve_build_artifacts()` function. `create_asgi_app()` SHALL be the sole caller of `resolve_build_artifacts()`; `_generate.py` SHALL obtain `BuildArtifacts` from the `_ServingApp.artifacts` field returned by `create_asgi_app()` rather than calling `resolve_build_artifacts()` directly. `cdn_temp_dir_obj` lifecycle SHALL be managed exclusively by `create_asgi_app()`, which SHALL call `__exit__()` on it immediately after wheel building.

#### Scenario: Dev/prod server uses shared setup
- **WHEN** `create_asgi_app()` is called
- **THEN** it SHALL call `resolve_build_artifacts()` to obtain build artifacts
- **AND** use those artifacts to create the ASGI app routes

#### Scenario: SSG uses shared setup
- **WHEN** `generate_static_site()` is called
- **THEN** it SHALL call `create_asgi_app()` to obtain a `_ServingApp` wrapper
- **AND** read `_ServingApp.artifacts` to access `BuildArtifacts`
- **AND** SHALL NOT call `resolve_build_artifacts()` directly
- **AND** SHALL NOT manage `cdn_temp_dir_obj` lifecycle (handled by `create_asgi_app()`)

#### Scenario: Build artifacts dataclass contains all resolved data
- **THEN** `BuildArtifacts` SHALL include `app_version`, `wheel_filename`, `extra_wheel_filenames`, `pyodide_package_names`, `wasm_local_urls`, `lockfile_url`, `runtime_serving`, and mode-specific fields (in-memory file maps for dev/prod, dist directory for SSG)

### Requirement: create_asgi_app() shall remain synchronous; hash-mode pre-rendering shall be a separate step

`create_asgi_app()` SHALL remain a synchronous function that returns a `_ServingApp` wrapper. The wrapper provides `asgi` (the underlying `Starlette` ASGI instance), `html_generator`, `hash_cache`, and `artifacts` (the `BuildArtifacts` instance) as typed attributes. `create_asgi_app()` SHALL NOT perform any async operations during construction. For hash-mode apps that need pre-rendered HTML cached at startup, a separate async function `_pre_render_hash_mode_html(app, html_generator)` SHALL be called after `create_asgi_app()` returns, producing the cached HTML that the hash-mode handler returns on every request. If `_pre_render_hash_mode_html()` raises an exception (e.g., due to a component rendering error during pre-rendering), the error SHALL propagate to the caller and the ASGI app SHALL NOT be started. This separation keeps `create_asgi_app()` usable with `uvicorn.run()` (which expects a synchronous app factory) and avoids unnecessary async complexity for the common history-mode case.

#### Scenario: Creating an ASGI app for a hash-mode app
- **WHEN** `create_asgi_app()` is called for a hash-mode app
- **THEN** it SHALL return a `_ServingApp` wrapper whose `.asgi` contains a synchronous handler returning pre-cached HTML
- **AND** `_pre_render_hash_mode_html(app)` SHALL be called afterward to generate and cache the HTML

#### Scenario: Creating an ASGI app for a history-mode app
- **WHEN** `create_asgi_app()` is called for a history-mode app
- **THEN** it SHALL return a `_ServingApp` wrapper
- **AND** no async pre-rendering SHALL be performed (each request renders dynamically)

#### Scenario: Calling create_asgi_app() from run_server()
- **WHEN** `run_server()` needs to create the ASGI app
- **THEN** it SHALL call `create_asgi_app()` synchronously to obtain a `_ServingApp` wrapper
- **AND** the mode SHALL be `"dev"` if the `--dev` CLI flag is present, otherwise `"prod"`
- **AND** for hash-mode, it SHALL call `asyncio.run(_pre_render_hash_mode_html(app))` after creation
- **AND** `serving.asgi` SHALL be passed to `uvicorn.run()` which expects a synchronous ASGI instance
- **AND** `run_server()` SHALL remain a synchronous function
- **AND** `build_config.server.dev` SHALL be read after `create_asgi_app()` returns to configure uvicorn file-watching reload

#### Scenario: Hash-mode pre-rendering raises during component rendering
- **WHEN** `_pre_render_hash_mode_html(app)` is called for a hash-mode app
- **AND** a component raises during SSR (e.g., an async setup fails, or a blocked fetch triggers a 500)
- **THEN** the error SHALL propagate to the caller
- **AND** `run_server()` SHALL catch the exception and abort server startup
- **AND** the ASGI app SHALL NOT be started
- **AND** RenderContext SHALL be disposed via `finally` block before the exception propagates
