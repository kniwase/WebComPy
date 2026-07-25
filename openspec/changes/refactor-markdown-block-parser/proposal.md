# Proposal: refactor-markdown-block-parser

## Why

`DefaultMarkdownParser` parses blocks line-by-line in a single regex-driven pass. The conformance harness (`test-template-conformance-harness`) makes the cost of that design measurable: container structures (nested blockquotes, lists with block children, loose lists), CommonMark tab handling, setext headings, and the GFM block extensions (tables, task list items) cannot be bolted onto a one-pass line scanner without compounding the fragility already demonstrated by the defect audit. This change replaces the block-structure layer with the standard CommonMark Phase 1 algorithm (container stack + leaf blocks), on which the inline rewrite (`refactor-markdown-inline-parser`) then builds.

## What Changes

- **Rewrite the block layer** of `DefaultMarkdownParser` as a container/leaf two-phase parser per the CommonMark appendix algorithm: blockquote and list containers with lazy continuation; leaf blocks for ATX/setext headings, fenced and indented code, thematic breaks, HTML blocks, paragraphs, and link reference definitions.
- **BREAKING**: Tab handling becomes CommonMark-conformant (tabs advance to the next 4-column stop with partial-tab support); the current tab→2-spaces normalization is removed, which also stops corrupting tabs inside fenced code.
- **BREAKING**: Setext headings are recognized — `Title\n---` now yields `<h2>Title</h2>` instead of `<p>Title</p><hr>`, and `Title\n===` yields `<h1>` instead of a paragraph.
- **BREAKING**: Space-less ATX headings (`#hashtag`) are no longer headings (CommonMark requires a space); fenced-code info strings are captured as `class="language-*"` on `<code>` (previously discarded); indented code blocks are supported.
- Add **GFM tables** (delimiter-row detection, alignment via `align` attributes or styles per GFM output, inline parsing of cell contents).
- Add **GFM task list items** (`- [ ]` / `- [x]` → static `<input type="checkbox" disabled [checked]>` at the start of the `<li>`; no reactivity).
- Re-verify the **`{% for %}` list-body pipeline** (`MarkdownForElement` pre-expansion) against the new parser: the for-body list detection heuristics are aligned with the real list grammar so expanded Markdown parses identically to hand-written Markdown.
- Remove the `gfm_deviation`-marked block-level tests and flip the corresponding strict xfails in the conformance suite.

### Non-goals

- Inline parsing (emphasis delimiter runs, code spans, links/images, entities, hard breaks, raw inline HTML, autolinks, strikethrough, disallowed raw HTML) — all in `refactor-markdown-inline-parser`. The current inline implementation is carried over unchanged as the leaf-content renderer for this change.
- Changes to the `{{ }}`/`{% %}` template-protection mechanism introduced in `fix-template-engine-defects` (code blocks stay protected; the mechanism is re-validated, not redesigned).
- `MarkdownForElement` architecture changes beyond detection-heuristic alignment.
- docs_app documentation updates.

## Known Issues Addressed

- Retires the block-level half of the cataloged Markdown deviations measured by the conformance harness (setext, closing ATX hashes, `~~~` fences, indented code, blockquote nesting/laziness, loose lists, list-internal block elements, tab corruption of code content).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `template-engine`: Block-level Markdown requirements replaced wholesale (headings, code blocks, blockquotes, lists, thematic breaks, HTML blocks, link reference definitions) and extended with GFM tables and task list items; tab handling re-specified; fence info strings re-specified.
- `markdown-conformance`: Block-section xfail entries are flipped as they pass; deviation list updated to remove retired items.

## Impact

- **Code**: `packages/webcompy/src/webcompy/template/_markdown_default.py` (block layer rewritten; module likely split, e.g. `_markdown_blocks.py`), `packages/webcompy/src/webcompy/template/_markdown_for.py` (detection alignment).
- **Specs**: `template-engine`, `markdown-conformance`.
- **Tests**: `tests/test_markdown_parser.py` (deviation tests removed/replaced), `tests/conformance/` (xfail flips), `tests/test_markdown_for.py` (integration re-verification).
- **Breaking surface**: Markdown sources relying on tab→2-spaces, `Title\n---` as `<hr>`, `#hashtag` headings, or discarded fence languages render differently (spec-conformantly).
