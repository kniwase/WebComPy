# Design: Hydration Split-Text Coalescing

## Context

See `proposal.md` for motivation and observed failure mode. On the browser hydration path, both `ElementWithChildren._hydrate_node` (`packages/webcompy/src/webcompy/elements/types/_base.py`) and `DynamicElement._hydrate_node` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py`) invoke `_normalize_hydration_text_runs(children, parent_node, start_idx, component_id)` before per-child adoption assigns or uses `_node_idx`.

Previously, `_normalize_hydration_text_runs` targeted only the **N element children -> 1 DOM `#text` node** direction (HTML parser text merging) and explicitly skipped single non-empty text children (`len(run) == 1 and parts[0] != ""`), while `_normalize_text_run` compared only `parent_node.childNodes[dom_idx].textContent` against `"".join(parts)`. When an external pre-hydration script splits one SSR `#text` node into `k >= 2` adjacent DOM `#text` nodes (e.g. Cloudflare `email-decode.min.js` substituting `document.createTextNode(...)` for `<a class="__cf_email__">`), neither branch reconciled the DOM back to element-tree granularity.

## Goals / Non-Goals

**Goals:**
- Coalesce `k >= 2` consecutive DOM `#text` nodes into a single `#text` node whenever their concatenated `textContent` matches the expected text of the single `TextElement` or multi-`TextElement` run at `dom_idx`.
- Preserve `__webcompy_prerendered_node__` across coalesced `#text` nodes whenever any coalesced node carried that flag.
- Keep the existing `_text_run_matches_dom` fast path and single-node mismatch reporting unchanged when no split coalescing applies.

**Non-Goals:**
- Detecting or repairing single-node replacements (`k == 1`) where an unmarked `#text` node replaced an entire prerendered `#text` node with no remaining prerendered `#text` sibling.
- Adding proxy/CDN-specific HTML directives (`<!--email_off-->`) or attribute parsing to core packages or SSG/SSR HTML output.

## Decisions

### D1 — General text coalescing at normalization time rather than CDN-specific SSR directives or `email_off` emission
Coalescing consecutive DOM `#text` nodes during `_normalize_hydration_text_runs` handles any compliant external pre-hydration DOM mutation that leaves contiguous `#text` siblings totaling the expected string, without encoding Cloudflare-specific assumptions or directives into `webcompy-server` or `webcompy`.

*Alternatives considered*:
- Wrapping `CodeBlock` or `<code>` HTML output in `<!--email_off-->...<!--/email_off-->` inside core packages: couples framework SSR output to one CDN vendor and does not help other pre-hydration DOM text mutations (browser extensions, translation scripts, script decoders). Rejected.
- Adding `docs_app`-only `<!--email_off-->` injection: `WebComPyPlugin`, `WebComPyBuildConfig`, `webcompy.elements`, and `CodeBlock` (`openspec/specs/code-block/spec.md`) provide no clean comment-node or HTML post-processing hook without either extending core APIs or bypassing private element internals. Out of scope for framework fix.

### D2 — Collect maximal contiguous `#text` slice only outside matched prefix and coalesce strictly on exact concatenated equality
Introduce two small private helpers in `packages/webcompy/src/webcompy/elements/types/_base.py`:
- `_collect_consecutive_text_nodes(parent_node, dom_idx)`: collects contiguous DOM children starting at `dom_idx` whose `nodeName.lower() == "#text"`.
- `_coalesce_text_nodes(text_nodes, merged_text)`: if `len(text_nodes) > 1`, computes `was_prerendered = any(getattr(n, "__webcompy_prerendered_node__", False) for n in text_nodes)`, assigns `primary.textContent = merged_text` on `text_nodes[0]`, restores `primary.__webcompy_prerendered_node__ = True` if `was_prerendered`, and calls `extra.remove()` in reverse order on `text_nodes[1:]`.

In `_normalize_hydration_text_runs`, for `len(run) == 1 and parts[0] != ""`, check `dom_idx` and only call `_coalesce_text_nodes` when `len(text_nodes) > 1` AND the joined text strictly equals `parts[0]`. If there are `<= 1` `#text` nodes or the joined text mismatches, leave `text_nodes` untouched so `TextElement._hydrate_node` reports mismatches identically to prior behavior.

In `_normalize_text_run`, `_text_run_matches_dom` continues to run first; when prefix nodes already align 1:1, the fast path returns before `_collect_consecutive_text_nodes` runs, so trailing stray `#text` nodes are never touched or merged into a matched run. Otherwise, `_collect_consecutive_text_nodes` gathers contiguous `#text` nodes, verifies `joined == expected`, coalesces if `len(text_nodes) > 1`, and splits via the existing UTF-16 `splitText` loop.

*Rationale*: Strict equality gating ensures stale/unexpected DOM content never hides a genuine hydration mismatch behind coalescing. Stopping at the first non-`#text` sibling prevents coalescing across adjacent element boundaries and preserves sibling `_node_idx` alignment.

*Alternatives considered*:
- Teaching `ElementWithChildren._hydrate_node` / `TextElement` to skip or accumulate `#text` nodes dynamically during per-child adoption: spreads cursor complexity across `_base.py`, `_dynamic.py`, and `_text.py`, whereas normalizing DOM `childNodes` upfront in `_normalize_hydration_text_runs` preserves the unified 1:1 `_node_idx` invariant relied upon by all child elements.

### D3 — Preserve `__webcompy_prerendered_node__` only across `k >= 2` coalesced siblings
When `email-decode.min.js` replaces `<a class="__cf_email__">` with `document.createTextNode(...)`, even the first segment may lack `__webcompy_prerendered_node__` if the email appeared at index 0 of the text node (e.g., `[#text('you@example.com'), #text('"')]`). Propagating `any(getattr(n, "__webcompy_prerendered_node__", False) for n in text_nodes)` across the coalesced `k >= 2` slice preserves adoption eligibility without loosening single-node (`k == 1`) prerendered identity checks on `TextElement._init_node`.

*Trade-off*: Unquoted standalone text completely replaced into a single unmarked `#text` node still records a mismatch and recreates the node; intentionally accepted as a non-goal to keep `__webcompy_prerendered_node__` semantics strict.

## Risks / Trade-offs

- **Sibling count in mixed stray-text mismatch cases**: `[Mismatched]` On a non-matching multi-node run with an unexpected extra adjacent `#text` node (e.g. `expected = "ab"`, DOM `[#text("xy"), #text("z")]`), the recorded `text` mismatch's `actual` reflects the concatenated DOM run (`"xyz"`) rather than only node 0 (`"xy"`). Normalization still halts without coalescing or splitting, which accurately reflects the unexpected text run present at that DOM slot.
- **Unquoted standalone email text**: [Limitation] A single `TextElement` with no surrounding text characters whose entire `#text` content is replaced by an unmarked `#text` node remains un-coalesced (Non-goal D3); verified `docs_app` `/sample/ui-form-controls/` uses quoted `"you@example.com"`.
