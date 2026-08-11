## Why

Markdown-backed docs pages render code blocks inside the `.prose` typography preset. The paragraph above a code block carries a bottom margin (`var(--space-4)`), so the block has 1rem of space above it, but the block itself has no margin and the paragraph below has no top margin — leaving 0 space below. The spacing is asymmetric: code blocks visually collide with the following paragraph.

## What Changes

- Add a `.prose pre` rule in `prose.css` that sets `margin: var(--space-4) 0`, giving code blocks symmetric 1rem vertical spacing. Adjacent sibling margins collapse in CSS, so the space above stays 1rem (unchanged) and the space below becomes 1rem (fixed).
- Wrap the rules in `code-block.css` in `@layer components` so the layered `.prose pre` rule can override the unlayered `.code-block { margin: 0 }`. This also aligns `code-block.css` with `components.css`, the one remaining stylesheet outside the layer system.
- Update the `markdown-document` spec's prose-preset coverage list to include code blocks.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `markdown-document`: the "prose typography preset stylesheet" requirement changes from covering headings, paragraphs, lists, tables, blockquotes, horizontal rules, and inline code to also covering code blocks with symmetric vertical spacing.

## Impact

- **Code**: `packages/webcompy/src/webcompy/ui/_styles/prose.css` (new `.prose pre` rule), `packages/webcompy/src/webcompy/ui/_styles/code-block.css` (wrap in `@layer components`).
- **Specs**: `markdown-document` (one modified requirement).
- **Tests**: `tests/test_ui_styles.py` extended to assert the `.prose pre` rule and the `components` layer wrapper. Existing assertions are unaffected.
- **No impact** on the docs site, the markdown pipeline, or any package other than the framework stylesheets. The `.prose` scope keeps the change opt-in to Markdown document pages.

## Known Issues Addressed

None.

## Non-goals

- No change to the spacing of code blocks outside `.prose` (e.g., demo cards using `CodeBlock` directly) — the `.prose` scope deliberately limits the fix to Markdown document pages.
- No change to the `markdown-document` pipeline or `render_markdown`.
- No change to the `tokens.css` spacing scale (`var(--space-4)` is reused, not redefined).