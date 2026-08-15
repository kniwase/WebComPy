# Component System

## Purpose

Components are the primary abstraction for building UIs. A component encapsulates a piece of the interface — its structure, behavior, and styling — into a reusable unit. This enables developers to decompose a complex page into manageable pieces, compose those pieces together, and reason about each piece independently.

WebComPy uses function-style components defined with `@define_component`. A setup function receives a `ComponentContext` and returns an element tree. Standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) register hooks without requiring explicit context access. Composables like `use_async_result` and `use_async` encapsulate stateful logic for reuse across components.

Components also provide scoped CSS to prevent styles from leaking between unrelated parts of the UI, and document head management so that each page component can declare its own title and meta tags.

**What WebComPy does not yet provide:** Component IDs are generated via MD5 hash, which is not collision-proof for very large applications.
## Requirements
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

### Requirement: Components shall receive data via props
A parent component SHALL be able to pass data to a child component through props, which the child accesses as a typed object via `context.props`.

#### Scenario: Passing user data to a profile component
- **WHEN** a parent renders `UserProfile(user_data)`
- **THEN** the `UserProfile` component SHALL receive `user_data` as `context.props`
- **AND** the component SHALL be able to use reactive values from props in its template

### Requirement: Components shall support slots for content projection
A component SHALL define named slots that parent components can fill with content, enabling composition patterns where the parent controls what appears in certain regions of the child's template.

#### Scenario: Using a named slot with fallback
- **WHEN** a component calls `context.slots("header", fallback=lambda: html.H1({}, "Default"))`
- **AND** a parent provides content for the "header" slot
- **THEN** the parent's content SHALL be rendered
- **WHEN** no content is provided for the "header" slot
- **THEN** the fallback SHALL be rendered

### Requirement: Scoped CSS shall prevent style leakage between components
A component's scoped CSS SHALL be automatically prefixed with an attribute selector unique to that component, ensuring that styles only apply to elements within that component.

#### Scenario: Defining scoped styles
- **WHEN** a developer sets `generator.scoped_style = {".btn": {"color": "red"}}`
- **THEN** the generated CSS SHALL be `.btn[webcompy-cid-{id}] { color: red; }`
- **AND** the component's root element SHALL have the `webcompy-cid-{id}` attribute
- **AND** the `.btn` style SHALL NOT affect `.btn` elements in other components

### Requirement: Scoped CSS shall support nested dictionary structures for media queries, at-rules, and pseudo-selectors
The framework SHALL allow developers to use CSS at-rules (`@media`, `@supports`, `@container`, etc.) as either top-level keys or nested keys in `scoped_style` dictionaries. At-rule keys themselves SHALL NOT receive the `[webcompy-cid-{id}]` attribute selector. Selectors inside at-rule blocks SHALL receive proper scoping. The framework SHALL recursively process these nested structures and generate valid CSS rules. At-rules (`@media`, `@supports`, `@container`) SHALL wrap selectors inside their blocks. Pseudo-classes (`:hover`, `:focus`) and pseudo-elements (`::before`, `::after`) SHALL attach directly to selectors without space. Combinator selectors (`>`, `+`, `~`, descendant space) SHALL maintain space separation.

#### Scenario: Defining a media query within scoped style
- **WHEN** a developer sets `scoped_style` with a nested `@media` rule:
  ```python
  {".button": {"color": "blue", "@media (max-width: 768px)": {"color": "red"}}}
  ```
- **THEN** the framework SHALL generate valid CSS with at-rule wrapping:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  @media (max-width: 768px) { .button[webcompy-cid-xxx] { color: red; } }
  ```
- **AND** both rules SHALL be scoped to the component via the `[webcompy-cid-xxx]` attribute

#### Scenario: Defining a pseudo-class selector within scoped style
- **WHEN** a developer sets `scoped_style` with a nested pseudo-class:
  ```python
  {".button": {"color": "blue", ":hover": {"background": "yellow"}}}
  ```
- **THEN** the framework SHALL generate pseudo-class attached without space:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  .button[webcompy-cid-xxx]:hover { background: yellow; }
  ```

