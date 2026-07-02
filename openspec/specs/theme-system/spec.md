# theme-system Specification

## Purpose
The framework's theme system enables a single WebComPy application to render a light, dark, or OS-preference-aware color scheme without per-component wiring. Themes are applied by injecting a single reactive `<style data-webcompy-dynamic>` element whose content reflects the active `Theme` value, instead of mutating an HTML attribute and relying on per-rule CSS selectors. This keeps the cascade order predictable (dynamic styles win unlayered), the SSR path trivial (one CSS string), and the client path reactive (one signal).
## Requirements
### Requirement: The framework SHALL define a `Theme` enum with `light`, `dark`, and `system` values

The framework SHALL provide a `webcompy.ui.theme.Theme` enum with three values: `Theme.LIGHT`, `Theme.DARK`, and `Theme.SYSTEM`. `Theme.SYSTEM` is the default and means the resolved theme is determined by the user's `prefers-color-scheme` media query.

#### Scenario: Importing the enum

- **WHEN** a developer writes `from webcompy.ui.theme import Theme`
- **THEN** `Theme.LIGHT`, `Theme.DARK`, and `Theme.SYSTEM` SHALL be accessible
- **AND** `Theme.SYSTEM` SHALL be the default value when no other value is provided

### Requirement: The framework SHALL provide a `ThemeManager` class

The framework SHALL provide a `webcompy.ui.theme.ThemeManager` class that owns a `Signal[Theme]` and a `Computed[str]` that derives a CSS string from the signal value. The manager registers the computed with the application via `app.append_style(self._css)` so the resolved CSS is injected as a reactive `<style data-webcompy-dynamic>` element. The manager persists the user's choice in a `webcompy-theme` cookie on the client. The manager SHALL NOT set any `data-theme` HTML attribute; the rendered theme is derived from the injected CSS, not from DOM attributes.

#### Scenario: Creating a ThemeManager stores the initial value

- **WHEN** a `ThemeManager` is created with `initial=Theme.DARK` and a `WebComPyApp` instance
- **THEN** the internal `Signal[Theme]` SHALL have `value == Theme.DARK`
- **AND** the computed CSS SHALL reflect the dark theme (token overrides for dark mode)
- **AND** no `data-theme` attribute SHALL be added to the `<html>` element

#### Scenario: Registering the manager installs a reactive style

- **WHEN** `manager.register_style()` is called
- **THEN** `app.append_style(manager._css)` SHALL be invoked
- **AND** a `<style data-webcompy-dynamic="...">` element SHALL appear in the rendered head
- **AND** subsequent updates to the `Signal[Theme]` SHALL update the element's `textContent` reactively

#### Scenario: Updating the theme updates the injected CSS

- **WHEN** the `ThemeManager.set(Theme.LIGHT)` is called on the client
- **THEN** the `Signal[Theme]` value SHALL become `Theme.LIGHT`
- **AND** the injected `<style data-webcompy-dynamic>` element's content SHALL change to the light-theme CSS (empty body for light, since light is the base)
- **AND** a `webcompy-theme=light` cookie SHALL be set with `Max-Age` of one year, `Path=/`, and `SameSite=Lax`

#### Scenario: Selecting the system theme uses a media query

- **WHEN** the `ThemeManager.set(Theme.SYSTEM)` is called
- **THEN** the injected CSS SHALL wrap the dark-token override in `@media (prefers-color-scheme: dark) { :root { ... } }`
- **AND** the `webcompy-theme` cookie SHALL be cleared (Max-Age=0)
- **AND** no `data-theme` attribute SHALL be added to the `<html>` element

### Requirement: The framework SHALL resolve the initial theme from a cookie on the server

The framework's CLI server (`packages/webcompy-cli/src/webcompy_cli/_server.py`) SHALL read the `webcompy-theme` cookie from the incoming request, parse its value as `Theme`, and pass it as `initial_theme` to `app.create_render_context()`. The `RenderContext` SHALL create the `ThemeManager` with that initial value so the server-rendered HTML includes the correct `<style data-webcompy-dynamic>` element on first paint.

