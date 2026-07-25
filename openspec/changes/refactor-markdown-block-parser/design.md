# Design: refactor-markdown-block-parser

## Context

After `test-template-conformance-harness`, the project has an objective GFM conformance suite with every failure tracked as a strict xfail. This change is the first of two rewrites that burn that list down. It covers everything CommonMark calls Phase 1: turning raw text into a block tree. The inline layer (Phase 2) is deliberately untouched — the existing inline implementation continues to render leaf content, and is replaced in the follow-up change. This split keeps each rewrite reviewable and maps cleanly onto the spec test sections (block sections vs inline sections).

The current parser (`_markdown_default.py`) is a single line loop with per-line regex dispatch. Its structural limits are proven: containers cannot nest, list items cannot hold block children, tabs are destroyed globally (including inside code), and paragraph continuation cannot look ahead for setext underlines.

## Goals / Non-Goals

**Goals:**
- CommonMark-conformant block structure: containers (blockquotes, lists/list items) with arbitrary nesting and lazy continuation; all leaf blocks including setext headings, indented code, and link reference definitions.
- GFM tables and task list items.
- All block-section strict xfails in the conformance suite flipped (headings, tabs, block quotes, lists, code blocks, HTML blocks, link reference definitions, thematic breaks, tables, task list items).
- `{% for %}` Markdown pipeline keeps working with detection heuristics aligned to the real grammar.

**Non-Goals:**
- Any inline-level conformance work.
- Performance tuning beyond avoiding pathological backtracking (regexes used only for line classification, not nesting).
- Changing the `MarkdownPort` interface (`render(str) -> str` stays).

## Decisions

### D1. Implement the reference two-phase block algorithm, not a custom variant

Follow the CommonMark appendix strategy: maintain an open-block stack; for each line, (1) descend the stack checking continuation, (2) optionally start new children (block start condition functions in priority order: blockquote → ATX heading → fenced code → HTML block → setext underline → thematic break → list item → indented code), (3) add the line to the deepest open block; then walk unmatched open blocks to incorporate lazily-continued lines; finalize blocks bottom-up.

- **Why**: the deviation list (nested quotes, lazy continuation, loose lists, list-internal blocks, tab stops) is exactly the set of behaviors that ad-hoc parsers get wrong; the reference algorithm is specified precisely enough to implement without invention, and the spec suite validates it directly.
- **Alternative considered**: incremental patches to the line loop — rejected; the audit already showed regex-ordering fragility, and containers fundamentally need a stack.

### D2. Tab expansion via offset tracking, never destructive rewriting

Columns are tracked with a `(offset, column)` cursor; advancing past a tab jumps to the next multiple of 4 and records a *partial tab* when a block boundary falls mid-tab (per spec). Source text is never pre-normalized.

- **BREAKING accepted**: the current tab→2-spaces rule (which also corrupts fenced-code content) is removed. Markdown authored for the old rule may re-indent; the conformance suite and docs examples are checked during implementation.

### D3. Module split: `_markdown_blocks.py` for structure, `_markdown_default.py` stays the facade

The block parser (~container tree + finalizers) lives in a new module; `DefaultMarkdownParser.render()` orchestrates: pre-expansion hooks (unchanged), block parse, inline render of leaf content (existing inline code, called through a narrow function reference so the inline rewrite can swap it), HTML emission.

- **Why**: the follow-up inline change then touches only the inline module and the facade seam — smaller diffs, independent review.

### D4. Setext detection lives in paragraph finalization

A paragraph whose last line matches a setext underline is converted to a heading at finalization (standard approach). This subsumes the old `Title\n---` → `<hr>` behavior — **BREAKING**, flagged in the proposal.

### D5. HTML blocks keep the existing template-aware constraints

All seven CommonMark HTML block types are recognized for block-boundary purposes. The template layer's rejection of `<script>`/`<style>`/etc. remains a *binding-layer* policy (unchanged); the Markdown layer emits HTML per spec. Multi-line comments/`<?`/`!` declarations now pass through correctly (fixing the single-line-only passthrough).

### D6. GFM tables as a leaf block parsed at paragraph finalization