#### Scenario: Defining deeply nested structures
- **WHEN** a developer defines multiple levels of nesting:
  ```python
  {".button": {
      "color": "blue",
      "@media (max-width: 768px)": {
          "color": "red",
          ":hover": {"background": "yellow"}
      }
  }}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .button[webcompy-cid-xxx] { color: blue; }
  @media (max-width: 768px) { 
    .button[webcompy-cid-xxx] { color: red; }
    .button[webcompy-cid-xxx]:hover { background: yellow; }
  }
  ```

#### Scenario: Using at-rules as top-level keys in scoped style
- **WHEN** a developer defines an at-rule as a top-level key in `scoped_style`:
  ```python
  Component.scoped_style = {
      "@media (max-width: 768px)": {
          ".button": {"color": "red"}
      }
  }
  ```
- **THEN** the at-rule key itself SHALL NOT receive the `[webcompy-cid-{id}]` attribute
- **AND** selectors inside the at-rule block SHALL receive the `[webcompy-cid-{id}]` attribute
- **AND** the generated CSS SHALL be valid:
  ```css
  @media (max-width: 768px) { .button[webcompy-cid-xxx] { color: red; } }
  ```
- **AND** the at-rule syntax SHALL remain intact (no attribute selectors in `@media` declaration)

#### Scenario: At-rule detection with leading whitespace
- **WHEN** a developer uses leading whitespace in an at-rule key:
  ```python
  Component.scoped_style = {
      " @media (max-width: 768px)": {".button": {"color": "red"}}
  }
  ```
- **THEN** the framework SHALL classify the key as an at-rule (despite leading space)
- **AND** the at-rule SHALL NOT receive cid attribute scoping

### Requirement: Nested scoped style shall maintain type safety with recursive type definition
The framework SHALL provide type annotations that accurately describe the nested structure of scoped styles, enabling IDE autocomplete and static type checking.

#### Scenario: Type checking nested style definitions
- **WHEN** a developer defines nested styles with incorrect types (e.g., a number instead of string for a CSS value)
- **THEN** a type checker (Pyright/MyPy) SHALL report a type error
- **AND** valid nested structures SHALL pass type checking without errors

#### Scenario: Backward compatibility with flat style definitions
- **WHEN** a developer uses the existing flat style structure:
  ```python
  {".button": {"color": "blue"}}
  ```
- **THEN** the code SHALL pass type checking without errors
- **AND** the generated CSS SHALL be identical to the current behavior

### Requirement: Nested scoped style shall support all CSS at-rules and pseudo-selectors
The framework SHALL accept any string key in nested style dictionaries, allowing developers to use `@media`, `@supports`, `@container`, pseudo-classes (`:hover`, `:focus`, `:active`), and pseudo-elements (`::before`, `::after`).

#### Scenario: Using @supports rule
- **WHEN** a developer defines:
  ```python
  {".card": {"padding": "20px", "@supports (display: grid)": {"display": "grid"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .card[webcompy-cid-xxx] { padding: 20px; }
  @supports (display: grid) { .card[webcompy-cid-xxx] { display: grid; } }
  ```

#### Scenario: Using pseudo-elements
- **WHEN** a developer defines:
  ```python
  {".tooltip": {"position": "relative", "::after": {"content": "attr(data-tip)"}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .tooltip[webcompy-cid-xxx] { position: relative; }
  .tooltip[webcompy-cid-xxx]::after { content: attr(data-tip); }
  ```

#### Scenario: Using combinator selectors in nested structure
- **WHEN** a developer defines:
  ```python
  {".menu": {"color": "black", "> li": {"color": "blue"}}}
  ```
