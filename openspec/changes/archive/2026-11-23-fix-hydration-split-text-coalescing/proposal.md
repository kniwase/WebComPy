# Proposal

## Why

Hydration text-run normalization currently handles the case where the HTML parser merges multiple adjacent `TextElement` children into fewer DOM `#text` nodes, but cannot recover when pre-hydration DOM transformations split a single expected `#text` node into multiple consecutive DOM `#text` nodes while preserving the same concatenated text content. In production behind CDNs/proxies such as Cloudflare Email Address Obfuscation (`email-decode.min.js` replacing `<a class="__cf_email__">` with `document.createTextNode(...)` between surrounding quotes), a single `TextElement` such as `'"you@example.com"'` becomes three consecutive `#text` nodes (`'"'`, `'you@example.com'`, `'"'`), causing index misalignment and spurious `text` and `node-count` hydration mismatch warnings (observed on `/sample/ui-form-controls/` for `CodeBlock` component `0047b9e5bb22cee8044a75daf772e131`).

## What Changes

- Extend hydration text-run normalization in `packages/webcompy/src/webcompy/elements/types/_base.py` so consecutive DOM `#text` nodes at a `TextElement` or `TextElement`-run position are coalesced into a single `#text` node whenever there are two or more consecutive `#text` nodes whose concatenated text matches the expected text of the single element or run.
- Preserve `__webcompy_prerendered_node__` across coalescing when any node in the coalesced DOM `#text` slice carried that marker, so decoded substring nodes replaced by external pre-hydration scripts do not block adoption of the coalesced node.
- Preserve existing fast paths (`_text_run_matches_dom` returning without DOM writes or removals when children already align 1:1) and existing mismatch reporting when concatenated `#text` content differs from expected text.
- Add unit tests in `tests/test_hydration_text_merge.py` covering single-element coalescing, trailing/leading non-prerendered split segments, mismatched split segments, multi-`TextElement` coalescing + re-splitting, trailing stray text-node preservation on the fast path, and sibling alignment.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `elements`: extend the hydration text-node normalization requirement (`Hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption`) to also coalesce multiple consecutive DOM `#text` nodes produced by pre-hydration DOM mutations when their concatenated text equals the run's expected text, preserving prerendered status across the coalesced run and keeping idempotent 1:1 DOM runs untouched.

## Impact

- **Affected code**: `packages/webcompy/src/webcompy/elements/types/_base.py` (`_collect_consecutive_text_nodes`, `_coalesce_text_nodes`, `_normalize_text_run`, `_normalize_hydration_text_runs`). Both `ElementWithChildren._hydrate_node` and `DynamicElement._hydrate_node` invoke `_normalize_hydration_text_runs` and benefit automatically.
- **Tests**: new unit tests in `tests/test_hydration_text_merge.py` (`TestHydrationSplitTextCoalescing`).
- **Specs**: delta spec in `openspec/specs/elements/spec.md`.
- **APIs/dependencies**: no public API changes, no new dependencies, and no server/CLI/build changes.
- **Risk**: low. Normalization runs strictly during browser hydration (`_hydrate_node`). When DOM nodes already correspond 1:1 to expected text nodes or when concatenated text differs from expected text, no coalescing occurs and existing mismatch reporting remains intact.

## Known Issues Addressed

- Resolves production hydration mismatch warnings observed on `/sample/ui-form-controls/` (`Hydration mismatches detected (2): node-count=1, text=1; components: 0047b9e5bb22cee8044a75daf772e131(2)`) where Cloudflare's `email-decode.min.js` splits a quoted email token inside `CodeBlock` (`<span class="tok-str s">"you@example.com"</span>`) into three consecutive `#text` nodes (`'"'`, `'you@example.com'`, `'"'`) before PyScript hydrates.
- No existing item in `openspec/config.yaml` tracks this behavior directly.

## Non-goals

- Adding Cloudflare-specific logic or HTML comment directives (e.g., `<!--email_off-->`) into the core framework or SSR HTML emitter.
- Changing `TextElement._init_node` / `ElementAbstract._hydrate_node` prerendered-marker rules for a standalone non-prerendered `#text` node when no split run exists (for example, an unquoted email substring replaced cleanly as a single unmarked `#text` node).
- Recovering when external scripts leave non-`#text` elements (such as unresolved `<a>` tags) in the DOM at hydration time.
- Modifying server rendering (`VirtualDOMNode`), `RawHTMLElement`, `_render`, reconciliation, or positioning code.
