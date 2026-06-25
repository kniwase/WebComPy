# Component System

## Purpose

Components are the primary abstraction for building UIs. A component encapsulates a piece of the interface — its structure, behavior, and styling — into a reusable unit. This enables developers to decompose a complex page into manageable pieces, compose those pieces together, and reason about each piece independently.

WebComPy uses function-style components defined with `@define_component`. A setup function receives a `ComponentContext` and returns an element tree. Standalone lifecycle decorators (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`) register hooks without requiring explicit context access. Composables like `useAsyncResult` and `useAsync` encapsulate stateful logic for reuse across components.

Components also provide scoped CSS to prevent styles from leaking between unrelated parts of the UI, and document head management so that each page component can declare its own title and meta tags.

**What WebComPy does not yet provide:** Component IDs are generated via MD5 hash, which is not collision-proof for very large applications.
## Requirements
### Requirement: Components shall be defined as reusable, self-contained units
A component SHALL encapsulate a template (what it renders), optional lifecycle hooks (what it does at key moments), and optional scoped CSS (how it looks). The component SHALL be invocable with props and slots to produce a rendered element.

#### Scenario: Creating a function-style component
- **WHEN** a developer decorates a setup function with `@define_component`
- **THEN** the function SHALL receive a `ComponentContext` with `props`, `slots()`, lifecycle hooks, and head management
- **AND** the function SHALL return the component's template as an element tree

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

### Requirement: Component shall inherit :preserve_children from root element

When a `Component` is created, the `__init_component()` method SHALL copy the `_preserve_children` boolean flag from the root `Element` node (the template root returned by the component setup function), following the same pattern as `_tag_name` and `_ref`. The flag SHALL control whether the component's `_render()` cleanup loop is skipped, just as it does for `Element` instances.

#### Scenario: Component preserves children when root element sets the flag
- **WHEN** a component's setup function returns `html.DIV({":preserve_children": True}, ...)`
- **THEN** the `Component` instance SHALL have `_preserve_children = True`
- **AND** the component's `_render()` SHALL skip the excess-child-node cleanup loop

#### Scenario: Component does not preserve children when root element does not set the flag
- **WHEN** a component's setup function returns `html.DIV({}, ...)` without `:preserve_children`
- **THEN** the `Component` instance SHALL have `_preserve_children = False`
- **AND** the component's `_render()` SHALL execute the cleanup loop normally

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

