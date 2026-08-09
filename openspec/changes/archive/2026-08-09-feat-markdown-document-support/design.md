# Design: feat-markdown-document-support

## Context

WebComPy renders Markdown through a two-phase, hand-written GFM parser (`DefaultMarkdownParser`) whose HTML output is re-parsed into reactive `Element` trees by `render_markdown`. The `markdown-conformance` spec pins this HTML output to byte-exact cmark-gfm compatibility (654 passing spec examples, strict-xfail regime), so the parser's default output cannot change.

For the docs site we need documentation-grade Markdown: heading anchors, TOC, highlighted code, typography styling, and per-page metadata. Investigation confirmed:

- `render_markdown(source, context)` today takes no options; no class/attribute injection exists.
- Fenced code renders as plain `<pre><code class="language-*">`; `webcompy.ui.code_block` already provides `CodeBlock` / `highlight()` with Python/Bash/TOML lexers.
- Heading elements render with no `id`; no TOC extraction utility exists, but element-tree walks have precedents (`SuspenseElement._collect_pending_coroutines`, `_subtree_has_async_setup`).
- `webcompy.resources.load_text` works in both environments; `ServerResourcePort` records SSR reads into the hydration payload, so Markdown loaded during SSR/SSG does not refetch in the browser.
- `context.set_title(str)` takes a plain string; async component setup (`async def` + `await`) is a first-class, spec-blessed pattern.
- WebComPy slots are argument-less (`NodeGenerator`); there is no scoped-slot mechanism for child→parent data flow.
- `ui/_styles/` registration is a single allow-list (`_STYLES_FILES`); dev server, SSG copy, and 404 guards all iterate it.

## Goals / Non-Goals

**Goals:**

- Author docs pages as `.md` files with frontmatter carrying page metadata (`title`, ordering, etc.).
- One async call (`load_markdown_document`) yields content element tree + metadata + TOC, consumable in `async def` component setup so SSR/SSG `<title>` is deterministic.
- All document-oriented rendering differences are opt-in; default Markdown behavior and conformance are untouched.
- Typography preset (`prose.css`) is opt-in, theme-aware via existing CSS variables, zero new dependencies.

**Non-Goals:**

- YAML frontmatter (any form), YAML parser implementation.
- Parser-level or `DefaultMarkdownParser` output changes.
- File-based automatic routing; docs_app layout/sidebar/content (separate changes).
- New external dependencies.

## Decisions

### 1. Post-bind transform layer instead of parser hooks

All document features (heading ids, code block replacement, class injection) operate on the `Element` tree **after** `render_markdown`'s HTML parse/bind phase, as opt-in transforms.

- **Why**: `markdown-conformance` pins `DefaultMarkdownParser` HTML byte-for-byte; any parser change risks the strict-xfail regime. Post-bind transforms leave parser and conformance untouched by construction.
- **Alternative rejected**: pluggable renderer callbacks in `_markdown_blocks._render()` — cleaner output control, but couples document features to parser internals and risks conformance drift.
- **Alternative rejected**: post-processing the HTML string with regex — fragile, duplicates parsing already done by the template parser.

`render_markdown` grows optional keyword arguments (`heading_ids`, `code_blocks`, `classes`) that apply these transforms before returning. Each transform is also a standalone function (e.g. `apply_heading_ids(element) -> None`, `replace_code_blocks(element) -> None`) so `load_markdown_document` composes them without re-parsing.

### 2. Frontmatter: flat `---` and TOML `+++`, no YAML

- `---` blocks parse as flat `key: value` lines (strings only).
- `+++` blocks parse as TOML via stdlib `tomllib` (nested tables, arrays, typed scalars).
- Both produce `dict[str, Any]`; the flat parser's values are all `str`.
- **Why**: Python has no stdlib YAML parser; `tomllib` is stdlib (3.11+), pure Python, and runs on Pyodide unchanged. TOML is idiomatic in the Python ecosystem (`pyproject.toml`). Hugo's `+++` TOML frontmatter is prior art.
- **Alternative rejected**: hand-rolled YAML subset (nested maps, sequences, scalars) — feasible (300–500 lines) but the YAML long tail (flow style, multiline scalars) guarantees user-facing gaps; maintenance cost is unjustified for metadata.
- **Alternative rejected**: PyYAML dependency — adds browser bundle weight and a dual-environment dependency for a solved problem.

Parsing lives in `webcompy/template/_frontmatter.py`: `split_frontmatter(source) -> tuple[dict[str, Any], str]` detects the delimiter on the first line, returns `(metadata, body)`. Malformed frontmatter raises `WebComPyException` naming the document problem (per `error-handling` spec conventions).

### 3. Metadata flows via return value, not component/child-to-parent channels

`load_markdown_document(path, ...)` is an **async utility**, not a component:

```python
@define_component
async def GettingStartedPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("docs/getting-started.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return html.ARTICLE({"class": "prose"}, doc.content)
```

