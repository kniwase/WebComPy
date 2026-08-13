## 0. Artifact Amendment

- [x] 0.1 Update proposal, design, and specs to require standalone `@on_mounted` / `@on_unmounted` decorators and to reject both hook forms in unnamed components.
- [x] 0.2 Add `port-abstraction` and `port-provisioning` delta specs for the new `CustomElementPort` and its `CUSTOM_ELEMENT_PORT_KEY`.

## 1. Browser Bridge Spike

- [x] 1.1 Verify a minimal Pyodide/PyScript `HTMLElement` subclass factory can call a retained Python proxy from `connectedCallback`, `disconnectedCallback`, and `attributeChangedCallback`.
- [x] 1.2 Define the browser custom-element port contract and proxy ownership rules without adding a browser dependency.

## 2. Component Metadata and Public API

- [x] 2.1 Extend `define_component` with bare-decorator and called-decorator overloads for a validated custom-element name and observed attributes.
- [x] 2.2 Store custom-element metadata on `ComponentGenerator` and reject invalid names, duplicate attributes, reserved framework attributes, and attribute-to-prop key collisions.
- [x] 2.3 Add `on_mounted` and `on_unmounted` to `Context`, `ComponentContext`, lifecycle state, and component properties, plus `@on_mounted` / `@on_unmounted` standalone decorators, while preserving existing lifecycle hooks and rejecting both hook forms in unnamed components.

## 3. Named Component Rendering

- [x] 3.1 Add the named-component template result type and normalize single values, sequences, text, signals, and empty results into wrapper children.
- [x] 3.2 Render named components as a custom-element wrapper with framework markers while preserving the existing one-node parent contract.
- [x] 3.3 Keep template-root attributes, events, refs, and preserve-children behavior on template children rather than copying them to the named wrapper.
- [x] 3.4 Add server virtual-DOM and serializer coverage for named wrappers and multiple light-DOM roots.

## 4. Attribute-to-Props Reflection

- [x] 4.1 Add the reactive props mapping used by observed-attribute components and preserve caller-supplied mapping values.
- [x] 4.2 Bind a custom-element node to its observed-attribute adapter and synchronize initial, changed, and removed attributes using string/`None` semantics.
- [x] 4.3 Ensure attribute updates trigger existing reactive rendering and never reflect prop updates back to DOM attributes.

## 5. Lifecycle Binding and Resource Cleanup

- [x] 5.1 Implement per-node bridge binding for lifecycle and attribute callbacks, including callbacks queued before hydration binding.
- [x] 5.2 Coalesce connected/disconnected reactions and dispatch mounted/unmounted hooks from final document `isConnected` state.
- [x] 5.3 Handle already-connected hydration adoption, DOM moves, logical destruction, branch adoption, and FFI proxy cleanup without retaining destroyed component instances.

## 6. Registration and Hydration Coordination

- [x] 6.1 Register known named custom elements before initial hydration and before first creation or adoption of later lazy components.
- [x] 6.2 Implement compatible-definition reuse and explicit incompatible-registry conflict errors.
- [x] 6.3 Verify server and SSG paths never access browser custom-element or FFI APIs.

## 7. Scoped CSS Host Support

- [x] 7.1 Extend the shared scoped-selector transformation to resolve `:host` and `:host(<compound-selector>)` for named components while retaining cid scoping.
- [x] 7.2 Reject host selectors for unnamed components and unsupported host forms with clear framework exceptions.
- [x] 7.3 Verify static runtime injection, SSR/SSG output, reactive style updates, and `@layer webcompy-scope` use the same host transformation.

## 8. Verification and Documentation

- [x] 8.1 Add unit tests for decorator validation, wrapper node counts, multi-root normalization, nested components, attribute props, and unnamed-component rejection of document-connection hooks.
- [x] 8.2 Add browser/E2E tests for registration, SSR upgrade before hydration, mounted/unmounted coalescing, external attribute changes, and repeat/switch reconciliation.
- [x] 8.3 Add scoped CSS tests for static and reactive `:host`, nested component isolation, SSR output, and incremental style injection.
- [ ] 8.4 Add public documentation and examples for named components, multiple roots, lifecycle hooks, observed attributes, and `:host`.
- [ ] 8.5 Update `AGENTS.md` and `.opencode/skills/webcompy-review/SKILL.md` spec mappings/invariants for the new capability, then run the documentation reference guardrail.
- [ ] 8.6 Run the relevant OpenSpec validation, formatter/linter, type checker, unit tests, and targeted E2E groups; record any unresolved bridge-runtime limitation.