- **THEN** the framework SHALL generate:
  ```css
  .menu[webcompy-cid-xxx] { color: black; }
  .menu[webcompy-cid-xxx] > li { color: blue; }
  ```

### Requirement: Scoped CSS SHALL be injected at browser runtime when SSR is absent

The framework SHALL inject scoped component styles as per-component `<style data-webcompy-cid="{hash}">` elements in `document.head`, along with a single `<style id="webcompy-scoped-styles">` element for the framework-level `*[hidden]{display:none}` rule. Style injection SHALL be idempotent: before creating any `<style>` element, the framework SHALL check for an existing element with the same identifier (`data-webcompy-cid` or `id`). When SSR has already produced these elements, the runtime SHALL detect them and skip injection. New components registered after initial render (e.g., lazy-loaded routes) SHALL have their styles injected on the next render cycle. Each injected `<style data-webcompy-cid>` element SHALL contain its rules wrapped in `@layer webcompy-scope { ... }`.

#### Scenario: Runtime injection when SSR is absent

- **WHEN** a `WebComPyApp` is created and `app.run()` is called at browser runtime with no pre-existing `<style id="webcompy-scoped-styles">` or `<style data-webcompy-cid="...">` elements in the DOM
- **THEN** `AppDocumentRoot._render()` SHALL create a `<style id="webcompy-scoped-styles">` element with `*[hidden]{display:none}`
- **AND** SHALL create a `<style data-webcompy-cid="...">` element for each registered component that has `scoped_style`, with rules wrapped in `@layer webcompy-scope`
- **AND** SHALL append all style elements to `document.head`
- **AND** component `scoped_style` rules SHALL apply correctly

#### Scenario: No duplicate when SSR has already injected styles

- **WHEN** a `WebComPyApp` hydrates a page that was server-side rendered
- **AND** the SSR output already contains both `<style id="webcompy-scoped-styles">` and `<style data-webcompy-cid="...">` elements in the document head
- **THEN** `_reconcile_scoped_styles()` SHALL check for existing elements via `querySelector`
- **AND** finding existing elements, SHALL skip injection for each
- **AND** no duplicate `<style>` elements SHALL be created

#### Scenario: Runtime style injection in isolated contexts

- **WHEN** a `WebComPyApp` runs inside an iframe with no SSR
- **THEN** scoped component styles SHALL be injected at runtime as per-component `<style>` elements, each wrapped in `@layer webcompy-scope`
- **AND** components inside the iframe SHALL render with their defined `scoped_style` CSS

### Requirement: AppDocumentRoot SHALL expose scoped_styles as a cid-to-CSS dict
`AppDocumentRoot.style` (concatenated CSS string) SHALL be removed. `AppDocumentRoot.scoped_styles` SHALL return a `dict[str, str]` mapping component cid values to their full CSS strings, sorted by cid for deterministic ordering. Components without `scoped_style` SHALL be excluded.

#### Scenario: Accessing scoped_styles from AppDocumentRoot
- **WHEN** `AppDocumentRoot.scoped_styles` is accessed
- **THEN** it SHALL iterate `ComponentStore.components` and return `{cid: css_string}` for each component with non-empty `scoped_style`
- **AND** the dict keys SHALL be sorted alphabetically

### Requirement: Components shall manage their lifecycle
Components SHALL provide hooks for before rendering, after rendering, and before destruction. These hooks allow components to perform side effects like fetching data, setting up subscriptions, or cleaning up resources. When `on_after_rendering` is triggered as part of a reactive update cascade (e.g., during `SwitchElement._refresh()`), it SHALL be deferred until after the reactive propagation completes, ensuring the DOM is fully settled before side effects run.

#### Scenario: Using standalone lifecycle decorators in a function-style component
- **WHEN** a developer uses `@on_after_rendering` or `@on_before_destroy` inside a `@define_component` setup function
- **THEN** the hooks SHALL fire at the same lifecycle points as `context.on_after_rendering()` and `context.on_before_destroy()`
- **AND** the hooks SHALL be cleaned up when the component is destroyed

