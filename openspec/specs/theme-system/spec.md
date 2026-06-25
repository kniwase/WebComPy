# theme-system Specification

## Purpose
TBD - created by archiving change feat-ui-toolkit-foundation. Update Purpose after archive.
## Requirements
### Requirement: The framework SHALL define a `Theme` enum with `light`, `dark`, and `system` values

The framework SHALL provide a `webcompy.ui.theme.Theme` enum with three values: `Theme.LIGHT`, `Theme.DARK`, and `Theme.SYSTEM`. `Theme.SYSTEM` is the default and means the resolved theme is determined by the user's `prefers-color-scheme` media query.

#### Scenario: Importing the enum

- **WHEN** a developer writes `from webcompy.ui.theme import Theme`
- **THEN** `Theme.LIGHT`, `Theme.DARK`, and `Theme.SYSTEM` SHALL be accessible
- **AND** `Theme.SYSTEM` SHALL be the default value when no other value is provided

### Requirement: The framework SHALL provide a `ThemeManager` class

The framework SHALL provide a `webcompy.ui.theme.ThemeManager` class that owns a `Signal[Theme]`, applies changes to the `<html>` element's `data-theme` attribute via `app.set_html_attr`, and persists changes to a `webcompy-theme` cookie on the client.

#### Scenario: Creating a ThemeManager sets the initial attribute

- **WHEN** a `ThemeManager` is created with `initial=Theme.DARK` and a `WebComPyApp` instance
- **THEN** the `<html>` element's `data-theme` attribute SHALL be set to `"dark"`
- **AND** the internal `Signal[Theme]` SHALL have `value == Theme.DARK`

#### Scenario: Updating the theme updates the attribute

- **WHEN** the `ThemeManager`'s signal value is set to `Theme.LIGHT`
- **THEN** the `<html>` element's `data-theme` attribute SHALL be updated to `"light"` reactively
- **AND** a `webcompy-theme=light` cookie SHALL be set with `Max-Age` of one year, `Path=/`, and `SameSite=Lax`

#### Scenario: Selecting the system theme removes the attribute

- **WHEN** the `ThemeManager`'s signal value is set to `Theme.SYSTEM`
- **THEN** the `<html>` element SHALL have no `data-theme` attribute (or the attribute is removed)
- **AND** the `webcompy-theme` cookie SHALL be cleared (Max-Age=0)

### Requirement: The framework SHALL resolve the initial theme from a cookie on the server

The framework's CLI server (`webcompy/cli/_server.py`) SHALL read the `webcompy-theme` cookie from the incoming request, parse its value as `Theme`, and provide a `ThemeManager` with that initial value via the application's DI scope.

#### Scenario: Server reads cookie for SSR

- **WHEN** a request arrives with `Cookie: webcompy-theme=dark`
- **THEN** the server-rendered HTML SHALL include `<html data-theme="dark">`
- **AND** no client-side JavaScript SHALL be required to apply the theme on first paint

#### Scenario: Missing cookie falls back to system

- **WHEN** a request arrives without a `webcompy-theme` cookie
- **THEN** the server SHALL render with `Theme.SYSTEM` (no `data-theme` attribute)
- **AND** the user's OS preference SHALL determine the resolved theme via `prefers-color-scheme`

#### Scenario: Invalid cookie value falls back to system

- **WHEN** a request arrives with `Cookie: webcompy-theme=invalid-value`
- **THEN** the server SHALL fall back to `Theme.SYSTEM` and not raise an error

### Requirement: The framework SHALL resolve the initial theme from the `<html>` attribute on the client

When a `WebComPyApp` starts in the browser, the framework SHALL read the `<html>` element's `data-theme` attribute (if present) and initialize the `ThemeManager` with the corresponding `Theme` value. If the attribute is absent, the initial value SHALL be `Theme.SYSTEM`.

#### Scenario: Client picks up the SSR-rendered theme

- **WHEN** a `WebComPyApp.run()` is called in the browser and the `<html>` element has `data-theme="dark"`
- **THEN** the `ThemeManager` SHALL be initialized with `Theme.DARK`
- **AND** the `Signal[Theme]` SHALL have `value == Theme.DARK` on first read

#### Scenario: Client with no attribute starts in system mode

- **WHEN** a `WebComPyApp.run()` is called in the browser and the `<html>` element has no `data-theme` attribute
- **THEN** the `ThemeManager` SHALL be initialized with `Theme.SYSTEM`

### Requirement: Multiple WebComPy apps on a single document SHALL NOT isolate their theme state

The framework SHALL NOT guarantee that multiple `WebComPyApp` instances on the same page have independent theme state. Because there is exactly one `<html>` element per document and exactly one `data-theme` attribute, the most recently rendered or activated app SHALL win. This limitation SHALL be documented.

#### Scenario: Two apps, conflicting themes

- **WHEN** app A activates `Theme.DARK` and app B activates `Theme.LIGHT` on the same page
- **THEN** the `<html>` element SHALL reflect whichever activation happened last
- **AND** no error SHALL be raised

### Requirement: The `data-theme` attribute SHALL be the single source of truth for the rendered theme

The framework SHALL NOT derive the rendered theme from the `Signal[Theme]` value directly; it SHALL derive it from the `<html>` element's `data-theme` attribute via CSS selectors. Component CSS SHALL target `:root[data-theme="dark"]` (or use `var(--*)` tokens whose values change in the dark selector block) to react to the active theme.

#### Scenario: CSS targets the attribute, not the signal

- **WHEN** a stylesheet contains `.my-card { background: var(--color-bg-card); }` and `tokens.css` overrides `--color-bg-card` under `:root[data-theme="dark"]`
- **THEN** `.my-card` SHALL render with the dark `--color-bg-card` value whenever the `<html>` element has `data-theme="dark"`
- **AND** the rendering SHALL NOT depend on the `ThemeManager` signal being observed by the component

