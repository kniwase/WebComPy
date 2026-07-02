# Wheel Builder

## Purpose

The wheel builder produces PEP 427-compliant Python wheels for browser deployment without depending on setuptools or wheel. It supports bundling the webcompy framework and user application into a single wheel, including non-Python asset files with runtime lookup via `load_asset`. This eliminates the `SetuptoolsDeprecationWarning` and reduces browser load overhead.

In the refactored package structure, the wheel builder moves to `webcompy_cli._wheel_builder` (formerly `packages/webcompy-cli/src/webcompy_cli/_wheel_builder.py`). The browser wheel now contains only the `webcompy` core package — `webcompy_cli`, `webcompy_server`, and `webcompy_testing` are separate packages and do not need explicit exclusion. The `_BROWSER_ONLY_EXCLUDE` mechanism is no longer necessary.

## Requirements

### MODIFIED: The wheel builder shall produce PEP 427-compliant wheels without setuptools
All wheels produced by the builder SHALL be valid PEP 427 `.whl` files. The builder SHALL NOT depend on `setuptools`, `distutils`, or `wheel`. The builder module SHALL live at `packages/webcompy-cli/src/webcompy_cli/_wheel_builder.py` (formerly `webcompy/cli/_wheel_builder.py`). Each wheel SHALL contain a `.dist-info/` directory with `METADATA`, `WHEEL`, `top_level.txt`, and `RECORD` files. The `RECORD` file SHALL list every file with its `sha256` hash (URL-safe base64, no padding) and size. The `.dist-info/WHEEL` SHALL include `Wheel-Version: 1.0`, `Root-Is-Purelib: true`, and `Tag: py3-none-any`.

#### Scenario: Building a wheel with no setuptools dependency
- **WHEN** the wheel builder module is imported
- **THEN** it SHALL NOT import `setuptools`, `distutils`, or `wheel`
- **AND** it SHALL only use Python standard library modules (`zipfile`, `hashlib`, `pathlib`, `os`, `re`)

#### Scenario: Wheel RECORD and METADATA compliance
- **WHEN** the CLI builds any wheel
- **THEN** the `.dist-info/METADATA` SHALL include `Metadata-Version`, `Name`, and `Version`
- **AND** the `.dist-info/RECORD` SHALL list every file with its `sha256` hash and size
- **AND** the `.dist-info/top_level.txt` SHALL list the top-level package name(s)

### MODIFIED: The app wheel shall bundle webcompy core and bundled dependencies (bundled mode)
When `wheel_mode="bundled"` (default), `make_webcompy_app_package()` SHALL produce a single PEP 427 wheel containing the `webcompy` core package (not `webcompy_cli`, `webcompy_server`, or `webcompy_testing`), the application package, and appropriate pure-Python dependencies based on `serve_all_deps`. The `_BROWSER_ONLY_EXCLUDE` mechanism is no longer needed because the packages are physically separate. The wheel filename SHALL include a content-derived hash for cache busting (see Content-hash wheel filename requirement).

#### Scenario: Building an app wheel with webcompy bundled (bundled mode)
- **WHEN** `make_webcompy_app_package()` is called with `wheel_mode="bundled"`
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy_cli/`, `webcompy_server/`, or `webcompy_testing/`
- **AND** `top_level.txt` SHALL list `webcompy` and the app name
- **AND** the wheel filename SHALL follow the content-hash pattern `{app_name}-0+sha.{hash8}-py3-none-any.whl`

#### Scenario: Building an app wheel without bundled dependencies (bundled mode)
- **WHEN** `make_webcompy_app_package(..., bundled_deps=None)` is called with `wheel_mode="bundled"`
- **THEN** the resulting wheel SHALL contain `webcompy` core and the app package only
- **AND** the wheel filename SHALL follow the content-hash pattern

#### Scenario: Building an app wheel with a single-file module dependency
- **WHEN** a bundled dependency extracted from a CDN wheel is a single `.py` file module (no `__init__.py`, just a top-level `.py` file, e.g., `six.py`)
- **THEN** the wheel SHALL include that `.py` file at the wheel root level (e.g., `six.py`, not `six/six.py`)
- **AND** `top_level.txt` SHALL list the module name alongside other top-level packages
- **AND** importing that module SHALL work after PyScript loads the wheel

### MODIFIED: The wheel builder shall support bundled dependencies in the app wheel
`make_webcompy_app_package()` SHALL accept an optional `bundled_deps` parameter of type `list[tuple[str, pathlib.Path]]`. When provided, each tuple represents a package name and its installed directory path. These directories SHALL be included in the app wheel alongside the app package, and their top-level names SHALL appear in `top_level.txt`.

#### Scenario: Building an app wheel with bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=[("click", Path("/site-packages/click"))])` is called
- **THEN** the resulting wheel SHALL contain webcompy, the app package, and `click/` directory
- **AND** `top_level.txt` SHALL list `webcompy`, the app name, and `click`

