# Theme Switching

## Purpose

Provide runtime light/dark theme switching for WebComPy applications. This enables users to toggle between themes manually, which is essential for documentation sites and applications that want to offer visual preference control.

## Requirements

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

Each `WebComPyApp` instance SHALL have its own independent theme state. Multiple apps on the same page SHALL NOT share theme state.

#### Scenario: Multiple apps with different themes
- **WHEN** app A sets theme to `"dark"`
- **AND** app B sets theme to `"light"`
- **THEN** app A's HTML SHALL have `class="dark"`
- **AND** app B's HTML SHALL have `class="light"`

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
