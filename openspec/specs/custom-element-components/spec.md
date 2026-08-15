# Custom Element Components

## Purpose

Named components defined with `@define_component("my-card")` render as Light DOM custom elements, giving each component a real DOM boundary (`<my-card>`) while keeping the existing Python component lifecycle. The browser registers the custom element before hydration so SSR markup upgrades in place, and the framework exposes document-connection hooks (`on_mounted` / `on_unmounted`) plus observed-attribute props for interoperating with external JavaScript.

## Requirements

### Requirement: Named components shall be defined as valid Light DOM custom elements

`define_component` SHALL accept a custom-element name and an optional sequence of observed attribute names; this called form SHALL be the only definition form (the bare form is removed — see the `components` capability naming-consistency requirement). The name SHALL satisfy the browser custom-element naming rules, including containing a hyphen, and SHALL match the setup function name via case conversion. Attribute names SHALL be normalized to lower case and duplicate names SHALL be rejected.

#### Scenario: Defining a named component
- **WHEN** a developer decorates a setup function with `@define_component("my-card")`
- **THEN** the returned `ComponentGenerator` SHALL retain `my-card` as its custom-element name
- **AND** a use of the generator SHALL render a `<my-card>` element in the browser and server environments

#### Scenario: Defining an observed-attribute component
- **WHEN** a developer decorates a setup function with `@define_component("my-card", observed_attributes=("theme-color",))`
- **THEN** the generator SHALL retain `theme-color` as an observed attribute
- **AND** the browser registration SHALL observe that attribute

#### Scenario: Rejecting an invalid custom-element name
- **WHEN** a developer supplies a name without a hyphen or otherwise invalid under the custom-element naming rules
- **THEN** definition SHALL raise `WebComPyComponentException`
- **AND** the component SHALL not be registered

### Requirement: Component wrappers shall be layout-transparent by default

The framework SHALL emit a default rule `[webcompy-component] { display: contents; }` in an early cascade layer (before `webcompy-scope`), in both SSR output and browser runtime injection, so that every component wrapper participates transparently in parent layout unless the author opts into a real box. The rule SHALL be emitted once per document regardless of component count. Authors SHALL be able to override the default per component definition via the `display` keyword argument or per component via `:host` scoped styles, both of which SHALL win over the default through normal cascade layering.

In browser runtime injection, the default-rule style element SHALL be positioned before every component (`@layer webcompy-scope`) style element already present in `<head>`. This guarantees a document-order first occurrence of `components` before `webcompy-scope` even on pages that do not link the framework UI stylesheet, keeping the override precedence intact; on pages that link the stylesheet, the fixed layer-order declaration dominates regardless of element order.

#### Scenario: Wrapper is transparent without author opt-in

- **WHEN** a component with no `display` kwarg and no `:host` display rule renders in the browser or SSR
- **THEN** the document SHALL contain the `[webcompy-component] { display: contents; }` rule
- **AND** the wrapper SHALL generate no layout box, leaving parent layout (flex/grid item identity, inline flow, percentage sizing) to the template children

#### Scenario: Author overrides the default

- **WHEN** a component declares `display="block"` or a `:host` scoped style with a display value
- **THEN** the author-level rule SHALL win over the framework default through cascade layering
- **AND** the wrapper SHALL generate a box with the declared display type

#### Scenario: Runtime default precedes component styles without the framework stylesheet

- **WHEN** a web page that does not link the framework UI stylesheet boots a WebComPy app in the browser and a component's style elements are injected into `<head>` during registration
- **THEN** the `webcompy-component-defaults` style element SHALL be placed before every `style[data-webcompy-cid]` and `style[data-webcompy-cid-rx]` element in `<head>`
- **AND** a component declared with `display="block"` SHALL compute to `display: block` on its wrapper despite the framework default

### Requirement: Named components shall expose exactly one parent-facing DOM node

