# Composables

## ADDED Requirements

### Requirement: use_theme shall return a Signal and ThemeController pair for theme manipulation

The framework SHALL provide a `webcompy.ui.composables.use_theme` (also re-exported from `webcompy.ui.theme`) composable function. When called inside a component's setup function, it SHALL return a `(Signal[Theme], ThemeController)` tuple where the signal reflects the current theme state of the active `ThemeManager` and the controller exposes `set(theme)`, `toggle()`, and `cycle()` methods.

#### Scenario: Reading the current theme from a component

- **WHEN** a developer writes `theme, controller = use_theme()` inside a `@define_component` setup function
- **THEN** `theme.value` SHALL return the current `Theme` value
- **AND** the value SHALL update reactively when the `ThemeManager`'s signal changes
- **AND** calling `controller.set(Theme.DARK)` SHALL update both the signal and the `<html>` `data-theme` attribute

#### Scenario: Calling use_theme outside a component setup

- **WHEN** `use_theme()` is called outside of a component setup function
- **THEN** the framework SHALL raise a `LookupError` with a message indicating that `use_theme` must be called inside a component setup context

### Requirement: use_theme shall integrate with the framework's DI scope

`use_theme()` SHALL resolve the active `ThemeManager` from the application DI scope. The same `ThemeManager` instance SHALL be returned to all components within the same app, ensuring consistent theme state across the app.

#### Scenario: Two components share the same ThemeManager

- **WHEN** component A calls `use_theme()` and component B calls `use_theme()` in the same app
- **THEN** both calls SHALL return signals bound to the same `ThemeManager`
- **AND** updating the theme from component A SHALL be visible in component B's signal

## MODIFIED Requirements

### Requirement: Composables shall be reusable stateful logic functions

Composables SHALL be plain Python functions (or function calls) that encapsulate signal state and lifecycle logic for use inside function-style component setup functions. They SHALL be callable inside a `@define_component` setup function and return values that integrate with the signal system (Signal, Computed, AsyncResult, etc.). WebComPy provides built-in composables (`useAsyncResult`, `useAsync`, and `use_theme`) for common patterns, and standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) that register hooks implicitly via context variables.

#### Scenario: Using a composable inside a component

- **WHEN** a developer calls a composable function inside a `@define_component` setup function
- **THEN** the returned signal values SHALL be usable in the component's template
- **AND** any lifecycle hooks registered by the composable SHALL fire at the correct times

#### Scenario: Using use_theme inside a component

- **WHEN** a developer calls `use_theme()` inside a `@define_component` setup function
- **THEN** the returned `Signal[Theme]` SHALL be usable in the component's template (e.g., to render a theme-aware label)
- **AND** the returned `ThemeController` SHALL be usable in event handlers (e.g., `@click` callbacks)

## REMOVED Requirements

(none)
