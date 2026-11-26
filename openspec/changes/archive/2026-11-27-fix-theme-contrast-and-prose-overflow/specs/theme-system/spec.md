# Spec Delta

## MODIFIED Requirements

### Requirement: The framework SHALL provide a `ThemeManager` class

The framework SHALL provide a `webcompy.ui.theme.ThemeManager` class that owns a `Signal[Theme]` and a `Computed[str]` that derives a CSS string from the signal value. The manager registers the computed with the application via `app.append_style(self._css)` so the resolved CSS is injected as a reactive `<style data-webcompy-dynamic>` element. The manager persists the user's choice in a `webcompy-theme` cookie on the client. The manager SHALL NOT set any `data-theme` HTML attribute; the rendered theme is derived from the injected CSS, not from DOM attributes. For `Theme.LIGHT`, the injected CSS SHALL declare `:root { color-scheme: light; }` (and explicit light overrides where needed) rather than an empty string so an OS dark preference does not override browser form-control color schemes; for `Theme.DARK`, it SHALL declare `color-scheme: dark` alongside dark token overrides; and for `Theme.SYSTEM`, it SHALL preserve `@media (prefers-color-scheme: dark)` token overrides under the base `color-scheme: light dark`.

#### Scenario: Creating a ThemeManager stores the initial value

- **WHEN** a `ThemeManager` is created with `initial=Theme.DARK` and a `WebComPyApp` instance
- **THEN** the internal `Signal[Theme]` SHALL have `value == Theme.DARK`
- **AND** the computed CSS SHALL reflect the dark theme (explicit `color-scheme: dark` plus token overrides for dark mode)
- **AND** no `data-theme` attribute SHALL be added to the `<html>` element

#### Scenario: Registering the manager installs a reactive style

- **WHEN** `manager.register_style()` is called
- **THEN** `app.append_style(manager._css)` SHALL be invoked
- **AND** a `<style data-webcompy-dynamic="...">` element SHALL appear in the rendered head
- **AND** subsequent updates to the `Signal[Theme]` SHALL update the element's `textContent` reactively

#### Scenario: Updating the theme updates the injected CSS

- **WHEN** `ThemeManager.set(Theme.LIGHT)` is called on the client
- **THEN** the `Signal[Theme]` value SHALL become `Theme.LIGHT`
- **AND** the injected `<style data-webcompy-dynamic>` element's content SHALL declare `:root { color-scheme: light; }` so light surface polarity and native controls apply even under an OS dark preference
- **AND** a `webcompy-theme=light` cookie SHALL be set with `Max-Age` of one year, `Path=/`, and `SameSite=Lax`

#### Scenario: Selecting the system theme uses a media query

- **WHEN** `ThemeManager.set(Theme.SYSTEM)` is called
- **THEN** the injected CSS SHALL wrap the dark-token override in `@media (prefers-color-scheme: dark) { :root { ... } }` while inheriting `:root { color-scheme: light dark; }`
- **AND** the `webcompy-theme` cookie SHALL be cleared (Max-Age=0)
- **AND** no `data-theme` attribute SHALL be added to the `<html>` element

## ADDED Requirements

### Requirement: Cookie-persisted theme hydration on statically exported pages SHALL avoid UI hydration mismatches

When a statically exported site (built without a per-request cookie, defaulting in HTML to `Theme.SYSTEM`) is opened or reloaded in a browser with a `webcompy-theme` cookie set, applying the persisted theme and updating theme-selector UI controls SHALL NOT trigger element-level hydration mismatches or emit hydration-mismatch warnings.

#### Scenario: Reloading a static page with a persisted dark cookie

- **WHEN** a user selects `dark` on a statically served WebComPy page and reloads the page
- **THEN** the active `<style data-webcompy-dynamic>` element and theme toggle control SHALL reflect `dark`
- **AND** browser hydration SHALL complete with zero hydration mismatch records for the theme control
