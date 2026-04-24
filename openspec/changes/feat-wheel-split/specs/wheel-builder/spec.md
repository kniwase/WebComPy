# Wheel Builder — Delta: feat-wheel-split

## ADDED Requirements

### Requirement: The wheel builder shall produce a browser-only framework wheel
`make_browser_webcompy_wheel(webcompy_package_dir, dest, version)` SHALL produce a PEP 427 wheel containing the webcompy framework source but excluding `webcompy/cli/` and `webcompy/cli/template_data/`. The wheel SHALL be named `webcompy-py3-none-any.whl` (no version suffix in filename).

#### Scenario: Building a browser-only wheel
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL be `webcompy-py3-none-any.whl` (without version)

### Requirement: The wheel builder shall support bundled dependencies in the app wheel
`make_webcompy_app_package()` SHALL accept an optional `bundled_deps` parameter of type `list[tuple[str, pathlib.Path]]`. When provided, each tuple represents a package name and its installed directory path. These directories SHALL be included in the app wheel alongside the app package, and their top-level names SHALL appear in `top_level.txt`.

#### Scenario: Building an app wheel with bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=[("click", Path("/site-packages/click"))])` is called
- **THEN** the resulting wheel SHALL contain both the app package and `click/` directory
- **AND** `top_level.txt` SHALL list both the app name and `click`

#### Scenario: Building an app wheel without bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=None)` is called
- **THEN** the resulting wheel SHALL contain only the app package
- **AND** `bundled_deps` parameter SHALL default to `None`

### Requirement: Wheel URLs shall use stable filenames without version suffixes
Wheel filenames served to browsers SHALL NOT include version strings. The framework wheel SHALL be named `webcompy-py3-none-any.whl` and the app wheel SHALL be named `{app_name}-py3-none-any.whl`. The version SHALL appear only in the wheel's METADATA, not in the URL.

#### Scenario: Framework wheel filename
- **WHEN** a framework wheel is built
- **THEN** the served filename SHALL be `webcompy-py3-none-any.whl`
- **AND** the METADATA SHALL contain `Version: {version}`

#### Scenario: App wheel filename
- **WHEN** an app wheel is built for an app named `myapp`
- **THEN** the served filename SHALL be `myapp-py3-none-any.whl`
- **AND** the METADATA SHALL contain `Version: {version}`