#### Scenario: Cleaning up before destruction
- **WHEN** a component is removed from the DOM
- **THEN** its `on_before_destroy` callback SHALL fire
- **AND** the component's title and meta entries SHALL be removed from the document head

#### Scenario: After-rendering hook during route navigation
- **WHEN** a component's `on_after_rendering` hook fires as a result of a route change (i.e., `SwitchElement._refresh()` replacing one component with another)
- **THEN** the hook SHALL execute after the entire DOM update and reactive propagation has completed
- **AND** any async operations started in the hook SHALL run in a clean event loop context

### Requirement: Component after-rendering lifecycle hook shall be deferred when triggered by reactive navigation
When a component's `on_after_rendering` hook is triggered as a side effect of a reactive change (such as a route change via `SwitchElement._refresh()`), the hook SHALL NOT execute synchronously within the reactive callback chain. Instead, it SHALL be deferred to run after the reactive propagation has completed and the DOM is fully updated.

#### Scenario: Navigating to a page that starts async operations in on_after_rendering
- **WHEN** a user clicks a `RouterLink` to navigate to a new page
- **AND** the new page component has an `on_after_rendering` hook that starts an async operation (e.g., `HttpClient.get()`)
- **THEN** the async operation SHALL execute successfully without errors
- **AND** the component SHALL be fully mounted in the DOM before `on_after_rendering` fires

#### Scenario: Direct URL access to a page with on_after_rendering
- **WHEN** a page is loaded directly via URL (initial hydration)
- **AND** the page component has an `on_after_rendering` hook
- **THEN** `on_after_rendering` SHALL fire after the component is fully rendered
- **AND** the behavior SHALL be consistent with the deferred behavior during navigation

### Requirement: Component setup shall integrate with DI scope
`Component.__setup` SHALL inherit the active DI scope from the ContextVar. When `provide()` is called during setup, a child DI scope SHALL be lazily created and set as the active scope for the remainder of the setup function.

#### Scenario: Component provides a value during setup
- **WHEN** a component setup function calls `provide(ThemeKey, dark_theme)`
- **THEN** a child DI scope SHALL be created for this component
- **AND** `ThemeKey` SHALL be available to descendant components via `inject(ThemeKey)`

#### Scenario: Component injects a value during setup
- **WHEN** a component setup function calls `inject(RouterKey)` and an ancestor scope provides `RouterKey`
- **THEN** the component SHALL receive the provided value

#### Scenario: Component setup restores DI scope on exit
- **WHEN** a component setup function completes or raises
- **THEN** the `_active_di_scope` ContextVar SHALL be reset to its value before the setup started

### Requirement: Component destruction shall dispose DI scope
When a component is destroyed and it has a child DI scope, that scope SHALL be disposed.

#### Scenario: Destroying a component with a DI scope
- **WHEN** a component that called `provide()` during setup is destroyed
- **THEN** its child DI scope SHALL be disposed
- **AND** descendant components' scopes SHALL also be disposed (recursive)

#### Scenario: Destroying a component without a DI scope
- **WHEN** a component that did not call `provide()` during setup is destroyed
- **THEN** no DI scope disposal SHALL occur (no child scope was created)

### Requirement: Context shall provide a provide method
`Context.provide(key, value)` SHALL be available as a convenience method that delegates to the module-level `provide()` function via `_active_di_scope`.

#### Scenario: Using context.provide in a component
- **WHEN** a developer calls `context.provide(ThemeKey, theme)` inside a component setup
- **THEN** the behavior SHALL be identical to calling `provide(ThemeKey, theme)` directly

### Requirement: Components shall manage document head properties
Each component instance SHALL be able to set the document title and meta tags through the app-scoped `HeadPropsStore` accessed via DI. When multiple components set the title, the most recently rendered one SHALL take precedence. When a component is destroyed, its head entries SHALL be removed from the app-scoped store.

