# Components Delta

## ADDED Requirements

### Requirement: ComponentContext shall provide use_reactive_scoped_style

The framework SHALL provide a `use_reactive_scoped_style(style: ReactiveScopedStyle)` method on `ComponentContext`. The method SHALL append the given style to the active `ComponentGenerator._reactive_styles` list. The method SHALL be callable from inside the component setup function (the function decorated with `@define_component`).

The method SHALL raise a `WebComPyException` if called from outside an active component setup context. The exception message SHALL identify the misuse and point to the `reactive_scoped_style` API.

#### Scenario: Calling use_reactive_scoped_style inside a component setup
- **WHEN** a developer writes:
  ```python
  @define_component
  def MyComponent(context):
      context.use_reactive_scoped_style(
          reactive_scoped_style(lambda: {".x": {"color": "red"}})
      )
      return html.DIV({}, "...")
  ```
- **THEN** the framework SHALL register the style with the component's generator
- **AND** the style SHALL be emitted into the document head on the next render

#### Scenario: Calling use_reactive_scoped_style outside a component
- **WHEN** a developer calls `use_reactive_scoped_style` from a non-component context (e.g., at module load time)
- **THEN** the framework SHALL raise a `WebComPyException`
- **AND** the exception message SHALL mention `reactive_scoped_style` and the active component context

### Requirement: ComponentGenerator shall track reactive styles

`ComponentGenerator` SHALL maintain a `_reactive_styles: list[ReactiveScopedStyle]` attribute, initialized to an empty list in `__init__`. The list SHALL be appended to by `ComponentContext.use_reactive_scoped_style`.

The attribute is private to the framework. User code SHALL NOT rely on the internal list layout.

#### Scenario: Generator starts with empty reactive styles list
- **WHEN** a `ComponentGenerator` is created from a `@define_component`-decorated function
- **THEN** its `_reactive_styles` list SHALL be empty
- **AND** registering a style via `use_reactive_scoped_style` SHALL append to this list
