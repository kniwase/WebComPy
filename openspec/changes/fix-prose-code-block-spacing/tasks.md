# Tasks: fix-prose-code-block-spacing

## 1. Framework Styles

- [x] 1.1 Wrap all rules in `packages/webcompy/src/webcompy/ui/_styles/code-block.css` in `@layer components { ... }` (`.code-block`, `.code-block code`, `.tok-*`, and the `@scope (.code-block)` block), keeping existing declarations and values unchanged
- [x] 1.2 Add a `.prose pre { margin: var(--space-4) 0; }` rule inside `@layer prose` in `packages/webcompy/src/webcompy/ui/_styles/prose.css`, placed after the `.prose p` rule

## 2. Tests

- [x] 2.1 Extend `tests/test_ui_styles.py` to assert `code-block.css` is wrapped in `@layer components` and `prose.css` contains the `.prose pre` rule with `margin: var(--space-4) 0`

## 3. Verification

- [x] 3.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run python -m pytest tests/ --tb=short`
- [x] 3.2 Run `python3 scripts/check-doc-spec-refs.py`
- [x] 3.3 Run `scripts/run-e2e-tests.sh docs-documents` (both serving modes)
- [x] 3.4 Run `openspec validate fix-prose-code-block-spacing --strict`