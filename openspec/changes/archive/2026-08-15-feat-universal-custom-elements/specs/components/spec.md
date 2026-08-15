# Delta Spec: components

## ADDED Requirements

### Requirement: Component definitions shall declare a custom-element name consistent with the setup function name

`define_component` SHALL require a custom-element name as its first argument; the bare no-argument decorator form SHALL NOT be available. At decoration time the framework SHALL validate that the decorated function's name equals `kebab_to_pascal(custom_element_name)`. A mismatch SHALL raise `WebComPyComponentException` whose message includes the function name, the declared custom-element name, and the expected name derived from the function. The existing custom-element-name validation (lowercase, contains a hyphen, not reserved) SHALL continue to apply, so Python names that cannot yield a valid hyphenated name — single-word names such as `App`, acronym-style names that do not round-trip such as `HTTPRequest` (whose normalized form is `HttpRequest`), and underscore-prefixed names — SHALL be rejected at definition time with guidance.

#### Scenario: Consistent definition is accepted

- **WHEN** a developer decorates `def UserCard(context)` with `@define_component("user-card")`
- **THEN** definition SHALL succeed
- **AND** the generator SHALL retain `user-card` as its custom-element name and `UserCard` as its component name

#### Scenario: Mismatched name is rejected

- **WHEN** a developer decorates `def Card(context)` with `@define_component("user-card")`
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the message SHALL identify the function name `Card`, the declared name `user-card`, and the expected consistent name

#### Scenario: Acronym-style name is rejected in favor of the normalized form

- **WHEN** a developer decorates `def HTTPRequest(context)` with `@define_component("http-request")`
- **THEN** definition SHALL raise `WebComPyComponentException` because `kebab_to_pascal("http-request")` is `HttpRequest`, not `HTTPRequest`
- **AND** the message SHALL guide the developer to rename the function to `HttpRequest`

#### Scenario: Single-word name is rejected

- **WHEN** a developer decorates `def App(context)` with `@define_component("app")`
- **THEN** definition SHALL raise `WebComPyComponentException` because `app` is not a valid custom-element name (no hyphen)
- **AND** the message SHALL guide the developer toward a multi-word component name

### Requirement: define_component shall accept a display keyword argument for the wrapper element

`define_component` SHALL accept a keyword-only `display` argument, defaulting to `None`, typed as the exported `ComponentDisplay` type alias: a `Literal` of `"contents"`, `"block"`, `"inline"`, `"inline-block"`, `"flex"`, `"inline-flex"`, `"grid"`, `"inline-grid"`, `"flow-root"`. At definition time the framework SHALL validate a provided value against the same `Literal` via `typing.get_args`, using a `TypeGuard` helper so the narrowed type flows into `ComponentGenerator`; an invalid value SHALL raise `WebComPyComponentException` listing the valid values derived from the alias. When `display` is set, the framework SHALL emit one cid-scoped rule `{custom-element-name}[webcompy-cid-{cid}] { display: <value>; }` as the first rule of the component's scoped-style output in both SSR and runtime injection paths. The cascade precedence SHALL be: the framework default `[webcompy-component] { display: contents; }` rule (earliest layer) SHALL lose to the `display` kwarg rule, which SHALL lose to the author's own `:host` scoped styles (same layer and specificity, emitted later).

#### Scenario: Applying a display value

- **WHEN** a developer writes `@define_component("user-card", display="block")`
- **THEN** the component's cid style output SHALL contain `user-card[webcompy-cid-{cid}] { display: block; }` before any author scoped rules
- **AND** this SHALL hold identically in SSR `<style data-webcompy-cid>` output and in runtime-injected styles

#### Scenario: Rejecting an invalid display value

- **WHEN** a developer writes `@define_component("user-card", display="bolck")`
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the message SHALL list the valid values exactly as declared in the `ComponentDisplay` alias

#### Scenario: Author :host style overrides the kwarg

- **WHEN** a component declares `display="block"` and also sets `scoped_style = {":host": {"display": "flex"}}`
- **THEN** the author's `:host` rule SHALL be emitted after the kwarg rule in the same layer
- **AND** the rendered wrapper SHALL compute to `display: flex`

### Requirement: Component setup functions may return multiple renderable roots

Every component SHALL accept a single renderable child, a list or tuple of renderable children, text, signal, and `None` setup results, normalized using the existing child-rendering rules, and SHALL render them in order inside the component's custom-element wrapper. A `FragmentElement` result (for example from a multi-root `render_markdown` call) SHALL be accepted as a single child. The component SHALL continue to report exactly one parent-facing node.

#### Scenario: Returning multiple roots

- **WHEN** a component returns `[html.HEADER({}, "Title"), html.MAIN({}, "Body"), html.FOOTER({}, "Footer")]`
- **THEN** all three elements SHALL render as ordered light-DOM children of the component's wrapper
- **AND** the parent container SHALL treat the component as one child node

#### Scenario: Returning a fragment result

- **WHEN** a component returns the `FragmentElement` produced by `render_markdown("# Title\n\nText.", ctx)`
- **THEN** the fragment's children SHALL render inside the component's wrapper
- **AND** no component-root type error SHALL be raised

## MODIFIED Requirements

### Requirement: Components shall be defined as reusable, self-contained units

A component SHALL encapsulate a template (what it renders), optional lifecycle hooks (what it does at key moments), and optional scoped CSS (how it looks). The component SHALL be invocable with props and slots to produce a rendered element. Every component is defined with a custom-element name (see the naming-consistency requirement) and renders one custom-element wrapper node.

#### Scenario: Creating a function-style component

