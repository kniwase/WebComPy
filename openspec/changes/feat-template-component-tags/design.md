## Context

Change 1 established that all tags in templates are treated as HTML elements. This change adds component resolution: when a template tag is not in the `HtmlTags` literal, the binder attempts to resolve it as a component via the DI-accessible `ComponentStore`. This enables declarative component usage in templates while keeping imports (and thus registration) explicit in Python.

The `ComponentStore` is already per-app and populated via `@define_component` when modules are imported. The template engine simply looks up component names in this store at bind time.

## Goals / Non-Goals

**Goals:**
- Resolve non-HTML tags as component references via ComponentStore DI lookup
- Support static props (`prop="value"`) and dynamic props (`:prop="var"`)
- Convert kebab-case component names to PascalCase for lookup
- Convert kebab-case prop names to snake_case for Python props dict
- Pass component body content as the default slot
- Handle self-closing component tags

**Non-Goals:**
- Named slots (only default slot in MVP)
- Event handlers on component tags (`@click` on `<card>`) — these would require special emitter semantics
- Expression evaluation in static props (always literal strings)
- Auto-import of component modules (developer must import explicitly for registration)

## Decisions

### D1: ComponentStore lookup via DI injection

The binder calls `inject(_COMPONENT_STORE_KEY)` to get the per-app ComponentStore. Component names are resolved by kebab→PascalCase conversion and dict lookup.

**Rationale**: The ComponentStore is already per-app via DI. No new global registry needed. Since `render_template` is called during component setup (which runs inside a DI scope), injection always succeeds.

**Note**: `_COMPONENT_STORE_KEY` is defined as `InjectKey[object]` (`di/_keys.py:8`), so `inject(_COMPONENT_STORE_KEY)` returns `object`. The binder SHALL cast the result to `ComponentStore`. If `_COMPONENT_STORE_KEY` is later retyped to `InjectKey[ComponentStore]`, the cast SHALL be removed and this note serves as a reminder to do so.

### D2: Hyphen convention for component tag classification

Tags containing hyphens (`-`) that are NOT found in ComponentStore raise an error. Tags without hyphens that are not found are treated as HTML (lenient).

**Rationale**: Vue convention — hyphens disambiguate: `<my-card>` is always a component. `<widget>` without hyphen could be a future HTML element, so lenient fallback is safer.

**Naming convention**: The `ComponentStore` is keyed by the function's `__name__` (`_generator.py:279`). The kebab→PascalCase conversion (`kebab_to_pascal("user-card")` → `"UserCard"`) only succeeds when the component definition function uses PascalCase naming (e.g., `def UserCard(ctx):`). Functions named in snake_case (e.g., `def user_card(ctx):`) will not match the converted name and cause a lookup error. This convention MUST be documented for component authors.

**Hyphen detection logic**: The kebab→PascalCase conversion SHALL only be invoked when the tag name contains at least one hyphen. Tags without hyphens (e.g., `<UserCard>` in PascalCase, `<usercard>` in lowercase) SHALL be passed directly to `ComponentStore` lookup using the tag name as-is. If the lookup fails for a non-hyphenated tag, it SHALL fall back to HTML element treatment (lenient fallback), consistent with the convention that only hyphenated unknown tags raise an error.

| Tag form | Example | Hyphen? | ComponentStore lookup | Failed lookup behavior |
|---|---|---|---|---|
| kebab-case | `<user-card>` | Yes | kebab→PascalCase (`UserCard`) | `WebComPyException` ("Component not found") |
| PascalCase | `<UserCard>` | No | as-is (`UserCard`) | lenient → treated as HTML |
| lowercase | `<usercard>` | No | as-is (`usercard`) | lenient → treated as HTML |

**Rationale**: The hyphen is the unambiguous signal that a tag is a component reference. PascalCase naming without a hyphen is ambiguous — it could be a component or a future HTML custom element (`HTMLUnknownElement`). The lenient fallback for non-hyphenated tags is the safer choice.

**Tag name type casting**: When the lenient fallback creates an `Element` from a non-hyphenated tag name, it SHALL use the same `cast("HtmlTags", tag_name)` strategy as Change 1's `bind_element` (see interpolation design D6).

### D3: Static props as literal strings, dynamic props as variable references

`title="Hello"` → literal string `"Hello"`. `:count="my_signal"` → variable lookup `context["my_signal"]`.

**Rationale**: The `:` prefix clearly separates "string literal" from "variable reference". This matches Vue's `:prop` convention and keeps the `{{ }}` syntax for interpolation within HTML attributes only.

### D4: kebab→snake_case for prop name conversion

`<card :item-count="x">` → `props["item_count"] = x`. Simple `replace("-", "_")`.

**Rationale**: Python component props use snake_case (`TypedDict` with `item_count`). HTML attribute names are conventionally kebab-case.

### D5: Default slot from body content

Body content is parsed and wrapped in a `lambda` generator, matching the `NodeGenerator` signature expected by components.

**Rationale**: Single-element body: passed directly. Multi-element body: wrapped in `FragmentElement` (from Change 2). This matches the existing `slots={"default": lambda: ...}` convention.

### D6: Component attribute interpolation via resolve_attr

Regular (non-`:` prefixed) component attributes MAY contain `{{ }}` interpolation patterns. These SHALL be processed by `resolve_attr` (from Change 1). When the interpolated variable is a `Signal`, the resulting `Computed` SHALL be passed as the prop value, enabling reactive prop updates.

**Rationale**: Consistency with HTML element attributes. Component authors receive a `Computed` prop and read `.value` to access the current interpolated string. The `resolve_attr` function in Change 1 handles both reactive and static evaluation automatically based on whether the interpolated variable is a `SignalBase`.

## Risks / Trade-offs

- **[Risk] Component not found due to missing import** → Mitigation: Clear error message: `"Component 'UserCard' not found. Component tags require PascalCase component function names (e.g., <user-card> resolves to UserCard). If your component is defined with a different name, use the Python API instead. Did you forget to import it? Available: ['Navbar', ...]"`.
- **[Risk] Name collision with future HTML elements** → Mitigation: Hyphen convention. Unknown non-hyphenated tags are lenient (future-proof).
- **[Risk] Prop name clashes** (e.g., `data-value` and `data_value` both map to `data_value`) → Mitigation: Document the convention. `replace("-", "_")` is deterministic and predictable.
- **[Trade-off] No named slots in MVP** → Acceptable. Default slot covers most use cases. Named slots can be added later (e.g., Vue-style `<template #name>` syntax).

## Open Questions

None — all design decisions resolved during planning phase.
