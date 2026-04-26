# Wheel Builder — Delta: feat-dependency-bundling

## ADDED Requirements

### Requirement: The app wheel shall bundle webcompy (excluding cli) and bundled dependencies
`make_webcompy_app_package()` SHALL produce a single PEP 427 wheel containing the webcompy framework source (excluding `webcompy/cli/`), the application package, and any bundled pure-Python dependencies. The wheel SHALL be named `{app_name}-py3-none-any.whl` (no version suffix in filename).

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