#### Scenario: Setting the page title from a component
- **WHEN** a component calls `context.set_title("My Page")`
- **THEN** the document title SHALL update to "My Page" in the relevant app's scope
- **AND** when the component is destroyed, its title entry SHALL be removed from the app-scoped store

#### Scenario: Multiple apps with independent head management
- **WHEN** two `WebComPyApp` instances exist simultaneously
- **THEN** each app SHALL have its own `HeadPropsStore` provided via DI
- **AND** title and meta settings in one app SHALL NOT affect the other

### Requirement: Component._detach_from_node() shall dispose DI scope and EffectScope when node is adopted
When a `Component` is the root of an old branch subtree being patched, `Component._detach_from_node()` SHALL call `super()._detach_from_node()` followed by `on_before_destroy` to dispose the `EffectScope` and DI child scope. This ensures proper lifecycle cleanup even when the DOM node is adopted by a new `Component` rather than removed from the DOM.

#### Scenario: Detaching a component whose node is adopted during patching
- **WHEN** a `Component`'s DOM node is adopted by a new `Component` during `_patch_children()`
- **THEN** `_detach_from_node()` SHALL call `super()._detach_from_node()` to release Python-side resources
- **AND** `on_before_destroy` SHALL be invoked to dispose the `EffectScope` and DI child scope
- **AND** the DOM node SHALL NOT be removed from the document

### Requirement: Async component setup failure shall run hooks registered inside the async body

When an async component setup body registers lifecycle hooks (such as `on_before_destroy` callbacks that clean up external resources like event listeners) and the async body subsequently raises or is cancelled, the component's destruction path SHALL invoke the destroy hooks registered inside that async body — not merely the hooks captured before the async body ran. The failed component SHALL be removed from its parent without re-running the failed setup, and the destruction SHALL NOT re-enter the error-handling pipeline in a way that masks the original failure.

#### Scenario: Listener cleanup registered in a failed async setup

- **WHEN** an async component setup body calls `use_window_event` (registering an `on_before_destroy` cleanup) and then raises
- **THEN** the component's `on_before_destroy` path SHALL execute the cleanup registered inside the async body
- **AND** the underlying listener cleanup SHALL run exactly once
- **AND** the component SHALL be removed from its parent without re-running the failed setup

#### Scenario: Existing cleanup ordering is preserved on success

- **WHEN** an async component setup body registers both an effect (via the effect scope) and a user `on_before_destroy` hook
- **THEN** on normal destruction the framework cleanup SHALL run before the user hook, and the async-body-registered user hook SHALL be invoked
- **AND** the change SHALL NOT alter the ordering for components whose async setup succeeds

### Requirement: Component registration shall enforce unique names with per-app stores
The framework SHALL maintain a per-app registry of component generators by name. If two components are registered with the same name within the same app, an error SHALL be raised. Each `WebComPyApp` SHALL own its own `ComponentStore` instance, provided into the app's DI scope. `ComponentGenerator` SHALL register into the active app's store via DI when a scope is available. When no DI scope exists (import time), registration SHALL be deferred until an app scope becomes active. No module-level `_default_component_store` global SHALL exist. Note: `ComponentGenerator.__registered` is a one-time flag; import-time components will only register into the first app's store. Subsequent apps will not inherit components defined before either app existed, unless a different registration mechanism is used or components are re-imported.

#### Scenario: Registering duplicate component names within the same app
- **WHEN** a developer defines two components with the same name in the same application
- **THEN** `WebComPyComponentException` SHALL be raised with a message about the duplicate

#### Scenario: Per-app component store isolation
- **WHEN** two `WebComPyApp` instances exist with different component sets
- **THEN** each app's `ComponentStore` SHALL only contain the components registered for that app
- **AND** scoped CSS collection SHALL be isolated per app