- **Why**: metadata is available synchronously within the parent's async setup, before the tree is returned — so `set_title` lands in SSR/SSG HTML. This mirrors the already-blessed `render_markdown(await load_text(...), ctx)` pattern.
- **Alternatives rejected**:
  - Callback prop / shared `Signal` written by a child component — value arrives after parent setup; SSR `<title>` timing is fragile; violates props-down.
  - Scoped slots (render props) — WebComPy slots take no arguments; extending the slot system is out of scope.
  - DI provide from child — DI flows downward only.

Returns a frozen dataclass `MarkdownDocument(content: ElementAbstract, metadata: Mapping[str, Any], toc: tuple[HeadingInfo, ...])` where `HeadingInfo` carries `level: int`, `text: str`, `id: str`.

### 4. TOC extraction and slug generation on the element tree

- Walk `_children` (and `_pending_children` for unmounted `FragmentElement`s) recursively, following the defensive `hasattr` walk pattern from `_suspense.py`.
- Heading text is collected from descendant `TextElement`s; `Computed`-wrapped text (from `{{ }}` interpolation) resolves to its current value.
- Slugs: Unicode-aware lowercase, whitespace→`-`, strip non-alphanumeric except `-`; duplicates get `-2`, `-3` suffixes (cmark-gfm/GitHub-style), deterministic per document.
- Ids and TOC come from the same walk so they can never disagree.

### 5. Code block replacement reuses `CodeBlock`

Post-bind walk finds `Element(tag="pre")` whose sole significant child is `<code class="language-{lang}">`, extracts the literal code text, and swaps the subtree for `CodeBlock({"code": text, "lang": lang})`.

- **Why**: reuses existing lexers, theming (`tok-*` classes + `syntax-theme.css`), and the reactive-capable component; no new highlighting path.
- Template-safety is preserved: the parser's `protect_lbrace` guarantee means code content never entered template processing, and replacement happens after binding regardless.

### 6. `prose.css` as opt-in separate stylesheet under `.prose` wrapper

- New `packages/webcompy/src/webcompy/ui/_styles/prose.css`, registered in `_STYLES_FILES` (dev server route, SSG copy, and guards pick it up automatically).
- Loaded explicitly by apps (head link to `/_webcompy-ui/prose.css`); **not** `@import`ed by `index.css` — zero impact on existing apps.
- All rules scoped under `.prose` descendants (`.prose h1`, `.prose table`, …) and wrapped in `@layer prose` so apps can override predictably; colors/spacing reference `tokens.css` variables for light/dark theme continuity.
- Covers: headings (with anchor link affordance styling), paragraphs, lists, tables, blockquotes, `hr`, inline `code`, and spacing rhythm. Fenced code blocks are styled by the existing `code-block.css` once `code_blocks=True` swaps in `CodeBlock`.
- **Alternative rejected**: always-on import in `index.css` — risks restyling existing apps' raw Markdown output; opt-in matches the "document features are opt-in" principle.

### 7. Module layout

- `webcompy/template/_frontmatter.py` — delimiter detection + flat/TOML parsing
- `webcompy/template/_markdown_transforms.py` — tree walk, `apply_heading_ids`, `replace_code_blocks`, `apply_class_map`, `collect_headings`, slugify
- `webcompy/template/_markdown_document.py` — `MarkdownDocument`, `HeadingInfo`, `load_markdown_document`
- Public exports from `webcompy.template`: `load_markdown_document`, `MarkdownDocument`, `HeadingInfo` (plus `render_markdown` option types in `__all__` as needed)

## Risks / Trade-offs

- [Post-bind walk misses exotic trees (SwitchElement inside Markdown, unmounted fragments)] → Walk handles `_children` + `_pending_children` defensively; transforms are best-effort on `Element` nodes and skip dynamic subtrees they cannot statically inspect; unit tests cover `{% if %}`/`{% for %}` bodies.
- [Duplicate or non-ASCII heading text produces unstable anchors] → Deterministic dedupe suffixes; Unicode-aware slug keeps CJK headings addressable; documented behavior.
- [Reactive headings change text after TOC extraction] → TOC/slug snapshot at setup; documented that reactive heading text is not re-indexed (docs content is static in practice).
- [`tomllib` unavailable or slow on Pyodide] → It is pure Python and ships with Pyodide's stdlib; parsing happens on small frontmatter blocks only; verified in E2E once docs_app consumes it.
- [`.prose` class name collides with user CSS] → Opt-in stylesheet and opt-in wrapper class; collision only matters if the app itself adopts `.prose`.
- [Transform options grow `render_markdown`'s signature] → Keyword-only arguments with defaults preserving current behavior; no positional changes.

## Migration Plan

Purely additive. No existing call sites change; conformance suite must pass unmodified. Rollback = revert the commit; no persisted state or output-format commitments exist yet (docs_app adoption comes in later changes).

## Open Questions

None blocking. Anchor-link UX (scroll behavior when clicking TOC entries) interacts with `scroll-restoration` and is deferred to the docs_app layout change.
