## 1. MarkdownPort ABC + DI Key

- [ ] 1.1 Define `MarkdownPort` ABC in `webcompy/ports/_markdown.py` with abstract `render(source: str) -> str` method
- [ ] 1.2 Add `MARKDOWN_PORT_KEY = InjectKey[MarkdownPort]("webcompy-port-markdown")` to `webcompy/ports/_keys.py`
- [ ] 1.3 Add `MarkdownPort` and `MARKDOWN_PORT_KEY` to `webcompy/ports/__init__.py` (import + `__all__`), following the existing port export pattern

## 2. DefaultMarkdownParser

- [ ] 2.1 Implement `DefaultMarkdownParser(MarkdownPort)` in `webcompy/template/_markdown_default.py`
- [ ] 2.2 Implement block-level parser: headings (`#`~`######`), paragraphs (consecutive non-blank lines), blank line handling
- [ ] 2.3 Implement list parser with nested list support (indent-based nesting, tab→2space normalization, ul/ol mixed nesting)
- [ ] 2.4 Implement fenced code block parser (```` ``` ```` fences, optional language hint ignored)
- [ ] 2.5 Implement blockquote parser (`>` prefix, multi-line joins)
- [ ] 2.6 Implement horizontal rule parser (`---`, `***`, `___` on own line)
- [ ] 2.7 Implement HTML block detection: lines starting with `<` output as-is (passthrough)
- [ ] 2.8 Implement inline parser: bold (`**`), italic (`*`), strikethrough (`~~`), inline code (`` ` ``), links (`[]()`), images (`![]()`)
- [ ] 2.9 Ensure inline formatting order: images before links, bold before italic
- [ ] 2.10 Apply `textwrap.dedent` to source before parsing

## 3. Port Registration

- [ ] 3.1 Import `DefaultMarkdownParser` and `MARKDOWN_PORT_KEY` in `BrowserRenderContext._register_ports()`
- [ ] 3.2 Provide `DefaultMarkdownParser()` via `self._di_scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())`
- [ ] 3.3 Do the same in `ServerRenderContext._register_ports()`

## 4. render_markdown Pipeline

- [ ] 4.1 Implement `render_markdown(source: str | Path, context: dict) -> ElementAbstract` in `webcompy/template/__init__.py`
- [ ] 4.2 Implement source loading: `str` → use directly; `Path` → `_load_file` from `webcompy.template._files` (created by Change 4)
- [ ] 4.3 Implement `inject(MARKDOWN_PORT_KEY).render(text)` to convert Markdown to HTML
- [ ] 4.4 Implement `_strip_directive_paragraphs(html) -> str` using regex to remove `<p>` wrappers around lone `{% %}` directives
- [ ] 4.5 Call `_render_nodes(html, context)` (shared function from Change 1) to parse + bind without single-root validation
- [ ] 4.6 If result has 1 node → return it directly; if multiple nodes → wrap in `FragmentElement` and return
- [ ] 4.7 Export `render_markdown` from `webcompy.template.__init__`

## 5. Unit Tests — DefaultMarkdownParser

- [ ] 5.1 Headings (h1-h6, with/without space after `#`)
- [ ] 5.2 Paragraphs (single line, multi-line joined, with inline formatting)
- [ ] 5.3 Unordered lists (`-` and `*` markers)
- [ ] 5.4 Ordered lists (`1.` and `1)` markers)
- [ ] 5.5 Nested lists (indent-based, ul/ol mixed, 3+ levels)
- [ ] 5.6 Deeply nested lists (3+ levels, alternate markers)
- [ ] 5.7 Code blocks (```` ``` ```` fenced, with language hint ignored)
- [ ] 5.8 Inline code (backtick)
- [ ] 5.9 Bold (`**text**`) and italic (`*text*`)
- [ ] 5.10 Strikethrough (`~~text~~`)
- [ ] 5.11 Links (`[text](url)`)
- [ ] 5.12 Images (`![alt](url)`)
- [ ] 5.13 Horizontal rules (`---`, `***`, `___`)
- [ ] 5.14 Blockquotes (`> text`, multi-line join)
- [ ] 5.15 HTML block passthrough (div, span, component tags like `<user-card>`)
- [ ] 5.16 `{{ }}` and `{% %}` preserved as plain text in output
- [ ] 5.17 Mixed content (heading + paragraph + nested list + blockquote + code)

## 6. Unit Tests — render_markdown Pipeline

- [ ] 6.1 Basic `render_markdown` single-root → returns Element
- [ ] 6.2 Basic `render_markdown` multi-root → returns FragmentElement
- [ ] 6.3 `{{ }}` interpolation in Markdown text (str and Signal values)
- [ ] 6.4 `{% if %}` / `{% elif %}` / `{% else %}` blocks in Markdown
- [ ] 6.5 `{% for %}` blocks wrapping multiple Markdown elements
- [ ] 6.6 `{% for %}` and `{% endfor %}` `<p>` wrapper stripping
- [ ] 6.7 `{% for %}` with nested `{% if %}` in body
- [ ] 6.8 Component tags in Markdown HTML blocks
- [ ] 6.9 File-based Markdown loading (`Path`)
- [ ] 6.10 `textwrap.dedent` applied to Markdown source
- [ ] 6.11 FragmentElement renders transparently inside parent element
- [ ] 6.12 render_markdown as component root with explicit wrapper

## 7. Unit Tests — DI

- [ ] 7.1 DefaultMarkdownParser provided by default in BrowserRenderContext
- [ ] 7.2 DefaultMarkdownParser provided by default in ServerRenderContext
- [ ] 7.3 Custom parser injection via `app.provide(MARKDOWN_PORT_KEY, ...)`
- [ ] 7.4 `inject(MARKDOWN_PORT_KEY)` returns correct instance after injection

## 8. Integration Tests

- [ ] 8.1 Component using `render_markdown` with `locals()`
- [ ] 8.2 Reactive Markdown: Signal value change → DOM text update
- [ ] 8.3 Markdown with `{% for %}` containing Markdown-formatted items (Signal preservation)
- [ ] 8.4 Markdown with component tags and dynamic props (`<card :count="signal">`)
- [ ] 8.5 SSR/SSG with Markdown template
- [ ] 8.6 Custom Markdown parser via DI (e.g., mistletoe adapter)

## 9. CI Review Update

- [ ] 9.1 Update `.opencode/agents/ci-review.md`: add MarkdownPort and DefaultMarkdownParser patterns
- [ ] 9.2 Update `AGENTS.md` File→Spec Mapping: `webcompy/ports/_markdown.py` → `port-abstraction` spec; `webcompy/template/_markdown_default.py` → `template-engine` spec
