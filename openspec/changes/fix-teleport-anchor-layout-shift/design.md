# Design: fix-teleport-anchor-layout-shift

## Context

`TeleportElement` renders a single static anchor at its logical position. Today the anchor is a text node: server-side rendering serializes it as the zero-width space `\u200b` so the slot survives HTML parsing, and the browser anchor is created as an empty text node. The zero-width space is invisible in width but not in height: when it follows a block-level sibling (e.g. `docs_app`'s navbar dropdown `<li>`, whose `<a>` is `display: block`), it wraps onto its own line box and adds one full line height (~24px under the global `line-height: 1.5`) to the element until hydration adopts the anchor and clears its text. See proposal.md — Why.

Key constraints that shape the approach:

- The anchor must survive HTML parsing as a distinct DOM node at its index position, or positional hydration adoption breaks (teleport spec, hydration-adopt-and-render contract).
- The anchor must contribute zero layout impact in the SSR HTML window (pre-hydration first paint) — this is the bug being fixed.
- `DOMPort` is the injectable node-creation abstraction; a new node kind requires method parity across browser, server, and testing-fake implementations.
- The server serializer (`ServerDOMPort.render_html`) and the server virtual DOM (`VirtualDOMNode`) currently support only elements and text nodes.

## Goals / Non-Goals

**Goals:**

- Replace the text-node anchor with a comment node carrying the fixed data `webcompy-teleport-anchor` in both SSR output and browser-created anchors, eliminating the layout shift.
- Keep the one-anchor accounting model, anchor-only SSR emission, and self-scheduled client render contract unchanged.
- Preserve (or simplify) hydration recovery semantics for anchors adjacent to bare text.

**Non-Goals:**

- Emitting teleported children during SSR.
- Introducing a general-purpose comment-element type into the element system; comment support exists only at the port/virtual-DOM level for the teleport anchor.
- CSS workarounds in `docs_app`.
- Changing shared-target ordering, inline fallback, or removal semantics.

## Decisions

### D1: Use a comment node, not a hidden element

**Decision**: The anchor becomes a comment node with fixed data `webcompy-teleport-anchor`, serialized as `<!--webcompy-teleport-anchor-->`.

**Alternatives considered**:

- *Hidden element (`<span hidden>`, `<i hidden>`)*: also layout-free, but `hidden` styling can be overridden by app CSS resets, it adds a persistent real element per teleport, and hydration matching changes by the same order of magnitude. Rejected.
- *CSS workaround in `docs_app` (`font-size: 0` on the dropdown `<li>`)*: fixes only the docs navbar; the framework hazard remains for every downstream app. Rejected as the primary fix.
- *Keeping the text anchor and accepting the layout box*: contradicts the bug report. Rejected.

Rationale: a comment is the only DOM node kind that is invisible in layout by definition, cannot be styled into visibility, survives HTML parsing as a distinct node, and is cheap (no attributes, no children). Comment nodes also break text runs during HTML parsing, which removes the text-merge recovery case (see D3).

### D2: Fixed marker data, identical in both environments

**Decision**: `_ANCHOR_TEXT = "\u200b"` becomes `_ANCHOR_DATA = "webcompy-teleport-anchor"`; `_create_node()` always calls `DOMPort.create_comment(_ANCHOR_DATA)`, removing the `ENVIRONMENT` conditional entirely.

The marker string contains no `--` sequence, keeping the serialized form valid HTML. Browser and server anchors carry identical data, so `_node_matches_existing()` checks `nodeName == "#comment"` plus exact data equality, and `_adopt_node()` keeps the data (comments do not render; retaining the marker aids debugging and does not affect layout). Matching remains index-based (`_get_existing_node()`); the marker makes the identity check precise.

### D3: Text-adjacent merge recovery is replaced by parse-stable ordering

**Decision**: The scenario where adjacent bare text runs merge around the anchor on parse is removed from the spec. Because comments break text runs, `[text, Teleport, text]` parses to three distinct nodes; hydration adopts the comment and each sibling in index order.

The existing defensive path in `_hydrate_node()` (existing node mismatch → remove/recreate anchor and schedule the teleport's own render) is kept unchanged: it still covers hand-edited DOM or future structural surprises, and remains exercised by the rewritten unit test. No new recovery logic is added.

### D4: `DOMPort.create_comment()` with three implementations

**Decision**: Add `create_comment(data: str) -> DOMNode` to the `DOMPort` ABC.

- **Browser** (`BrowserDOMPort`): `document.createComment(data)` — a standard web API; the `_raw.pyi` stub types `document` as `Any`, so no stub change is required (an optional `createComment` annotation can be added for tidiness).
- **Server** (`ServerDOMPort`): `VirtualDOMNode("#comment", node_type=8, text_content=data)`; `VirtualDOMNode.nodeName` gains a `node_type == 8 → "#comment"` branch; `textContent` getter/setter already handles non-element nodes through the existing else branch; `_serialize_node()` gains a `nodeType == 8 → <!--data-->` branch before the element branch (data is a fixed constant, so verbatim emission is safe).
- **Testing** (`FakeBrowserDOMPort`): inherits from `ServerDOMPort`; add an explicit `create_comment` alongside the existing `create_text_node` so the fake surfaces the same comment-node properties (`FakeDOMNode` extends `VirtualDOMNode`, so nodeType 8 support flows through).

### D5: Regression coverage at the unit and browser levels

**Decision**: Two layers of regression protection.

- **Unit (SSR string level)**: server-render a teleport placed after a block-level sibling (mirroring the navbar structure) and assert the output contains `<!--webcompy-teleport-anchor-->` and contains no `\u200b`. This is deterministic and fast.
- **E2E (layout level, `e2e/docs/test_home.py`)**: after `page.goto(url, wait_until="domcontentloaded")` — before Pyodide finishes booting — measure `offsetHeight` of the first `.navbar-item` (Home) and of the `.navbar-item-dropdown` list items and assert they are equal. Pre-fix, the dropdown items are ~24px taller in this window; post-fix they match. This is the only place a real browser layout engine can verify the visual regression.

## Risks / Trade-offs

- *Comment nodes and positional hydration indexing*: comments count as one child node; SSR structure and browser parse match 1:1, so sibling indices stay aligned. [Risk: a hand-written comment at a teleport position in app HTML] → Mitigation: the marker data check in `_node_matches_existing()` keeps adoption precise; framework-generated output contains no other comments.
- *HTML parsers in tests*: `_FakeDOMParser` (stdlib `HTMLParser`) currently ignores comments; the round-trip hydration tests would drop the anchor. → Mitigation: add `handle_comment` to the fake parser as part of the test updates (BeautifulSoup, used elsewhere, already preserves comments).
- *Serialization of arbitrary data*: `create_comment` is a public port method; data containing `--` would produce invalid HTML. → The teleport marker is a fixed constant and is the only caller; the spec scopes comment serialization to verbatim `<!--data-->`. Future callers must supply comment-safe data (documented in the port docstring).
- *Deployed static sites*: pages generated with the old `\u200b` anchor are served until the next deployment; no in-place migration exists. → Mitigation: static output is regenerated on every deploy (CI SSG), and the old anchor is an internal serialization detail with no persistence contract.

## Migration Plan

1. Ship the framework change (ports, virtual DOM, teleport anchor) with its unit tests in one change.
2. Add the E2E regression to `e2e/docs/test_home.py` in the same change.
3. `docs_app` regenerates automatically in CI; no app-level migration steps.
4. Rollback: revert the change commit — the previous ZWSP-anchor behavior is fully restored (no data migration, no forward-compat markers).

## Open Questions

(none)
