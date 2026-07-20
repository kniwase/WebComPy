## Why

After the HTML template engine (Changes 1-5), the next frontier is Markdown — the lingua franca of documentation, blogs, and content-heavy pages. Allowing developers to write templates in Markdown with the same `{{ }}` interpolation, `{% if %}`/`{% for %}` control flow, and component tags (`<user-card>`) as HTML templates dramatically reduces boilerplate for content-heavy components. A DI-injectable Markdown parser port allows users to start with the built-in minimal parser (stdlib-only) and upgrade to a full CommonMark-compliant parser by injecting a third-party library.

## What Changes

- Define `MarkdownPort` ABC in `webcompy/ports` with DI key `MARKDOWN_PORT_KEY`
- Implement `DefaultMarkdownParser` — a minimal but practical Markdown-to-HTML converter (~300 lines) supporting headings, paragraphs, ordered/unordered/nested lists, code blocks, inline formatting, links, images, blockquotes, horizontal rules, and HTML block passthrough
- Implement `render_markdown(source, context)` — a pipeline that converts Markdown to HTML, strips `<p>` wrappers around `{% %}` directives, and feeds the result to `render_template`
- Register `DefaultMarkdownParser` in both `BrowserRenderContext` and `ServerRenderContext`
- File-based Markdown loading delegated to `webcompy.resources.load_text` (async); callers compose `render_markdown(await load_text(path), ctx)` inside async component setup. `render_markdown` accepts `str` only.
- Support all HTML template engine features: `{{ }}`, `{% if %}`, component tags in HTML blocks
- Support `{% for %}` via standard `repeat()` path (baseline): Markdown-native list bodies produce one list block per iteration; full list-merging with `MarkdownForElement` is added in Change 7

## Capabilities

### New Capabilities
_None — extends `template-engine` and `port-abstraction`_

### Modified Capabilities
- `template-engine`: Markdown template rendering via `render_markdown`
- `port-abstraction`: New `MarkdownPort` ABC and `MARKDOWN_PORT_KEY` DI key

## Known Issues Addressed
_None — this is a new capability layered on Changes 1, 2, 4, 5_

## Non-goals
- Tables, footnotes, definition lists in DefaultMarkdownParser (available via third-party DI injection)
- Full CommonMark compliance in DefaultMarkdownParser
- Markdown-to-Markdown transformations
- Inline-only Markdown (always full document)
- `{% for %}` list-body merging into single `<ul>` — deferred to Change 7 (`MarkdownForElement`)

## Impact

- **New file**: `webcompy/ports/_markdown.py` — `MarkdownPort` ABC
- **New file**: `webcompy/template/_markdown_default.py` — `DefaultMarkdownParser`
- **Modified file**: `webcompy/ports/_keys.py` — add `MARKDOWN_PORT_KEY`
- **Modified file**: `webcompy/app/_render_context.py` — `BrowserRenderContext._register_ports()`
- **Modified file**: `webcompy-server/src/webcompy_server/_context.py` — `ServerRenderContext._register_ports()`
- **Modified file**: `webcompy/template/__init__.py` — export `render_markdown`
- **No breaking changes**

## Dependencies

- **Depends on**: Change 1 (template interpolation — `render_template` API)
- **Depends on**: Change 2 (control flow — `{% if %}`/`{% for %}` in Markdown)
- **Depends on**: Change 3 (component tags — `<user-card>` in Markdown HTML blocks)
- **Depends on**: Change 4 (`webcompy.resources.load_text` for file-based Markdown loading; callers compose `render_markdown(await load_text(path), ctx)`)
- **Required by**: Change 7 (markdown for-expansion — `MarkdownForElement` list-body merging)
- **Recommended implementation order**: Sixth template-engine change (0 → 1 → 2 → 3 → 4 → 5 → **6** → 7)
