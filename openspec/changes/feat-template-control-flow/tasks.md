## 1. FragmentElement

- [x] 1.1 Implement `FragmentElement(DynamicElement)` in `packages/webcompy/src/webcompy/elements/types/_fragment.py` (constructor accepts `list[ElementAbstract]`, `_on_set_parent` is no-op). After `refactor-element-foundations`, `FragmentElement` (an `ElementAbstract` subclass) is automatically valid as `ElementChildren`; no separate type-alias edit is needed.
- [x] 1.2 Test FragmentElement rendering (single child, multiple children, zero children, nested in repeat, nested in switch)
- [x] 1.3 Test FragmentElement hydration: zero children (no-op), single child (child hydrated), multiple children (all hydrated in parent)

## 2. Template AST — Control Flow Nodes

- [x] 2.1 Add `IfNode(branches: list[tuple[str|None, list[TemplateNode]]])` and `ForNode(loop_vars: list[str], iterable_path: str, body: list[TemplateNode])` to `_ast.py` (`loop_vars` is a list to support single variable `["item"]` and tuple unpacking `["key", "value"]`)
- [x] 2.2 Add `DIRECTIVE_PATTERN` regex to match `{% if %}`, `{% elif %}`, `{% else %}`, `{% endif %}`, `{% for %}`, `{% endfor %}` with variable path extraction
- [x] 2.3 Add `DirectiveToken` types (IfDirective, ElseDirective, EndIfDirective, ForDirective, EndForDirective) for the bracket-matching phase

## 3. Parser — {% %} Block Extraction and Bracket Matching

- [x] 3.1 Implement text node post-processing: scan `TemplateText` children for `{% %}` patterns, split into `LiteralText` and `DirectiveToken` sequences
- [x] 3.2 Implement bracket-matching algorithm: walk children list, match `{% if %}`→`{% endif %}`, `{% for %}`→`{% endfor %}`, group intermediate children into IfNode/ForNode. For `{% for %}`, split the left-hand side on `,` → list of loop variable names (supporting both `"item"` and `"key, value"` tuples)
- [x] 3.3 Handle `{% elif %}` and `{% else %}` within `{% if %}` blocks
- [x] 3.4 Handle nested control flow (if inside for, for inside if) via recursive application of bracket matching
- [x] 3.5 Raise error on malformed blocks (missing endif, missing endfor, mismatched nesting)

## 4. Binder — Control Flow Binding

- [ ] 4.1 Implement `bind_if(node: IfNode, ctx) -> ElementChildren` with Signal detection → `switch()` path vs static truthiness evaluation path
- [ ] 4.2 Implement `bind_for(node: ForNode, ctx) -> ElementChildren` with Signal detection → `repeat()` + FragmentElement path vs list comprehension path
- [ ] 4.3 Implement branch/iteration body binding with context extension (loop variable added to context)
- [ ] 4.4 Implement FragmentElement wrapping for multi-child branches/iterations
- [ ] 4.5 Implement dict key-value mapping for `{% for key, value in dict %}`: select `repeat()` `Callable[[V, K], ElementChildren]` overload, map callback args `(value=args[0], key=args[1])` to loop variable names by position
- [ ] 4.6 Widen `SwitchCasesSignal` type alias in `packages/webcompy/src/webcompy/elements/types/_switch.py:23` from `list[tuple[SignalBase[Any], NodeGenerator]]` to `list[tuple[Any, NodeGenerator]]` — aligns with runtime behavior in `_select_generator()` and with `SwitchCasesSignalList` which already uses `Any`; pure type-level change

## 5. Unit Tests — Parser Control Flow

- [x] 5.1 Test `{% if %}` / `{% endif %}` parsing into IfNode (single branch, with elif/else)
- [x] 5.2 Test `{% for %}` / `{% endfor %}` parsing into ForNode
- [x] 5.3 Test nested control flow parsing (if in for, for in if)
- [x] 5.4 Test malformed block error cases

## 6. Unit Tests — Binder Control Flow

- [ ] 6.1 Test reactive if binding (Signal condition → switch generation)
- [ ] 6.2 Test static if binding (bool/None condition → conditional inclusion)
- [ ] 6.3 Test if-elif-else chain binding
- [ ] 6.4 Test reactive for binding (ReactiveList → repeat generation, single child)
- [ ] 6.5 Test reactive for binding with multiple children (FragmentElement wrapping)
- [ ] 6.6 Test static for binding (plain list → list comprehension)
- [ ] 6.7 Test for binding with ReactiveDict
- [ ] 6.8 Test dict key-value unpacking (`{% for k, v in d %}`) with ReactiveDict — both `k` and `v` available in body
- [ ] 6.9 Test loop variable scoping (item available in body)
- [ ] 6.10 Test dot notation in conditions and iterables

## 7. Integration Tests

- [ ] 7.1 Test `render_template` with `{% if %}` and `{% for %}` end-to-end (component setup context)
- [ ] 7.2 Test nested control flow integration (for containing if)
- [ ] 7.3 Test multi-element scenarios with FragmentElement in switch and repeat contexts
- [ ] 7.4 Test switch() truthiness evaluation semantics with Signal conditions

## 8. SSR & Hydration

- [ ] 8.1 Test `render_app_html_sync(app)` with a template component using `{% if %}` / `{% for %}` — verify SSR HTML contains correct branch / repeated elements
- [ ] 8.2 Test `TestRenderer.render(component)` — verify prerendered nodes from conditional and loop branches have `__webcompy_prerendered_node__` flag
- [ ] 8.3 E2E: add a template-based demo page under `e2e/core/` with control flow using `static_site` fixture — verify (a) pre-rendered HTML matches conditional branch output, (b) hydration correctly reuses existing DOM nodes, (c) Signal change triggers `switch()` branch switch with correct DOM update

## 9. CI Review Update

- [ ] 9.1 Update `.opencode/agents/ci-review.md`: add `FragmentElement` as a new `DynamicElement` subclass (no DOM node, transparent child rendering, `_is_patchable` returns False, follows `SwitchElement` lifecycle for re-render / deferred `on_after_rendering`)
- [ ] 9.2 Update `AGENTS.md` File→Spec Mapping: `webcompy/elements/types/_fragment.py` → `elements` spec
