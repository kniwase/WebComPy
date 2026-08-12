# Design: fix-ssr-scoped-style-layer-order

## Context

SSR/SSG HTML generation assembles `<head>` in `webcompy_server/_html.py` (`_generate_html_impl`):

1. The `<head>` element is built with `<base>`, color-scheme `<meta>`, the `/_webcompy-ui/index.css` link, `core.css` link, and scripts.
2. `HeadElement.get_head_content_html()` produces a single HTML string containing title, meta, the `*[hidden]` utility style, per-component scoped styles (`@layer webcompy-scope { ... }`), reactive scoped styles, dynamic styles, and app links.
3. That string is inserted immediately after `<head>` via `html_output.replace("<head>", ...)` — i.e., **before** the index.css link.

`index.css` begins with `@layer reset, tokens, components, prose, webcompy-scope;`. Since cascade layer priority is determined by each layer name's **first occurrence** in document order (CSS Cascade 5 §6.4.3), the scoped styles' `@layer webcompy-scope` block becomes the first declaration, fixing the layer order as `[webcompy-scope, reset, tokens, components, prose]` — the reverse of the design intent. Scoped styles therefore lose to every layered framework rule on SSR pages.

In CSR, `HeadElement._render()` appends scoped `<style>` elements via `head_el.appendChild(...)` — at the end of `<head>`, after all stylesheet links — so the intended order holds. Hydration updates existing elements in place and preserves their positions, so it is unaffected by the initial order bug.

## Goals / Non-Goals

**Goals:**

- SSR/SSG output declares the fixed layer order (via the index.css link) before any layered rule, restoring compliance with css-architecture ("The declaration SHALL appear before any rule that uses one of these layers").
- SSR and CSR produce the same effective cascade order; scoped styles win over reset/tokens/components/prose on both paths.
- Correct the factually wrong cascade-priority descriptions in css-architecture scenarios.

**Non-Goals:**

- Changing the fixed layer order or any shipped stylesheet content.
- Changing CSR injection, hydration reconciliation, or dev-mode behavior.
- Reordering anything else in `<head>` (app links, dynamic styles, core.css, scripts keep their current relative positions).

## Decisions

### Decision 1: Move scoped style emission after the index.css link (chosen)

Split `HeadElement.get_head_content_html()` into two methods:

- `get_head_content_html()` — title, meta, `*[hidden]` utility style, dynamic styles, app links (everything except scoped styles). Inserted after `<head>` as today.
- `get_scoped_styles_html()` — per-component `<style data-webcompy-cid>` and `<style data-webcompy-cid-rx>` elements only.

In `_generate_html_impl`, insert part B immediately after the index.css link by anchoring on its rendered HTML: `html_output.replace(index_css_link_html, index_css_link_html + "\n" + scoped_styles_html, 1)`. The link markup is deterministic (`<link rel="stylesheet" href="{base_url}_webcompy-ui/index.css"/>`), so the anchor is stable. This avoids passing raw unescaped HTML through the `_HtmlElement` tree (string children are escaped text nodes).

Resulting head order:

```
<head>
  ├─ part A: base / color-scheme meta ... title, meta, *[hidden], dynamic styles, app links
  ├─ <link index.css>      ← layer order declared here (full 5-layer statement)
  ├─ part B: scoped styles ← webcompy-scope is last = highest priority
  ├─ <link core.css> / scripts
```

Since `index.css` declares the complete 5-layer order including `prose`, apps that do not link `prose.css` still get the correct order, and apps that do link it (in part A, before index.css) get the same fixed order because prose.css declares the identical statement.

**Alternatives considered:**

| Option | Why rejected |
|---|---|
| Inline `@layer ...;` statement at top of `<head>` (sketched in the known-issue text) | Duplicates the layer list as a second source of truth that can drift from index.css; deciding whether to include `prose` creates SSR/CSR inconsistency risk. |
| Move the index.css link before all head content | Changes stylesheet order for every app page (broad blast radius); app links would move after framework CSS. |
| Drop `@layer` wrapping of scoped styles (back to unlayered) | Violates css-architecture ("All scoped component CSS IS layered"); unlayered scoped styles would beat dynamic app styles too. |
| Reorder layers so `webcompy-scope` precedes `components`/`prose` | Changes CSR behavior too; scoped styles could no longer override the prose preset, breaking the docs typography design. |
| Move style elements to `<head>` end during hydration | Layer order is fixed by first occurrence at parse time; pre-JS paint stays broken (FOUC), and DOM shuffling is hacky. |

### Decision 2: Position components.css as framework defaults; scoped styles win

Under the correct order, `webcompy-scope` (last) beats `components`. The css-architecture scenario claiming "components.css overrides scoped_style ... SHALL win" described the buggy SSR behavior as if it were the design (CSR already contradicts it today). We correct the spec: components.css provides framework-level default styles, and scoped styles — being author intent in the highest-priority layer — override them. Same for the reset scenario's inverted "higher-priority layer" wording.

## Risks / Trade-offs

- [SSR pages that implicitly relied on scoped styles losing to framework CSS will change appearance] → This is the bug being fixed (CSR already behaves this way). Verify with the docs E2E group, which covers pages with scoped styles (e.g., `.docs-pager a`).
- [String-anchor replace breaks if index.css link markup changes] → The link is rendered in the same function; keep the anchor construction adjacent to the link element definition so they evolve together. A unit test asserts scoped styles appear after the link, catching anchor drift.
- [Third-party tooling parsing `get_head_content_html()` output] → The method keeps its name and returns all non-scoped head content; scoped styles move to the new method. Only `_html.py` consumes these methods for SSG.

## Migration Plan

No runtime migration needed. Generated sites pick up the fix on their next `webcompy generate`. Rollback is a plain revert.

## Open Questions

None.
