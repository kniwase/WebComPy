# Proposal: fix-teleport-anchor-layout-shift

## Why

The Teleport SSR anchor — a zero-width-space (`\u200b`) text node serialized at the teleport's logical position — participates in CSS layout. When the anchor follows a block-level sibling (e.g. `docs_app`'s navbar dropdown `<li>`, whose `<a>` is `display: block`), the zero-width space wraps onto its own line box and adds one full line height (≈24px with the global `line-height: 1.5`) to the element. On initial page load this makes the navbar taller than intended (the centered Home link appears to drop down and the bar extends downward); after hydration, the adopted anchor's text is cleared and the layout snaps back. The docs site's transparent content-mode loading screen exposes the broken state for the entire boot duration.

The zero-width-space text anchor was chosen so the anchor slot survives HTML parsing, but a comment node achieves the same goal without creating any layout box, and additionally prevents the text-merge case (HTML parsers never merge text runs across a comment), simplifying hydration recovery semantics.

## What Changes

- **Comment-node anchor**: the Teleport anchor SHALL be a comment node with the fixed data `webcompy-teleport-anchor` instead of a zero-width-space text node, in both SSR output (`<!--webcompy-teleport-anchor-->`) and browser-created anchors (`document.createComment`).
- **Hydration adoption for comment anchors**: `TeleportElement` hydration matching and adoption SHALL recognize and adopt the prerendered comment node at the logical position (index-based), keeping the marker data intact.
- **Text-adjacent semantics simplified**: because comment nodes break text runs during HTML parsing, adjacent bare text siblings no longer merge around the anchor; the merge-recovery scenario is removed and replaced with the guarantee that text/comment/text order survives parsing unchanged.
- **`DOMPort.create_comment(data)`**: the `DOMPort` ABC SHALL gain a `create_comment` method implemented by the browser port (raw `document.createComment`), the server port (`VirtualDOMNode` comment node), and the testing fake.
- **Server virtual-DOM comment support**: `VirtualDOMNode` SHALL support comment nodes (`nodeType == 8`, `nodeName == "#comment"`), and the server HTML serializer SHALL emit them as `<!--data-->`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `teleport`: the SSR anchor representation changes from a zero-width-space text node to a comment node; the text-adjacent merge-recovery requirement is replaced with parse-stable ordering semantics.
- `virtual-dom`: the server virtual DOM gains comment-node creation and HTML serialization support.
- `port-abstraction`: the `DOMPort` contract gains `create_comment()`, with parity across browser, server, and testing implementations.

## Known Issues Addressed

- On initial load, SSR pages containing a Teleport after a block-level sibling (e.g. `docs_app` navbar dropdowns) render with an extra line box from the zero-width-space anchor, making the navbar taller until hydration clears the anchor text (visible layout shift: the Home link appears to drop down and the navbar extends downward).

## Non-goals

- Changing the one-anchor-node accounting model or the anchor-only SSR policy — only the anchor node kind (and its serialization/matching) changes.
- Emitting teleported children during SSR — teleported content remains absent from SSR HTML.
- CSS-based workarounds in `docs_app` (e.g. `font-size: 0` on dropdown list items) — the root cause lives in the framework and is fixed there.
- Inline rendering fallback, shared-target ordering, and other existing Teleport behaviors remain untouched.

## Impact

- **Code**: `webcompy/elements/types/_teleport.py` (anchor creation, matching, adoption), `webcompy/ports/_dom.py` (ABC), `webcompy/ports/_browser/_dom.py` (browser impl), `webcompy_server/ports/_dom.py` (server impl + serializer), `webcompy_server/ports/_virtual_dom.py` (comment node support), `webcompy_testing/_ports.py` (fake impl).
- **Apps**: no app code changes; `docs_app` navbar benefits directly from the fixed anchor representation.
- **APIs**: additive only — new `DOMPort.create_comment()`. The `\u200b` anchor is an internal SSR serialization detail, not a public API; no breaking change for app code.
- **Specs**: 3 modified capabilities (see above).
- **Tests**: update `tests/test_teleport.py` anchor fixtures/assertions and the fake HTML parser (comment support); add a regression test asserting the navbar-context anchor emits a comment (no `\u200b`); add an E2E docs-home assertion that dropdown list items have the same height as plain items immediately after `domcontentloaded` (pre-hydration).
