## 1. Name Conversion Utilities

- [x] 1.1 Implement `kebab_to_pascal(kebab: str) -> str` (e.g., `"user-card"` → `"UserCard"`)
- [x] 1.2 Implement `kebab_to_snake(kebab: str) -> str` (e.g., `"item-count"` → `"item_count"`)

## 2. Tag Resolution

- [x] 2.1 Implement `resolve_tag(tag: str, store: ComponentStore)` returning `TagResolution` (NEWLINE, HTML, or COMPONENT)
- [x] 2.2 Implement hyphen-based error vs lenient fallback: hyphenated unknown → error, non-hyphenated → HTML element

## 2. Tag Resolution

- [x] 2.1 Implement `resolve_tag(tag: str, store: ComponentStore)` returning `TagResolution` (NEWLINE, HTML, or COMPONENT)
- [x] 2.2 Implement hyphen-based error vs lenient fallback: hyphenated unknown → error, non-hyphenated → HTML element
- [ ] 2.3 Integrate tag resolution into `bind_element` — intercept before HTML element creation, route to component path or HTML path
- [ ] 2.4 Implement ComponentStore injection: `store = inject(_COMPONENT_STORE_KEY)` — note that `_COMPONENT_STORE_KEY` is typed `InjectKey[object]` (`di/_keys.py:8`) so the return value is `object` and requires a cast to `ComponentStore`

## 3. Props Binding

- [ ] 3.1 Implement static prop resolution: attribute value used as-is (literal string)
- [ ] 3.2 Implement dynamic prop resolution: `:-prefixed` attribute → `resolve_var(value, ctx)` → stored in props dict
- [ ] 3.3 Apply `kebab_to_snake` conversion to prop names before storing
- [ ] 3.4 Implement `{{ }}` interpolation in regular component attributes using `resolve_attr` (reactive Computed for Signal values, static string for non-Signals)

## 4. Slot Binding

- [ ] 4.1 Implement default slot generation: bind component body children, wrap multi-element in FragmentElement, create lambda generator
- [ ] 4.2 Pass empty `slots={}` for self-closing tags (no body)

## 5. Component Instantiation

- [ ] 5.1 Call `generator(props, slots=slots)` to create Component instance, returning it as the child element

## 6. Unit Tests

- [ ] 6.1 Test component tag resolution (kebab→PascalCase lookup, successful match)
- [ ] 6.2 Test component not found with hyphen (error with available names)
- [ ] 6.3 Test unknown tag without hyphen (lenient HTML fallback)
- [ ] 6.4 Test self-closing component tag
- [ ] 6.5 Test static prop binding (string literal)
- [ ] 6.6 Test dynamic prop binding (variable lookup, Signal preservation)
- [ ] 6.7 Test prop name kebab→snake_case conversion
- [ ] 6.8 Test default slot with single child
- [ ] 6.9 Test default slot with multiple children (FragmentElement wrapping)
- [ ] 6.10 Test empty default slot (self-closing)
- [ ] 6.11 Test HTML tags unaffected (no component resolution for `<div>`, etc.)
- [ ] 6.12 Test `<br>` still maps to NewLine (not component lookup)

## 7. Integration Tests

- [ ] 7.1 Test end-to-end: `render_template` with `<user-card>` in component setup
- [ ] 7.2 Test component receives reactive Signal via `:prop` and updates when Signal changes
- [ ] 7.3 Test nested component tags (component inside component)

## 8. SSR & Hydration

- [ ] 8.1 Test `render_app_html_sync(app)` with a component using `<user-card>` in template — verify SSR HTML includes the component's rendered output
- [ ] 8.2 Test `TestRenderer.render()` with component tags — verify prerendered component nodes have correct `webcompy-component` attribute and `__webcompy_prerendered_node__` flags
- [ ] 8.3 E2E: verify (a) pre-rendered HTML from `<user-card>` component tag matches expected structure, (b) hydration reuses existing component DOM nodes, (c) reactive prop changes (`:count="signal"`) propagate to the child component after hydration

## 9. CI Review Update

- [ ] 9.1 Update `.opencode/agents/ci-review.md`: add component-tag resolution pattern (DI-based ComponentStore lookup via `_COMPONENT_STORE_KEY`, kebab→PascalCase name conversion, kebab→snake_case prop conversion, hyphen convention for component-vs-HTML disambiguation)
- [ ] 9.2 Update `AGENTS.md` File→Spec Mapping: `webcompy/template/_binder.py` component tag path → `template-engine` spec
