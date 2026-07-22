## 1. MarkdownForElement Implementation

- [x] 1.1 Implement `MarkdownForElement(DynamicElement)` in `webcompy/template/_markdown_for.py` (constructor accepts iterable, body_markdown str, loop_vars list[str], context dict)
- [x] 1.2 Implement `_render()`: read iterable items, per-item rename loop vars in expression spans with `__wmdf_{N}_{varname}` prefix, inject synthetic keys into per-item context, concatenate markdown, `MarkdownPort.render()`, `<p>` strip, `_render_nodes()`, set children
- [x] 1.3 Implement `_refresh()` following `SwitchElement._refresh` pattern (re-expand, patch children, defer `on_after_rendering`); use shared `_run_refresh_sync(self._refresh, *args)` from `webcompy.elements.types._dynamic` for the callback registration path
- [x] 1.4 Register `on_after_updating` on reactive iterable during `_render()` if not `_signal_activated`; store callback node in `_callback_nodes`
- [x] 1.5 Handle static iterable (plain list/dict): no callback registration, one-shot render

## 2. Expression-Scoped Renaming

Span boundaries for `{{ }}` and `{% %}` SHALL use the same brace delimiters as Changes 1 and 2. Renamed variable paths SHALL be validated against `HOLE_PATTERN` from `webcompy.template._holes` (Change 1). `{% %}` span boundaries SHALL match the same delimiter structure as `DIRECTIVE_PATTERN` from `webcompy.template._ast` (Change 2). Variable name replacement within spans SHALL use simple string substitution (no regex needed).

- [x] 2.1 Implement `_rename_in_expressions(text: str, var_name: str, replacement: str) -> str` that renames `var_name` → `replacement` only within `{{ }}` / `{% %}` spans
- [x] 2.2 Handle tuple unpacking: rename all loop variable names in expression spans (`{% for k, v in d %}` → `__wmdf_N_k`, `__wmdf_N_v`)
- [x] 2.3 Ensure prose (non-expression text) is NOT affected by renaming

## 3. Nested and Inline Directive Handling

- [x] 3.1 Implement nested `{% for %}` detection and routing: if body contains `{% for %}` → recursively create `MarkdownForElement` (or repeat if non-list body) with composite naming prefix
- [x] 3.2 Statically evaluate `{% if %}` inside list-body for: resolve condition per item using `resolve_var` against per-item context; omit body for falsy iterations
- [x] 3.3 Handle `{% elif %}` / `{% else %}` within static per-item if evaluation

## 4. Body-Type Detection in render_markdown Pipeline

- [x] 4.1 Implement `_is_list_body(body_text: str) -> bool` heuristic: strip if-directive lines, check remaining non-empty lines start with `-`, `*`, `+`, or digit+`.`/`)`
- [x] 4.2 Integrate detection into `render_markdown`: for-each `{% for %}` block, if list body → create `MarkdownForElement`; else → use standard repeat() path
- [x] 4.3 Ensure non-list for-loops continue to work with reactive `{% if %}` (unchanged from Change 6 baseline)

## 5. Reserved Prefix Documentation

- [x] 5.1 Document `__wmdf_` as framework-reserved prefix for synthetic context keys in the template engine module docstring and README

## 6. Unit Tests — MarkdownForElement

- [x] 6.1 Single list-body for produces one `<ul>` with N `<li>` children (static list)
- [x] 6.2 Ordered list body produces one `<ol>` with N `<li>` children
- [x] 6.3 Field-level reactivity: `{{ item.field }}` with Signal → DOM text updates on field change without block re-render
- [x] 6.4 Collection reactivity: `ReactiveList` append → `_refresh` called → `<ul>` updated with new `<li>`
- [x] 6.5 Collection reactivity: `ReactiveList` remove → `_refresh` → `<ul>` updated
- [x] 6.6 Collection reactivity: `ReactiveDict` change → `_refresh` → `<ul>` updated
- [x] 6.7 Static iterable (plain list): no on_after_updating registered, `_refresh` not called on change
- [x] 6.8 Loop variable renaming correctness (item → `__wmdf_N_item`)
- [x] 6.9 Renaming scoped to expressions only (prose "item" preserved)
- [x] 6.10 Tuple unpacking (`{% for k, v in d %}`) — both vars renamed and bound correctly
- [x] 6.11 Nested `{% for %}` in list body (inner for merged recursively)

## 7. Unit Tests — If-in-For Static Evaluation

- [x] 7.1 `{% if item.active %}` in list-body for: static evaluation, truthy branch emitted, falsy omitted
- [x] 7.2 `{% if %}` re-evaluates on collection change (block re-render)
- [x] 7.3 `{% elif %}` / `{% else %}` within static per-item if
- [x] 7.4 Non-list for with `{% if %}`: reactive via switch() (unchanged from Change 6)

## 8. Unit Tests — Body-Type Detection

- [x] 8.1 List body (`- ` lines) → routed to MarkdownForElement
- [x] 8.2 Unordered list (`* ` marker) → MarkdownForElement
- [x] 8.3 Ordered list (`1. ` marker) → MarkdownForElement
- [x] 8.4 Non-list body (heading `# `) → routed to repeat()
- [x] 8.5 Non-list body (plain text paragraphs) → routed to repeat()
- [x] 8.6 Non-list body (HTML blocks `<div>`) → routed to repeat()
- [x] 8.7 Non-list body preserves reactive `{% if %}` (repeat + switch)

## 9. Unit Tests — HTML-Block Escape Hatch

- [x] 9.1 `<ul>{% for %}{% if %}<li>...</li>{% endif %}{% endfor %}</ul>` produces single `<ul>` with reactive if (repeat + switch path)
- [x] 9.2 Incremental (O(1)) patching: adding one item to list does not re-render all items

## 10. Unit Tests — Lifecycle

- [x] 10.1 Callback node stored in `_callback_nodes` on reactive iterable
- [x] 10.2 Callback node destroyed on element cleanup
- [x] 10.3 `on_after_rendering` deferred during `_refresh()` (signal_activated)
- [x] 10.4 Zero children case (empty iterable): no DOM nodes created, no error

## 11. Integration Tests

- [x] 11.1 End-to-end: `render_markdown` with `{% for %}` over list body and `locals()` context
- [x] 11.2 Mixed for: list-body for + non-list for in same Markdown document

## 12. SSR & Hydration

- [x] 12.1 `render_app_html_sync(app)` with Markdown template using list-body `{% for %}` — verify SSR HTML contains single `<ul>` with correct `<li>` elements
- [x] 12.2 `TestRenderer.render()` — verify `__webcompy_prerendered_node__` flags on children of MarkdownForElement
- [x] 12.3 E2E: test that after hydration, field-level Signal changes update individual `<li>` text nodes
- [x] 12.4 E2E: test that after hydration, ReactiveList append triggers re-render of the merged `<ul>` block

## 13. CI Review Update

- [ ] 13.1 Update `.opencode/agents/ci-review.md`: add `MarkdownForElement` pattern (reactive block-rendering DynamicElement, expression-scoped renaming, list-body detection heuristic, lifecycle mirroring SwitchElement, `__wmdf_` reserved prefix)
- [ ] 13.2 Update `AGENTS.md` File→Spec Mapping: `webcompy/template/_markdown_for.py` → `template-engine` spec