### MODIFIED: App wheel filenames shall include a content-hash for cache busting
The app wheel filename SHALL embed a SHA-256 hash derived from the wheel file contents, enabling automatic cache busting when the application code changes. The filename SHALL follow the PEP 440 local version identifier pattern: `{normalized_name}-0+sha.{hash8}-py3-none-any.whl`, where `{hash8}` is the first 8 hex characters of the SHA-256 digest of the wheel bytes. This ensures that any change to the bundled code produces a different filename, invalidating browser and CDN caches without requiring manual version bumps.

#### Scenario: Content-hash in app wheel filename
- **WHEN** `make_webcompy_app_package()` builds an app wheel for an app named `myapp`
- **THEN** the wheel filename SHALL match the pattern `myapp-0+sha.{hash8}-py3-none-any.whl`
- **AND** the filename SHALL be PEP 427-compliant (5 dash-separated parts before `.whl`)
- **AND** the METADATA SHALL contain `Version: 0+sha.{hash8}`

#### Scenario: Content hash changes when code changes
- **WHEN** the same app is built twice with different source code
- **THEN** the two wheel filenames SHALL differ in the `{hash8}` component
- **AND** the same source code built repeatedly SHALL produce the same `{hash8}`

#### Scenario: Content-hash filename propagated to HTML
- **WHEN** the dev server or static generator produces HTML
- **THEN** the `py-config.packages` URL SHALL reference the content-hashed wheel filename
- **AND** no consumer SHALL compute the wheel filename independently — it SHALL use the filename returned by `make_webcompy_app_package()`

### MODIFIED: The wheel builder shall support assets for non-Python files
The wheel builder SHALL accept an `assets` parameter specifying a mapping of string keys to file paths (relative to the app package directory). Files referenced by these paths SHALL be included in the wheel inside the package tree. Additionally, the builder SHALL generate an `_assets_registry.py` module inside the app package that maps each key to its full package-qualified path, enabling runtime asset lookup via `importlib.resources`.

#### Scenario: Including asset files in a wheel
- **WHEN** `assets={"logo": "logo.png", "config": "data/config.json"}` is specified and the referenced files exist in the app package
- **THEN** the wheel SHALL contain `myapp/logo.png` and `myapp/data/config.json` at the correct paths
- **AND** the wheel SHALL contain `myapp/_assets_registry.py` with a `_REGISTRY` dict mapping each key to its package path

#### Scenario: No assets specified
- **WHEN** `assets` is `None` (default)
- **THEN** the wheel SHALL contain only `.py`, `.pyi`, and `py.typed` files
- **AND** the wheel SHALL NOT contain an `_assets_registry.py` module

#### Scenario: Accessing assets at runtime
- **WHEN** a developer calls `load_asset("logo")` in browser or server code
- **THEN** the function SHALL return the raw `bytes` content of the asset file
- **AND** `AssetNotFoundError` SHALL be raised if the key is not found in the registry or the registry module is missing

### MODIFIED: The wheel builder shall support bundling multiple packages into a single wheel
The wheel builder SHALL be able to bundle multiple top-level packages (e.g., the webcompy framework and a user application) into a single wheel. The bundled wheel SHALL list all top-level packages in `top_level.txt`. Both packages SHALL be importable after PyScript loads the wheel. The wheel filename SHALL be derived from the app package name using PEP 427 normalization (underscores, not hyphens, in the distribution name component), and a helper function SHALL compute this filename for use by all consumers.

