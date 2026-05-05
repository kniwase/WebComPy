# HTML Attribute Control

## Purpose

WebComPy applications need the ability to set attributes on the root `<html>` element for features like class-based dark mode (`<html class="dark">`), language attributes (`lang="ja"`), or custom `data-*` attributes. This capability bridges the gap between the component tree (which renders inside `#webcompy-app`) and the outer document structure.

## Requirements

### Requirement: The application shall support setting static attributes on the HTML element

Developers SHALL be able to call `app.set_html_attr(key, value)` where `key` is an attribute name and `value` is a static string.

#### Scenario: Setting a language attribute
- **WHEN** a developer calls `app.set_html_attr("lang", "ja")`
- **THEN** the `<html>` element in the generated HTML SHALL include `lang="ja"`
- **AND** in the browser, the live `<html>` element SHALL have `lang="ja"`

### Requirement: The application shall support reactive HTML attributes

Developers SHALL be able to pass a `Computed[str]` value to `set_html_attr`. When the computed value changes, the live `<html>` element SHALL be updated in the browser.

#### Scenario: Reactive dark mode class
- **WHEN** a developer creates `theme = Signal("light")` and calls `app.set_html_attr("class", computed(lambda: theme.value))`
- **THEN** initially the `<html>` element SHALL have `class="light"`
- **WHEN** `theme.value` is changed to `"dark"`
- **THEN** the `<html>` element SHALL update to `class="dark"`

### Requirement: HTML attributes shall be per-application

Each `WebComPyApp` instance SHALL have its own set of HTML attributes. Setting an attribute on one app SHALL NOT affect another app.

#### Scenario: Two apps with different HTML attributes
- **WHEN** app A calls `app.set_html_attr("lang", "ja")`
- **AND** app B calls `app.set_html_attr("lang", "en")`
- **THEN** app A's HTML output SHALL have `lang="ja"`
- **AND** app B's HTML output SHALL have `lang="en"`

### Requirement: Attributes shall appear in static site generation output

When generating HTML via `generate_html()`, the `<html>` element SHALL include all attributes set via `set_html_attr`.

#### Scenario: SSG with HTML attributes
- **WHEN** an app sets `app.set_html_attr("data-theme", "dark")`
- **AND** static site generation runs
- **THEN** the generated `index.html` SHALL contain `<html data-theme="dark">`

### Requirement: Attributes shall be removable

Developers SHALL be able to remove a previously set attribute via `app.remove_html_attr(key)`.

#### Scenario: Removing an attribute
- **WHEN** a developer calls `app.set_html_attr("data-custom", "value")` followed by `app.remove_html_attr("data-custom")`
- **THEN** the `<html>` element SHALL NOT contain `data-custom`
- **AND** in the browser, the attribute SHALL be removed from the live DOM