#### Scenario: Import-time registration without DI scope
- **WHEN** a `@define_component` decorated function is defined at module level (before any app exists)
- **THEN** the `ComponentGenerator` SHALL store its registration info locally
- **AND** when an app is created and its DI scope becomes active, the component SHALL be registered into that app's store
- **AND** once registered, the `ComponentGenerator.__registered` flag prevents re-registration into a second app's store; only the first app created receives import-time components

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
- **WHEN** a `@define_component` decorated function is defined at module level (before any app exists)
- **THEN** the `ComponentGenerator` SHALL store its registration info locally
- **AND** when an app is created and its DI scope becomes active, the component SHALL be registered into that app's store
- **AND** once registered, the `ComponentGenerator.__registered` flag prevents re-registration into a second app's store; only the first app created receives import-time components

### Requirement: Scoped CSS SHALL be wrapped in `@layer webcompy-scope` automatically

When the framework emits a `<style data-webcompy-cid="{hash}">` element for a component's `scoped_style`, the framework SHALL wrap the rule body in `@layer webcompy-scope { ... }`. This applies to both server-side rendered output and client-side runtime injection. The wrapping is automatic and does not require opt-in by the developer.

#### Scenario: SSR output wraps scoped_style in @layer

- **WHEN** a component's `scoped_style = {".btn": {"color": "red"}}` is rendered during SSR
- **THEN** the server-rendered `<style data-webcompy-cid="...">` element SHALL contain `@layer webcompy-scope { .btn[webcompy-cid-xxx] { color: red; } }`
- **AND** the rule SHALL have lower priority than unlayered rules in the same stylesheet

#### Scenario: Runtime injection wraps scoped_style in @layer

- **WHEN** a component's `scoped_style` is injected at browser runtime (no SSR)
- **THEN** the runtime-injected `<style data-webcompy-cid="...">` element SHALL contain the same `@layer webcompy-scope { ... }` wrapper
- **AND** the visual result SHALL match the SSR case

#### Scenario: A components.css rule overrides a scoped_style rule

- **WHEN** the framework's `components.css` defines a rule for a selector that also appears in a component's `scoped_style`
- **AND** `components.css` is declared in the `components` layer, declared before `webcompy-scope`
- **THEN** the `components.css` rule SHALL win over the `scoped_style` rule

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

### Requirement: ComponentGenerator shall track reactive styles

`ComponentGenerator` SHALL maintain a `_reactive_styles: list[ReactiveScopedStyle]` attribute, initialized to an empty list in `__init__`. The list SHALL be appended to by `ComponentContext.use_reactive_scoped_style`.

The attribute is private to the framework. User code SHALL NOT rely on the internal list layout.

#### Scenario: Generator starts with empty reactive styles list
- **WHEN** a `ComponentGenerator` is created from a `@define_component`-decorated function
- **THEN** its `_reactive_styles` list SHALL be empty
- **AND** registering a style via `use_reactive_scoped_style` SHALL append to this list

### Requirement: Components shall restore Signal values via factory-skip during setup