A paragraph whose first line contains a pipe and whose second line is a valid delimiter row is re-parsed as a table: header cells, alignment from delimiter colons, row splitting on unescaped pipes (with `\|` and code-span awareness deferred to the inline layer's escaping, applied when cells are inline-rendered).

- **Why finalization**: table detection requires lookahead over the paragraph, exactly like setext — the reference GFM approach.

### D7. Task list items as a list-item content transform

At list-item finalization, a leading `[ ]`/`[x]`/`[X]` marker (per GFM rules: after the bullet, followed by whitespace) is converted to `<input type="checkbox" disabled="" [checked=""]> ` at the start of the item's first paragraph — static HTML, no reactivity, matching the GFM output shape.

- Interaction with the template binder is safe: `<input>` is a void element and boolean attributes are supported.

### D8. Fence info strings captured, first word only, entity-decoded

`<code class="language-{first-word}">` per CommonMark/GFM. **BREAKING**: previously discarded. `~~~` fences supported alongside ``` ``` fences.

### D9. `{% for %}` detection aligned to the real list grammar

`_markdown_for._is_list_body` currently uses its own marker regex; it is re-pointed at the block parser's list-item start condition (single source of truth). `MarkdownForElement`'s merged-list output is re-verified end-to-end: expanded bodies (list items + nested for + static if) must parse under the new block parser to the same merged `<ul>`/`<ol>` structure as before, with `+` markers now uniform.

- **Risk containment**: `test_markdown_for.py` runs unchanged where possible; semantic changes (e.g. tab handling) get dedicated new tests.

### D10. Link reference definitions parsed (used by the inline change)

Block Phase 1 must recognize and *absorb* link reference definition paragraphs (they produce no output). The parsed table is stored on the parse result so the inline rewrite can resolve reference links; this change only guarantees definitions no longer leak into output as paragraph text.

### D11. `textwrap.dedent` is applied to multi-line sources only

`textwrap.dedent` on a single-line source strips *all* leading whitespace (the whole prefix is "common"), which destroys conformance-relevant indentation (`"\tfoo"` → `"foo"`). This is also one of the mechanisms by which the old parser corrupted tabs. Therefore: `render()`/the block parser applies `textwrap.dedent` **only when the source contains a newline**; single-line sources are parsed as-is. The delta spec scenario wording ("`textwrap.dedent` SHALL be applied to the source before parsing") SHALL be amended at spec-sync time to reflect this.

### D12. Implementation strategy: structural port of the reference block parser

The block layer SHALL be implemented as a **structural port of the reference two-phase algorithm** (the CommonMark appendix strategy, as embodied by commonmark.js / commonmark.py `blocks.py`), not written from memory or as a custom variant. Concretely:

- Read the reference implementation (`commonmark.py` `blocks.py`, ~600 lines — https://github.com/readthedocs/commonmark.py/blob/master/commonmark/blocks.py, fetchable read-only via web_fetch) and the vendored `spec.txt` prose sections (Tabs, Block quotes, List items, Lists, Appendix) **before writing code**. An earlier implementation attempt that drafted the driver from memory produced two discarded drafts; that approach is explicitly rejected.
- Port the structure: `Parser.incorporate_line` (continuation descent → lazy continuation → block-start priority loop → line incorporation), per-kind `continue_`/`finalize`/`can_contain` operations, `parse_list_marker` (W+N padding rules), `lists_match`, `ends_with_blank_line`-based tight/loose determination, and the `advance_offset`/`find_next_nonspace` cursor with partial tabs. Port the *structure and rules*, not verbatim code; adapt to the WebComPy `_Block` model and the narrow inline seam (D3).
- commonmark.py lacks GFM extensions: tables (D6) and task list items (D7) are added on top per their spec.txt examples. Its HTML-block type 1 lacks `textarea` (older spec) — use the GFM `spec.txt` tag lists instead.
- Validation is example-driven: after each block kind lands, run the matching spec.txt section through the conformance harness and confirm the expected flips before proceeding.
- The reference's NUL-replacement (`\0` → U+FFFD) is ported as-is (input sanitization).

## Risks / Trade-offs

- [Big-bang rewrite of the block layer regresses template integration] → The conformance suite + existing `test_markdown*.py` + `webcompy generate` on docs_app form the regression net; integration tests run before and after.
- [Lazy continuation + tabs interact in the spec's hardest corner cases] → Implement the reference algorithm literally; spec examples are the arbiter, not intuition.
- [Carried-over inline layer leaves some block-section examples failing (cells/headings render inline content)] → Expected: any block example whose failure is *solely* inline-caused stays xfailed with a note; block-caused failures must all flip.
- [Setext/tab BREAKING changes alter existing user content] → Documented in the proposal and PR; old behaviors were already marked `gfm_deviation` and listed as scheduled for removal.
- [Pyodide recursion depth with deeply nested containers] → The algorithm is iterative (explicit stack), not recursive; verified with a deep-nesting stress test.

## Migration Plan

Users affected by the three BREAKING items get compile-visible output changes (rendered HTML), not runtime errors. Migration notes in the PR: replace intentional `Title\n---`-as-`<hr>` with a blank line before `---`; add a space after heading `#`; fence-language classes now appear in output (CSS/highlighting may key on them).

## Open Questions

1. Table cell inline rendering lands with the carried-over inline layer first (limited), then improves in the inline rewrite — acceptable interim state? (Assumed yes.)
2. Whether list-body `{% for %}` detection should also accept task-list bodies (`- [ ] {{ item }}`) — decide during implementation; default: yes, treated as list bodies.
