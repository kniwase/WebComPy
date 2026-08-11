# Design: fix-prose-code-block-spacing

## Context

Markdown-backed docs pages (docs_app `/documents/*`) render code blocks through `docs_page_template` -> `<article class="prose">`. The `prose.css` typography preset styles paragraphs with `margin: 0 0 var(--space-4)` (1rem bottom), so a code block preceded by a paragraph has 1rem above it. The code block itself is `<pre class="code-block">` with `margin: 0` (from `code-block.css`), and the following paragraph has no top margin — leaving 0 space below. The result is asymmetric vertical spacing: the block visually collides with the paragraph underneath.

The root cause is twofold:
1. `.code-block` hard-codes `margin: 0` in `code-block.css`, which sits **outside** the `@layer` system declared in `index.css` (`@layer reset, tokens, components, webcompy-scope;`). Because unlayered rules beat layered rules in CSS cascade, a `.prose pre` rule inside `@layer prose` cannot override it.
2. `prose.css` has no rule touching `pre` margins at all.

## Goals / Non-Goals

**Goals:**

- Code blocks inside `.prose` get symmetric 1rem vertical spacing (above and below).
- The fix is scoped to `.prose`, so Markdown document pages are affected and nothing else.
- `code-block.css` aligns with the framework's layer system.

**Non-Goals:**

- No change to code blocks outside `.prose` (e.g., demo cards using `CodeBlock` directly) — they keep `margin: 0`.
- No change to the spacing scale; `var(--space-4)` (1rem) is reused.
- No change to the markdown pipeline, `render_markdown`, or `docs_app`.

## Decisions

### 1. Add `.prose pre { margin: var(--space-4) 0; }` in `prose.css`

The paragraph above a code block already supplies 1rem of space via its `margin-bottom`. Adding the same amount as the code block's own top margin produces **no additional space above** because adjacent sibling margins collapse in CSS (1rem + 1rem collapses to 1rem). The bottom margin newly supplies 1rem below the block, fixing the asymmetry.

Alternatives considered:
- **`.prose .code-block { margin: var(--space-4) 0; }`** — same effect, but the element selector `.prose pre` matches the actual `<pre>` element and is consistent with the existing `.prose pre code` rule in `prose.css`.
- **`.prose pre + p { margin-top: var(--space-4); }`** — breaks when the element after the code block is not a `<p>` (e.g., a heading or list); rejected.
- **Change `.code-block { margin: 0 }` to `margin: var(--space-4) 0` globally** — affects code blocks outside `.prose` (demo cards); rejected for scope.

### 2. Wrap `code-block.css` rules in `@layer components`

CSS cascade gives unlayered rules higher priority than layered rules, so the layered `.prose pre` rule cannot beat the unlayered `.code-block { margin: 0 }`. Wrapping `code-block.css` in `@layer components` moves it under the same layer as `components.css` (which already declares `@layer components`), so the later-declared `@layer prose` wins. This also fixes the one stylesheet that was left outside the layer system.

Alternatives considered:
- **Unlayered `.prose .code-block { margin: var(--space-4) 0; }` in `code-block.css`** — works (higher specificity beats the unlayered `.code-block`), but mixes a prose-specific rule into `code-block.css` and leaves the layer inconsistency; rejected.
- **`!important`** — rejected as a hack.

### 3. Keep the margin at `var(--space-4)` (1rem)

The existing paragraph bottom margin defines the reference spacing. Reusing the token keeps the preset consistent with the rest of `prose.css` and the theme.

## Risks / Trade-offs

- [Margin collapsing assumptions (top space stays 1rem)] → Vertical margin collapsing between adjacent block siblings is well-specified CSS behavior; the paragraph and code block are direct block children of `.prose` with nothing between them, so the collapse applies. Verified by unit-testing the rule presence and visually confirmed via docs E2E.
- [`@layer components` wrapping changes cascade priority for other `code-block.css` rules] → `syntax-theme.css` (unlayered) sets the same background/token colors, so no visual change; `@scope` and `.tok-*` rules move into the layer with identical values. Unit tests assert the wrapper and scope remain present.
- [Prose-only scope misses code blocks outside `.prose`] → Deliberate non-goal; the proposal scopes the fix to Markdown document pages.

## Migration Plan

Single branch, no data migration. Rollback = revert the merge commit; the change is purely additive CSS.

## Open Questions

None.