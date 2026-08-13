## Context

WebComPy currently implements a component as an `ElementBase` whose single DOM node is copied from the element returned by the setup function. The component root receives `webcompy-component` and `webcompy-cid-*` attributes, while hydration matches nodes by position and tag name. Non-dynamic elements are therefore assumed to own one DOM node, and the existing scoped CSS implementation relies on cid attributes on the root and its descendants.

The change introduces an opt-in custom-element representation without introducing Shadow DOM. A named component must remain one node from its parent element's perspective so that existing repeat, switch, patching, and hydration algorithms do not need to become general multi-node algorithms. The component's template can instead become the custom element's light-DOM children.

The browser implementation must also bridge native custom-element reactions to Python. Server rendering and SSG must never access browser APIs: they only need to serialize the custom-element tag and its normal children.

## Goals / Non-Goals

**Goals:**

- Support both the existing bare `@define_component` form and a named form such as `@define_component("my-card", observed_attributes=("theme",))`.
- Render a named component as exactly one Light DOM custom-element node.
- Allow a named setup function to return a sequence of existing renderable children.
- Provide document-connection lifecycle hooks named `on_mounted` and `on_unmounted`, exposed both as `ComponentContext` methods and as standalone decorators.
- Reflect declared DOM attributes into a reactive props mapping in the attribute-to-props direction.
- Register browser custom elements before hydration and handle elements that were parsed before registration.
- Preserve cid markers, existing scoped-style isolation, SSR output, and unnamed-component behavior.
- Make `:host` usable in named components' static and reactive scoped styles without changing the cid-based isolation model.
- Add a dedicated `CustomElementPort` ABC following the existing port-abstraction rules, provisioned in browser, server, and testing render contexts.

**Non-Goals:**

- Shadow roots, Shadow DOM lifecycle semantics, or Shadow DOM style encapsulation.
- A general multi-node `Component` implementation. Multi-root output is supported only inside the one-node named custom-element wrapper.
- Replacing cid-attribute scoping with custom-element tag selectors.
- Props-to-attribute reflection or a bidirectional attribute/prop binding system.
- Event-to-read-only-signal utilities.
- A new JavaScript runtime dependency or a user-authored JavaScript class for each component.

## Decisions

### 1. Named components use an opt-in wrapper

`define_component` remains usable as a bare decorator. The called form accepts a validated custom-element name and an optional sequence of observed attribute names. The generator stores the custom-element metadata independently from the Python component name and cid.

The custom-element name SHALL contain a hyphen and satisfy the platform's custom-element name rules. Attribute names are normalized to the browser's lower-case form, and duplicate names or attribute-to-prop key collisions are rejected during definition.

Unnamed components keep their current single-root behavior. This avoids changing existing DOM output and avoids silently changing the meaning of root attributes, event handlers, refs, and `:preserve_children` for existing applications.

**Alternative considered:** Infer a custom-element name from the Python function name. This was rejected because it makes page-global name collisions implicit and makes an API rename change the DOM contract.

### 2. The custom element is the component boundary; the template becomes its children

For a named component, `Component._tag_name` is the custom-element name and its framework attributes are generated on that wrapper. The setup result is normalized into the wrapper's child list. A single element result remains valid; a list or tuple of renderable children becomes multiple light-DOM children. Text, signal, and `None` values use the existing child normalization rules.

The wrapper always reports `_node_count == 1`. Parent containers see only the custom-element node, while the wrapper's own child indexing handles the normalized template children. This preserves the existing node-count invariant used by `repeat`, `switch`, `_patch_children`, hydration, and keyed reconciliation.

The named wrapper does not inherit attributes, event handlers, refs, or `:preserve_children` from one selected template root. Those values remain attached to the template children that produced them. Framework markers remain on the wrapper, and cid propagation to its descendants continues through the existing component ownership logic.

**Alternative considered:** Return a fragment directly from the component. This was rejected because a fragment is a dynamic multi-node container and would expose the existing multi-node reconciliation paths to every parent that uses the component.

### 3. Use a browser-only custom-element port

