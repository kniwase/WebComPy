# Proposal: feat-markdown-document-support

## Why

The docs_app documentation section (`/documents`) is currently a "Work In Progress" stub, and we want to author documentation pages in Markdown. WebComPy already renders Markdown via `render_markdown`, but the output lacks everything long-form documentation needs: heading anchors, a table of contents, syntax-highlighted code blocks, and a typography stylesheet. In addition, page metadata (title, ordering, section) has no home — Markdown documents need frontmatter support so a single `.md` file can carry both content and metadata.

## What Changes

- Add **frontmatter parsing** for Markdown documents:
  - `---` delimited blocks: flat `key: value` pairs parsed into string metadata
  - `+++` delimited blocks: TOML parsed via stdlib `tomllib` into structured metadata (`dict[str, Any]`), supporting nested tables and arrays
- Add **opt-in post-bind document transforms** to `render_markdown` (default output remains byte-exact cmark-gfm conformant):
  - `heading_ids`: inject slugified `id` attributes into `<h1>`–`<h6>` elements
  - `code_blocks`: replace `<pre><code class="language-*">` subtrees with `CodeBlock` components for syntax highlighting
  - `classes`: inject a tag→CSS-class map into rendered elements
- Add a high-level async utility **`load_markdown_document()`** that loads a Markdown resource (via `load_text` / `ResourcePort`), splits frontmatter, renders the body with the document transforms, extracts a table of contents, and returns a `MarkdownDocument` dataclass (`content`, `metadata`, `toc`). Parents consume it in `async def` component setup (e.g. `context.set_title(doc.metadata["title"])`), so SSR/SSG `<title>` output is deterministic.
- Add a **`prose.css` typography preset** to `webcompy/ui/_styles/`, registered in `_STYLES_FILES` and served opt-in at `/_webcompy-ui/prose.css`, styled under a `.prose` wrapper class and themed via existing `tokens.css` CSS variables (light/dark aware).

## Capabilities

### New Capabilities

- `markdown-document`: Frontmatter formats (`---` flat, `+++` TOML), the `load_markdown_document()` async utility and `MarkdownDocument` result type, TOC extraction, and the opt-in `prose.css` typography preset.

### Modified Capabilities

- `template-engine`: `render_markdown` gains opt-in document-oriented options (`heading_ids`, `code_blocks`, `classes`). Default behavior is unchanged; the conformance-pinned HTML output of `DefaultMarkdownParser` is untouched.

## Impact

- **Code**: `packages/webcompy/src/webcompy/template/` (new document/frontmatter/transform modules, `render_markdown` signature), `packages/webcompy/src/webcompy/ui/_styles/` (new `prose.css`, `_STYLES_FILES` registration), public exports in `webcompy/template/__init__.py`
- **APIs**: additive only — `render_markdown(..., heading_ids=..., code_blocks=..., classes=...)`, new `load_markdown_document()`, new `MarkdownDocument` type
- **Dependencies**: none added (TOML via stdlib `tomllib`; works on Pyodide since it is pure Python)
- **Specs**: new `markdown-document` spec; delta to `template-engine`; `markdown-conformance` untouched (defaults unchanged — conformance suite must keep passing)
- **Follow-up changes**: docs_app documentation layout/pages and content changes build on this capability (separate changes)

## Known Issues Addressed

None.

## Non-goals

- Full YAML frontmatter support (anchors, flow collections, multi-line scalars) — TOML covers structured metadata needs with zero new dependencies
- Changes to `DefaultMarkdownParser` HTML output or GFM conformance behavior
- File-system-based automatic routing for Markdown pages (docs pages will be registered as explicit routes in a later docs_app change)
- Search, versioning, i18n, or prev/next navigation for the docs site (later docs_app changes)
- Scoped-slot-style child-to-parent metadata flow — metadata is consumed via the `load_markdown_document()` return value in the parent's async setup
