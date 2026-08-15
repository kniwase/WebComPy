# Proposal: Universal Custom Elements

## Why

WebComPy currently supports two component forms: unnamed components (bare `@define_component`) that render as their template's root element, and named components (`@define_component("my-card")`) that render as Light DOM custom elements. This duality splits the internal implementation into two rendering paths, gates useful features (multiple roots, `:host` styles, `on_mounted`/`on_unmounted`, observed attributes) behind an opt-in most components never take, and leaves the custom-element name as a free-form value disconnected from the template engine's existing kebab-case-tag-to-PascalCase-name resolution convention. Unifying on named custom elements for every component collapses the dual path into one, makes every component capability universally available, and lets component identity be verified at definition time.

## What Changes

- **BREAKING**: Remove the bare `@define_component` form. Every component definition SHALL declare a custom-element name: `@define_component("user-card")`.
- **BREAKING**: Enforce a bidirectional naming-consistency rule at definition time: the setup function name SHALL equal `kebab_to_pascal(custom_element_name)`. Acronym-style names (`HTTPRequest`) must be written in normalized form (`HttpRequest`); single-word names (`App`, `Button`) cannot produce a valid hyphenated custom-element name and must be renamed to multi-word names.
- **BREAKING**: Every component renders one custom-element wrapper node; the template root element becomes a light-DOM child of the wrapper instead of being adopted as the component node. Root attributes, event handlers, refs, and `:preserve_children` are no longer hoisted onto the component node.
- **BREAKING**: Unnamed-only restrictions disappear: all components may return multiple roots, use `:host` scoped styles, register `on_mounted`/`on_unmounted`, and declare `observed_attributes`.
- Add a `display` keyword argument to `define_component` so authors can declare the wrapper's CSS display value at the definition site. Values are restricted to a curated `Literal` allowlist validated at runtime via `get_args` and a `TypeGuard` narrowing helper.
- Inject a framework-default CSS rule `[webcompy-component] { display: contents; }` in an early cascade layer so wrappers are layout-transparent unless the author opts into a real box. Precedence: framework default < `display` kwarg < `:host` scoped styles.
- Emit a runtime warning from `Transition` when the conditional child's computed `display` is `contents` or `none`, since CSS transitions/animations cannot run on such elements.
- Retain the unnamed rendering path internally for `AppDocumentRoot` only (the mount-point node cannot be a custom element); the public API can no longer reach it.
- Add a `ComponentStore` uniqueness check for custom-element names so distinct Python names collapsing to the same kebab name are rejected at registration.

## Capabilities

### New Capabilities

(None — all changes modify existing capabilities.)

### Modified Capabilities

- `components`: The component definition API changes (required name argument, naming-consistency validation, `display` kwarg); the unnamed rendering semantics are removed from the public API; unnamed-only rejection requirements are deleted; the `:preserve_children` inheritance requirement is removed.
- `custom-element-components`: The requirement retaining the bare form is removed; the capability becomes the single component rendering model and gains the wrapper display-default behavior.
- `template-engine`: The scenario requiring an explicit wrapper for multi-root Markdown returned from a component setup is inverted — named components accept fragment/multi-node results.
- `transition`: A new requirement covers the runtime warning for children whose computed `display` prevents transitions from running.

## Impact

- **Code**: `packages/webcompy` component system (`_generator.py`, `_component.py`, `_css_utils.py`, `_libs.py`), transition element (`_transition.py`), framework stylesheets, `ui/code_block`; migration of ~422 decorator call sites across `tests/`, `e2e/`, `docs_app/`, CLI `template_data/`, and demo apps, including ~71 component renames and `lazy()` import-path string updates.
- **APIs**: `define_component` signature (name argument now required, new `display` kwarg); new exported `ComponentDisplay` type alias.
- **Specs**: `components`, `custom-element-components`, `template-engine`, `transition` delta specs.
- **Docs**: `custom_elements.md` rewritten; quickstart and all component examples updated; a migration guide covering wrapper insertion effects (structural pseudo-classes, sibling combinators, transitions).
- **Downstream users**: fully breaking change; every component definition and some CSS assumptions must be migrated.

## Known Issues Addressed

- None of the tracked known issues are resolved by this change. (The MD5-based component-ID collision note is unaffected: IDs remain name-derived, and renames change IDs consistently across SSR and client.)

## Non-goals

- Full removal of the unnamed rendering path from `Component` internals (retained for `AppDocumentRoot`).
- Per-instance wrapper display control (the `display` kwarg is per-definition; per-instance styling remains the job of scoped/global CSS).
- Reactive wrapper display values (covered by existing reactive scoped styles with `:host`).
- Shadow DOM support (WebComPy custom elements remain Light DOM).
- A deprecation transition period for the bare form (big-bang removal).
- Changing `ComponentStore` keying away from Python function names.
