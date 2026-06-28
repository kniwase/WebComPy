# app-styles Specification

## Purpose
TBD - created by archiving change feat-reactive-app-style. Update Purpose after archive.
## Requirements
### Requirement: app.append_style shall accept a string or Computed[str]

`WebComPyApp.append_style(content)` SHALL accept either a plain string (static) or a `Computed[str]` (reactive). The framework SHALL render the content into a single `<style data-webcompy-dynamic="{id}">` element inside `<head>`, where `{id}` is the position in the head element's `_styles` list (0-based).

#### Scenario: Registering a static string
- **WHEN** a developer calls `app.append_style(".my-class { color: red; }")` at app setup
- **THEN** the framework SHALL emit `<style data-webcompy-dynamic="0">.my-class { color: red; }</style>` in `<head>`
- **AND** the element SHALL not be re-rendered unless `append_style` is called again

#### Scenario: Registering a Computed[str]
- **WHEN** a developer calls `app.append_style(computed_str)` at app setup
- **THEN** the framework SHALL emit `<style data-webcompy-dynamic="0">{computed_str.value}</style>` in `<head>` with the current value
- **AND** when the underlying signals change, the framework SHALL update the element's `textContent` to the new computed value

#### Scenario: Registering multiple styles
- **WHEN** a developer calls `app.append_style` three times with different content
- **THEN** three `<style data-webcompy-dynamic>` elements SHALL be emitted, with `id` values `0`, `1`, `2`
- **AND** updates to one SHALL NOT affect the others

### Requirement: Dynamic styles are emitted unlayered

The framework SHALL emit `<style data-webcompy-dynamic="{id}">` elements whose textContent is the user-supplied content without an outer `@layer` wrapping. Emitting dynamic styles unlayered lets them win over any layered framework CSS in the cascade. Users who need to override unlayered application CSS can append `!important` to the relevant declarations.

#### Scenario: Rendered style is unlayered
- **WHEN** `app.append_style(":root { --x: red; }")` is called
- **THEN** the emitted `<style data-webcompy-dynamic="0">` element SHALL contain `:root { --x: red; }` directly (no surrounding `@layer webcompy-dynamic { ... }` wrapper)

### Requirement: Reactive styles shall update the DOM on computed change

When a `Computed[str]` registered via `app.append_style` changes, the framework SHALL update the matching `<style data-webcompy-dynamic="{id}">` element's `textContent` to the new value. The update SHALL be synchronous from the signal setter's perspective.

#### Scenario: Computed change updates the style
- **WHEN** a signal read inside the `Computed` is set to a new value
- **THEN** the matching `<style data-webcompy-dynamic>` element's `textContent` SHALL reflect the new CSS
- **AND** the document's computed styles SHALL update accordingly

### Requirement: App-level style subscriptions shall be disposed on teardown

The `CallbackConsumerNode` registered for each reactive style SHALL be disposed when the head element is cleaned up (e.g., app dispose, render context dispose). The framework SHALL NOT leave dangling subscriptions.

#### Scenario: Cleanup disposes subscriptions
- **WHEN** the app's render context is disposed
- **THEN** all `app.append_style` subscriptions SHALL be disposed
- **AND** subsequent signal changes SHALL NOT attempt to update non-existent `<style>` elements

### Requirement: reactive_style helper shall build a Computed[str] from a var mapping

The framework SHALL provide a `reactive_style(selector, vars_dict)` helper that returns a `Computed[str]`. The helper SHALL support plain strings, `SignalBase[str]`, and `Callable[[], str]` as values in `vars_dict`. The returned `Computed[str]` SHALL produce CSS of the form `{selector} { {name}: {value}; ... }`.

#### Scenario: Building a reactive style from a dict
- **WHEN** a developer writes:
  ```python
  app.append_style(reactive_style(":root", {
      "--color-accent": Signal("#0969da"),
      "--color-bg": "white",
  }))
  ```
- **THEN** the returned `Computed[str]` SHALL produce `":root {\n  --color-accent: #0969da;\n  --color-bg: white;\n}"`
- **AND** when the signal is set to a new value, the computed SHALL re-evaluate

### Requirement: reactive_block helper shall build a Computed[str] from a content string

The framework SHALL provide a `reactive_block(selector, content)` helper that returns a `Computed[str]`. `content` SHALL be a string, `SignalBase[str]`, or callable returning a string. The returned `Computed[str]` SHALL produce CSS of the form `{selector} { {content} }`.

#### Scenario: Building a reactive block
- **WHEN** a developer writes:
  ```python
  app.append_style(reactive_block("body", computed(lambda: f"color: {fg.value};")))
  ```
- **THEN** the returned `Computed[str]` SHALL produce `"body {\ncolor: ...\n}"`
- **AND** changes to `fg` SHALL trigger re-evaluation

