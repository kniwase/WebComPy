# Design: refactor-markdown-inline-parser

## Context

After `refactor-markdown-block-parser`, leaf blocks hand their text content to an inline renderer through a narrow seam (a function reference the block facade calls). This change replaces that renderer. The legacy implementation is sequential regex substitution with placeholder tokens — proven order-dependent (nested-marker corruption) and structurally unable to implement delimiter-run emphasis, which CommonMark defines as a stack-matching process, not a pattern.

The conformance harness defines the goal precisely: every remaining strict xfail is inline-caused; this change empties the list.

## Goals / Non-Goals

**Goals:**
- CommonMark-conformant inline parsing, including the full emphasis/strong delimiter algorithm.
- GFM strikethrough, extended autolinks, disallowed raw HTML.
- Full GFM spec-suite pass (zero xfails) plus green template-integration tests.
- Template-syntax protection (`{{ }}`/`{% %}` literal inside code) preserved with equivalent-or-better semantics.

**Non-Goals:**
- Block-level work, non-GFM extensions, `MarkdownPort` interface changes, performance work beyond linear-time guarantees.

## Decisions

### D1. Two-pass inline parser: scan to tokens, then process delimiters

Implement the reference approach: (1) scan the string left-to-right emitting a node list — text runs, code spans (matched variable-length backticks), raw HTML, autolinks, backslash escapes, entity references (resolved via `html.entities.html5`), hard/soft breaks, and *delimiter runs* for `*`, `_`, `~` plus link-opener brackets; (2) walk the delimiter stack matching openers/closers per the CommonMark rules (including the "odd multiple of 3" rule and intraword `_` restrictions), building `<em>`/`<strong>`/`<del>`; (3) process brackets bottom-up for links/images.

- **Why**: delimiter runs are the only conformant way to resolve `*a **b** c*`, `***x***`, intraword underscores, and arbitrary nesting — the exact class that defeated the regex approach.
- **Alternative considered**: porting an existing pure-Python parser's inline engine — rejected (project decision: no new dependency; ownership of the security-sensitive escaping/URL logic is preferred).

### D2. Link destination/title parsing per the spec state machines

Inline destinations: `<...>` form or balanced-parens form (nested balanced parens allowed, escaped parens, no unescaped spaces); titles in `"..."`, `'...'`, or `(...)`. Reference resolution uses the block layer's definition table with CommonMark label normalization (case-fold, whitespace collapse). Full → collapsed → shortcut precedence per spec.

### D3. Security policies compose at the end of link construction

Every link/image/autolink/extended-autolink passes the final destination through the existing allow-list (`http:`, `https:`, `mailto:`, relative, `#fragment`, plus bare `www.`→`http://` per GFM). Disallowed schemes render as literal text (no element) — identical outcome to the current policy, now covering all link forms.

- **GFM disallowed raw HTML**: tags in GFM's filtered list (`title`, `textarea`, `style`, `xmp`, `iframe`, `noembed`, `noframes`, `script`, `plaintext`) are entity-escaped (leading `<` → `&lt;`) when they appear as inline HTML or HTML blocks of types 2-7. HTML blocks of **type 1** (`<script>`, `<pre>`, `<style>`, `<textarea>` raw-text containers) pass through verbatim: the GFM spec suite pins verbatim output for those examples, so filtering them would break conformance. Consequently Markdown→HTML output CAN contain `<script>`/`<style>`/`<textarea>` raw when they open a type-1 block; the template binding layer rejects `script`/`style`/`iframe`/`noembed`/`noframes`/`xmp` (raises at bind time), but `<textarea>`/`<title>`/`<plaintext>` type-1 blocks are not rejected by the binding layer and flow into the DOM — a residual raw-HTML surface that requires a downstream HTML sanitizer for untrusted Markdown.

### D4. Template-syntax protection via tokenization, replacing placeholders

In the new architecture, code spans and code-block content never enter inline parsing — their text is emitted verbatim (HTML-escaped). `{{`/`{%` protection therefore becomes structural: nothing to protect, because nothing interprets. The placeholder machinery from `fix-template-engine-defects` is removed; the *tests* it introduced are kept and must pass unchanged (plus new cases: `{% for %}` inside code spans, adjacent code spans with template syntax).

- **Why remove placeholders**: they existed to survive a pipeline that re-scanned code content; the real parser never re-scans it. Fewer moving parts, no spoofing surface.
- **Verified invariant**: `render_markdown` context values must never appear inside `<code>`/`<pre>` output.

### D5. Entities resolved in text, preserved in URLs, never inside code

Named (`&copy;`) and numeric (`&#65;`, `&#x41;`) references resolve per spec in normal text using stdlib `html.entities.html5` (Pyodide-available); in link destinations/titles they are resolved per spec rules; inside code spans/blocks they stay literal. HTML-escaping of literal `&`/`<` in text stays correct (escape-then-resolve ordering per spec).

### D6. Hard/soft breaks and GFM strikethrough/autolinks as first-class scan tokens

Trailing-two-spaces and backslash breaks → `<br>`; single newlines → soft-break newline (matching GFM expected output). Strikethrough uses the delimiter machinery with `~` runs (one or two tildes per GFM). Extended autolinks (`www.`, bare scheme URLs, emails) are recognized in the scan with GFM's boundary/trailing-punctuation trimming rules, then pass through D3's allow-list.

### D7. docs_app limitations page written last, against final behavior

A docs page (English, matching docs_app conventions) documents the intentional limitations codified in `test-template-conformance-harness` plus the Markdown feature matrix (supported GFM constructs, and non-goals like footnotes). Written only after the parser is final so examples are verified against reality.

## Risks / Trade-offs

- [Delimiter algorithm subtlety (odd-multiple-of-3 rule, intraword `_`)] → Implement the spec pseudocode literally; spec examples are the arbiter; add property-style tests comparing against the vendored suite sections.
- [Underscore emphasis activation renders existing `_snake_case_` content differently] → Intraword rules make `foo_bar_baz` safe; BREAKING note in PR covers `_leading/trailing_` cases.
- [Removing the placeholder mechanism regresses template protection] → Kept tests + D4's invariant check; additionally fuzz code content containing `{{`/`{%` combinations.
- [Linear-time guarantee vs. pathological inputs] → Delimiter processing is stack-based (linear); add adversarial-input tests (long delimiter seas, deep bracket nesting) with a generous but finite time budget.
- [Extended autolinks' boundary rules (trailing punctuation trimming)] → Follow GFM's explicit rules; their spec examples cover the edge cases.

## Migration Plan

BREAKING items (underscore emphasis, hard breaks, conformant nesting) change rendered output, not APIs. PR includes a migration note: audit Markdown sources for `_`-adjacent words and trailing double spaces used as intentional line joins. docs_app is regenerated and diff-reviewed as part of the change.

## Open Questions

1. Soft-break rendering (newline vs space) follows GFM expected output (newline) — confirm no downstream `render_template` whitespace sensitivity (checked during integration).
2. Whether extended autolinks apply inside `<a href>`-producing reference links (they don't per spec — autolinks are a separate construct; no action, noted to avoid confusion).