#### Scenario: Bundling framework and application
- **WHEN** the CLI builds a bundled wheel containing `webcompy` and `myapp` packages
- **THEN** the `.dist-info/top_level.txt` SHALL contain both `webcompy` and `myapp`
- **AND** `import webcompy` SHALL work after the wheel is installed
- **AND** `import myapp` SHALL work after the wheel is installed
- **AND** only a single `.whl` file SHALL be produced

#### Scenario: Bundled wheel naming (non-app wheels)
- **WHEN** the CLI builds a bundled wheel for an app package named `docs_app` with version `25.107.43200`
- **THEN** the wheel file name SHALL be `docs_app-25.107.43200-py3-none-any.whl`
- **AND** `get_wheel_filename("docs_app", "25.107.43200")` SHALL return `"docs_app-25.107.43200-py3-none-any.whl"`
- **AND** the filename SHALL match the URL referenced in the generated HTML

#### Scenario: Wheel filename consistency across all consumers
- **WHEN** the HTML template, dev server, and static generator each need the wheel filename
- **THEN** the app wheel filename SHALL come from the return value of `make_webcompy_app_package()`
- **AND** non-app wheels SHALL use `get_wheel_filename(name, version)` from the wheel builder module
- **AND** no consumer SHALL hardcode the wheel filename pattern

### MODIFIED: The wheel builder shall produce a framework wheel in split mode
When `wheel_mode="split"`, `make_browser_webcompy_wheel()` SHALL produce a PEP 427 wheel containing the `webcompy` core package only (not `webcompy_cli`, `webcompy_server`, or `webcompy_testing`). `_BROWSER_ONLY_EXCLUDE` is no longer needed. The wheel filename SHALL use a content-derived hash: `webcompy-0+sha.{hash8}-py3-none-any.whl`.

#### Scenario: Building a framework wheel in split mode
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy_cli/`, `webcompy_server/`, or `webcompy_testing/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL follow the content-hash pattern `webcompy-0+sha.{hash8}-py3-none-any.whl`

#### Scenario: Framework wheel hash changes on version upgrade
- **WHEN** a new version of webcompy is released and `make_browser_webcompy_wheel()` is called again
- **THEN** the wheel filename SHALL change, invalidating browser caches for all users

### MODIFIED: The app wheel in split mode shall bundle the app and all dependencies
When `wheel_mode="split"`, `make_webcompy_app_package()` SHALL produce a wheel containing the app package, its assets, and ALL pure-Python dependencies (both locally-installed and CDN-downloaded). The wheel filename SHALL use content-hash: `{app_name}-0+sha.{hash8}-py3-none-any.whl`. Dependencies are NOT split into individual wheels.

#### Scenario: Building app wheel in split mode
- **WHEN** `make_webcompy_app_package()` is called with `wheel_mode="split"`
- **THEN** the resulting wheel SHALL contain the app package, its assets, and all bundled dependencies
- **AND** the wheel SHALL NOT contain `webcompy/` (framework is a separate wheel)
- **AND** the filename SHALL follow the content-hash pattern

### ADDED: Browser wheel contents shall be determined by package structure, not exclusion list

With the package split, the browser wheel SHALL contain only the `webcompy` core package. Because `webcompy_cli`, `webcompy_server`, and `webcompy_testing` are physically separate packages, they SHALL NOT appear in the browser wheel without needing any explicit `_BROWSER_ONLY_EXCLUDE` mechanism. The wheel builder SHALL discover `webcompy` package files from its package root and include all `.py`, `.pyi`, and `py.typed` files.

#### Scenario: No _BROWSER_ONLY_EXCLUDE needed
- **WHEN** the wheel builder builds a browser wheel
- **THEN** the `_BROWSER_ONLY_EXCLUDE` list SHALL be empty or removed
- **AND** the wheel SHALL naturally contain only files under the `webcompy/` directory tree