## 1. Module Setup

- [x] 1.1 Create `packages/webcompy/src/webcompy/template/` package directory structure with `__init__.py`

## 2. Shared Holes Module (_holes.py)

- [x] 2.1 Create `_holes.py` module — no imports from other template modules (avoids circular dependencies)
- [x] 2.2 Implement `HOLE_PATTERN` regex: `\{\{\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\}\}` — first segment MUST start with letter/underscore (rejects `{{123}}` digit-first patterns as literal text)
- [x] 2.3 Implement `LiteralText(text: str)` and `Hole(var_path: str)` dataclasses
- [x] 2.4 Implement `split_text(text: str) -> list[LiteralText | Hole]` for `{{ }}` extraction from text and attribute values
- [x] 2.5 Implement `resolve_var(path: str, ctx: dict) -> Any` with dot-notation support (dict key access with `isinstance` check, fallback to `getattr`)
- [x] 2.6 Implement `resolve_holes(text: str, ctx: dict) -> str` that resolves all `{{ }}` patterns to string values (extracts `.value` from Signals, `str()` for others, `""` for `None`; used by Change 5 `css_text_template`)

## 3. Template AST

- [x] 3.1 Implement `_ast.py` with TemplateNode, TemplateElement, TemplateText, AttrSpec dataclasses (imports `LiteralText`, `Hole`, `split_text` from `_holes.py`)

## 4. HTML Parser (Tree Builder)

- [x] 4.1 Implement `TemplateTreeBuilder(HTMLParser)` with `VOID_ELEMENTS` set and `handle_starttag` (element creation, stack push, void element exclusion)
- [x] 4.2 Implement `handle_startendtag` for self-closing tag syntax (`<tag />`)
- [x] 4.3 Implement `handle_endtag` with stack matching
- [x] 4.4 Implement `handle_data` with `{{ }}` scanning and `split_text` integration
- [x] 4.5 Implement `handle_comment` to skip comments
- [x] 4.6 Implement `<br>` tag preservation and boolean attribute (`None` or `""` → `True`) handling
- [x] 4.7 Implement `REJECTED_TAGS` check (`script`, `style`, `iframe`, `noembed`, `noframes`, `xmp`) raising `WebComPyException`

## 5. Compilation Cache

- [x] 5.1 Implement `_cache.py` with module-level `_template_cache` dict and `get_or_compile()` function (dedent → strip → cache lookup/miss → parse → store → return)

## 6. Event Handler and Ref Binding

- [x] 6.1 Implement `classify_attrs()` that partitions attribute specs into: `@event` → events dict, `:ref` → ref lookup, boolean → attr True, regular → attr string
- [x] 6.2 Implement event handler resolution: `@click="on_click"` → `events["click"] = resolve_var("on_click", ctx)`
- [x] 6.3 Implement DomNodeRef resolution: `:ref="my_ref"` → `ref = resolve_var("my_ref", ctx)`

## 7. Attribute Evaluation (Reactive + Static)

- [x] 7.1 Implement `resolve_attr(parts, ctx) -> AttrValue` with Signal detection: check all Hole references for `isinstance(resolve_var(...), SignalBase)`
- [x] 7.2 Implement `Computed` generation branch: when Signals are detected, create a `Computed(lambda: ...)` closure that concatenates literal parts and current Signal `.value`s (using `Computed(fn)` from `webcompy.signal` — Tier 2 internal constructor API)
- [x] 7.3 Ensure static path preserves original behavior: when no Signals are referenced, resolve to plain string via concatenation
- [x] 7.4 Test `Computed` lifecycle: component destroy cleans up attribute `Computed` consumer nodes (verified via `on_after_updating` callback node cleanup on `Element` destruction)

## 8. Element Tree Binding

- [x] 8.1 Implement `bind_element(node: TemplateElement, ctx) -> Element` that creates `Element` instances with resolved attrs, events, ref, and recursively bound children
- [x] 8.2 Implement `bind_children(nodes, ctx) -> list` that dispatches TemplateText → text parts binding, TemplateElement → bind_element
- [x] 8.3 Implement `bind_text_part(node: TemplateText, ctx) -> list[ElementChildren]` that processes all parts of a `TemplateText` node in a single call: `LiteralText` → its text, Hole → `resolve_var(Hole.var_path, ctx)` (None skipped per spec, `str`/`SignalBase`/`ElementAbstract` passed through, anything else `str()`-converted)

## 9. Shared Pipeline + Public API

