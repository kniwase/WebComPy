# reactive-scoped-style Specification

## Purpose
TBD - created by archiving change feat-reactive-scoped-style. Update Purpose after archive.
## Requirements
### Requirement: A function shall produce a reactive scoped style from a callable

A developer SHALL be able to declare a reactive scoped style inside the component setup function by calling `reactive_scoped_style(func)`, where `func` is a `Callable[[], dict[str, Any]]` that returns the existing scoped-style dictionary shape (selector → declarations). The function SHALL be evaluated as a `Computed` so that any signal read inside the function is tracked as a dependency.

#### Scenario: Declaring a reactive style with a constant dict
- **WHEN** a developer writes:
  ```python
  @define_component()
  def MyComponent(context):
      context.use_reactive_scoped_style(
          reactive_scoped_style(lambda: {".my-class": {"color": "blue"}})
      )
      return html.DIV({}, "...")
  ```
- **THEN** the framework SHALL register the style
- **AND** a `<style data-webcompy-cid-rx="{cid}-0">` element SHALL be emitted into `<head>` with the scoped CSS string

#### Scenario: Declaring a reactive style that reads a signal
- **WHEN** a developer writes:
  ```python
  @define_component()
  def MyComponent(context):
      color = Signal("blue")
      context.use_reactive_scoped_style(
          reactive_scoped_style(lambda: {".my-class": {"color": color.value}})
      )
      return html.DIV({}, "...")
  ```
- **THEN** the framework SHALL register the style
- **AND** the initial `<style>` element SHALL contain `color: blue`
- **AND** when `color.value` is set to `"red"`, the `<style>` element's `textContent` SHALL be updated to `color: red` without a re-render of the component

### Requirement: Reactive styles shall be registered via ComponentContext

A reactive style SHALL be registered by calling `context.use_reactive_scoped_style(style)` from within the component setup function. The framework SHALL associate the style with the current `ComponentGenerator` (the same one created by `@define_component`).

#### Scenario: Calling use_reactive_scoped_style inside a component
- **WHEN** a developer calls `context.use_reactive_scoped_style(style)` inside the component setup function
- **THEN** the framework SHALL append `style` to the active `ComponentGenerator._reactive_styles` list
- **AND** the style SHALL be emitted into the document head on the next render

#### Scenario: Calling use_reactive_scoped_style outside a component
- **WHEN** a developer calls `use_reactive_scoped_style` from a context that is not inside a `@define_component` setup function
- **THEN** the framework SHALL raise a `WebComPyException` with a message identifying the misuse

### Requirement: Multiple reactive styles per component shall be allowed

A single `ComponentGenerator` SHALL accept any number of registered reactive styles. Each SHALL be rendered as a separate `<style data-webcompy-cid-rx="{cid}-{index}">` element, where `{index}` is the position in the generator's `_reactive_styles` list (0-based).

#### Scenario: Registering three reactive styles
- **WHEN** a developer registers three reactive styles in a single component
- **THEN** three `<style data-webcompy-cid-rx>` elements SHALL be emitted
- **AND** their `index` values SHALL be `0`, `1`, `2` respectively
- **AND** updates to any one style SHALL NOT affect the others

### Requirement: Reactive styles shall coexist with the static scoped_style API

A component MAY define both a static `scoped_style` dictionary AND one or more reactive styles. The two SHALL be rendered as separate elements: the static style uses `data-webcompy-cid="{cid}"`; the reactive styles use `data-webcompy-cid-rx="{cid}-{index}"`. Updates to the reactive style SHALL NOT modify the static `<style>` element.

#### Scenario: Component with both static and reactive styles
- **WHEN** a developer defines:
  ```python
  @define_component()
  def MyComponent(context):
      color = Signal("blue")
      context.use_reactive_scoped_style(
          reactive_scoped_style(lambda: {".dynamic": {"color": color.value}})
      )
      return html.DIV({}, "...")

  MyComponent.scoped_style = {".static": {"font-size": "1rem"}}
  ```
- **THEN** the document head SHALL contain a `<style data-webcompy-cid="...">` for the static rule
- **AND** a `<style data-webcompy-cid-rx="...-0">` for the reactive rule
- **AND** both SHALL coexist independently

### Requirement: Reactive styles shall update the DOM on signal change

When any signal read inside the reactive style function changes, the framework SHALL:

1. Re-evaluate the function to obtain the new dict
2. Re-render the dict to a scoped CSS string (with selector scoping and `@layer webcompy-scope` wrapping)
3. Set the `<style data-webcompy-cid-rx="{cid}-{index}">` element's `textContent` to the new CSS string

The update SHALL be synchronous from the signal setter's perspective (matching the existing `set_html_attr` semantics for `Computed` values).

