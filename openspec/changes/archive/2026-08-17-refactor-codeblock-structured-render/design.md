# Design: Refactor CodeBlock to Structured Token Rendering

## Context

`CodeBlock` (see proposal.md — Why) currently renders highlight output as one `RawHTMLElement` inside `<code>`, i.e. `<code><span>{highlighted HTML}</span></code>`. Constraints shaping this design:

- `highlight(code, lang) -> str` is a public API whose HTML-string contract and output MUST NOT change (spec: code-block).
- `Token`, `TokenType`, and the lexer registry are already public and provide structured tokenization.
- The dual-class requirement (`tok-{type}` + Pygments short class) MUST keep producing identical class strings.
- `code-block.css` and `tokens.css` style only `.code-block`, `.code-block code`, and `.tok-*` classes — nothing references the raw-HTML wrapper span (verified).
- `repeat()` accepts `SignalBase[list[V]]`, so a computed token list can drive the reactive branch through the standard reconciliation path.

## Goals / Non-Goals

**Goals:**

- Token spans become framework-managed elements that hydrate, diff, and diagnose like every other element.
- One source of truth for span class composition shared by `highlight()` and the component.
- SSR and CSR render byte-identical HTML (existing scenario, now without the wrapper).

**Non-Goals:**

- No new public tokenization API (no public `tokenize()`).
- No change to `RawHTMLElement` behavior (that is the generic fix in `fix-hydration-adopt-and-render`).
- No keyed reconciliation for tokens; a code edit re-highlights the whole block.

## Decisions

### D1 — Static branch renders spans directly under `<code>`

Build one `create_element("span", {"class": _token_span_classes(token.type)}, token.value)` per token as direct children of the `code` element. Text is assigned as text content, so escaping is structural (no manual `html.escape`).

- Alternative considered: keep `raw_html` and rely on the generic `RawHTMLElement` adoption fix from `fix-hydration-adopt-and-render`. Rejected here: that fix preserves node identity but leaves tokens opaque to the framework — no reconciliation, no mismatch diagnostics, and the wrapper span remains. This change removes the opacity for CodeBlock specifically; the generic fix still lands separately for all other `raw_html` consumers.

### D2 — Private class-composition helper shared with `highlight()`

Extract a private `_token_span_classes(token_type: TokenType) -> str` in `_highlight.py` that joins the semantic class and the Pygments short class (empty when none). `_render_token` uses it for the HTML path; the component uses it for structured spans. `highlight()` output remains byte-identical (existing tests in `tests/test_code_block_highlight.py` guard this).

- Alternative considered: duplicating the class logic in the component. Rejected: class-string drift between the public API and the component would break Pygments compatibility.

### D3 — Reactive branch uses a computed token list + `repeat`