A named component SHALL render one custom-element wrapper node and SHALL preserve the existing `_node_count == 1` contract seen by parent elements. The setup result SHALL become the wrapper's light-DOM child sequence. A single existing renderable child, a list or tuple of renderable children, text, signal, and `None` values SHALL be normalized using the existing child-rendering rules. The wrapper SHALL not inherit attributes, event handlers, refs, or `:preserve_children` from a selected template root.

#### Scenario: Rendering a named component with one template root
- **WHEN** a named component returns `html.DIV({"class": "card"}, "content")`
- **THEN** the DOM SHALL contain `<my-card>` as the component node
- **AND** the `div.card` SHALL be a child of `<my-card>`
- **AND** the component SHALL report one parent-facing node

#### Scenario: Rendering a named component with multiple roots
- **WHEN** a named component returns `[html.HEADER({}, "Title"), html.MAIN({}, "Body"), html.FOOTER({}, "Footer")]`
- **THEN** the DOM SHALL contain one `<my-card>` element
- **AND** the three returned elements SHALL occur as ordered light-DOM children of `<my-card>`
- **AND** the parent container SHALL continue to treat the component as one child node

#### Scenario: Using a named component in keyed repetition
- **WHEN** a keyed `repeat` renders named components whose setup functions return multiple roots
- **THEN** each item SHALL own one custom-element wrapper
- **AND** inserting, removing, and reordering items SHALL not lose or overlap any wrapper or inner root

#### Scenario: Rendering an empty named component
- **WHEN** a named component returns an empty sequence
- **THEN** the DOM SHALL contain the custom-element wrapper
- **AND** the wrapper SHALL have no framework-created template children

### Requirement: Browser custom-element registration shall precede hydration

In the browser, WebComPy SHALL register all currently known named component generators before beginning child hydration. Registration SHALL upgrade already-parsed matching SSR elements before those nodes are adopted. Components resolved after startup SHALL be registered before their first node is created or adopted. Server and SSG rendering SHALL skip browser registration entirely.

#### Scenario: Hydrating a server-rendered named component
- **WHEN** the browser loads SSR markup containing `<my-card>` and `app.run()` starts hydration
- **THEN** WebComPy SHALL define or reuse `my-card` before `_hydrate_node()` adopts the component node
- **AND** the existing `<my-card>` node SHALL be adopted rather than replaced

#### Scenario: Registering a lazy named component
- **WHEN** a lazy component with a custom-element name resolves after the initial render
- **THEN** WebComPy SHALL register the custom element before creating or adopting its first DOM node
- **AND** subsequent renders SHALL use the registered element

#### Scenario: Rendering on the server
- **WHEN** a named component is rendered during SSR or SSG
- **THEN** no `customElements` or browser API SHALL be accessed
- **AND** the server output SHALL contain the custom-element tag and its serialized light-DOM children

### Requirement: Custom-element registry conflicts shall be explicit

When a named component is registered, WebComPy SHALL consult the document's `customElements` registry. An existing compatible WebComPy definition with matching custom-element and observed-attribute metadata SHALL be reused. A non-WebComPy definition or an incompatible WebComPy definition SHALL cause a clear `WebComPyComponentException`; WebComPy SHALL not silently replace it.

#### Scenario: Reusing a compatible definition
- **WHEN** two WebComPy application instances request the same custom-element name with the same registered metadata
- **THEN** the second registration SHALL reuse the existing browser definition
- **AND** each component node SHALL retain its own Python lifecycle and attribute binding

#### Scenario: Rejecting an incompatible definition
- **WHEN** a custom-element name is already defined with different observed attributes or by another library
- **THEN** registration SHALL raise `WebComPyComponentException`
- **AND** the existing browser definition SHALL remain unchanged

### Requirement: Named components shall expose document-connection lifecycle hooks

Named components SHALL allow setup functions to register `on_mounted` and `on_unmounted` callbacks. `on_mounted` SHALL run when the bound custom-element node is connected to a document, and `on_unmounted` SHALL run when it becomes disconnected from a document. The hooks SHALL be distinct from `on_after_rendering` and `on_before_destroy`. A bind to an already-connected hydrated node SHALL count as a mount for that component instance.

