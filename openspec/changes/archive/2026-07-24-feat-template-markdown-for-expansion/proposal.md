## Why

Change 6's Markdown pipeline renders `{% for %}` blocks via the standard HTML-first repeat() path. This means a loop wrapping Markdown native list items such as `{% for item in items %}\n- {{ item }}\n{% endfor %}` produces one `<ul>` per iteration — because the Markdown parser generates a complete `<ul>` block per item, and repeat() stacks them as independent subtrees. For documentation and content pages, developers expect list items to merge into a single `<ul>`.

This change introduces `MarkdownForElement` — a reactive `DynamicElement` that expands `{% for %}` loops at the markdown-text level, concatenates per-item markdown into one string, renders the merged markdown as **one** `<ul>` with all `<li>` children, and preserves field-level reactivity. Collection changes trigger a wholesale re-render of the merged block.

## What Changes

- Add `MarkdownForElement(DynamicElement)` in `webcompy/template/_markdown_for.py` — reactive block-rendering for `{% for %}` in Markdown templates
- Integrate body-type detection into the `render_markdown` pipeline: list-body `{% for %}` → `MarkdownForElement` (merged `<ul>` + reactive); non-list-body `{% for %}` → repeat() (unchanged, fully reactive)
- Implement expression-scoped loop-variable renaming (`{{ item.x }}` → `{{ __wmdf_N_item.x }}`) within per-item markdown body text, with `__wmdf_N_item = items[N]` injected into context
- Support nested `{% for %}`, tuple unpacking (`{% for k, v in d %}`), and nested `{% if %}` (static per item)
- Document the `__wmdf_` reserved prefix for synthetic context keys
- `{% for %}` over non-list bodies (headings, paragraphs, HTML blocks) continues to use repeat() from Change 6 — fully reactive with reactive `{% if %}`
- Provide an HTML-block escape hatch: `<ul>{% for item in items %}<li>{{ item }}</li>{% endfor %}</ul>` for fully-incremental reactive list loops

## Capabilities

### New Capabilities
_None — extends `template-engine`_

### Modified Capabilities
- `template-engine`: `{% for %}` over Markdown list bodies produces a single `<ul>` with merged `<li>` children and collection-level reactivity via `MarkdownForElement`

## Known Issues Addressed
- Markdown `{% for %}` over native list syntax now produces a single `<ul>` instead of one per iteration (addressed via `MarkdownForElement`)

## Non-goals
- Reactive `{% if %}` inside a merging `{% for %}` list body — the `{% if %}` is statically evaluated per item (fundamental constraint of Markdown block rendering; use HTML-block escape hatch for reactive list-item conditionals)
- `{% else %}` within `{% for %}` (empty-iterable fallback)
- Incremental (O(1)) DOM patching for list-body `{% for %}` — `MarkdownForElement` does O(N) block re-render on collection change, which is acceptable for content pages
- General-purpose reactive-markdown primitive (`reactive_markdown(computed_source)`) — out of scope; `MarkdownForElement` is focused on the for-loop use case

## Impact

- **New file**: `webcompy/template/_markdown_for.py` — `MarkdownForElement(DynamicElement)` (~100 lines)
- **Modified file**: `webcompy/template/__init__.py` — body-type detection in `render_markdown` pipeline; route list-body `{% for %}` to `MarkdownForElement`
- **Leverages existing**: `DynamicElement._render` / `_refresh` infrastructure (mirrors `SwitchElement` lifecycle, using shared `_run_refresh_sync` helper from `refactor-element-foundations`), `inject(MARKDOWN_PORT_KEY)` from Change 6, `_render_nodes` from Change 1, `FragmentElement` from Change 2, `_holes.resolve_var` for variable resolution
- **No breaking changes**: Non-list `{% for %}` behavior unchanged (repeat()); `<ul>` single-block output is the correct behavior users expect

## Dependencies

- **Depends on**: Change 1 (template interpolation — `_render_nodes` shared pipeline, `_holes.resolve_var`)
- **Depends on**: Change 2 (control flow — `FragmentElement` for multi-child wrapping, for-loop AST structure)
- **Depends on**: Change 6 (Markdown — `MarkdownPort`, `DefaultMarkdownParser`, `render_markdown` pipeline, `<p>` stripping) — MUST be archived after Change 6
- **Required by**: None
- **Recommended implementation order**: Seventh template-engine change (0 → 1 → 2 → 3 → 4 → 5 → 6 → **7**)
