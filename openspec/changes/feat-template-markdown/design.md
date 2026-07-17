## Context

WebComPy's template engine (Changes 1-5) processes HTML template strings with `{{ }}` interpolation, `{% if %}`/`{% for %}` control flow, and component tag resolution. This change adds Markdown as an alternative template syntax by converting Markdown to HTML and feeding it through the existing HTML template engine pipeline.

The key challenge is the interaction between Markdown's block-level parsing and Jinja2's `{% %}` block directives. Markdown parsers wrap freestanding text lines in `<p>` tags, which would incorrectly wrap `{% for %}` and `{% endif %}` directives. A post-processing step removes these `<p>` wrappers.

For the Markdown parser itself, Python's stdlib provides no built-in solution. A DI-injectable `MarkdownPort` allows the framework to ship a minimal built-in parser while enabling users to inject a full-featured third-party parser (mistletoe, markdown, etc.) for complete CommonMark compatibility.

## Goals / Non-Goals

**Goals:**
- Define `MarkdownPort` ABC with DI injection
- Implement built-in `DefaultMarkdownParser` supporting common Markdown features
- Implement `render_markdown` pipeline: Markdown → HTML → directive cleanup → `render_template`
- Support nested lists via indent-based parsing
- Support HTML block passthrough (including component tags)
- Support file-based Markdown via `Path`
- Support all template engine features in Markdown: `{{ }}`, `{% if %}`/`{% for %}`, component tags

**Non-Goals:**
- Tables, footnotes, definition lists in DefaultMarkdownParser (available via third-party injection)
- Full CommonMark compliance in DefaultMarkdownParser
- Markdown-to-Markdown transformations
- Inline-only Markdown (always full document)

## Decisions

### D1: `MarkdownPort` ABC with DI injection

Follows the existing port abstraction pattern (`DOMPort`, `FetchPort`, etc.). `MarkdownPort` defines a single `render(source: str) -> str` method. `MARKDOWN_PORT_KEY` is an `InjectKey[MarkdownPort]`. Both `BrowserRenderContext` and `ServerRenderContext` provide `DefaultMarkdownParser()` as the default.

**Rationale**: The built-in parser handles 90% of use cases (documentation pages, blogs, simple content). Users needing tables, footnotes, or strict CommonMark compliance can inject a third-party parser. This follows WebComPy's established port pattern and avoids mandating an external dependency.

**Alternatives considered**: Requiring an external Markdown dependency would violate the stdlib-only constraint. A full CommonMark parser from scratch would be ~1000+ lines and is not a good use of framework development time.

### D2: Post-processing to strip `<p>` wrappers from `{% %}` directives

Markdown parsers wrap freestanding text lines in `<p>` tags. This produces `<p>{% for item in items %}</p>` which the template engine's bracket matcher (Change 2) would treat as a single-element body rather than a multi-element block. A regex post-process removes `<p>` tags wrapping lone `{% %}` directives.

```python
re.sub(r'<p>\s*(\{%[^<]*?%\})\s*</p>', r'\1', html)
```

**Rationale**: Simple, targeted fix. Only removes `<p>` around lines that are purely `{% %}` directives. Lines containing both text AND directives (e.g., `<p>Text {% if x %}</p>`) are left intact. The regex uses non-greedy matching and excludes `<` from the directive body to prevent matching across HTML elements.

### D3: HTML block detection for preserving component tags

Lines starting with `<` are detected as HTML blocks and passed through unchanged by the Markdown parser. This preserves component tags (`<user-card>`) and other raw HTML in Markdown content.

**Rationale**: Standard Markdown behavior — most parsers pass HTML through unchanged. Component tags from Change 3 resolve during the `render_template` step of the pipeline.

### D4: Indent-based nested list parsing

List items are grouped by indent level. When indent increases, a nested sub-list begins (recursive parsing). Tabs are normalized to 2 spaces for consistent indent calculation.

**Rationale**: Nested lists are essential for documentation and content. The indent-based approach maps naturally to Markdown's visual structure. Tab normalization avoids platform-specific indent issues.