#### Scenario: Server reads cookie for SSR

- **WHEN** a request arrives with `Cookie: webcompy-theme=dark`
- **THEN** the server-rendered HTML SHALL include a `<style data-webcompy-dynamic="...">` element containing the dark-theme token overrides
- **AND** no client-side JavaScript SHALL be required to apply the theme on first paint

#### Scenario: Missing cookie falls back to system

- **WHEN** a request arrives without a `webcompy-theme` cookie
- **THEN** the server SHALL render with `Theme.SYSTEM` (the injected CSS SHALL use the `prefers-color-scheme` media-query wrapper)

#### Scenario: Invalid cookie value falls back to system

- **WHEN** a request arrives with `Cookie: webcompy-theme=invalid-value`
- **THEN** the server SHALL fall back to `Theme.SYSTEM` and not raise an error

#### Scenario: Initial theme can be overridden by app config

- **WHEN** `WebComPyAppConfig(theme={"default": "dark"})` is set and the request has no `webcompy-theme` cookie
- **THEN** the server SHALL initialize the `ThemeManager` with `Theme.DARK`

### Requirement: The framework SHALL resolve the initial theme from the cookie on the client

When a `WebComPyApp` starts in the browser, the framework SHALL read the `webcompy-theme` cookie (via `read_theme_cookie_value()` resolving `COOKIE_PORT_KEY`) and initialize the `ThemeManager` with the corresponding `Theme` value. If the cookie is absent, the initial value SHALL be `Theme.SYSTEM` (or the value from `WebComPyAppConfig.theme["default"]` if configured).

#### Scenario: Client picks up the persisted theme

- **WHEN** a `WebComPyApp.run()` is called in the browser and `document.cookie` contains `webcompy-theme=dark`
- **THEN** the `ThemeManager` SHALL be initialized with `Theme.DARK`
- **AND** the `Signal[Theme]` SHALL have `value == Theme.DARK` on first read

#### Scenario: Client with no cookie starts in system mode

- **WHEN** a `WebComPyApp.run()` is called in the browser and no `webcompy-theme` cookie is present
- **THEN** the `ThemeManager` SHALL be initialized with `Theme.SYSTEM`

### Requirement: Multiple WebComPy apps on a single document SHALL NOT isolate their theme state

The framework SHALL NOT guarantee that multiple `WebComPyApp` instances on the same page have independent theme state. Because the reactive style is appended to a single shared `<head>` and the cookie is shared by the browser, the most recently rendered or activated app SHALL win. This limitation SHALL be documented.

#### Scenario: Two apps, conflicting themes

- **WHEN** app A activates `Theme.DARK` and app B activates `Theme.LIGHT` on the same page
- **THEN** the rendered `<style data-webcompy-dynamic>` element SHALL reflect whichever activation happened last
- **AND** no error SHALL be raised

### Requirement: The reactive CSS injection SHALL be the single source of truth for the rendered theme

The framework SHALL NOT mutate any HTML attribute (e.g. `data-theme`) to communicate the active theme. The rendered theme SHALL be derived from the `<style data-webcompy-dynamic>` element that `ThemeManager.register_style()` installs. Component CSS SHALL use `var(--*)` tokens whose values change inside the injected rule body to react to the active theme; no per-component logic SHALL be required.

#### Scenario: CSS targets the injected rule, not an attribute

- **WHEN** a stylesheet contains `.my-card { background: var(--color-bg-card); }` and the active theme's injected CSS overrides `--color-bg-card` under `:root { ... }`
- **THEN** `.my-card` SHALL render with the dark `--color-bg-card` value whenever the `ThemeManager` signal value is `Theme.DARK`
- **AND** the rendering SHALL NOT depend on any `data-theme` attribute on the `<html>` element