- **WHEN** a developer decorates a setup function with `@define_component("my-widget")`
- **THEN** the function SHALL receive a `ComponentContext` with `props`, `slots()`, lifecycle hooks, and head management
- **AND** the function SHALL return the component's template as an element tree
- **AND** uses of the component SHALL render a `<my-widget>` custom-element wrapper

#### Scenario: Registering lifecycle hooks via standalone decorators

- **WHEN** a developer uses `@on_after_rendering` as a decorator inside a function-style component setup
- **THEN** the decorated function SHALL be registered as an after-rendering lifecycle hook
- **AND** the behavior SHALL be equivalent to `context.on_after_rendering(func)`

### Requirement: Component registration shall enforce unique names with per-app stores

The framework SHALL maintain a per-app registry of component generators by name. If two components are registered with the same name within the same app, an error SHALL be raised. Two distinct generators within the same app SHALL NOT share a custom-element name, even when their Python names differ (for example `MyHTTPRequest` and `MyHttpRequest` both mapping to `my-http-request`); such a collision SHALL raise an error at registration. Each `WebComPyApp` SHALL own its own `ComponentStore` instance, provided into the app's DI scope. `ComponentGenerator` SHALL register into the active app's store via DI when a scope is available. When no DI scope exists (import time), registration SHALL be deferred until an app scope becomes active. No module-level `_default_component_store` global SHALL exist. Note: `ComponentGenerator.__registered` is a one-time flag; import-time components will only register into the first app's store. Subsequent apps will not inherit components defined before either app existed, unless a different registration mechanism is used or components are re-imported.

#### Scenario: Registering duplicate component names within the same app

- **WHEN** a developer defines two components with the same name in the same application
- **THEN** `WebComPyComponentException` SHALL be raised with a message about the duplicate

#### Scenario: Registering colliding custom-element names within the same app

- **WHEN** two distinct generators in the same app resolve to the same custom-element name
- **THEN** `WebComPyComponentException` SHALL be raised identifying the colliding custom-element name

#### Scenario: Per-app component store isolation

- **WHEN** two `WebComPyApp` instances exist with different component sets
- **THEN** each app's `ComponentStore` SHALL only contain the components registered for that app
- **AND** scoped CSS collection SHALL be isolated per app

#### Scenario: Import-time registration without DI scope

- **WHEN** a `@define_component("...")` decorated function is defined at module level (before any app exists)
- **THEN** the `ComponentGenerator` SHALL store its registration info locally
- **AND** when an app is created and its DI scope becomes active, the component SHALL be registered into that app's store
- **AND** once registered, the `ComponentGenerator.__registered` flag prevents re-registration into a second app's store; only the first app created receives import-time components

### Requirement: ComponentContext shall provide use_reactive_scoped_style

The framework SHALL provide a `use_reactive_scoped_style(style: ReactiveScopedStyle)` method on `ComponentContext`. The method SHALL append the given style to the active `ComponentGenerator._reactive_styles` list. The method SHALL be callable from inside the component setup function (the function decorated with `@define_component`).

The method SHALL raise a `WebComPyException` if called from outside an active component setup context. The exception message SHALL identify the misuse and point to the `reactive_scoped_style` API.

#### Scenario: Calling use_reactive_scoped_style inside a component setup

- **WHEN** a developer writes:
  ```python
  @define_component("my-component")
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

### Requirement: Component scoped styles shall support the named host selector

Scoped styles for a component SHALL accept `:host` and `:host(<compound-selector>)` as aliases for that component's custom-element wrapper. The generated selector SHALL retain the existing cid attribute scoping and SHALL be shared by static and reactive style paths. Since every component has a custom-element wrapper, `:host` SHALL always be available.

#### Scenario: Styling the custom-element wrapper

- **WHEN** a component declares scoped style `{":host": {"display": "block"}}`
- **THEN** the generated CSS SHALL target the custom-element wrapper
- **AND** the selector SHALL include the component's existing cid attribute

#### Scenario: Styling a host state

- **WHEN** a component declares scoped style `{":host(.compact)": {"padding": "0"}}`
- **THEN** the generated CSS SHALL target the named custom element with the `.compact` class
- **AND** the selector SHALL remain cid-scoped

## REMOVED Requirements

### Requirement: Component definitions may opt into a named custom-element boundary

**Reason**: The named custom-element boundary is now mandatory for every component, and the custom-element name is no longer an independent value — it must match the setup function name via case conversion (see the naming-consistency requirement).

**Migration**: Pass a custom-element name to every `@define_component` call, choosing the kebab-case form of the setup function name (`UserCard` → `@define_component("user-card")`). Rename functions whose names cannot satisfy the rule (single-word, acronym-style, or underscore-prefixed names).

### Requirement: Named component setup functions may return multiple roots

**Reason**: Superseded by the universal multiple-roots requirement — the named/unnamed distinction no longer exists, so a requirement scoped to named components is redundant.

**Migration**: Unnamed components previously restricted to a single root element now render that root as the single light-DOM child of the custom-element wrapper; no code change is required beyond the mandatory naming migration.

### Requirement: Document-connection hooks shall be rejected for unnamed components

**Reason**: There are no unnamed components; `on_mounted` and `on_unmounted` are available on every component.

**Migration**: Remove any guards around document-connection hook registration; the hooks now work universally.

### Requirement: Component shall inherit :preserve_children from root element

**Reason**: The component node is now always a custom-element wrapper that never inherits attributes, event handlers, refs, or `:preserve_children` from the template root; the root element renders as a child of the wrapper and keeps its own flags.

**Migration**: Set `:preserve_children` on the inner root element (unchanged syntax); externally managed content lives inside that element one level below the wrapper, where the element's own flag continues to apply.
