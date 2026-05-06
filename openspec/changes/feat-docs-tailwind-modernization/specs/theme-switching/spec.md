# Theme Switching

## Purpose

Provide runtime light/dark theme switching for WebComPy applications. This enables users to toggle between themes manually, which is essential for documentation sites and applications that want to offer visual preference control.

## ADDED Requirements

### Requirement: The application SHALL support reactive theme state

A `Signal[str]` SHALL be used to track the current theme (e.g., `"light"` or `"dark"`). Changes to this Signal SHALL trigger reactive updates across the application.

#### Scenario: Toggle button switches theme
- **WHEN** a user clicks a theme toggle button
- **THEN** the theme Signal SHALL change from `"light"` to `"dark"` or vice versa
- **AND** all reactive components depending on the theme SHALL update

### Requirement: Theme changes SHALL affect the HTML root element

The current theme class SHALL be applied to the `<html>` element so that CSS frameworks using class-based dark mode (like Tailwind) can detect the theme.

#### Scenario: HTML element reflects theme
- **WHEN** the theme is `"dark"`
- **THEN** the `<html>` element SHALL have `class="dark"`
- **WHEN** the theme changes to `"light"`
- **THEN** the `<html>` element SHALL have `class="light"`

### Requirement: The theme SHALL be per-application

Each `WebComPyApp` instance SHALL have its own independent theme state. **However, since there is only one `<html>` element per document, setting `class` on `<html>` via `app.set_html_attr` means multiple apps on the same page will conflict.** The most recently rendered app's `html_attrs` will take effect. This is a known limitation of the single `<html>` element model.

#### Scenario: Single app theme switching
- **WHEN** an app sets theme to `"dark"`
- **THEN** the app's HTML output SHALL have `class="dark"`
- **WHEN** the theme changes to `"light"`
- **THEN** the app's HTML output SHALL have `class="light"`

#### Scenario: Multiple apps limitation
- **WHEN** app A sets theme to `"dark"`
- **AND** app B sets theme to `"light"`
- **THEN** only one theme class SHALL be present on the `<html>` element
- **AND** the most recently rendered app's theme SHALL take effect

### Requirement: Theme toggle UI SHALL be accessible

The theme toggle button SHALL have:
- `aria-label="Toggle theme"` or similar descriptive label
- `role="switch"`
- `aria-checked` reflecting the current state (for screen readers)

#### Scenario: Screen reader navigation
- **WHEN** a screen reader focuses the theme toggle
- **THEN** it SHALL announce the current theme state
- **AND** describe the action (e.g., "Toggle theme, switch, dark")

### Requirement: External stylesheet themes SHALL switch reactively

When the theme changes, external stylesheet links (like highlight.js themes) SHALL update to match the selected theme.

#### Scenario: Highlight.js theme switching
- **WHEN** the theme is `"light"`
- **THEN** the highlight.js stylesheet SHALL be the light theme
- **WHEN** the theme changes to `"dark"`
- **THEN** the highlight.js stylesheet SHALL switch to the dark theme