### D5: Inline formatting order (images before links)

Inline parsing applies transformations in a specific order: images (`![alt](url)`) before links (`[text](url)`), then bold, italic, strikethrough, and inline code. This prevents `![alt](url)` from being partially consumed by the link regex.

**Rationale**: Images start with `!` and contain `[...](...)` which overlaps with the link pattern. Processing images first ensures `!` is consumed before the link regex sees the bracket structure.

### D6: FragmentElement for multi-root Markdown documents

`render_markdown` does NOT call `render_template` directly. Instead, it uses the lower-level parser and binder from Change 1 (exposed as `_render_nodes` function) which returns ALL root nodes without single-root validation. The nodes are then wrapped:

- Single root node → returned as-is (`Element`)
- Multiple root nodes → wrapped in `FragmentElement` (no DOM wrapper)

This works because Markdown naturally produces multiple top-level HTML elements (`<h1>`, `<p>`, `<ul>`, etc.). FragmentElement (from Change 2) is transparent — its children render directly in the parent DOM. When `render_markdown` is used as a child of an HTML element, no extra wrapper `<div>` appears in the DOM. When used as a component root, the developer explicitly chooses the wrapper element:

```python
return html.ARTICLE({}, render_markdown("# Title\n\nText", locals()))
```

**Rationale**: Adding a default `<div>` wrapper to every Markdown document would pollute the DOM with semantically meaningless elements. FragmentElement avoids this entirely. The developer retains control: for component roots, they wrap in a semantic element (`<article>`, `<section>`, `<div>`); for child content, FragmentElement is transparent.

**Component root constraint**: When `render_markdown` returns a `FragmentElement` (multiple top-level elements), it is NOT a valid component root. `Component.__init_component` (`_component.py:188-189`) requires `isinstance(node, Element)`, and `FragmentElement` is a `DynamicElement`, not an `Element`. Developers MUST wrap multi-root Markdown in an explicit `Element` wrapper when used as a component root.

**Change 7 refinement**: In Change 7, `{% for %}` over Markdown list bodies is routed to `MarkdownForElement` which merges list items into a single `<ul>` (instead of the baseline one-`<ul>`-per-iteration). Non-list for-loops stay on the fully-reactive `repeat()` path.

**Implementation**: Change 1 is updated to expose `_render_nodes(source, context) -> list[ElementAbstract]` via the internal pipeline `_cache.py` → `_bind.py` → `_render_nodes`. This shared function parses + binds without single-root validation. `render_template` wraps `_render_nodes` with root validation. `render_markdown` uses `_render_nodes` directly.

## Risks / Trade-offs

- **[Risk] DefaultMarkdownParser edge cases in real-world Markdown** → Mitigation: DI injection allows users to replace with a battle-tested parser. The built-in parser is documented as "minimal but practical."
- **[Risk] `<p>` stripping regex too aggressive** → Mitigation: The regex is targeted: only matches `<p>` wrapping a single `{% %}` directive with optional whitespace. Nested or compound cases are not stripped (safe default).
- **[Risk] Markdown block-level state machine complexity** → Mitigation: Line-by-line parser with simple state transitions (para, list, code, html, blank). No lookahead beyond 1 line in most cases.
- **[Trade-off] No CommonMark compliance in built-in parser** → Acceptable — the DI injection mechanism provides the upgrade path if needed.
- **[Trade-off] DefaultMarkdownParser (~300 lines) adds to browser wheel bundle size** → Acceptable. The parser is part of the `webcompy` core package and always included in the browser wheel. ~300 lines of Python compresses to ~10KB, which is negligible compared to the PyScript/Emscripten WASM runtime (several MB). If bundle size becomes a concern in the future, `DefaultMarkdownParser` can be lazy-imported at first `inject(MARKDOWN_PORT_KEY)` time, avoiding the overhead for apps that do not use Markdown.

## Open Questions

None — all design decisions resolved during planning phase.