Custom-element registration and per-node binding SHALL be owned by a dedicated `CustomElementPort` ABC in `webcompy.ports`, following the port-abstraction rule that each browser API surface gets its own port. The browser implementation creates a small JavaScript `HTMLElement` subclass for each named element, with `connectedCallback`, `disconnectedCallback`, and the declared `observedAttributes`. The bridge is created through the existing PyScript/FFI facilities; it does not add an npm or Python dependency.

Each WebComPy node receives a bridge binding after creation or hydration adoption. The binding retains the required FFI proxies, forwards lifecycle and attribute reactions to Python, and releases them when the component binding is destroyed. The bridge queues reactions that occur before binding, which is required when SSR markup is upgraded before the component tree is hydrated.

The page-level `customElements` registry is not mirrored by a new Python global. Component generators and app stores retain registration metadata; the browser registry remains the source of truth for whether a tag is defined.

If a tag is already defined, the bridge reuses it only when its WebComPy marker and observed-attribute metadata match. A non-WebComPy definition or incompatible metadata raises a clear component exception rather than silently taking ownership of another library's tag.

**Alternative considered:** Emit custom-looking unknown tags without calling `customElements.define`. This would avoid the FFI bridge but would not provide native lifecycle callbacks or attribute observation, which are core goals of this change.

### 4. Coalesce native lifecycle reactions by document connection

Native custom-element callbacks can be triggered by DOM moves made during reconciliation. The bridge therefore coalesces connected and disconnected reactions in a microtask and checks the element's final `isConnected` state before invoking Python hooks.

For a bound component instance, a transition to document-connected invokes `on_mounted` once, and a transition to document-disconnected invokes `on_unmounted` once. A move that disconnects and reconnects the same element before the coalescing point produces neither hook. Binding an already-connected SSR node counts as connected for the newly hydrated component instance, even if no native callback occurs after binding.

The hooks describe DOM document connection, not template completion or logical destruction. `on_before_rendering`, `on_after_rendering`, and `on_before_destroy` keep their existing meanings and ordering. Async mounted/unmounted callbacks use the existing async/error routing path.

The standalone decorators `@on_mounted` and `@on_unmounted` SHALL be available in addition to the `ComponentContext` methods, mirroring the existing lifecycle decorators. Both forms SHALL raise `WebComPyComponentException` during setup when used in an unnamed component, because an unnamed component has no custom-element boundary whose document connection could be observed. Registering silently and never firing is rejected.

**Alternative considered:** Invoke hooks directly from `Component._render` and `_remove_element`. This was rejected because those methods cannot distinguish document attachment from attachment to a detached subtree, and logical destruction is intentionally different from DOM detachment during adoption.

### 5. Observed attributes use a reactive mapping

When observed attributes are declared, the named component receives a reactive mapping for `context.props`. Existing mapping values supplied by the caller are copied into that mapping; non-mapping props remain invalid for an observed-attribute component. Each observed attribute is exposed under its snake-case prop key, with `kebab-case` converted to `snake_case`.

Attribute values remain strings. A present boolean-style attribute is exposed as an empty string, and a removed attribute is exposed as `None`. The initial mapping is created before setup; after the wrapper is created or adopted, the bridge reads the current DOM attributes and updates the mapping before child hydration proceeds. Later `attributeChangedCallback` notifications update the same mapping, so reads from templates or effects are reactive.

The framework never writes these prop values back to attributes. Framework marker attributes are not observed unless explicitly declared, and declaring a marker attribute is rejected. This avoids feedback loops and keeps the boundary metadata under framework control.

**Alternative considered:** Expose one `Signal` per attribute as a separate context API. This would make attribute reads explicit but would change the existing mapping-shaped props convention and would overlap with the separately planned event-signal utility.

### 6. Define before hydration and lazily before first use

On browser startup, the app registers all currently known named component generators before `_hydrate_node()` begins. The registration occurs after the mount subtree can be marked as prerendered but before child hydration, so already-parsed SSR custom elements can be upgraded and bound without replacing their nodes. Components resolved later are registered before their first node is created or adopted.

