# Wheel Builder

## Purpose

The wheel builder produces PEP 427-compliant Python wheels for browser deployment without depending on setuptools or wheel. It supports bundling the webcompy framework and user application into a single wheel, including non-Python asset files with runtime lookup via `load_asset`. This eliminates the `SetuptoolsDeprecationWarning` and reduces browser load overhead.

## Requirements

### Requirement: The wheel builder shall produce browser-only and application wheels separately
The CLI SHALL build two wheels: a browser-only wheel containing the webcompy framework (excluding `cli/`) and an application wheel containing the app code and bundled pure-Python dependencies. The browser-only wheel URL SHALL be stable and cacheable.

#### Scenario: Building a browser-only wheel
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** it SHALL produce a PEP 427 wheel containing `webcompy/` without `cli/`
- **AND** `top_level.txt` SHALL list `webcompy`

#### Scenario: Building an application wheel with bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=[("mydep", path)])` is called
- **THEN** it SHALL produce a wheel containing the app package and `mydep/`
- **AND** `top_level.txt` SHALL list both packages

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