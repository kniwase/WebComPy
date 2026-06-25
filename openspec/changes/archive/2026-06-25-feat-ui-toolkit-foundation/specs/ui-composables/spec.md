# UI Composables

## Purpose

Provide reusable composable functions for UI toolkit features, starting with `use_theme()`. Composables are plain functions called inside a component's setup function that return reactive state and controller objects for use in the component's template and lifecycle.

## ADDED Requirements

### Requirement: The framework SHALL provide a `use_theme()` composable

The framework SHALL provide a `use_theme()` function under `webcompy.ui.composables` (or `webcompy.ui.theme`) that, when called inside a component setup function, returns a `(Signal[Theme], ThemeController)` tuple representing the current theme state and a controller for modifying it.

#### Scenario: Calling use_theme in a component

- **WHEN** a developer calls `theme, controller = use_theme()` inside a `@define_component` setup function
- **THEN** `theme` SHALL be a `Signal[Theme]` whose value reflects the current `ThemeManager` state
- **AND** `controller` SHALL be a `ThemeController` with `set`, `toggle`, and `cycle` methods

### Requirement: `ThemeController.set(theme)` SHALL set the theme

`ThemeController.set(theme: Theme)` SHALL update the `ThemeManager`'s signal to the given value, which causes the `<html>` `data-theme` attribute and the `webcompy-theme` cookie to update reactively.

#### Scenario: Setting an explicit theme

- **WHEN** `controller.set(Theme.DARK)` is called from a component event handler
- **THEN** the `ThemeManager`'s signal value SHALL become `Theme.DARK`
- **AND** the `<html>` element's `data-theme` attribute SHALL be updated to `"dark"`
- **AND** a `webcompy-theme=dark` cookie SHALL be set

### Requirement: `ThemeController.toggle()` SHALL switch between `light` and `dark`

`ThemeController.toggle()` SHALL switch from `Theme.LIGHT` to `Theme.DARK` and from `Theme.DARK` to `Theme.LIGHT`. When the current value is `Theme.SYSTEM`, `toggle()` SHALL switch to the opposite of the user's `prefers-color-scheme` preference.

#### Scenario: Toggling from light to dark

- **WHEN** the current theme is `Theme.LIGHT` and `controller.toggle()` is called
- **THEN** the theme SHALL become `Theme.DARK`

#### Scenario: Toggling from system

- **WHEN** the current theme is `Theme.SYSTEM` and the user's OS preference is light
- **THEN** `controller.toggle()` SHALL set the theme to `Theme.DARK`

### Requirement: `ThemeController.cycle()` SHALL cycle through `light` → `dark` → `system` → `light`

`ThemeController.cycle()` SHALL advance the theme in the order `LIGHT → DARK → SYSTEM → LIGHT`, wrapping from `SYSTEM` back to `LIGHT`. This is intended for a "theme picker" button that walks through all three modes.

#### Scenario: Cycling through the three states

- **WHEN** the current theme is `Theme.LIGHT` and `controller.cycle()` is called repeatedly three times
- **THEN** the theme sequence SHALL be `LIGHT → DARK → SYSTEM → LIGHT`