During browser hydration, signal values SHALL be restored during component setup by `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables. Each composable SHALL check `HYDRATION_SIGNAL_DATA_KEY` (via DI injection) before invoking its factory. If a transferred value exists for the composable's key, the factory SHALL be skipped and the signal SHALL be created directly with the restored value. No separate restoration step runs in `Component._render()` — the `_restore_signals()` method has been removed.

Signals created outside composables (e.g., `Signal()` in event handlers or `on_before_rendering` hooks) SHALL NOT participate in transfer and SHALL NOT be restored from the hydration payload. Components that need SSR-transferable state SHALL create their signals via `use_state()` / `use_reactive_list()` / `use_reactive_dict()` inside the setup function.

#### Scenario: Factory-skip restores value before first render
- **WHEN** a component is hydrated in the browser
- **AND** the hydration payload contains a value for this composable's key
- **THEN** the composable SHALL restore the value and skip the factory
- **AND** the restored value SHALL be available before template evaluation and `on_before_rendering` hooks

#### Scenario: Component without transfer data runs factory
- **WHEN** a component is hydrated
- **AND** the hydration payload does not contain a value for this composable's key
- **THEN** the composable SHALL run its factory to produce the initial value
- **AND** the signal SHALL still be registered for future SSR transfer

#### Scenario: Signals created outside composables are not restored
- **WHEN** a component creates a `Signal` directly (not via `use_state()` / `use_reactive_list()` / `use_reactive_dict()`)
- **THEN** the signal SHALL NOT be registered in `_transferable_signals`
- **AND** the signal SHALL NOT be collected for transfer
- **AND** the signal SHALL NOT be restored from the hydration payload

### Requirement: Selector scoping shall be depth-aware

When splitting selectors on combinators for `[webcompy-cid-{id}]` insertion, the framework SHALL only split at combinators appearing at depth zero — never inside parentheses `()`, attribute-selector brackets `[]`, or quoted strings. Whitespace runs of any kind (spaces, newlines, tabs) at depth zero SHALL be treated as descendant combinators.

#### Scenario: Functional pseudo-class preserved
- **WHEN** a scoped style contains the selector `.x:nth-child(2n+1)`
- **THEN** the generated CSS SHALL be `.x:nth-child(2n+1)[webcompy-cid-{id}]` (or equivalent valid selector with the cid attached to the compound)
- **AND** the `+` inside `:nth-child(...)` SHALL NOT be treated as a combinator

#### Scenario: Attribute selector value preserved
- **WHEN** a scoped style contains the selector `[data-x="a>b"]` or `[title="Hello, World"]`
- **THEN** the attribute value SHALL be preserved verbatim
- **AND** the cid attribute SHALL be attached without splitting inside the brackets

#### Scenario: Tilde combinator without spaces
- **WHEN** a scoped style contains the selector `a~b`
- **THEN** both `a` and `b` SHALL receive the cid attribute: `a[webcompy-cid-{id}]~b[webcompy-cid-{id}]`

#### Scenario: Newline descendant combinator
- **WHEN** a selector list spans multiple lines (e.g., `.a\n.b` within a multi-line CSS text key)
- **THEN** the newline SHALL be treated as a descendant combinator and both compounds SHALL be scoped

### Requirement: Scoped attribute selector shall be inserted before trailing pseudo-elements

When attaching `[webcompy-cid-{id}]` to a compound selector that ends with a pseudo-element chain (`::before`, `::after`, `::placeholder`, functional pseudo-elements such as `::slotted(...)`), the cid attribute selector SHALL be inserted **before** the pseudo-element chain so the resulting selector is valid CSS.

#### Scenario: Pseudo-element selector
- **WHEN** a scoped style contains the flat selector `.x::before`
- **THEN** the generated CSS selector SHALL be `.x[webcompy-cid-{id}]::before` (not `.x::before[webcompy-cid-{id}]`)

#### Scenario: Pseudo-class then pseudo-element
- **WHEN** a scoped style contains the selector `.x:hover::before`
- **THEN** the generated CSS selector SHALL be `.x:hover[webcompy-cid-{id}]::before` or `.x[webcompy-cid-{id}]:hover::before` — in both forms the cid SHALL precede `::before`

### Requirement: Declaration-body at-rules shall be rendered unscoped

At-rules whose body consists of declarations rather than nested rules — `@font-face`, `@page`, `@property`, `@counter-style` — SHALL be rendered without `[webcompy-cid-{id}]` scoping and SHALL NOT raise an error. Keyframes at-rule detection SHALL be case-insensitive and SHALL recognize vendor prefixes (`@-webkit-keyframes`, `@-moz-keyframes`, `@-o-keyframes`).

#### Scenario: @font-face rendered unscoped
- **WHEN** a scoped style contains `{"@font-face": {"font-family": "'X'", "src": "url(x.woff2)"}}`
- **THEN** the generated CSS SHALL contain `@font-face { font-family: 'X'; src: url(x.woff2); }` with no cid attribute
- **AND** no exception SHALL be raised

#### Scenario: Vendor-prefixed keyframes
- **WHEN** a scoped style contains `{"@-webkit-keyframes spin": {"0%": {"opacity": "0"}}}`
- **THEN** the inner `0%` key SHALL NOT receive a cid attribute
- **AND** the generated CSS SHALL be valid

### Requirement: CSS nesting parent selector shall be rejected

Selectors containing the CSS-nesting parent selector `&` SHALL raise `WebComPyException` with a message stating that CSS nesting with `&` is not supported in scoped styles and suggesting the implicit-nesting dict form (e.g., `{".btn": {":hover": {...}}}`) instead.

#### Scenario: Ampersand selector rejected
- **WHEN** a scoped style or `css_text` source contains `.btn { &:hover { color: red; } }`
- **THEN** `WebComPyException` SHALL be raised naming the `&` selector and suggesting the nested dict form

### Requirement: Components shall support an on_error_captured setup hook

Component setup SHALL support registering error-capture hooks via `context.on_error_captured(fn)` (following the same active-component-context pattern as `on_before_destroy`). `fn` receives the raised `Exception` and MAY return `False` to mark the error handled and stop propagation. Hooks SHALL be invoked nearest-first when a descendant raises (see the `error-handling` capability for the full propagation order). Hooks SHALL be released when the component is destroyed. Calling the registration function outside component setup SHALL raise `LookupError`.

#### Scenario: Registration during setup
- **WHEN** a component setup calls `context.on_error_captured(lambda err: False)` and a descendant later raises
- **THEN** the hook SHALL be invoked with the exception before any boundary engages
- **AND** returning `False` SHALL prevent boundary engagement

#### Scenario: Registration outside setup raises
- **WHEN** `on_error_captured` registration is attempted outside a component setup function
- **THEN** a `LookupError` SHALL be raised

#### Scenario: Hooks released on destroy
- **WHEN** a component with captured-error hooks is destroyed
- **THEN** its hooks SHALL no longer be invoked for subsequent errors

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

### Requirement: ComponentContext shall provide document-connection hooks for named components

`ComponentContext` SHALL provide `on_mounted` and `on_unmounted` registration methods for named custom-element components. The methods SHALL accept the same synchronous or asynchronous callback forms supported by the existing lifecycle hooks. The hooks SHALL be released with the component binding.

#### Scenario: Registering document-connection hooks
- **WHEN** a named component calls `context.on_mounted(on_mount)` and `context.on_unmounted(on_unmount)` during setup
- **THEN** both callbacks SHALL be stored for that component instance
- **AND** they SHALL be invoked at the custom-element document-connection points

#### Scenario: Keeping existing lifecycle hooks
- **WHEN** a component registers `on_before_rendering`, `on_after_rendering`, or `on_before_destroy`
- **THEN** each existing hook SHALL retain its current trigger and ordering
- **AND** adding document-connection hooks SHALL not replace or reorder those existing hooks

### Requirement: Document-connection hooks shall be available as standalone decorators

The framework SHALL provide `@on_mounted` and `@on_unmounted` standalone decorators usable inside a named component setup function, equivalent to `context.on_mounted(func)` and `context.on_unmounted(func)`. Using them outside a component setup SHALL raise the same error class as the existing lifecycle decorators.

#### Scenario: Registering hooks via standalone decorators
- **WHEN** a named component applies `@on_mounted` and `@on_unmounted` inside its setup function
- **THEN** both callbacks SHALL be registered for that component instance
- **AND** their behavior SHALL be equivalent to the `ComponentContext` methods

#### Scenario: Using a standalone decorator outside setup
- **WHEN** `@on_mounted` or `@on_unmounted` is applied outside a component setup function
- **THEN** an error SHALL be raised indicating the decorator must be used inside component setup

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
