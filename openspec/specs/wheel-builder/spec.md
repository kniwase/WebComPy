# Wheel Builder

## Purpose

The wheel builder produces PEP 427-compliant Python wheels for browser deployment without depending on setuptools or wheel. It supports bundling the webcompy framework and user application into a single wheel, including non-Python asset files with runtime lookup via `load_asset`. This eliminates the `SetuptoolsDeprecationWarning` and reduces browser load overhead.

## Requirements

### Requirement: The wheel builder shall produce PEP 427-compliant wheels without setuptools
All wheels produced by the builder SHALL be valid PEP 427 `.whl` files. The builder SHALL NOT depend on `setuptools`, `distutils`, or `wheel`. Each wheel SHALL contain a `.dist-info/` directory with `METADATA`, `WHEEL`, `top_level.txt`, and `RECORD` files. The `RECORD` file SHALL list every file with its `sha256` hash (URL-safe base64, no padding) and size. The `.dist-info/WHEEL` SHALL include `Wheel-Version: 1.0`, `Root-Is-Purelib: true`, and `Tag: py3-none-any`.

#### Scenario: Building a wheel with no setuptools dependency
- **WHEN** the wheel builder module is imported
- **THEN** it SHALL NOT import `setuptools`, `distutils`, or `wheel`
- **AND** it SHALL only use Python standard library modules (`zipfile`, `hashlib`, `pathlib`, `os`, `re`)

#### Scenario: Wheel RECORD and METADATA compliance
- **WHEN** the CLI builds any wheel
- **THEN** the `.dist-info/METADATA` SHALL include `Metadata-Version`, `Name`, and `Version`
- **AND** the `.dist-info/RECORD` SHALL list every file with its `sha256` hash and size
- **AND** the `.dist-info/top_level.txt` SHALL list the top-level package name(s)

### Requirement: The app wheel shall bundle webcompy (excluding cli) and bundled dependencies
`make_webcompy_app_package()` SHALL produce a single PEP 427 wheel containing the webcompy framework source (excluding `webcompy/cli/`), the application package, and any bundled pure-Python dependencies (i.e., packages not available from the Pyodide CDN). The wheel SHALL be named `{app_name}-py3-none-any.whl` (no version suffix in filename). `make_browser_webcompy_wheel()` SHALL NOT exist — webcompy is bundled inside the app wheel.

#### Scenario: Building an app wheel with webcompy bundled
- **WHEN** `make_webcompy_app_package()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy` and the app name
- **AND** the wheel filename SHALL be `{app_name}-py3-none-any.whl` (without version)

#### Scenario: Building an app wheel without bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=None)` is called
- **THEN** the resulting wheel SHALL contain webcompy (excl. cli) and the app package only
- **AND** the wheel filename SHALL be `{app_name}-py3-none-any.whl`

### Requirement: The wheel builder shall support bundled dependencies in the app wheel
`make_webcompy_app_package()` SHALL accept an optional `bundled_deps` parameter of type `list[tuple[str, pathlib.Path]]`. When provided, each tuple represents a package name and its installed directory path. These directories SHALL be included in the app wheel alongside the app package, and their top-level names SHALL appear in `top_level.txt`.

#### Scenario: Building an app wheel with bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=[("click", Path("/site-packages/click"))])` is called
- **THEN** the resulting wheel SHALL contain webcompy, the app package, and `click/` directory
- **AND** `top_level.txt` SHALL list `webcompy`, the app name, and `click`

### Requirement: Wheel URLs shall use stable filenames without version suffixes
The wheel filename served to browsers SHALL NOT include a version string. The app wheel SHALL be named `{app_name}-py3-none-any.whl`. The version SHALL appear only in the wheel's METADATA, not in the URL.

#### Scenario: App wheel filename
- **WHEN** an app wheel is built for an app named `myapp`
- **THEN** the served filename SHALL be `myapp-py3-none-any.whl`
- **AND** the METADATA SHALL contain `Version: {version}`

### Requirement: The wheel builder shall support assets for non-Python files
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

### Requirement: The wheel builder shall support bundling multiple packages into a single wheel
The wheel builder SHALL be able to bundle multiple top-level packages (e.g., the webcompy framework and a user application) into a single wheel. The bundled wheel SHALL list all top-level packages in `top_level.txt`. Both packages SHALL be importable after PyScript loads the wheel. The wheel filename SHALL be derived from the app package name using PEP 427 normalization (underscores, not hyphens, in the distribution name component), and a helper function SHALL compute this filename for use by all consumers.

#### Scenario: Bundling framework and application
- **WHEN** the CLI builds a bundled wheel containing `webcompy` and `myapp` packages
- **THEN** the `.dist-info/top_level.txt` SHALL contain both `webcompy` and `myapp`
- **AND** `import webcompy` SHALL work after the wheel is installed
- **AND** `import myapp` SHALL work after the wheel is installed
- **AND** only a single `.whl` file SHALL be produced

#### Scenario: Bundled wheel naming
- **WHEN** the CLI builds a bundled wheel for an app package named `docs_src` with version `25.107.43200`
- **THEN** the wheel file name SHALL be `docs_src-25.107.43200-py3-none-any.whl`
- **AND** `get_wheel_filename("docs_src", "25.107.43200")` SHALL return `"docs_src-25.107.43200-py3-none-any.whl"`
- **AND** the filename SHALL match the URL referenced in the generated HTML

#### Scenario: Wheel filename consistency across all consumers
- **WHEN** the HTML template, dev server, and static generator each need the wheel filename
- **THEN** they SHALL all call `get_wheel_filename(name, version)` from the wheel builder module
- **AND** no consumer SHALL hardcode the wheel filename pattern