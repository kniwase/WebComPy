# Proposal: fix-dynamic-child-node-index

## Why

Dynamic container elements (`DynamicElement`, `RepeatElement`, `SwitchElement`, `SuspenseElement`, `ClientOnlyElement`, `MarkdownForElement`, and `ElementBase`) assign each child's `_node_idx` as `self._node_idx + c_idx` — the child's **position index** in the children list — instead of the **cumulative node offset** (sum of preceding siblings' `_node_count`). For single-node children the two are identical, so the defect is invisible. For multi-node children (`FragmentElement`, produced by any multi-line template body with whitespace text nodes), later children are positioned at wrong DOM indices, causing rendered nodes to be lost or misplaced: a reactive `{% for %}` with a multi-line body renders only its last item's element after a refresh, and a multi-element `{% if %}` branch misbehaves. This blocks idiomatic multi-line template bodies in reactive control flow and was found while verifying `feat-template-expression-language`.

## What Changes

- Replace index-based `_node_idx` assignment with cumulative node-offset assignment in all 12 sites across 7 files:
  - `elements/types/_base.py` (`ElementBase._render`)
  - `elements/types/_dynamic.py` (`DynamicElement._render`)
  - `elements/types/_client_only.py` (`ClientOnlyElement._hydrate_node`)
  - `elements/types/_switch.py` (`SwitchElement._render`, `SwitchElement._refresh` ×2)
  - `elements/types/_repeat.py` (`RepeatElement._refresh` regenerate path, `RepeatElement._reconcile_children`)
  - `elements/types/_suspense.py` (`SuspenseElement` ×2)
  - `template/_markdown_for.py` (`MarkdownForElement._render`, `MarkdownForElement._refresh`)
- Add regression tests pinning multi-node-child positioning for reactive `{% for %}` (initial render and post-mutation refresh), multi-element `{% if %}` branch toggling, and keyed reconciliation with fragment children.

No public API changes. Behavior is unchanged for single-node children (index and cumulative offset coincide).

## Capabilities

### New Capabilities

### Modified Capabilities

- `elements`: Add a normative requirement pinning cumulative child node indexing in dynamic containers, with regression scenarios for multi-node (`FragmentElement`) children in repeat/switch render and refresh paths.

## Known Issues Addressed

- **Multi-line template body + reactive control flow loses DOM nodes** (discovered during `feat-template-expression-language` verification): `{% for %}`/`{% if %}` whose bodies produce `FragmentElement` children render only the last fragment's elements after a refresh (and in `TestRenderer` even on initial render), because fragment children receive overlapping `_node_idx` values.

## Non-goals

- Changes to the key-based reconciliation algorithm itself (key matching, reuse semantics).
- Changes to hydration/adopt behavior (`_hydrate_node` already uses cumulative indexing and is untouched except `ClientOnlyElement`, which uses the buggy pattern).
- Whitespace-text-node elimination from template binding (fragments with text nodes remain valid input; this change makes containers handle them correctly).
- Any public API or spec-level behavior change beyond pinning the corrected positioning.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/types/{_base,_dynamic,_client_only,_switch,_repeat,_suspense}.py` and `packages/webcompy/src/webcompy/template/_markdown_for.py` — 12 mechanical edits, each replacing enumerate-index assignment with a cumulative-offset loop (the pattern already used by `_re_index_children`, `_hydrate_node`, `_position_element_nodes`, and `_append_child`).
- **Specs**: `openspec/specs/elements/spec.md` (delta: one ADDED requirement).
- **Tests**: new regression tests in `tests/` (TestRenderer-based); full unit suite and full e2e suite re-run.
- **Risk**: low — for single-node children, cumulative offset equals child index, so existing behavior is preserved by construction; multi-node children previously produced broken DOM, so no working behavior depends on the current indexing.