#### Scenario: Signal change updates the style element
- **WHEN** a signal read inside a reactive style function is set to a new value
- **THEN** the matching `<style data-webcompy-cid-rx>` element SHALL reflect the new CSS
- **AND** the new CSS SHALL take effect in the document's computed styles without any explicit `set_html_attr` or `data-*` attribute change

### Requirement: Reactive style subscriptions shall be disposed with the component

The `CallbackConsumerNode` registered for each reactive style SHALL be disposed when the owning component is destroyed (`on_before_destroy`). The framework SHALL NOT leave dangling subscriptions after a component is removed from the tree.

#### Scenario: Component is destroyed
- **WHEN** a component is removed from the DOM
- **THEN** all reactive style subscriptions for that component SHALL be disposed
- **AND** subsequent signal changes SHALL NOT attempt to update non-existent `<style>` elements

### Requirement: Reactive styles shall be renderable during SSR

During static site generation and prerendered serving, the framework SHALL evaluate each registered reactive style once and emit the resulting CSS as a `<style data-webcompy-cid-rx>` element in the generated HTML. The SSR output SHALL reflect the signal values at the time of generation. Collection of reactive styles for the head SHALL run after the component tree render completes and pending render-settling async work has been awaited, so reactive styles registered during async component setup SHALL also be emitted.

#### Scenario: SSG renders initial reactive style
- **WHEN** a component with a reactive style is included in a static-generated page
- **THEN** the generated HTML SHALL contain a `<style data-webcompy-cid-rx>` element
- **AND** its `textContent` SHALL equal the value of the reactive style's `Computed` at generation time

#### Scenario: Reactive style registered during async setup
- **WHEN** a component with async setup registers a reactive scoped style
- **AND** the page containing the component is prerendered
- **THEN** the generated HTML SHALL contain the corresponding `<style data-webcompy-cid-rx>` element after the async work settles

### Requirement: Reactive style functions shall be synchronous

A `reactive_scoped_style` function SHALL be a synchronous callable. Async functions SHALL NOT be accepted. The `Computed` contract requires synchronous evaluation.

#### Scenario: Passing an async function
- **WHEN** a developer passes `async def f(): ...` to `reactive_scoped_style`
- **THEN** the framework SHALL raise a `TypeError` at registration time with a message indicating the function must be synchronous

### Requirement: Reactive scoping shall be identical to static scoping

The selector-scoping transformation applied to reactive scoped styles SHALL be the same transformation used for static `scoped_style` (a single shared implementation). For any identical style dict input, the scoped selector output of the static and reactive paths SHALL match.

#### Scenario: Same input, same output
- **WHEN** the same selector set (including combinators such as `a~b`, leading `> .child`, and functional pseudo-classes like `:nth-child(2n+1)`) is rendered through the static `scoped_style` setter and through `reactive_scoped_style`
- **THEN** both paths SHALL produce identical scoped selectors
- **AND** neither path SHALL split selectors inside parentheses, brackets, or strings

#### Scenario: Leading combinator at top level
- **WHEN** a top-level selector starts with a combinator (e.g., `> .child`)
- **THEN** both paths SHALL emit a valid scoped selector (e.g., `*[webcompy-cid-{id}]> .child[webcompy-cid-{id}]`)
- **AND** the reactive path SHALL NOT differ from the static path

### Requirement: Reactive scoped styles shall support `:host` for named components

A reactive scoped style registered by a named component SHALL accept `:host` and `:host(<compound-selector>)`. Its generated CSS SHALL replace the host pseudo-class with the named custom-element selector, retain cid scoping, and use the same transformation as static scoped styles.

#### Scenario: Rendering a reactive host rule
- **WHEN** a named component registers `reactive_scoped_style(lambda: {":host": {"color": color.value}})`
- **THEN** the emitted `style[data-webcompy-cid-rx]` element SHALL target the named custom-element wrapper
- **AND** the selector SHALL include the component cid attribute

#### Scenario: Updating a reactive host rule
- **WHEN** a signal read by a reactive `:host(.active)` style changes
- **THEN** the existing reactive style element's text content SHALL update
- **AND** the updated selector SHALL remain equivalent to the static scoped-style transformation

#### Scenario: Reactive host style during SSR
- **WHEN** SSG evaluates a named component's reactive scoped style containing `:host`
- **THEN** the generated `style[data-webcompy-cid-rx]` element SHALL contain the named-element selector
- **AND** the server SHALL not require browser custom-element registration

### Requirement: Reactive scoped style shall reject `:host` without a named component

When a reactive scoped style uses `:host` for an unnamed component, the framework SHALL raise `WebComPyException` rather than emitting an unscoped or invalid selector.

#### Scenario: Registering an unnamed reactive host style
- **WHEN** an unnamed component registers a reactive scoped style containing `:host`
- **THEN** registration or first CSS evaluation SHALL raise `WebComPyException`
- **AND** no reactive style element SHALL be created for that invalid rule

