# Proposal: refactor-markdown-inline-parser

## Why

With the block layer rebuilt on the CommonMark algorithm (`refactor-markdown-block-parser`), the remaining conformance failures are all inline-level: the current inline implementation processes constructs by sequential regex substitution, which cannot implement delimiter-run emphasis (the core of CommonMark inline parsing), mangles nested/nearby markers, and lacks entire feature classes (reference links, autolinks, entities, hard breaks, escaping). This change replaces the inline layer with a delimiter-stack inline parser, adds the remaining GFM inline extensions, and brings the conformance suite to full pass — completing the GFM conformance goal.

## What Changes

- **Rewrite the inline layer** as a character-scanning inline parser per the CommonMark algorithm: backslash escapes, entity/numeric references (stdlib `html.entities`), code spans (variable-length backtick strings), raw inline HTML, autolinks (`<scheme:...>`, `<email>`), links/images (inline destinations with balanced parens and optional titles, full and collapsed reference links via the block-layer definition table), and emphasis/strong via the delimiter-run algorithm (`*` and `_`, intraword rules, arbitrary nesting incl. `***`).
- **BREAKING**: Underscore emphasis (`_em_`, `__strong__`) becomes active per CommonMark intraword rules (`foo_bar_baz` stays literal); previously `_` was inert.
- **BREAKING**: Hard line breaks (trailing two spaces or backslash) now produce `<br>`; hard-to-predict paragraph rendering differences are possible for sources relying on space-collapsing.
- Add **GFM strikethrough** conformantly (one or two `~` delimiters, replacing the current regex-only `~~` handling), **GFM extended autolinks** (`www.`, bare URLs, email addresses — with the existing URL scheme allow-list applied after extension), and **GFM disallowed raw HTML** filtering aligned with the template layer's rejected-tags policy.
- **Port the `{{ }}`/`{% %}` template protection** introduced in `fix-template-engine-defects` to the new parser: code spans and code blocks keep template syntax literal (placeholder mechanism or a cleaner equivalent enabled by the real parser).
- Preserve the URL scheme allow-list (`http`/`https`/`mailto`/relative/fragment) across all new link forms (inline, reference, autolink, extended autolink).
- Resolve link/image titles and parenthesized destinations correctly; parse multi-backtick code spans.
- Remove remaining `gfm_deviation` tests, flip all remaining strict xfails to reach **full GFM spec-suite pass**, and update docs_app with the template-engine limitations page (final state).

### Non-goals

- Block-structure changes (done in `refactor-markdown-block-parser`).
- Reactive task-list checkboxes, footnotes, definition lists, heading anchors/IDs, or other non-GFM extensions.
- Performance optimization beyond linear-time parsing guarantees (no catastrophic regex backtracking).
- Changes to the `MarkdownPort` interface or the `render_markdown` reactive pipeline semantics.

## Known Issues Addressed

- Retires the inline half of the cataloged Markdown deviations: delimiter-run emphasis, `***`, underscore rules, backslash escapes, link titles/parens, reference links, autolinks, multi-backtick code spans, entity references, hard breaks, inline raw HTML passthrough, and strikethrough conformance — completing the conformance program started in the audit.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `template-engine`: Inline-level Markdown requirements replaced wholesale (emphasis/strong, code spans, links/images/autolinks, entities, escapes, hard breaks, raw HTML) and extended with GFM strikethrough, extended autolinks, and disallowed raw HTML; template-syntax protection re-specified against the new parser.
- `markdown-conformance`: Conformance goal updated to full pass; deviation list emptied.

## Impact

- **Code**: new `packages/webcompy/src/webcompy/template/_markdown_inline.py`; seam usage in `webcompy/template/_markdown_default.py`; protection-mechanism port (touching `template/__init__.py` only if the placeholder strategy changes).
- **Specs**: `template-engine`, `markdown-conformance`.
- **Tests**: `tests/test_markdown_parser.py` (deviation tests removed), `tests/conformance/` (xfail list emptied), new inline-focused unit tests.
- **docs_app**: new "Template engine limitations" page; Markdown-feature docs updated to final state.
- **Breaking surface**: underscore emphasis activation, hard breaks, and conformant emphasis nesting can alter rendering of existing Markdown sources (spec-conformantly).
