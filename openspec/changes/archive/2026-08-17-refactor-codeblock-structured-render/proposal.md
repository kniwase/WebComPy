# Proposal: Refactor CodeBlock to Structured Token Rendering

## Why

The `CodeBlock` component renders highlighted code as an opaque HTML string injected through `raw_html()`. Browser measurements on the docs app show that the syntax-highlight token spans are the last remaining category of prerendered DOM destroyed during hydration: 114 of 114 `tok-*` spans on the quickstart page and 229 of 229 on the home page are removed and recreated, because the framework re-applies `innerHTML` when adopting the raw-HTML wrapper even though the content already matches. The token spans also live outside the framework's element model: they cannot be adopted, diffed, reconciled, or diagnosed — the framework only ever sees one opaque string.

## What Changes

- `CodeBlock`'s static path renders token spans as a structured element tree: the `<code>` element's children become framework-managed `<span class="tok-{type} [pygments]">` elements whose text is assigned as text content (inherently escaped), replacing `raw_html(highlight(...))`.
- The intermediate raw-HTML wrapper `<span>` between `<code>` and the token spans is removed; token spans become direct children of `<code>`. Framework CSS is unaffected (verified: `code-block.css` and `tokens.css` target only `.code-block`, `.code-block code`, and `.tok-*` classes).
- `CodeBlock`'s reactive path re-tokenizes through `use_computed` producing a token list, rendered with `repeat` (positional reconciliation; a code change re-highlights the whole block anyway).
- Unknown-language and empty-tokenization fallbacks render a single structured `tok-ident` span with the escaped code (mirroring the public `highlight()` fallback classes).
- A private class-composition helper is extracted so the span class logic (`tok-{type}` + Pygments short class) is shared between the structured renderer and the public `highlight()` function, which keeps its HTML-string contract and output unchanged.
- SSR output shape changes only by dropping the wrapper span; the rendered HTML remains identical between SSR and CSR.
- The `syntax-highlight-lexers` spec requirement for Bash variable references is corrected to match the implementation and `code-block` spec: `$NAME` and `${NAME}` references are preserved verbatim in the token `value` (the spec currently claims the leading `$` and braces are stripped, which contradicts both the `BashLexer` implementation and the `code-block` spec). Spec-only correction; no lexer code changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `code-block`: `CodeBlock` component requirement — structured, framework-managed token spans rendered as direct children of `<code>`; no `raw_html` injection; reactive update via a reactive token list; structured fallback for unknown languages and empty input
- `syntax-highlight-lexers`: `BashLexer` variable-reference requirement — `$NAME` / `${NAME}` references SHALL be preserved verbatim in the token `value` (was: stripped to the bare name)

## Known Issues Addressed

- **Hydration token-span identity loss**: all prerendered highlight spans (114/114 on quickstart, 229/229 on home) are destroyed during hydration because the raw-HTML wrapper re-applies `innerHTML` on adoption. Structured spans adopt naturally like every other element.
- **Token content invisible to framework diagnostics**: with `raw_html`, no mismatch records or reconciliation can ever see individual tokens.
- **Duplicated escaping logic**: HTML escaping happens inside `_highlight.py`; structured rendering escapes structurally via text nodes, and the class composition is shared through one private helper.
- **Spec contradiction on Bash variable tokens**: `syntax-highlight-lexers/spec.md` required stripping `$` and braces from Bash variable references while `BashLexer`, `code-block/spec.md`, and `tests/test_code_block_lexers.py` all preserve them; the spec is corrected to match.

## Non-goals

- No public `tokenize(code, lang)` API: the lexer registry and `Token` API remain the public tokenization surface.
- No changes to the public `highlight()` function, its HTML-string contract, or its output.
- No changes to lexer implementations, `TokenType`, `Token`, the registry, or the Pygments adapter.
- No changes to CSS or theme styles.
- No changes to `RawHTMLElement` itself — the generic raw-HTML adoption fix belongs to change `fix-hydration-adopt-and-render`.

## Impact

- **Code**: `webcompy/ui/code_block/_component.py`, `webcompy/ui/code_block/_highlight.py`
- **Public API**: unchanged (`CodeBlock` props, `highlight()`, `TokenType`, `Token`, lexer registry keep their contracts)
- **DOM shape**: token spans move from inside a raw-HTML wrapper to direct children of `<code>` (wrapper removed). Downstream CSS targeting the wrapper would need updating; no framework CSS does.
- **Payload**: each token span becomes a serialized element (including `webcompy-cid` attributes in scoped-style contexts where applicable)
- **Tests**: `tests/test_code_block_component.py` rewritten to assert structured children; `tests/test_code_block_highlight.py` unchanged; E2E docs groups re-verified
- **Specs**: deltas for `code-block` and `syntax-highlight-lexers` (the latter is a spec-only correction of an existing contradiction)
- **Docs maintenance**: `AGENTS.md` Current Specs list and File→Spec mapping gain `code-block` and `syntax-highlight-lexers` rows (pre-existing omission discovered during this change); `scripts/check-doc-spec-refs.py` must pass
- **Dependency**: token-span identity verification during hydration depends on the adoption behavior of change `fix-hydration-adopt-and-render` (in flight). If this change lands first, the identity-preservation acceptance check is deferred until that change merges.
