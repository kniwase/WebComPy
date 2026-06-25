# App Config

## ADDED Requirements

### Requirement: WebComPyAppConfig.theme shall configure default theme and persistence behavior

`WebComPyAppConfig` SHALL accept an optional `theme: dict | None` field. When provided, the dict SHALL accept the keys `default` (one of `"light"`, `"dark"`, `"system"`, defaulting to `"system"`) and `persist` (`True` or `False`, defaulting to `True`). When `persist=True`, theme changes SHALL be written to a `webcompy-theme` cookie; when `False`, theme changes SHALL NOT be persisted.

#### Scenario: Default theme configuration

- **WHEN** a developer sets `WebComPyAppConfig(theme={"default": "dark"})`
- **THEN** the application's `ThemeManager` SHALL be initialized with `Theme.DARK` when no `webcompy-theme` cookie is present
- **AND** the `<html>` element SHALL be rendered with `data-theme="dark"` during SSR

#### Scenario: Persistence disabled

- **WHEN** a developer sets `WebComPyAppConfig(theme={"default": "light", "persist": False})`
- **AND** a user toggles the theme to `Theme.DARK` via the UI
- **THEN** the `<html>` element SHALL be updated to `data-theme="dark"`
- **AND** no `webcompy-theme` cookie SHALL be written
- **AND** on a subsequent page load, the theme SHALL return to `Theme.LIGHT`

## MODIFIED Requirements

### Requirement: WebComPyBuildConfig.assets shall map keys to file paths

`WebComPyBuildConfig.assets` SHALL accept an optional mapping of string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`. In addition, files placed directly in the directory specified by `static_files_dir` (default `"static"`) SHALL be served as static assets by the dev server and copied into the build output by the SSG, without needing an explicit `assets` entry.

#### Scenario: Configuring assets

- **WHEN** a developer provides `assets={"logo": "images/logo.png"}`
- **THEN** the asset SHALL be included in the bundled wheel
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

#### Scenario: Omitting assets

- **WHEN** a developer does not provide `assets`
- **THEN** `assets` SHALL default to `None`
- **AND** no assets SHALL be included in the bundled wheel

#### Scenario: Static directory files are served without explicit assets entries

- **WHEN** a developer places a file at `static/styles/tokens.css` relative to the app package
- **AND** the dev server or SSG runs
- **THEN** the file SHALL be reachable at the URL `static/styles/tokens.css` (or the equivalent under the `static_files_dir` setting)
- **AND** no `assets` entry SHALL be required to make it reachable

## REMOVED Requirements

(none)