#### Scenario: Mounting a named component into the document
- **WHEN** a named component registers `context.on_mounted(callback)` and its wrapper becomes document-connected
- **THEN** `callback` SHALL run once for that connection
- **AND** the callback SHALL not require the component to use `on_after_rendering`

#### Scenario: Unmounting a named component from the document
- **WHEN** a named component's wrapper is removed from the document
- **THEN** its registered `on_unmounted` callback SHALL run
- **AND** its existing `on_before_destroy` behavior SHALL remain independent

#### Scenario: Hydrating an already-connected wrapper
- **WHEN** hydration adopts a named component wrapper that is already connected to the document
- **THEN** the component's `on_mounted` callback SHALL run once for the newly bound component instance
- **AND** the existing DOM node SHALL remain in place

#### Scenario: Moving a wrapper within the same document
- **WHEN** reconciliation temporarily disconnects and reconnects a named wrapper before lifecycle reactions are coalesced
- **THEN** neither `on_unmounted` nor a second `on_mounted` callback SHALL run for that move

#### Scenario: Registering document-connection hooks via standalone decorators
- **WHEN** a named component applies `@on_mounted` and `@on_unmounted` inside its setup function
- **THEN** both callbacks SHALL be registered for that component instance
- **AND** they SHALL fire at the same document-connection points as the `ComponentContext` methods

### Requirement: Observed custom-element attributes shall update props in one direction

For a named component with observed attributes, `context.props` SHALL expose a reactive mapping containing the declared attributes under snake-case keys. The mapping SHALL preserve caller-supplied mapping values and update observed keys when the corresponding DOM attribute is added, changed, or removed. Attribute values SHALL be strings; a present valueless attribute SHALL be `""`, and a removed attribute SHALL be `None`. WebComPy SHALL not write prop values back to attributes.

#### Scenario: Reading an initial observed attribute
- **WHEN** an adopted or newly bound `<my-card theme-color="dark">` has `theme-color` declared as observed
- **THEN** `context.props["theme_color"]` SHALL become `"dark"`
- **AND** a template that reads the prop reactively SHALL render the current value

#### Scenario: Reacting to an attribute change
- **WHEN** external JavaScript changes `my_card.setAttribute("theme-color", "light")`
- **THEN** `context.props["theme_color"]` SHALL update to `"light"`
- **AND** dependent WebComPy DOM content SHALL update without recreating the wrapper

#### Scenario: Reacting to attribute removal
- **WHEN** external JavaScript removes an observed `theme-color` attribute
- **THEN** `context.props["theme_color"]` SHALL update to `None`
- **AND** dependent content SHALL receive the removal through the normal reactive update path

#### Scenario: Preserving attribute value types
- **WHEN** external JavaScript sets an observed attribute to `"42"` or creates it without a value
- **THEN** the prop SHALL be `"42"` or `""` respectively
- **AND** WebComPy SHALL not infer numeric or boolean types

#### Scenario: Avoiding prop-to-attribute reflection
- **WHEN** application code changes an observed prop value
- **THEN** WebComPy SHALL update dependent component content
- **AND** it SHALL not call `setAttribute` or `removeAttribute` for that prop

### Requirement: Custom-element bindings shall release browser resources

Per-node lifecycle and attribute callback proxies SHALL be released when the component binding is logically destroyed. Queued lifecycle work SHALL either complete against the captured callback or be cancelled without invoking a destroyed component instance. The DOM node SHALL remain reusable by the existing adoption paths when it is not removed.

#### Scenario: Destroying a named component binding
- **WHEN** a named component is removed and its callback resources are disposed
- **THEN** later external attribute changes SHALL not invoke the destroyed component
- **AND** no FFI proxy for that binding SHALL remain registered

#### Scenario: Adopting a wrapper during branch patching
- **WHEN** an old component binding is detached because a new component adopts the same DOM node
- **THEN** the old binding's reactive and callback resources SHALL be released
- **AND** the custom-element DOM node SHALL not be removed solely because of the adoption