On the server, registration is skipped completely. The server DOM port creates a virtual node using the custom-element tag, and the existing serializer emits it as an ordinary HTML element. The same component code therefore remains executable in both environments.

The `CustomElementPort` SHALL be provisioned in every render context via the `CUSTOM_ELEMENT_PORT_KEY` DI key: a browser implementation in `BrowserRenderContext`, a no-op implementation in `ServerRenderContext`, and a fake/recording implementation in the testing render path. The port SHALL NOT import `Component`; component-specific callbacks are passed as callables at `bind()` time.

### 7. Keep cid scoping and add `:host` as a selector alias

The existing cid attribute is retained on named wrappers and on ordinary descendants. No tag-selector migration is attempted, so nested component style boundaries remain unchanged.

The shared selector transformation gains a host-tag parameter. In a named component, `:host` is replaced by the custom-element selector and then receives the normal cid attribute, for example `:host(.dark)` becomes `my-card.dark[webcompy-cid-{id}]`. `:host` in an unnamed component raises a clear exception because there is no stable host tag. Unsupported host forms are rejected rather than emitted as invalid Light DOM CSS.

Static scoped styles, reactive scoped styles, browser injection, SSR/SSG head output, and CSS layer wrapping all use the same transformed CSS path. This keeps the new syntax consistent across render modes.

### 8. Test at the DOM boundary and at the environment boundary

Tests will cover decorator validation and metadata, one-node wrapper behavior, multi-root children, nested components, repeat/switch placement, SSR serialization, hydration adoption, upgrade-before-hydration, duplicate registry definitions, lifecycle coalescing, attribute addition/change/removal, reactive prop updates, and `:host` output for static and reactive styles. Browser tests are required for native custom-element reactions; server tests must verify that no browser API is touched.

## Risks / Trade-offs

- **[Pyodide cannot construct the required JavaScript subclass through the first attempted FFI path]** → Start with a minimal browser spike that defines one class, upgrades one existing node, and forwards one callback. Keep the bridge behind a port so the construction mechanism can change without changing component code.
- **[Custom-element names are page-global while component stores are app-local]** → Reuse only compatible WebComPy definitions and reject incompatible definitions. Document that applications sharing a document must coordinate names.
- **[Native callbacks arrive before Python hydration binding]** → Queue current connection state and latest observed attribute values in the bridge, then synchronize them during node binding.
- **[DOM moves cause noisy connected/disconnected callbacks]** → Coalesce reactions in a microtask and inspect final `isConnected` state.
- **[Attribute strings may not match the type expected by application props]** → Define string/`None` semantics explicitly and leave typed deserialization out of scope.
- **[A custom-element wrapper changes layout because custom elements are inline by default]** → Document that applications may set display behavior through normal CSS, including the new `:host` selector; do not impose a framework default.
- **[Existing component IDs remain MD5-based]** → Keep cid generation unchanged in this change and retain the known collision limitation in project documentation.

## Migration Plan

No migration is required for existing unnamed components. Applications can opt in one component at a time by supplying a custom-element name. The resulting HTML shape changes only for opted-in components: their former root becomes a child of the named wrapper.

Existing scoped styles continue to use cid attributes, so current selectors do not need rewriting. Applications that want to style the wrapper can add `:host` after adopting a name. Attribute observation is opt-in and has no effect on components without `observed_attributes`.

Rollback consists of removing the custom-element name and observed-attribute arguments and returning the setup function to its previous single-root result. Because browser custom-element definitions cannot be unregistered from a live document, rollback of a running page requires a page reload; a fresh server render is unaffected.

## Open Questions

- The implementation spike must select the exact Pyodide mechanism for creating an `HTMLElement` subclass and retaining its callback proxies. This is an implementation choice, not a product/API decision; the bridge contract above must remain stable.
- Browser tests must confirm the precise custom-element reaction ordering in the supported PyScript runtime, especially for an already-connected SSR node and for reconciliation moves. If the runtime differs from browser standards, the bridge adapter must normalize it to the document-connection semantics specified above.