- [ ] 9.1 Implement `_render_nodes(source: str, context: Mapping[str, Any] | None = None) -> list[ElementChildren]` in `template/__init__.py` as the shared internal pipeline: dedent → cache → parse → bind all root nodes without single-root validation (enables reuse by Change 6's `render_markdown`)
- [ ] 9.2 Implement `render_template(source: str, context: dict[str, Any]) -> Element` in `__init__.py` that calls `_render_nodes` and asserts exactly one root Element

## 10. Unit Tests — Holes Module

- [x] 10.1 Test HOLE_PATTERN matches `{{ varname }}`, `{{ a.b.c }}` with optional whitespace
- [x] 10.2 Test HOLE_PATTERN rejects `{{123}}` (digit-first), `{{}}` (empty), `{{` (unclosed) — all treated as literal text
- [x] 10.3 Test `split_text` with literal-only text, hole-only text, mixed content, multiple holes
- [x] 10.4 Test `resolve_var` dict key access, object attribute access, chained paths, missing key → KeyError
- [x] 10.5 Test `resolve_holes` with plain strings (passthrough), Signal values (`.value` extraction), `None` → `""`
- [x] 10.6 Test `resolve_holes` with mixed literal and holes in CSS-style text (validates Change 5 compatibility)

## 11. Unit Tests — Parser

- [x] 11.1 Test basic HTML structure parsing (nested elements, attributes, text content)
- [x] 11.2 Test void elements (`<br>`, `<img>`, `<input>`, `<hr>`, `<source>`, etc.) and self-closing syntax
- [x] 11.3 Test boolean attributes (bare `disabled`, `disabled=""`, `disabled="disabled"`)
- [x] 11.4 Test HTML comments (skipping, nested content)
- [x] 11.5 Test REJECTED_TAGS rejection (`<script>`, `<style>`, etc.)
- [x] 11.6 Test `{{ }}` splitting in text and attribute values (literal/hole parts)

## 12. Unit Tests — Binding

- [x] 12.1 Test text interpolation with Signal, str, int, None, Element, Component values
- [x] 12.2 Test dot notation resolution (dict access, object attribute access, chained)
- [x] 12.3 Test attribute evaluation: single Signal in attribute (Computed + DOM reactive update), mixed literal+Signal, multiple Signals, no-Signal static path, integer/bool static
- [x] 12.4 Test event handler binding (`@click`, multiple handlers)
- [x] 12.5 Test DomNodeRef binding (`:ref`)
- [x] 12.6 Test missing variable error (KeyError with available names)

## 13. Unit Tests — Integration

- [ ] 13.1 Test `render_template` end-to-end with real component setup
- [ ] 13.2 Test `locals()` usage pattern
- [ ] 13.3 Test compile cache (same string → cache hit, different → cache miss)
- [ ] 13.4 Test `textwrap.dedent` behavior with indented triple-quoted strings
- [ ] 13.5 Test root element validation (single root OK, multiple roots error, whitespace trimming)
- [ ] 13.6 Test lenient unknown tag handling (`<widget>` → `Element("widget", ...)`)

## 14. Spike

- [ ] 14.1 Verify `html.parser.HTMLParser` functionality in PyScript/Emscripten environment

## 15. SSR & Hydration

- [ ] 15.1 Test `render_app_html_sync(app)` with a template-based component — verify SSR HTML output contains expected text and element structure from `{{ }}` interpolation
- [ ] 15.2 Test `TestRenderer.render(component)` — verify prerendered `__webcompy_prerendered_node__` flag is set on text nodes from Signal interpolation
- [ ] 15.3 E2E: add a template-based demo page under `e2e/core/` using `static_site` fixture — verify (a) pre-rendered HTML matches the template structure, (b) hydration payload includes transferred Signal values, (c) after browser load, changing a Signal value updates the corresponding DOM text node

## 16. CI Review Update

- [ ] 16.1 Update `.opencode/agents/ci-review.md`: add template engine patterns (HTMLParser-based AST compilation, `HOLE_PATTERN`, `resolve_var`, `render_template` / `_render_nodes`)
- [ ] 16.2 Update `AGENTS.md` File->Spec Mapping: `webcompy/template/` -> `template-engine` spec

## 17. Future Enhancement — Cache Eviction

- [x] 17.1 Add eviction policy (`functools.lru_cache` or size cap) to `_template_cache` in `_cache.py` for long-running dynamic-template workloads

## 18. Main Spec Generation (Archive Time)

- [ ] 18.1 Before archiving this change, sync its delta spec to `openspec/specs/template-engine/spec.md` via the standard OpenSpec archive workflow. Each template-engine change syncs its own delta incrementally; later changes' MODIFIED/REMOVED/RENAMED sections supersede the corresponding earlier requirements.