A private `_tokenize_with_fallback(code, lang) -> list[Token]` in `_highlight.py` implements the shared tokenization semantics: empty code → `[]`; unknown language or zero tokens → `[Token(IDENTIFIER, code)]` (which renders class `tok-ident` — identical to today's fallback span, because `IDENTIFIER` has no Pygments short class). The reactive branch computes `use_computed(lambda: _tokenize_with_fallback(code_signal.value, lang))` and renders `repeat(tokens, lambda token: span(...))` with positional reconciliation.

- `highlight()` itself is rebuilt on the same helper (`_render_tokens(_tokenize_with_fallback(...))`) — output byte-identical, verified by existing tests.
- Alternative considered: a computed returning a prebuilt fragment of spans, rendered through a dynamic child generator. Rejected: `repeat` gives per-span reconciliation and standard adoption semantics for free.

### D4 — Fallback and empty-input rendering

Unknown language / no tokens → single `tok-ident` span (D3 helper). Empty code → no children under `<code>`. Today empty code renders an empty wrapper `<span></span>`; the new shape is `<code></code>`, which is covered by a new scenario in the delta spec.

### D5 — DOM shape change and CSS safety

The wrapper span between `<code>` and the token spans is removed. Framework CSS has no selector for it (verified in Context). Downstream CSS targeting the wrapper would need updating; none exists in this repo.

### D6 — Serialized payload note

Token spans are now real serialized elements, so scoped-style contexts add `webcompy-cid-*` attributes to each span (as they already do for every other element in the docs pages). This grows the SSG payload versus innerHTML. Accepted: docs pages are dominated by prose, not code; the docs E2E runs will surface any significant regression.

**Measured (task 5.7)**: SSG output for the code-heavy pages grew by 21.2% (home, 52,612 → 63,755 bytes) and 11.4% (quickstart, 48,774 → 54,321 bytes). ~92% of the home delta (~10,305 of 11,134 bytes) is the `webcompy-cid-*` attribute on each of the 229 token spans (229 × 45 chars), which is the framework's existing scoped-CSS behavior applied to token spans that were previously opaque. The residual ~800 bytes is structural span serialization. Accepted as marginal: the delta is a one-time static file download, dominated by framework-standard attributes, and proportional to code density (the home page is an unusually code-heavy page).

### D7 — AGENTS.md spec-reference maintenance

`AGENTS.md` is missing the `code-block` and `syntax-highlight-lexers` specs from the Current Specs list and the File→Spec mapping table (`webcompy/ui/code_block/` has no row). This change adds those rows and runs `scripts/check-doc-spec-refs.py` as part of the change (per the Review Knowledge Maintenance rules), since it is the first change touching `webcompy/ui/code_block/` after the omission was discovered.

### D8 — Hydration adoption verification dependency

The acceptance check "prerendered token spans are adopted during hydration" (delta spec scenario) relies on the adoption behavior introduced by change `fix-hydration-adopt-and-render`, which is in flight and not merged into main. Task breakdown keeps the unit-level structure tests unconditional; the browser-level identity measurement is performed if that change has merged, otherwise recorded as deferred with the dependency noted.

### D9 — Spec-only correction of the Bash variable-reference contradiction

`openspec/specs/syntax-highlight-lexers/spec.md` requires `BashLexer` to strip the leading `$` (and braces) from `$NAME` / `${NAME}` references, but the implementation (`lexers/_bash.py` yields the full match verbatim), the `code-block` spec ("The `$` prefix is preserved in the token value so the rendered HTML faithfully displays the variable syntax"), and `tests/test_code_block_lexers.py` (asserts `$HOME` and `${PATH}`) all agree on preservation. This change corrects the `syntax-highlight-lexers` requirement to match — a spec-only fix with no lexer code changes, discovered while adding the AGENTS.md rows for this area (D7).

- Alternative considered: leaving the contradiction for a later change. Rejected: this is the first change to touch `webcompy/ui/code_block/` documentation, the user plans to sync and archive these specs, and the correction is confined to a single requirement paragraph plus its two scenarios.

## Risks / Trade-offs

- [Wrapper removal breaks downstream CSS] → No framework CSS references the wrapper; noted in proposal Impact. Fallback: re-add a plain wrapper `<span>` in the component without `raw_html` if a downstream report surfaces.
- [Payload growth from per-span serialization + `webcompy-cid` attributes] → Measure SSG output size for a docs page with many code blocks during verification; accept if marginal, otherwise revisit D6.
- [Reactive re-highlight cost on large code] → Positional `repeat` without keys; a code change rebuilds the whole token sequence anyway, and reactive code blocks in the demo/docs apps are small.
- [SSR/CSR HTML byte-identity] → Both sides build the same element tree from the same tokens; existing "identical between SSR and CSR" tests keep guarding it.

## Migration Plan

No data or configuration migration. Deployment is a framework release: SSG sites regenerate their HTML on next build (the only output change is the removed wrapper span). Rollback is a normal version revert; no persisted state is involved.

## Open Questions

(none)
