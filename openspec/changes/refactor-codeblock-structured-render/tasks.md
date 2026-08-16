# Tasks: Refactor CodeBlock to Structured Token Rendering

## 1. Shared Tokenization Foundation (`_highlight.py`)

- [ ] 1.1 Add private `_token_span_classes(token_type) -> str` composing the semantic `tok-{type}` class and the Pygments short class (empty when none), reusing `PYGMENTS_SHORT_CLASS`
- [ ] 1.2 Add private `_tokenize_with_fallback(code, lang) -> list[Token]` implementing empty-code (`[]`), unknown-language, and no-token fallback (`[Token(IDENTIFIER, code)]`) semantics; keep `LexerNotFoundError` handling inside the helper
- [ ] 1.3 Rebuild `highlight()` and `_render_token()` on the new helpers so the public HTML output is byte-identical; run `tests/test_code_block_highlight.py` and `tests/test_code_block_lexers.py` to confirm no output change

## 2. Structured Component Rendering (`_component.py`)

- [ ] 2.1 Static branch: replace `raw_html(highlight(...))` with per-token `create_element("span", {"class": _token_span_classes(...)}, token.value)` children directly under the `code` element; drop the wrapper span
- [ ] 2.2 Reactive branch: replace the `use_computed(lambda: highlight(...))` raw-HTML signal with `use_computed(lambda: _tokenize_with_fallback(...))` and render the token list via `repeat(..., lambda token: span(...))`
- [ ] 2.3 Empty-code and fallback paths: confirm the component renders no children for empty code and a single `tok-ident` span for unknown languages/no tokens (per delta spec scenarios)

## 3. Component Unit Tests

- [ ] 3.1 Rewrite `tests/test_code_block_component.py` to assert the structured child shape (span elements with expected classes as `code` children, no wrapper, text as text nodes) for static, reactive, fallback, and empty cases
- [ ] 3.2 Add unit coverage that class strings match the public `highlight()` output span-for-span (guard against drift between the two renderers)

## 4. Docs Maintenance (AGENTS.md Spec References)

- [ ] 4.1 Add `code-block` and `syntax-highlight-lexers` rows to the Current Specs list in `AGENTS.md`
- [ ] 4.2 Add a File→Spec mapping row for `webcompy/ui/code_block/` pointing to `code-block/spec.md` and `syntax-highlight-lexers/spec.md`
- [ ] 4.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 5. Verification

- [ ] 5.1 Run `uv run ruff check .` and `uv run ruff format --check .`; fix findings
- [ ] 5.2 Run `uv run pyright`; fix findings
- [ ] 5.3 Run `uv run python -m pytest tests/ --tb=short` and confirm the full unit suite passes
- [ ] 5.4 Run an SSG smoke build (`webcompy generate` on docs_app) and verify code blocks render with direct token spans and no wrapper element in the generated HTML
- [ ] 5.5 Run the E2E docs groups (`scripts/run-e2e-tests.sh docs-documents docs-home`) plus the template group (`template`) in prod and static modes; confirm no regressions and no new console warnings
- [ ] 5.6 If change `fix-hydration-adopt-and-render` is merged into the base branch, run the browser measurement script and confirm prerendered token spans survive hydration (alive count includes all `tok-*` spans); otherwise record the check as deferred with the dependency noted
- [ ] 5.7 Compare SSG HTML size for a code-heavy docs page before/after to quantify the D6 payload delta; record the result in design.md
- [ ] 5.8 Run `openspec validate refactor-codeblock-structured-render --strict` and confirm the change artifacts are valid
