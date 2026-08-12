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

CSS cascade gives unlayered rules higher priority than layered rules, so the layered `.prose pre` rule cannot beat the unlayered `.code-block { margin: 0 }`. Wrapping `code-block.css` in `@layer components` moves it under the same layer as `components.css` (which already declares `@layer components`), so the `@layer prose` rule wins as long as `prose` is ordered after `components`. This also fixes the one stylesheet that was left outside the layer system.

Alternatives considered:
- **Unlayered `.prose .code-block { margin: var(--space-4) 0; }` in `code-block.css`** — works (higher specificity beats the unlayered `.code-block`), but mixes a prose-specific rule into `code-block.css` and leaves the layer inconsistency; rejected.
- **`!important`** — rejected as a hack.

### 3. Keep the margin at `var(--space-4)` (1rem)

The existing paragraph bottom margin defines the reference spacing. Reusing the token keeps the preset consistent with the rest of `prose.css` and the theme.

### 4. Declare the cascade layer order in `prose.css`

The cascade layer order is defined by the order in which layer names **first appear** in the document (CSS Cascade 5 §6.4.3), not by the order in which the stylesheets are served. In the generated HTML head, the app's `set_head` links (including `prose.css`) are inserted immediately after `<head>` (`webcompy-server/_html.py`), so `prose.css` is fetched and parsed **before** `index.css`. If `prose.css` only contains `@layer prose { ... }`, then `prose` is the first layer declared and `components` (declared later by `index.css`) wins — the exact opposite of what the fix needs.

To make the ordering robust regardless of load order, `prose.css` declares the full layer order up front, before its `@layer prose { ... }` block:

```css
@layer reset, tokens, components, prose, webcompy-scope;

@layer prose {
  ...
}
```

With this statement, `prose` is guaranteed to be ordered **after** `components`, so `.prose pre` wins over `.code-block { margin: 0 }` regardless of stylesheet load order. Verified in Chromium via Playwright for both load orders (`prose.css` first and `index.css` first): the computed `pre` margin-top is 1rem in both cases.

The position of `prose` relative to `webcompy-scope` is **not** guaranteed by this statement and depends on whether `webcompy-scope` was declared earlier in the document. CSS Cascade 5 §6.4.3 fixes the layer order by the **first occurrence** of each layer name; a layer name that first appears in a later `@layer` statement is appended at the **end** of the existing layer order. The framework's SSR head generation emits scoped component styles (`<style data-webcompy-cid>`, wrapped in `@layer webcompy-scope`) before the app's `set_head` links (`get_head_content_html()` in `webcompy/elements/_head.py`), so on SSR-rendered pages with scoped styles — including docs_app — `webcompy-scope` is declared before `prose.css` is parsed. The resulting layer order is `[webcompy-scope, reset, tokens, components, prose]`: `prose` comes **after** `webcompy-scope`, so app scoped styles cannot override `.prose pre` on those pages. On pages where `prose.css`'s statement is the first layer declaration (e.g., pure client-side rendering, where scoped styles are appended to `<head>` only after the stylesheet links), the order is `[reset, tokens, components, prose, webcompy-scope]` and scoped styles retain the ability to override the preset. Both outcomes were verified in Chromium via Playwright; the margin fix itself holds in every ordering.

Alternatives considered:
- **Add `prose` to the `@layer` statement in `index.css`** — ineffective when `prose.css` loads first, because the layer order is fixed by the first occurrence of each layer name; the `index.css` statement cannot reorder an already-declared `prose`. Verified in Chromium (margin stays 0px); rejected.
- **Reorder the head so `index.css` loads before the app's `set_head` links** — a framework-wide change to `webcompy-server/_html.py` affecting every application's stylesheet order; out of scope for this fix. Rejected.

## Risks / Trade-offs

- [Margin collapsing assumptions (top space stays 1rem)] → Vertical margin collapsing between adjacent block siblings is well-specified CSS behavior; the paragraph and code block are direct block children of `.prose` with nothing between them, so the collapse applies. Verified by unit-testing the rule presence and confirmed in Chromium via Playwright (the visual gap between the paragraph and the code block computes to 1rem, not 2rem).
- [`@layer components` wrapping changes cascade priority for other `code-block.css` rules] → `syntax-theme.css` (unlayered) sets the same background/token colors, so no visual change; `@scope` and `.tok-*` rules move into the layer with identical values. Unit tests assert the wrapper and scope remain present.
- [Layer order depends on `prose` being declared after `components`] → The layer-order statement at the top of `prose.css` guarantees `prose` is ordered after `components` regardless of stylesheet load order, so the margin fix holds in every ordering (verified in Chromium via Playwright). The statement does NOT guarantee `prose` is ordered before `webcompy-scope`: on SSR-rendered pages with scoped styles (scoped styles are emitted before the `prose.css` link; docs_app is such a page), `prose` is appended after `webcompy-scope` and scoped component styles lose to `.prose pre`. No docs_app scoped style targets `pre`/`code` inside `.prose`, so there is no visible regression; the loss of the "scoped styles can override the preset" property on those pages is an accepted trade-off. A framework-level fix (declaring the layer order before scoped styles are emitted) would be a separate change, tracked as a known issue.
- [Prose-only scope misses code blocks outside `.prose`] → Deliberate non-goal; the proposal scopes the fix to Markdown document pages.

## Migration Plan

Single branch, no data migration. Rollback = revert the merge commit; the change is purely additive CSS.

## Open Questions

None.