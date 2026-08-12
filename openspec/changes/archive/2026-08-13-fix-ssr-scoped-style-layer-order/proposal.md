# Proposal: fix-ssr-scoped-style-layer-order

## Why

On SSR/SSG-generated pages, per-component scoped styles (`<style data-webcompy-cid>`, wrapped in `@layer webcompy-scope`) are emitted into `<head>` before the framework stylesheet links (`/_webcompy-ui/index.css`). Because CSS cascade layer priority is fixed by each layer name's first occurrence (CSS Cascade 5 §6.4.3), the layer order in SSR output becomes `[webcompy-scope, reset, tokens, components, prose]` — the exact reverse of the intended `[reset, tokens, components, prose, webcompy-scope]`. As a result, scoped styles lose to every layered framework rule on SSR pages (e.g., in docs_app, `.docs-pager a` renders in link color `#0969da` instead of the author's intended `var(--color-fg)`), while CSR pages behave correctly because runtime-injected styles land at the end of `<head>`.

This violates the css-architecture requirement that the layer-order declaration "SHALL appear before any rule that uses one of these layers", so this change is a bug fix that restores spec compliance and SSR/CSR parity — not a new behavior design.

## What Changes

- Split `HeadElement.get_head_content_html()` into two parts: head content (title, meta, `*[hidden]` utility rule, dynamic styles, app links) and scoped styles (`<style data-webcompy-cid>` / `<style data-webcompy-cid-rx>` elements).
- Change SSR HTML generation (`webcompy_server/_html.py`) to emit scoped style elements **after** the `/_webcompy-ui/index.css` stylesheet link, so the fixed `@layer reset, tokens, components, prose, webcompy-scope;` declaration is processed before any rule using those layers.
- Correct two factually wrong scenarios in the css-architecture spec: `components.css overrides scoped_style` (later layers win, so scoped styles — not components.css — win under the intended order; components.css is repositioned as framework-level defaults) and `Reset applies before component styles` (reset is the lowest-priority layer, not "higher-priority").
- Add an explicit css-architecture requirement that SSR/SSG output emits layered scoped style elements after the layer-order declaration.
- Update head-vdom spec to reflect the split head-content API.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `css-architecture`: Correct the wrong cascade-priority scenarios; add requirement that scoped style elements are emitted after the layer-order declaration in SSR/SSG output.
- `head-vdom`: `get_head_content_html()` is split into a head-content method and a scoped-styles method.

## Known Issues Addressed

- Element System known issue: "On SSR-rendered pages, scoped component styles ... are emitted before the framework stylesheet links, so `webcompy-scope` becomes the FIRST cascade layer and scoped styles lose to layered framework rules." This change resolves it by emission-order fix (the chosen approach differs from the inline-`@layer`-statement sketch in the issue text; see design.md for the tradeoff rationale).

## Non-goals

- No change to the fixed layer order itself (`reset, tokens, components, prose, webcompy-scope` stays).
- No change to CSR style injection (`HeadElement._render()` already appends at `<head>` end).
- No change to the content of `index.css`, `prose.css`, `components.css`, or any other shipped stylesheet.
- No change to hydration behavior (existing `<style>` elements are updated in place; positions are preserved).
- No change to dev-mode (non-prerendered) pages, which already get correct ordering via client-side injection.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/_head.py` (split `get_head_content_html()`), `packages/webcompy-server/src/webcompy_server/_html.py` (emit scoped styles after index.css link).
- **Specs**: `openspec/specs/css-architecture/spec.md` (2 scenario corrections + 1 new requirement), `openspec/specs/head-vdom/spec.md` (API description update).
- **Tests**: New unit assertions that `data-webcompy-cid` styles appear after the index.css link in generated HTML; existing scoped-CSS tests unaffected (layer wrapping itself unchanged).
- **Behavior**: SSR pages now match CSR — scoped styles win over reset/tokens/components/prose layers. Visual changes are expected only where pages implicitly relied on the buggy order (docs_app pager links render as authored). Verified via docs E2E group.
