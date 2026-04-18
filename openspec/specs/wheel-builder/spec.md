# Wheel Builder

## Purpose

The wheel builder produces PEP 427-compliant Python wheels for browser deployment without depending on setuptools or wheel. It supports bundling the webcompy framework and user application into a single wheel, including non-Python asset files with runtime lookup via `load_asset`. This eliminates the `SetuptoolsDeprecationWarning` and reduces browser load overhead.

## Requirements

### Requirement: The wheel builder shall produce PEP 427-compliant wheels without setuptools
The CLI SHALL build Python wheels by manually constructing ZIP archives containing the package source tree and a `.dist-info` directory with `METADATA`, `WHEEL`, `top_level.txt`, and `RECORD` files. The builder SHALL NOT depend on `setuptools`, `distutils`, or `wheel`.

#### Scenario: Building a simple wheel
- **WHEN** the CLI builds a wheel for a package at a given path
- **THEN** the output SHALL be a valid PEP 427 `.whl` file
- **AND** the wheel SHALL contain all `.py` files and `py.typed`/`.pyi` files from the package
- **AND** the `.dist-info/METADATA` SHALL include `Metadata-Version`, `Name`, and `Version`
- **AND** the `.dist-info/WHEEL` SHALL include `Wheel-Version: 1.0`, `Root-Is-Purelib: true`, and `Tag: py3-none-any`
- **AND** the `.dist-info/RECORD` SHALL list every file with its `sha256` hash (URL-safe base64, no padding) and size
- **AND** the `.dist-info/top_level.txt` SHALL list the top-level package name

#### Scenario: Building a wheel with no setuptools dependency
- **WHEN** the wheel builder module is imported
- **THEN** it SHALL NOT import `setuptools`, `distutils`, or `wheel`
- **AND** it SHALL only use Python standard library modules (`zipfile`, `hashlib`, `pathlib`, `os`, `re`)

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
The wheel builder SHALL be able to bundle multiple top-level packages (e.g., the webcompy framework and a user application) into a single wheel. The bundled wheel SHALL list all top-level packages in `top_level.txt`. Both packages SHALL be importable after PyScript loads the wheel.

#### Scenario: Bundling framework and application
- **WHEN** the CLI builds a bundled wheel containing `webcompy` and `app` packages
- **THEN** the `.dist-info/top_level.txt` SHALL contain both `webcompy` and `app`
- **AND** `import webcompy` SHALL work after the wheel is installed
- **AND** `import app` SHALL work after the wheel is installed
- **AND** only a single `.whl` file SHALL be produced

#### Scenario: Bundled wheel naming
- **WHEN** the CLI builds a bundled wheel with name `app` and version `25.107.43200`
- **THEN** the wheel file name SHALL follow PEP 427: `app-25.107.43200-py3-none-any.whl`